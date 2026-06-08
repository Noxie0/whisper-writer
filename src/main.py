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
        self._stream = stream
        self._log = log_file

    def write(self, data):
        self._stream.write(data)
        try:
            self._log.write(data)
        except Exception:
            pass

    def flush(self):
        self._stream.flush()
        try:
            self._log.flush()
        except Exception:
            pass

    def fileno(self):
        return self._stream.fileno()


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
            self.initialize_components()
        else:
            print('No valid configuration file found. Opening settings window...')
            self.settings_window.show()

    def _setup_file_log(self):
        os.makedirs(_LOGS_DIR, exist_ok=True)
        ts = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        log_path = os.path.join(_LOGS_DIR, f'{ts}.log')
        self._log_file = open(log_path, 'w', encoding='utf-8', buffering=1)
        _log_hooks.append(lambda msg: self._write_log(msg))
        sys.stdout = _Tee(sys.stdout, self._log_file)
        sys.stderr = _Tee(sys.stderr, self._log_file)

    def _write_log(self, msg):
        if self._log_file and not self._log_file.closed:
            self._log_file.write(msg + '\n')

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
        self.input_simulator = InputSimulator()

        self.key_listener = KeyListener()
        self.key_listener.add_callback("on_activate", self.on_activation)
        self.key_listener.add_callback("on_deactivate", self.on_deactivation)

        self._load_model_with_dialog()

        self.result_thread = None

        self.main_window = MainWindow()
        self.main_window.openSettings.connect(self.settings_window.show)
        self.main_window.startListening.connect(self.key_listener.start)
        self.main_window.closeApp.connect(self.exit_app)

        if not ConfigManager.get_config_value('misc', 'hide_status_window'):
            self.status_window = StatusWindow()

        self.create_tray_icon()
        self.main_window.show()

    def create_tray_icon(self):
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

    def cleanup(self):
        if self.key_listener:
            self.key_listener.stop()
        if self.input_simulator:
            self.input_simulator.cleanup()
        if self._log_file and not self._log_file.closed:
            self._log_file.close()

    def exit_app(self):
        self.cleanup()
        QApplication.quit()

    def restart_app(self):
        self.cleanup()
        QApplication.quit()
        QProcess.startDetached(sys.executable, sys.argv)

    def on_settings_closed(self):
        if not os.path.exists(os.path.join(_SRC_DIR, 'config.yaml')):
            QMessageBox.information(
                self.settings_window,
                'Using Default Values',
                'Settings closed without saving. Default values are being used.'
            )
            self.initialize_components()

    def on_activation(self):
        if self.result_thread and self.result_thread.isRunning():
            recording_mode = ConfigManager.get_config_value('recording_options', 'recording_mode')
            if recording_mode == 'press_to_toggle':
                self.result_thread.stop_recording()
            elif recording_mode == 'continuous':
                self.stop_result_thread()
            return

        self.start_result_thread()

    def on_deactivation(self):
        if ConfigManager.get_config_value('recording_options', 'recording_mode') == 'hold_to_record':
            if self.result_thread and self.result_thread.isRunning():
                self.result_thread.stop_recording()

    def start_result_thread(self):
        if self.result_thread and self.result_thread.isRunning():
            return

        self.result_thread = ResultThread(self.local_model)
        if not ConfigManager.get_config_value('misc', 'hide_status_window'):
            self.result_thread.statusSignal.connect(self.status_window.updateStatus)
            self.result_thread.audioLevelSignal.connect(self.status_window.updateLevel)
            self.status_window.closeSignal.connect(self.stop_result_thread)
        self.result_thread.resultSignal.connect(self.on_transcription_complete)
        self.result_thread.start()

    def stop_result_thread(self):
        if self.result_thread and self.result_thread.isRunning():
            self.result_thread.stop()

    def on_transcription_complete(self, result):
        pyperclip.copy(result)
        self.input_simulator.typewrite(result)

        if ConfigManager.get_config_value('misc', 'noise_on_completion'):
            AudioPlayer(_asset('beep.wav')).play(block=True)

        if ConfigManager.get_config_value('recording_options', 'recording_mode') == 'continuous':
            self.start_result_thread()
        else:
            self.key_listener.start()

    def run(self):
        sys.exit(self.app.exec_())


if __name__ == '__main__':
    app = WhisperWriterApp()
    app.run()
