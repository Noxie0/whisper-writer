import os
import sys
import datetime
import time
import pyperclip
from audioplayer import AudioPlayer
from pynput.keyboard import Controller
from PyQt5.QtCore import QObject, QProcess, QThread, Qt, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QAction, QMessageBox,
    QDialog, QVBoxLayout, QLabel, QProgressBar,
)

_SRC_DIR  = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.dirname(_SRC_DIR)
_LOGS_DIR = os.path.join(_ROOT_DIR, 'logs')

def _asset(name):
    return os.path.join(_ROOT_DIR, 'assets', name)

from key_listener import KeyListener
from result_thread import ResultThread
from ui.main_window import MainWindow
from ui.settings_window import SettingsWindow, _log_hooks
from ui.status_window import StatusWindow
from transcription import create_local_model, _model_cached_locally
from input_simulation import InputSimulator
from utils import ConfigManager


class _Tee:
    """Write to both the original stream and the log file simultaneously."""
    def __init__(self, stream, log_file):
        self._stream = stream  # may be None (pythonw / no-console environment)
        self._log = log_file

    def write(self, data):
        if self._stream is not None:
            self._stream.write(data)
        try:
            self._log.write(data)
        except Exception:
            pass

    def flush(self):
        if self._stream is not None:
            self._stream.flush()
        try:
            self._log.flush()
        except Exception:
            pass

    def fileno(self):
        if self._stream is not None:
            return self._stream.fileno()
        raise OSError('underlying stream has no file descriptor')


class ModelLoaderThread(QThread):
    status = pyqtSignal(str)
    model_ready = pyqtSignal(object)
    load_error = pyqtSignal(str)

    def run(self):
        try:
            opts = ConfigManager.get_config_section('model_options')['local']
            model_name = opts.get('model_path') or opts['model']
            cached, _ = _model_cached_locally(model_name)
            if cached:
                self.status.emit(f'Loading {model_name} model...')
            else:
                self.status.emit(
                    f'Downloading {model_name} model...\nThis may take a few minutes on first run.'
                )
            model = create_local_model()
            self.model_ready.emit(model)
        except Exception as e:
            self.load_error.emit(str(e))


class WhisperWriterApp(QObject):
    def __init__(self):
        super().__init__()
        self.app = QApplication(sys.argv)
        self.app.setWindowIcon(QIcon(_asset('ww-logo.png')))
        self.key_listener = None
        self.input_simulator = None
        self.local_model = None
        self.result_thread = None
        self.main_window = None
        self.status_window = None
        self._log_file = None

        self._setup_file_log()
        ConfigManager.initialize()

        self.settings_window = SettingsWindow()
        self.settings_window.settings_closed.connect(self.on_settings_closed)
        self.settings_window.settings_saved.connect(self.restart_app)

        if ConfigManager.config_file_exists():
            ConfigManager.console_print('Config file found. Initializing components.')
            self.initialize_components()
        else:
            ConfigManager.console_print('No config file found. Opening settings window.')
            self.settings_window.show()

    def _setup_file_log(self):
        os.makedirs(_LOGS_DIR, exist_ok=True)
        ts = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        log_path = os.path.join(_LOGS_DIR, f'{ts}.log')
        self._log_file = open(log_path, 'w', encoding='utf-8', buffering=1)
        _log_hooks.append(lambda msg: self._write_log(msg))
        if sys.stdout is not None:
            sys.stdout = _Tee(sys.stdout, self._log_file)
        if sys.stderr is not None:
            sys.stderr = _Tee(sys.stderr, self._log_file)

        ConfigManager.console_print('=== WhisperWriter session started ===')
        ConfigManager.console_print(f'Log: {log_path}')
        ConfigManager.console_print(
            f'Python {sys.version} | platform: {sys.platform} | PID: {os.getpid()}'
        )
        ConfigManager.console_print(f'Executable: {sys.executable}')
        ConfigManager.console_print(f'Working dir: {_ROOT_DIR}')

    def _write_log(self, msg):
        if self._log_file and not self._log_file.closed:
            ts = datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]
            self._log_file.write(f'[{ts}] {msg}\n')

    def _load_model_with_dialog(self):
        dialog = QDialog()
        dialog.setWindowTitle('WhisperWriter')
        dialog.setFixedWidth(420)
        dialog.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1e1e2e;
                border: 1px solid #45475a;
            }
            QLabel {
                color: #cdd6f4;
                font-size: 13px;
            }
            QProgressBar {
                border: none;
                background-color: #313244;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #89b4fa;
                border-radius: 4px;
            }
        """)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)

        label = QLabel('Preparing model...')
        label.setAlignment(Qt.AlignCenter)
        label.setWordWrap(True)

        bar = QProgressBar()
        bar.setRange(0, 0)
        bar.setTextVisible(False)
        bar.setFixedHeight(8)

        layout.addWidget(label)
        layout.addWidget(bar)

        self._loader = ModelLoaderThread()
        self._loader.status.connect(label.setText)
        self._loader.model_ready.connect(lambda m: setattr(self, 'local_model', m))
        self._loader.model_ready.connect(lambda _: dialog.accept())
        self._loader.load_error.connect(lambda err: self._on_model_load_error(label, bar, err))
        self._loader.start()

        screen = self.app.primaryScreen().geometry()
        dialog.move(
            screen.center().x() - dialog.sizeHint().width() // 2,
            screen.center().y() - 80,
        )
        dialog.exec_()

    def _on_model_load_error(self, label, bar, err):
        bar.setRange(0, 1)
        label.setText(f'Error loading model:\n{err}')
        ConfigManager.console_print(f'Model load error: {err}')

    def initialize_components(self):
        ConfigManager.console_print('--- initialize_components start ---')

        ConfigManager.console_print('Creating InputSimulator...')
        self.input_simulator = InputSimulator()
        ConfigManager.console_print('InputSimulator ready.')

        ConfigManager.console_print('Creating KeyListener...')
        self.key_listener = KeyListener()
        self.key_listener.add_callback("on_activate", self.on_activation)
        self.key_listener.add_callback("on_deactivate", self.on_deactivation)
        ConfigManager.console_print('KeyListener ready.')

        ConfigManager.console_print('Loading model...')
        self._load_model_with_dialog()
        ConfigManager.console_print(f'Model loaded: {self.local_model}')

        self.result_thread = None

        ConfigManager.console_print('Creating MainWindow...')
        self.main_window = MainWindow()
        self.main_window.openSettings.connect(self.settings_window.show)
        self.main_window.startListening.connect(self.key_listener.start)
        self.main_window.closeApp.connect(self.exit_app)
        ConfigManager.console_print('MainWindow ready.')

        if not ConfigManager.get_config_value('misc', 'hide_status_window'):
            ConfigManager.console_print('Creating StatusWindow...')
            self.status_window = StatusWindow()
            ConfigManager.console_print('StatusWindow ready.')
        else:
            ConfigManager.console_print('StatusWindow hidden (hide_status_window=true).')

        self.create_tray_icon()
        self.main_window.show()
        ConfigManager.console_print('--- initialize_components done. App ready. ---')

    def create_tray_icon(self):
        ConfigManager.console_print('Creating system tray icon...')
        self.tray_icon = QSystemTrayIcon(QIcon(_asset('ww-logo-dark.png')), self.app)

        tray_menu = QMenu()

        show_action = QAction('WhisperWriter Main Menu', self.app)
        show_action.triggered.connect(self.main_window.show)
        tray_menu.addAction(show_action)

        settings_action = QAction('Open Settings', self.app)
        settings_action.triggered.connect(self.settings_window.show)
        tray_menu.addAction(settings_action)

        exit_action = QAction('Exit', self.app)
        exit_action.triggered.connect(self.exit_app)
        tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        ConfigManager.console_print('Tray icon ready.')

    def cleanup(self):
        ConfigManager.console_print('cleanup() called.')
        if self.key_listener:
            ConfigManager.console_print('Stopping KeyListener...')
            self.key_listener.stop()
        if self.input_simulator:
            ConfigManager.console_print('Cleaning up InputSimulator...')
            self.input_simulator.cleanup()
        ConfigManager.console_print('=== WhisperWriter session ended ===')
        if self._log_file and not self._log_file.closed:
            self._log_file.close()

    def exit_app(self):
        ConfigManager.console_print('exit_app() called.')
        self.cleanup()
        QApplication.quit()

    def restart_app(self):
        ConfigManager.console_print('restart_app() called — settings saved, restarting.')
        self.cleanup()
        QApplication.quit()
        QProcess.startDetached(sys.executable, sys.argv)

    def on_settings_closed(self):
        if not os.path.exists(os.path.join(_SRC_DIR, 'config.yaml')):
            ConfigManager.console_print('Settings closed without saving — using defaults.')
            QMessageBox.information(
                self.settings_window,
                'Using Default Values',
                'Settings closed without saving. Default values are being used.'
            )
            self.initialize_components()

    def on_activation(self):
        recording_mode = ConfigManager.get_config_value('recording_options', 'recording_mode')
        if self.result_thread and self.result_thread.isRunning():
            ConfigManager.console_print(
                f'Hotkey activated (thread running, mode={recording_mode}) — stopping.'
            )
            if recording_mode == 'press_to_toggle':
                self.result_thread.stop_recording()
            elif recording_mode == 'continuous':
                self.stop_result_thread()
            return

        ConfigManager.console_print(f'Hotkey activated. Starting recording (mode={recording_mode}).')
        self.start_result_thread()

    def on_deactivation(self):
        recording_mode = ConfigManager.get_config_value('recording_options', 'recording_mode')
        if recording_mode == 'hold_to_record':
            if self.result_thread and self.result_thread.isRunning():
                ConfigManager.console_print('Hotkey released (hold_to_record) — stopping recording.')
                self.result_thread.stop_recording()

    def start_result_thread(self):
        if self.result_thread and self.result_thread.isRunning():
            ConfigManager.console_print('start_result_thread() called but thread already running — skipped.')
            return

        ConfigManager.console_print('Starting ResultThread...')
        self.result_thread = ResultThread(self.local_model)
        if not ConfigManager.get_config_value('misc', 'hide_status_window'):
            self.result_thread.statusSignal.connect(self.status_window.updateStatus)
            self.result_thread.audioLevelSignal.connect(self.status_window.updateLevel)
            self.status_window.closeSignal.connect(self.stop_result_thread)
        self.result_thread.resultSignal.connect(self.on_transcription_complete)
        self.result_thread.start()

    def stop_result_thread(self):
        if self.result_thread and self.result_thread.isRunning():
            ConfigManager.console_print('Stopping ResultThread...')
            self.result_thread.stop()

    def on_transcription_complete(self, result):
        ConfigManager.console_print(
            f'Transcription complete ({len(result)} chars). Typing result: {result!r}'
        )
        pyperclip.copy(result)
        self.input_simulator.typewrite(result)

        if ConfigManager.get_config_value('misc', 'noise_on_completion'):
            AudioPlayer(_asset('beep.wav')).play(block=True)

        recording_mode = ConfigManager.get_config_value('recording_options', 'recording_mode')
        if recording_mode == 'continuous':
            ConfigManager.console_print('Continuous mode — restarting recording.')
            self.start_result_thread()
        else:
            ConfigManager.console_print('Restarting key listener.')
            self.key_listener.start()

    def run(self):
        sys.exit(self.app.exec_())


if __name__ == '__main__':
    app = WhisperWriterApp()
    app.run()
