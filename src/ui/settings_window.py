import os
import sys
from PyQt5.QtWidgets import (
    QApplication, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QCheckBox,
    QMessageBox, QTabWidget, QWidget, QSizePolicy, QSpacerItem, QToolButton, QFileDialog,
    QScrollArea, QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QSpinBox, QDoubleSpinBox, QDialog, QTextBrowser, QPlainTextEdit
)
from PyQt5.QtCore import Qt, QProcess, pyqtSignal
from PyQt5.QtGui import QFont

_UI_DIR = os.path.dirname(os.path.abspath(__file__))
_ASSETS = os.path.normpath(os.path.join(_UI_DIR, '..', '..', 'assets')).replace('\\', '/')
_ARROW_DOWN = f'{_ASSETS}/arrow_down.svg'
_ARROW_UP = f'{_ASSETS}/arrow_up.svg'
_CHECKMARK = f'{_ASSETS}/checkmark.svg'

_OPTION_LABEL_MAPS = {
    'recording_mode': {
        'continuous': 'Continuous',
        'voice_activity_detection': 'Voice Activity Detection',
        'press_to_toggle': 'Press to Toggle',
        'hold_to_record': 'Hold to Record',
    },
}


class HotkeyCapture(QLineEdit):
    """Click-to-capture hotkey field. Press any key combo to set; Escape cancels."""

    _KEY_MAP = {
        Qt.Key_Space: 'space', Qt.Key_Return: 'enter', Qt.Key_Enter: 'enter',
        Qt.Key_Tab: 'tab', Qt.Key_Backspace: 'backspace', Qt.Key_Delete: 'delete',
        Qt.Key_Insert: 'insert', Qt.Key_Home: 'home', Qt.Key_End: 'end',
        Qt.Key_PageUp: 'page_up', Qt.Key_PageDown: 'page_down',
        Qt.Key_Up: 'up', Qt.Key_Down: 'down', Qt.Key_Left: 'left', Qt.Key_Right: 'right',
        Qt.Key_Escape: 'escape', Qt.Key_CapsLock: 'caps_lock',
        Qt.Key_NumLock: 'num_lock', Qt.Key_ScrollLock: 'scroll_lock',
        Qt.Key_Print: 'print_screen', Qt.Key_Pause: 'pause',
        Qt.Key_F1: 'f1', Qt.Key_F2: 'f2', Qt.Key_F3: 'f3', Qt.Key_F4: 'f4',
        Qt.Key_F5: 'f5', Qt.Key_F6: 'f6', Qt.Key_F7: 'f7', Qt.Key_F8: 'f8',
        Qt.Key_F9: 'f9', Qt.Key_F10: 'f10', Qt.Key_F11: 'f11', Qt.Key_F12: 'f12',
    }
    _MODIFIERS = {Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta,
                  Qt.Key_Super_L, Qt.Key_Super_R}

    _STYLE_NORMAL = ("background: #45475a; color: #cdd6f4; border: 1px solid #7f849c; "
                     "border-radius: 6px; padding: 2px 8px; font-size: 11px;")
    _STYLE_CAPTURING = ("background: #1e1e2e; color: #cba6f7; border: 2px solid #cba6f7; "
                        "border-radius: 6px; padding: 2px 8px; font-size: 11px;")

    def __init__(self, value='', parent=None):
        super().__init__(parent)
        self.setText(value)
        self.setReadOnly(True)
        self.setPlaceholderText('Click to capture...')
        self.setCursor(Qt.PointingHandCursor)
        self._capturing = False
        self._prev = value
        self.setStyleSheet(self._STYLE_NORMAL)

    def mousePressEvent(self, event):
        if not self._capturing:
            self._capturing = True
            self._prev = self.text()
            self.setText('Press any key...')
            self.setStyleSheet(self._STYLE_CAPTURING)
            self.setFocus()

    def keyPressEvent(self, event):
        if not self._capturing:
            return
        key = event.key()
        if key in self._MODIFIERS:
            return
        if key == Qt.Key_Escape:
            self.setText(self._prev)
            self._end_capture()
            return

        parts = []
        mods = event.modifiers()
        if mods & Qt.ControlModifier:
            parts.append('ctrl')
        if mods & Qt.AltModifier:
            parts.append('alt')
        if mods & Qt.ShiftModifier:
            parts.append('shift')
        if mods & Qt.MetaModifier:
            parts.append('cmd')

        name = self._KEY_MAP.get(key)
        if name is None:
            if Qt.Key_A <= key <= Qt.Key_Z:
                name = chr(key).lower()
            elif 32 <= key <= 126:
                name = chr(key).lower()
        if name:
            parts.append(name)
            self.setText('+'.join(parts))
        self._end_capture()

    def focusOutEvent(self, event):
        if self._capturing:
            self.setText(self._prev)
            self._end_capture()
        super().focusOutEvent(event)

    def _end_capture(self):
        self._capturing = False
        self.setStyleSheet(self._STYLE_NORMAL)
        self.clearFocus()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ui.base_window import BaseWindow
from utils import ConfigManager
from vocabulary import get_vocabulary, save_vocabulary

_log_hooks = []

def _patch_console_print():
    _orig_fn = ConfigManager.console_print.__func__
    @classmethod
    def _patched(cls, message):
        msg_str = str(message)
        for hook in list(_log_hooks):
            try:
                hook(msg_str)
            except Exception:
                pass
        if cls._instance and cls._instance.config['misc']['print_to_terminal']:
            print(message)
    ConfigManager.console_print = _patched
_patch_console_print()

_MODEL_HELP_HTML = """
<html><body style="font-family: 'Segoe UI', sans-serif; font-size: 11px; color: #cdd6f4; background-color: #181825;">

<p style="color: #cba6f7; font-size: 13px; font-weight: bold; margin: 0 0 4px 0;">Whisper Model Selection Guide</p>
<p style="color: #9399b2; margin: 0 0 12px 0;">All models run locally on your machine. Larger models are slower but more accurate.</p>

<table width="100%" cellspacing="0" cellpadding="5" style="border-collapse: collapse;">
  <tr style="background-color: #313244; color: #9399b2; font-size: 10px;">
    <td><b>Model</b></td><td><b>Params</b></td><td><b>Device</b></td><td><b>VRAM (fp16)</b></td><td><b>Best for</b></td>
  </tr>
  <tr style="background-color: #1e1e2e;">
    <td><span style="color: #cba6f7;">tiny / tiny.en</span></td><td>39 M</td><td>CPU or GPU</td><td>~1 GB</td><td>Fastest, simple speech</td>
  </tr>
  <tr style="background-color: #181825;">
    <td><span style="color: #cba6f7;">base / base.en</span></td><td>74 M</td><td>CPU or GPU</td><td>~1 GB</td><td>Fast with better quality</td>
  </tr>
  <tr style="background-color: #1e1e2e;">
    <td><span style="color: #cba6f7;">small / small.en</span></td><td>244 M</td><td>CPU or GPU</td><td>~2 GB</td><td>Good CPU choice</td>
  </tr>
  <tr style="background-color: #181825;">
    <td><span style="color: #cba6f7;">medium / medium.en</span></td><td>769 M</td><td>GPU recommended</td><td>~5 GB</td><td>Best speed/accuracy balance</td>
  </tr>
  <tr style="background-color: #1e1e2e;">
    <td><span style="color: #cba6f7;">large-v2</span></td><td>1550 M</td><td>GPU required</td><td>~10 GB</td><td>High accuracy</td>
  </tr>
  <tr style="background-color: #181825;">
    <td><span style="color: #cba6f7;">large-v3</span></td><td>1550 M</td><td>GPU required</td><td>~10 GB</td><td>Best accuracy &amp; multilingual</td>
  </tr>
</table>

<p style="color: #cba6f7; font-weight: bold; margin: 14px 0 4px 0;">Tips</p>
<ul style="color: #bac2de; margin: 0; padding-left: 18px; line-height: 1.7;">
  <li><b>.en variants</b> are English-only and ~10–15% faster than multilingual models.</li>
  <li><b>CPU only</b> — Use <i>tiny</i>, <i>base</i>, or <i>small</i>. Set compute_type to <i>int8</i>.</li>
  <li><b>GPU with 4–6 GB VRAM</b> — <i>small</i> or <i>medium</i> with <i>float16</i> or <i>int8</i>.</li>
  <li><b>GPU with ≥10 GB VRAM</b> — <i>large-v3</i> with <i>float16</i> for maximum accuracy.</li>
  <li>Using <i>int8</i> compute type roughly <b>halves</b> VRAM usage with minimal quality loss.</li>
  <li>Set device to <i>cuda</i> for NVIDIA GPUs, <i>cpu</i> to force CPU, <i>auto</i> to let the app decide.</li>
</ul>

</body></html>
"""

_SPINBOX_CONFIG = {
    'temperature':            dict(min=0.0,  max=1.0,      step=0.05,  decimals=2),
    'writing_key_press_delay': dict(min=0.0, max=1.0,      step=0.001, decimals=3),
    'sample_rate':            dict(min=4000, max=192000,   step=1000),
    'silence_duration':       dict(min=50,   max=10000,    step=50),
    'min_duration':           dict(min=0,    max=5000,     step=25),
}

_HELP_TOOLTIPS = {
    'language':                  'Transcription language. Blank = auto-detect.  Click ? for details.',
    'temperature':               'Output randomness (0.0 = most accurate).  Click ? for details.',
    'initial_prompt':            'Text hint to prime the model before it starts.  Click ? for details.',
    'device':                    'Where Whisper runs: GPU (cuda), CPU, or auto.  Click ? for details.',
    'compute_type':              'Numeric precision for inference. int8 = fastest.  Click ? for details.',
    'condition_on_previous_text':'Use last transcription as context for the next.  Click ? for details.',
    'vad_filter':                'Strip silence before transcribing.  Click ? for details.',
    'model_path':                'Path to a local model folder. Blank = auto-download.  Click ? for details.',
    'activation_key':            'Keyboard shortcut that triggers recording.  Click ? for details.',
    'input_backend':             'Library used to detect the activation key globally.  Click ? for details.',
    'recording_mode':            'How the activation key controls recording.  Click ? for details.',
    'sound_device':              'Microphone to record from.  Click ? for details.',
    'sample_rate':               'Audio sample rate in Hz. Whisper needs 16 000.  Click ? for details.',
    'silence_duration':          'Silence length (ms) that triggers auto-stop.  Click ? for details.',
    'min_duration':              'Recordings shorter than this are discarded.  Click ? for details.',
    'writing_key_press_delay':   'Pause between simulated keystrokes when typing.  Click ? for details.',
    'remove_trailing_period':    'Strip the period Whisper adds at the end.  Click ? for details.',
    'add_trailing_space':        'Add a space after transcription finishes.  Click ? for details.',
    'remove_capitalization':     'Convert all transcribed text to lowercase.  Click ? for details.',
    'input_method':              'Method used to simulate keystrokes.  Click ? for details.',
    'print_to_terminal':         'Log status and transcriptions to the terminal.  Click ? for details.',
    'hide_status_window':        'Hide the floating recording status window.  Click ? for details.',
    'noise_on_completion':       'Play a sound when transcription finishes typing.  Click ? for details.',
}

def _help(title, subtitle, body):
    return (title, (
        '<html><body style="font-family: \'Segoe UI\', sans-serif; font-size: 11px; '
        'color: #cdd6f4; background-color: #181825; padding: 2px;">'
        '<p style="color: #cba6f7; font-size: 13px; font-weight: bold; margin: 0 0 4px 0;">' + title + '</p>'
        '<p style="color: #9399b2; margin: 0 0 12px 0;">' + subtitle + '</p>'
        + body +
        '</body></html>'
    ))

def _tbl(*rows):
    hdr = rows[0]
    cells = ''.join(f'<td style="padding:5px;"><b>{c}</b></td>' for c in hdr)
    out = ('<table width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;">'
           f'<tr style="background:#313244;color:#9399b2;font-size:10px;">{cells}</tr>')
    for i, row in enumerate(rows[1:]):
        bg = '#1e1e2e' if i % 2 == 0 else '#181825'
        cells = ''.join(
            f'<td style="padding:5px;color:#cba6f7;">{c}</td>' if j == 0
            else f'<td style="padding:5px;">{c}</td>'
            for j, c in enumerate(row)
        )
        out += f'<tr style="background:{bg};">{cells}</tr>'
    return out + '</table>'

def _ul(*items):
    li = ''.join(f'<li style="line-height:1.7;">{i}</li>' for i in items)
    return f'<ul style="color:#bac2de;margin:4px 0;padding-left:18px;">{li}</ul>'

_note = '<p style="color:#9399b2;margin-top:10px;">'

_HELP_HTML = {
    'language': _help(
        'Transcription Language',
        'Tells Whisper which spoken language to expect.',
        '<p>Leave blank to <b>auto-detect</b> the language from the audio — works well in most cases.</p>'
        '<p style="margin-top:8px;">Set an <b>ISO-639-1 code</b> to force a specific language and skip detection:</p>'
        + _ul(
            '<span style="color:#cba6f7;">en</span> — English',
            '<span style="color:#cba6f7;">fr</span> — French',
            '<span style="color:#cba6f7;">de</span> — German',
            '<span style="color:#cba6f7;">es</span> — Spanish',
            '<span style="color:#cba6f7;">ja</span> — Japanese',
            '<span style="color:#cba6f7;">zh</span> — Chinese',
        )
        + _note + 'Setting the language explicitly is slightly faster and avoids wrong-language output.</p>'
    ),
    'temperature': _help(
        'Temperature',
        'Controls how creative or literal the transcription output is.',
        _tbl(
            ('Value', 'Effect'),
            ('0.0', 'Deterministic — always picks the most likely word'),
            ('0.2 – 0.5', 'Slightly varied — can help with unclear audio'),
            ('1.0', 'Most random — rarely useful for transcription'),
        )
        + _note + '<b>Recommended:</b> 0.0 for everyday dictation.</p>'
    ),
    'initial_prompt': _help(
        'Initial Prompt',
        'A text hint given to Whisper before transcription starts.',
        '<p>Use this to nudge the model toward specific words, terms, or punctuation style. Examples:</p>'
        + _ul(
            '<span style="color:#cba6f7;">"WhisperWriter, PyQt5, sounddevice"</span> — hints at technical terms',
            '<span style="color:#cba6f7;">"No punctuation please."</span> — discourages punctuation',
            '<span style="color:#cba6f7;">"Always use Oxford commas."</span> — formatting preference',
        )
        + _note + 'Leave blank if you do not need any special priming.</p>'
    ),
    'device': _help(
        'Inference Device',
        'Where the Whisper model runs for transcription.',
        _tbl(
            ('Option', 'What it does'),
            ('auto', 'Uses GPU if available, falls back to CPU automatically'),
            ('cuda', 'Forces NVIDIA GPU — fastest option'),
            ('cpu', 'Forces CPU — slower but always compatible'),
        )
        + _note + '<b>Recommended:</b> Leave on <i>auto</i> unless you need to force a specific device.</p>'
    ),
    'compute_type': _help(
        'Compute Type',
        'The numerical precision used when running the model. Affects speed, VRAM usage, and accuracy.',
        _tbl(
            ('Option', 'Speed', 'VRAM', 'Requires'),
            ('default', 'Varies', 'Varies', 'Anything — backend decides'),
            ('int8', 'Fastest', 'Lowest', 'CPU or GPU'),
            ('float16', 'Fast', 'Medium', 'CUDA GPU only'),
            ('float32', 'Slowest', 'Highest', 'CPU or GPU'),
        )
        + _note + '<b>Tip:</b> <i>int8</i> roughly halves VRAM usage vs float16 with minimal accuracy loss.</p>'
    ),
    'condition_on_previous_text': _help(
        'Condition on Previous Text',
        'Feeds your last transcription back to the model as context for the next one.',
        '<p><b>When enabled:</b> Whisper uses what you said before to help interpret the next segment. Good for long-form dictation where consistency matters.</p>'
        '<p style="margin-top:8px;"><b>When disabled:</b> Each transcription is treated independently. More reliable if the model starts repeating itself or getting stuck in loops.</p>'
        + _note + '<b>Recommended:</b> Enabled. Disable if you notice repetition artifacts.</p>'
    ),
    'vad_filter': _help(
        'VAD Filter',
        "Uses Whisper's built-in Voice Activity Detection to strip silence before transcribing.",
        '<p><b>Benefits:</b></p>'
        + _ul(
            'Faster transcription — model skips empty audio',
            'Reduces hallucinations (Whisper can invent words from background noise)',
        )
        + '<p style="margin-top:8px;"><b>Drawback:</b> May clip the very beginning or end of your speech if you start or stop quietly.</p>'
        + _note + '<b>Recommended:</b> Enable if you are in a noisy environment or get random words inserted.</p>'
    ),
    'model_path': _help(
        'Custom Model Path',
        'Path to a manually downloaded Whisper model folder.',
        '<p>Leave blank to let WhisperWriter automatically download the selected model to the Hugging Face cache.</p>'
        '<p style="margin-top:8px;">Set this if you:</p>'
        + _ul(
            'Downloaded a model manually or from a custom source',
            'Are on a machine without internet access',
            'Want to use a fine-tuned or quantized model variant',
        )
        + _note + 'Use the Browse button to locate the model folder on disk.</p>'
    ),
    'activation_key': _help(
        'Activation Key',
        'The keyboard shortcut that starts and stops recording.',
        '<p>Click the field and press your desired key combination. Keys are joined with <span style="color:#cba6f7;">+</span>.</p>'
        '<p style="margin-top:8px;"><b>Examples:</b></p>'
        + _ul(
            '<span style="color:#cba6f7;">ctrl+shift+space</span> — default',
            '<span style="color:#cba6f7;">alt+r</span>',
            '<span style="color:#cba6f7;">f9</span>',
            '<span style="color:#cba6f7;">caps_lock</span>',
        )
        + _note + 'The exact behavior depends on the Recording Mode setting.</p>'
    ),
    'input_backend': _help(
        'Input Backend',
        'The library used to detect the activation key globally across the system.',
        _tbl(
            ('Option', 'Platform', 'Notes'),
            ('auto', 'All', 'Picks the best option automatically'),
            ('pynput', 'Windows / macOS / Linux (X11)', 'Most compatible choice'),
            ('evdev', 'Linux only', 'Lower-level, works under Wayland'),
        )
        + _note + '<b>Recommended:</b> Leave on <i>auto</i> unless key detection is not working.</p>'
    ),
    'recording_mode': _help(
        'Recording Mode',
        'Controls how the activation key starts and stops recording.',
        _tbl(
            ('Mode', 'How it works'),
            ('Continuous', 'Keeps restarting after speech pauses until you press the key again. Best for long dictation sessions.'),
            ('Voice Activity Detection', 'Starts when you press the key, stops automatically after a period of silence.'),
            ('Press to Toggle', 'Press once to start recording, press again to stop and transcribe.'),
            ('Hold to Record', 'Hold the key to record, release to stop and transcribe immediately.'),
        )
    ),
    'sound_device': _help(
        'Recording Device',
        'The microphone WhisperWriter captures audio from.',
        '<p>Select <span style="color:#cba6f7;">Default (system)</span> to use whatever microphone Windows has set as the system default input device.</p>'
        '<p style="margin-top:8px;">Select a specific device if you have multiple microphones and want to pin WhisperWriter to one regardless of the system default.</p>'
        + _note + 'Only active, non-disabled input devices are listed.</p>'
    ),
    'sample_rate': _help(
        'Sample Rate',
        'The number of audio samples captured per second during recording.',
        '<p>Whisper was trained on <span style="color:#cba6f7;">16 000 Hz</span> audio. Recording at this rate gives the best transcription quality and fastest processing.</p>'
        '<p style="margin-top:8px;">Only change this if your microphone explicitly does not support 16 000 Hz — most modern microphones do.</p>'
        + _note + '<b>Recommended:</b> 16000</p>'
    ),
    'silence_duration': _help(
        'Silence Duration',
        'How long a pause must last before the app considers you done speaking.',
        '<p>Used in <span style="color:#cba6f7;">Continuous</span> and <span style="color:#cba6f7;">Voice Activity Detection</span> modes to detect the end of a speech segment.</p>'
        + _ul(
            '<b>Lower (300–600 ms)</b> — stops quickly after a pause, good for short phrases',
            '<b>Default (900 ms)</b> — comfortable buffer for natural speech rhythm',
            '<b>Higher (1500+ ms)</b> — tolerates longer pauses mid-sentence without stopping early',
        )
    ),
    'min_duration': _help(
        'Minimum Duration',
        'Recordings shorter than this threshold are silently discarded.',
        '<p>Prevents accidental triggers — like the sound of pressing the activation key — from being sent to the transcription model.</p>'
        '<p style="margin-top:8px;"><b>Increase</b> if short accidental recordings are being transcribed.</p>'
        '<p><b>Decrease</b> if the very beginning of your speech is getting cut off.</p>'
        + _note + '<b>Default:</b> 100 ms</p>'
    ),
    'writing_key_press_delay': _help(
        'Key Press Delay',
        'The pause between each simulated keystroke when typing out the transcription.',
        '<p>Most applications handle rapid input fine at the default of <span style="color:#cba6f7;">0.005 s</span> (5 ms).</p>'
        '<p style="margin-top:8px;"><b>Increase if:</b></p>'
        + _ul(
            'Characters appear out of order or are skipped',
            'The target app cannot keep up with input speed',
            'You are typing into a browser or web app',
        )
        + _note + '<b>Recommended:</b> 0.005. Try 0.01–0.05 if you see issues.</p>'
    ),
    'remove_trailing_period': _help(
        'Remove Trailing Period',
        'Strips the period Whisper often appends at the end of each transcription.',
        '<p>Whisper tends to end transcriptions with a period even when you are dictating mid-sentence.</p>'
        '<p style="margin-top:8px;"><b>Enable if:</b> The period keeps appearing at the wrong place in your text.</p>'
        '<p><b>Keep disabled if:</b> You are dictating full sentences where the period is correct.</p>'
    ),
    'add_trailing_space': _help(
        'Add Trailing Space',
        'Appends a space after the transcribed text is typed out.',
        '<p>Ensures the next word you type or dictate starts with a natural space separator — so you do not have to manually press Space between recordings.</p>'
        '<p style="margin-top:8px;"><b>Disable if:</b> The extra space causes formatting issues in your target application.</p>'
        + _note + '<b>Recommended:</b> Enabled.</p>'
    ),
    'remove_capitalization': _help(
        'Remove Capitalization',
        'Converts all transcribed text to lowercase before typing it out.',
        '<p>Whisper automatically capitalizes the first word and proper nouns. Enable this to strip all capitalization from the output.</p>'
        '<p style="margin-top:8px;"><b>Useful for:</b> Command inputs, code fields, search bars, or anywhere lowercase is expected.</p>'
    ),
    'input_method': _help(
        'Input Method',
        'The library used to simulate keystrokes when typing out transcriptions.',
        _tbl(
            ('Option', 'Platform', 'Notes'),
            ('pynput', 'Windows / macOS / Linux (X11)', 'Default. Works on most setups.'),
            ('ydotool', 'Linux (Wayland)', 'Requires ydotool daemon to be running'),
            ('dotool', 'Linux (Wayland)', 'Alternative to ydotool'),
        )
        + _note + '<b>Recommended:</b> <i>pynput</i> for Windows and most Linux setups.</p>'
    ),
    'print_to_terminal': _help(
        'Print to Terminal',
        'Logs status updates and transcription output to the terminal or console.',
        '<p>When enabled you will see messages such as:</p>'
        + _ul(
            'Recording started / stopped',
            'Speech detected',
            'Transcription time in seconds',
            'The full transcribed text',
        )
        + _note + 'Useful for debugging. Has no visible effect if the app is running without a terminal window.</p>'
    ),
    'hide_status_window': _help(
        'Hide Status Window',
        'Controls whether the small floating window is shown while the app is active.',
        '<p>The status window displays the current state in real time:</p>'
        + _ul(
            '<b>Idle</b> — waiting for the activation key',
            '<b>Recording</b> — capturing audio with a live waveform',
            '<b>Transcribing</b> — processing the recorded audio',
        )
        + '<p style="margin-top:8px;">When hidden the app still runs normally — you will just have no visual feedback.</p>'
    ),
    'noise_on_completion': _help(
        'Noise on Completion',
        'Plays a short sound when the transcription has finished typing.',
        '<p>Provides audio feedback so you know the text has been fully typed out — useful when you are looking away from the screen or dictating into a background window.</p>'
    ),
}


class SettingsWindow(BaseWindow):
    settings_closed = pyqtSignal()
    settings_saved = pyqtSignal()
    _console_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__('Settings', 700, 760)
        self.schema = ConfigManager.get_schema()
        self.init_settings_ui()

    def init_settings_ui(self):
        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)

        self.create_tabs()
        self.create_vocabulary_tab()
        self.create_console_tab()
        self.create_about_tab()
        self.create_buttons()

    def create_tabs(self):
        for category, settings in self.schema.items():
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setFrameShape(QFrame.NoFrame)
            scroll.setStyleSheet("background: transparent; border: none;")
            scroll.viewport().setAutoFillBackground(False)

            content = QWidget()
            content.setStyleSheet("background: transparent;")
            tab_layout = QVBoxLayout(content)
            tab_layout.setContentsMargins(16, 16, 16, 16)
            tab_layout.setSpacing(4)

            self.create_settings_widgets(tab_layout, category, settings)
            tab_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

            scroll.setWidget(content)
            self.tabs.addTab(scroll, category.replace('_', ' ').title())

    def _make_section_header(self, text):
        header = QLabel(text.replace('_', ' ').upper())
        header.setFont(QFont('Segoe UI', 8, QFont.Bold))
        header.setStyleSheet("color: #cba6f7; letter-spacing: 1.5px; padding: 10px 0 2px 0;")
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #313244; border: none; margin-bottom: 4px;")
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(2)
        vbox.addWidget(header)
        vbox.addWidget(sep)
        return container

    def create_settings_widgets(self, layout, category, settings):
        for sub_category, sub_settings in settings.items():
            if isinstance(sub_settings, dict) and 'value' in sub_settings:
                self.add_setting_widget(layout, sub_category, sub_settings, category)
            else:
                layout.addWidget(self._make_section_header(sub_category))
                for key, meta in sub_settings.items():
                    self.add_setting_widget(layout, key, meta, category, sub_category)

    def create_vocabulary_tab(self):
        tab = QWidget()
        tab.setStyleSheet("background: transparent;")
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(16, 16, 16, 16)
        tab_layout.setSpacing(10)

        info = QLabel(
            "Vocabulary substitutions are applied to the transcription before it is typed out. "
            "Use them to fix words Whisper consistently gets wrong, expand abbreviations, or correct proper nouns.\n\n"
            "Example: type “gonna” in the left column and “going to” in the right, "
            "and every time Whisper writes “gonna” it will be replaced automatically. "
            "Matching is case-insensitive."
        )
        info.setStyleSheet("color: #9399b2; font-size: 12px; line-height: 1.5;")
        info.setWordWrap(True)
        tab_layout.addWidget(info)

        self.vocab_table = QTableWidget(0, 2)
        self.vocab_table.setFont(QFont('Segoe UI', 11))
        self.vocab_table.horizontalHeader().setFont(QFont('Segoe UI', 10, QFont.Bold))
        self.vocab_table.setHorizontalHeaderLabels(["Word / Phrase", "Replacement"])
        self.vocab_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.vocab_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.vocab_table.verticalHeader().setVisible(False)
        self.vocab_table.setAlternatingRowColors(True)
        self.vocab_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.vocab_table.setShowGrid(True)
        self.vocab_table.setMaximumHeight(460)
        tab_layout.addWidget(self.vocab_table)

        for entry in get_vocabulary():
            self._add_vocab_row(entry.get('from', ''), entry.get('to', ''))

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        add_btn = QPushButton('+ Add Row')
        add_btn.setFixedWidth(110)
        add_btn.setFixedHeight(34)
        add_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #cba6f7, stop:1 #a98de8);
                color: #1e1e2e;
                border: none;
                border-radius: 8px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #d4b1ff, stop:1 #b4befe);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #a98de8, stop:1 #9173c6);
            }
        """)
        add_btn.clicked.connect(lambda: self._add_vocab_row('', ''))

        remove_btn = QPushButton('Remove Selected')
        remove_btn.setFixedWidth(140)
        remove_btn.setFixedHeight(34)
        remove_btn.setStyleSheet("""
            QPushButton {
                background: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 8px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #f38ba8;
                color: #1e1e2e;
                border-color: #f38ba8;
            }
            QPushButton:pressed {
                background: #e64553;
            }
        """)
        remove_btn.clicked.connect(self._remove_selected_vocab_rows)

        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(remove_btn)
        btn_layout.addStretch()
        tab_layout.addLayout(btn_layout)

        self.tabs.addTab(tab, 'Vocabulary')

    def _add_vocab_row(self, from_word='', to_word=''):
        row = self.vocab_table.rowCount()
        self.vocab_table.insertRow(row)
        self.vocab_table.setItem(row, 0, QTableWidgetItem(from_word))
        self.vocab_table.setItem(row, 1, QTableWidgetItem(to_word))
        self.vocab_table.setRowHeight(row, 36)

    def _remove_selected_vocab_rows(self):
        rows = sorted(set(item.row() for item in self.vocab_table.selectedItems()), reverse=True)
        for row in rows:
            self.vocab_table.removeRow(row)

    def create_console_tab(self):
        tab = QWidget()
        tab.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header_row = QHBoxLayout()
        title = QLabel("Application Logs")
        title.setStyleSheet("color: #cba6f7; font-size: 13px; font-weight: bold;")
        header_row.addWidget(title)
        header_row.addStretch()
        clear_btn = QPushButton("Clear")
        clear_btn.setFixedSize(70, 28)
        clear_btn.setStyleSheet("""
            QPushButton { background: #313244; color: #9399b2; border: 1px solid #45475a;
                border-radius: 6px; font-size: 10px; font-weight: 500; padding: 2px 8px; }
            QPushButton:hover { background: #45475a; color: #cdd6f4; }
            QPushButton:pressed { background: #181825; }
        """)
        header_row.addWidget(clear_btn)
        layout.addLayout(header_row)

        self.console_output = QPlainTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setFont(QFont('Consolas', 9))
        self.console_output.setStyleSheet("""
            QPlainTextEdit { background-color: #11111b; color: #a6e3a1; border: 1px solid #313244;
                border-radius: 6px; padding: 8px; }
            QScrollBar:vertical { background: #181825; width: 6px; border-radius: 3px; margin: 0; }
            QScrollBar::handle:vertical { background: #45475a; border-radius: 3px; min-height: 20px; }
            QScrollBar::handle:vertical:hover { background: #cba6f7; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)
        self.console_output.setMaximumBlockCount(500)
        layout.addWidget(self.console_output)

        hint = QLabel("All app log messages appear here regardless of the 'Print to Terminal' setting.")
        hint.setStyleSheet("color: #585b70; font-size: 10px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        clear_btn.clicked.connect(self.console_output.clear)

        self._console_signal.connect(self._append_console_log)
        self._console_hook = lambda msg: self._console_signal.emit(msg)
        _log_hooks.append(self._console_hook)

        self.tabs.addTab(tab, 'Logs')

    def _append_console_log(self, message):
        from datetime import datetime
        ts = datetime.now().strftime('%H:%M:%S')
        self.console_output.appendPlainText(f'[{ts}]  {message}')
        sb = self.console_output.verticalScrollBar()
        sb.setValue(sb.maximum())

    def create_about_tab(self):
        tab = QWidget()
        tab.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(28, 32, 28, 28)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignTop)

        name_label = QLabel("WhisperWriter")
        name_label.setFont(QFont('Segoe UI', 22, QFont.Bold))
        name_label.setStyleSheet("color: #cba6f7;")
        layout.addWidget(name_label)

        tagline = QLabel("Local, offline speech-to-text that types for you.")
        tagline.setStyleSheet("color: #9399b2; font-size: 12px;")
        layout.addWidget(tagline)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background: #313244; border: none; margin: 8px 0;")
        layout.addWidget(sep)

        orig_header = QLabel("ORIGINAL PROJECT")
        orig_header.setStyleSheet("color: #6c7086; font-size: 10px; font-weight: bold; letter-spacing: 1.5px;")
        layout.addWidget(orig_header)

        github_link = QLabel(
            '<a href="https://github.com/savbell/whisper-writer" '
            'style="color: #89b4fa; text-decoration: none; font-size: 12px;">'
            'github.com/savbell/whisper-writer</a>'
        )
        github_link.setOpenExternalLinks(True)
        github_link.setTextFormat(Qt.RichText)
        layout.addWidget(github_link)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("background: #313244; border: none; margin: 8px 0;")
        layout.addWidget(sep2)

        rewrite_header = QLabel("THIS VERSION")
        rewrite_header.setStyleSheet("color: #6c7086; font-size: 10px; font-weight: bold; letter-spacing: 1.5px;")
        layout.addWidget(rewrite_header)

        credit = QLabel("Rewritten by <b style='color:#cdd6f4;'>noxie</b> and <b style='color:#cdd6f4;'>Claude Sonnet 4.6</b>")
        credit.setStyleSheet("color: #9399b2; font-size: 12px;")
        credit.setTextFormat(Qt.RichText)
        layout.addWidget(credit)

        layout.addStretch()

        self.tabs.addTab(tab, 'About')

    def create_buttons(self):
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        reset_button = QPushButton('Reset to Saved')
        reset_button.setFixedHeight(38)
        reset_button.setStyleSheet("""
            QPushButton {
                background: #313244;
                color: #9399b2;
                border: 1px solid #45475a;
                border-radius: 8px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #45475a;
                color: #cdd6f4;
            }
            QPushButton:pressed {
                background: #181825;
            }
        """)
        reset_button.clicked.connect(self.reset_settings)

        save_button = QPushButton('Save Settings')
        save_button.setFixedHeight(38)
        save_button.clicked.connect(self.save_settings)

        btn_layout.addWidget(reset_button)
        btn_layout.addWidget(save_button)
        self.main_layout.addLayout(btn_layout)

    def add_setting_widget(self, layout, key, meta, category, sub_category=None):
        widget = self.create_widget_for_type(key, meta, category, sub_category)
        if not widget:
            return

        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(10, 6, 6, 6)
        row_layout.setSpacing(8)

        label = QLabel(key.replace('_', ' ').capitalize() + ':')
        label.setFixedWidth(175)
        label.setStyleSheet("color: #bac2de; font-size: 11px;")

        help_button = self.create_help_button(meta.get('description', ''), key)

        row_layout.addWidget(label)
        if isinstance(widget, QWidget):
            row_layout.addWidget(widget)
        else:
            row_layout.addLayout(widget)
        row_layout.addWidget(help_button)
        row_layout.addStretch()

        layout.addLayout(row_layout)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #313244; border: none;")
        layout.addWidget(sep)

        widget_name = f"{category}_{sub_category}_{key}_input" if sub_category else f"{category}_{key}_input"
        label_name = f"{category}_{sub_category}_{key}_label" if sub_category else f"{category}_{key}_label"
        help_name = f"{category}_{sub_category}_{key}_help" if sub_category else f"{category}_{key}_help"

        label.setObjectName(label_name)
        help_button.setObjectName(help_name)

        if isinstance(widget, QWidget):
            widget.setObjectName(widget_name)
        else:
            line_edit = widget.itemAt(0).widget()
            if isinstance(line_edit, QLineEdit):
                line_edit.setObjectName(widget_name)

    def create_widget_for_type(self, key, meta, category, sub_category):
        meta_type = meta.get('type')
        current_value = self.get_config_value(category, sub_category, key, meta)

        if meta_type == 'bool':
            return self.create_checkbox(current_value, key)
        elif meta_type == 'str' and 'options' in meta:
            return self.create_combobox(current_value, meta['options'], _OPTION_LABEL_MAPS.get(key))
        elif key == 'activation_key':
            widget = HotkeyCapture(str(current_value) if current_value else '')
            widget.setFixedWidth(200)
            return widget
        elif key == 'sound_device':
            return self.create_device_combobox(current_value)
        elif meta_type == 'str':
            return self.create_line_edit(current_value, key)
        elif meta_type == 'int':
            return self.create_spinbox(key, current_value)
        elif meta_type == 'float':
            return self.create_double_spinbox(key, current_value)
        return None

    def create_checkbox(self, value, key):
        widget = QCheckBox()
        widget.setChecked(bool(value))
        widget.setStyleSheet(
            "QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; "
            "border: 2px solid #7f849c; background: #313244; } "
            "QCheckBox::indicator:checked { background: #cba6f7; border-color: #cba6f7; "
            f"image: url({_CHECKMARK}); }} "
            "QCheckBox::indicator:hover { border-color: #cba6f7; } "
        )
        return widget

    def create_device_combobox(self, current_value):
        import sounddevice as sd
        widget = QComboBox()
        widget.setProperty('device_combo', True)
        widget.addItem('Default (system)', None)
        try:
            hostapis = sd.query_hostapis()
            wasapi_idx = next((i for i, h in enumerate(hostapis) if 'WASAPI' in h['name']), None)
            devices = sd.query_devices()
            for device in devices:
                if device['max_input_channels'] > 0 and device['hostapi'] == wasapi_idx:
                    widget.addItem(device['name'], device['name'])
        except Exception:
            pass
        if current_value:
            for i in range(widget.count()):
                if widget.itemData(i) == current_value:
                    widget.setCurrentIndex(i)
                    break
        widget.setFixedWidth(260)
        widget.setStyleSheet(
            "QComboBox { background-color: #45475a; color: #cdd6f4; border: 1px solid #7f849c; "
            "border-radius: 6px; padding: 5px 10px; } "
            "QComboBox:focus { border: 2px solid #cba6f7; } "
            "QComboBox::drop-down { border: none; width: 24px; } "
            f"QComboBox::down-arrow {{ image: url({_ARROW_DOWN}); width: 10px; height: 6px; }} "
            "QComboBox QAbstractItemView { background-color: #181825; color: #cdd6f4; "
            "border: 1px solid #45475a; selection-background-color: #cba6f7; selection-color: #1e1e2e; }"
        )
        return widget

    def create_combobox(self, value, options, label_map=None):
        widget = QComboBox()
        if label_map:
            for opt in options:
                widget.addItem(label_map.get(str(opt), str(opt)), str(opt))
            target = str(value) if value is not None else ''
            for i in range(widget.count()):
                if widget.itemData(i) == target:
                    widget.setCurrentIndex(i)
                    break
        else:
            widget.addItems([str(o) for o in options])
            widget.setCurrentText(str(value) if value is not None else '')
        widget.setFixedWidth(200)
        widget.setStyleSheet(
            "QComboBox { background-color: #45475a; color: #cdd6f4; border: 1px solid #7f849c; "
            "border-radius: 6px; padding: 5px 10px; } "
            "QComboBox:focus { border: 2px solid #cba6f7; } "
            "QComboBox::drop-down { border: none; width: 24px; } "
            f"QComboBox::down-arrow {{ image: url({_ARROW_DOWN}); width: 10px; height: 6px; }} "
            "QComboBox QAbstractItemView { background-color: #181825; color: #cdd6f4; "
            "border: 1px solid #45475a; selection-background-color: #cba6f7; selection-color: #1e1e2e; }"
        )
        return widget

    def create_spinbox(self, key, value):
        cfg = _SPINBOX_CONFIG.get(key, {})
        widget = QSpinBox()
        widget.setMinimum(cfg.get('min', 0))
        widget.setMaximum(cfg.get('max', 999999))
        widget.setSingleStep(cfg.get('step', 1))
        widget.setFixedWidth(120)
        widget.setValue(int(value) if value is not None else cfg.get('min', 0))
        widget.setStyleSheet("""
            QSpinBox {
                background: #313244;
                color: #cdd6f4;
                border: 1px solid #7f849c;
                border-radius: 6px;
                padding: 2px 6px;
                font-size: 11px;
            }
            QSpinBox:focus { border: 2px solid #cba6f7; }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 18px;
                background: #45475a;
                border: none;
                border-left: 1px solid #7f849c;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover { background: #585b70; }
            QSpinBox::up-arrow { image: url(""" + _ARROW_UP + """); width: 8px; height: 5px; }
            QSpinBox::down-arrow { image: url(""" + _ARROW_DOWN + """); width: 8px; height: 5px; }
        """)
        return widget

    def create_double_spinbox(self, key, value):
        cfg = _SPINBOX_CONFIG.get(key, {})
        widget = QDoubleSpinBox()
        widget.setMinimum(cfg.get('min', 0.0))
        widget.setMaximum(cfg.get('max', 9999.0))
        widget.setSingleStep(cfg.get('step', 0.1))
        widget.setDecimals(cfg.get('decimals', 2))
        widget.setFixedWidth(120)
        widget.setValue(float(value) if value is not None else cfg.get('min', 0.0))
        widget.setStyleSheet("""
            QDoubleSpinBox {
                background: #313244;
                color: #cdd6f4;
                border: 1px solid #7f849c;
                border-radius: 6px;
                padding: 2px 6px;
                font-size: 11px;
            }
            QDoubleSpinBox:focus { border: 2px solid #cba6f7; }
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                width: 18px;
                background: #45475a;
                border: none;
                border-left: 1px solid #7f849c;
            }
            QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover { background: #585b70; }
            QDoubleSpinBox::up-arrow { image: url(""" + _ARROW_UP + """); width: 8px; height: 5px; }
            QDoubleSpinBox::down-arrow { image: url(""" + _ARROW_DOWN + """); width: 8px; height: 5px; }
        """)
        return widget

    def create_line_edit(self, value, key=None):
        text = str(value) if value is not None else ''
        widget = QLineEdit(text)
        widget.setStyleSheet(
            "QLineEdit { background-color: #45475a; color: #cdd6f4; border: 1px solid #7f849c; "
            "border-radius: 6px; padding: 4px 8px; } "
            "QLineEdit:focus { border: 2px solid #cba6f7; } "
            "QLineEdit:disabled { background-color: #313244; color: #6c7086; border-color: #45475a; }"
        )

        if key == 'model_path':
            browse_button = QPushButton('Browse')
            browse_button.setFixedWidth(80)
            browse_button.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #cba6f7, stop:1 #a98de8);
                    color: #1e1e2e;
                    border: none;
                    border-radius: 8px;
                    padding: 5px 8px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #d4b1ff, stop:1 #b4befe);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #a98de8, stop:1 #9173c6);
                }
            """)
            browse_button.clicked.connect(lambda: self.browse_model_path(widget))

            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(6)
            row.addWidget(widget)
            row.addWidget(browse_button)

            container = QWidget()
            container.setLayout(row)
            container.setStyleSheet("background: transparent; border: none;")
            return container

        return widget

    def create_help_button(self, description, key=None):
        btn = QToolButton()
        btn.setText('?')
        btn.setFixedSize(20, 20)
        btn.setStyleSheet("""
            QToolButton {
                background: #313244;
                color: #cba6f7;
                border: 1px solid #585b70;
                border-radius: 10px;
                font-size: 10px;
                font-weight: bold;
            }
            QToolButton:hover {
                color: #1e1e2e;
                border-color: #cba6f7;
                background: #cba6f7;
            }
        """)
        tooltip = _HELP_TOOLTIPS.get(key, description)
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFocusPolicy(Qt.TabFocus)
        if key == 'model':
            btn.clicked.connect(self.show_model_help)
        elif key in _HELP_HTML:
            title, html = _HELP_HTML[key]
            btn.clicked.connect(lambda checked=False, t=title, h=html: self.show_html_help(t, h))
        else:
            btn.clicked.connect(lambda: self.show_description(description))
        return btn

    def show_model_help(self):
        dlg = QDialog(self)
        dlg.setWindowTitle('Model Selection Guide')
        dlg.setFixedSize(580, 440)
        dlg.setStyleSheet("""
            QDialog { background-color: #181825; }
            QPushButton { min-width: 80px; }
        """)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        browser = QTextBrowser()
        browser.setHtml(_MODEL_HELP_HTML)
        browser.setStyleSheet("""
            QTextBrowser {
                background-color: #181825;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
            }
            QScrollBar:vertical { background: #181825; width: 6px; border-radius: 3px; margin: 0; }
            QScrollBar::handle:vertical { background: #45475a; border-radius: 3px; min-height: 20px; }
            QScrollBar::handle:vertical:hover { background: #cba6f7; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)
        browser.setOpenExternalLinks(False)
        layout.addWidget(browser)

        ok_btn = QPushButton('OK')
        ok_btn.setFixedHeight(34)
        ok_btn.clicked.connect(dlg.accept)
        layout.addWidget(ok_btn, alignment=Qt.AlignRight)

        dlg.exec_()

    def show_html_help(self, title, html):
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.setFixedSize(520, 380)
        dlg.setStyleSheet("""
            QDialog { background-color: #181825; }
            QPushButton { min-width: 80px; }
        """)
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        browser = QTextBrowser()
        browser.setHtml(html)
        browser.setStyleSheet("""
            QTextBrowser {
                background-color: #181825;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
            }
            QScrollBar:vertical { background: #181825; width: 6px; border-radius: 3px; margin: 0; }
            QScrollBar::handle:vertical { background: #45475a; border-radius: 3px; min-height: 20px; }
            QScrollBar::handle:vertical:hover { background: #cba6f7; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)
        browser.setOpenExternalLinks(False)
        layout.addWidget(browser)
        ok_btn = QPushButton('OK')
        ok_btn.setFixedHeight(34)
        ok_btn.clicked.connect(dlg.accept)
        layout.addWidget(ok_btn, alignment=Qt.AlignRight)
        dlg.exec_()

    def get_config_value(self, category, sub_category, key, meta):
        if sub_category:
            val = ConfigManager.get_config_value(category, sub_category, key)
        else:
            val = ConfigManager.get_config_value(category, key)
        return val if val is not None else meta.get('value')

    def browse_model_path(self, widget):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Whisper Model File", "", "Model Files (*.bin);;All Files (*)"
        )
        if file_path:
            widget.setText(file_path)

    def show_description(self, description):
        msg = QMessageBox(self)
        msg.setWindowTitle('Setting Info')
        msg.setText(description)
        msg.setIcon(QMessageBox.Information)
        msg.setStyleSheet(
            "QMessageBox { background-color: #181825; } "
            "QLabel { color: #cdd6f4; } "
            "QPushButton { min-width: 80px; }"
        )
        msg.exec_()

    def save_settings(self):
        self.iterate_settings(self.save_setting)

        replacements = []
        for row in range(self.vocab_table.rowCount()):
            from_item = self.vocab_table.item(row, 0)
            to_item = self.vocab_table.item(row, 1)
            from_word = from_item.text().strip() if from_item else ''
            to_word = to_item.text().strip() if to_item else ''
            if from_word:
                replacements.append({'from': from_word, 'to': to_word})
        save_vocabulary(replacements)

        ConfigManager.save_config()

        msg = QMessageBox(self)
        msg.setWindowTitle('Saved')
        msg.setText('Settings saved. The application will restart.')
        msg.setIcon(QMessageBox.Information)
        msg.setStyleSheet(
            "QMessageBox { background-color: #181825; } "
            "QLabel { color: #cdd6f4; } "
            "QPushButton { min-width: 80px; }"
        )
        msg.exec_()
        self.settings_saved.emit()
        self.close()

    def save_setting(self, widget, category, sub_category, key, meta):
        value = self.get_widget_value_typed(widget, meta.get('type'))
        if sub_category:
            ConfigManager.set_config_value(value, category, sub_category, key)
        else:
            ConfigManager.set_config_value(value, category, key)

    def reset_settings(self):
        ConfigManager.reload_config()
        self.update_widgets_from_config()
        vocab = get_vocabulary()
        self.vocab_table.setRowCount(0)
        for entry in vocab:
            self._add_vocab_row(entry.get('from', ''), entry.get('to', ''))

    def update_widgets_from_config(self):
        self.iterate_settings(self.update_widget_value)

    def update_widget_value(self, widget, category, sub_category, key, meta):
        if sub_category:
            config_value = ConfigManager.get_config_value(category, sub_category, key)
        else:
            config_value = ConfigManager.get_config_value(category, key)
        self.set_widget_value(widget, config_value, meta.get('type'))

    def set_widget_value(self, widget, value, value_type):
        if isinstance(widget, QCheckBox):
            widget.setChecked(bool(value))
        elif isinstance(widget, QComboBox):
            target = str(value) if value is not None else None
            found = False
            for i in range(widget.count()):
                if widget.itemData(i) == target:
                    widget.setCurrentIndex(i)
                    found = True
                    break
            if not found and target is not None:
                widget.setCurrentText(target)
        elif isinstance(widget, QDoubleSpinBox):
            widget.setValue(float(value) if value is not None else 0.0)
        elif isinstance(widget, QSpinBox):
            widget.setValue(int(value) if value is not None else 0)
        elif isinstance(widget, HotkeyCapture):
            widget.setText(str(value) if value is not None else '')
        elif isinstance(widget, QLineEdit):
            widget.setText(str(value) if value is not None else '')
        elif isinstance(widget, QWidget) and widget.layout():
            line_edit = widget.layout().itemAt(0).widget()
            if isinstance(line_edit, QLineEdit):
                line_edit.setText(str(value) if value is not None else '')

    def get_widget_value_typed(self, widget, value_type):
        if isinstance(widget, QCheckBox):
            return widget.isChecked()
        elif isinstance(widget, QComboBox):
            if widget.property('device_combo'):
                return widget.currentData()
            data = widget.currentData()
            return data if data is not None else (widget.currentText() or None)
        elif isinstance(widget, QDoubleSpinBox):
            return widget.value()
        elif isinstance(widget, QSpinBox):
            return widget.value()
        elif isinstance(widget, HotkeyCapture):
            return widget.text() or None
        elif isinstance(widget, QLineEdit):
            text = widget.text()
            if value_type == 'int':
                return int(text) if text else None
            elif value_type == 'float':
                return float(text) if text else None
            return text or None
        elif isinstance(widget, QWidget) and widget.layout():
            line_edit = widget.layout().itemAt(0).widget()
            if isinstance(line_edit, QLineEdit):
                return line_edit.text() or None
        return None

    def iterate_settings(self, func):
        for category, settings in self.schema.items():
            for sub_category, sub_settings in settings.items():
                if isinstance(sub_settings, dict) and 'value' in sub_settings:
                    widget = self.findChild(QWidget, f"{category}_{sub_category}_input")
                    if widget:
                        func(widget, category, None, sub_category, sub_settings)
                else:
                    for key, meta in sub_settings.items():
                        widget = self.findChild(QWidget, f"{category}_{sub_category}_{key}_input")
                        if widget:
                            func(widget, category, sub_category, key, meta)

    def closeEvent(self, event):
        msg = QMessageBox(self)
        msg.setWindowTitle('Close Without Saving?')
        msg.setText('Close without saving changes?')
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        msg.setStyleSheet(
            "QMessageBox { background-color: #181825; } "
            "QLabel { color: #cdd6f4; } "
            "QPushButton { min-width: 80px; }"
        )
        reply = msg.exec_()

        if reply == QMessageBox.Yes:
            if hasattr(self, '_console_hook') and self._console_hook in _log_hooks:
                _log_hooks.remove(self._console_hook)
            ConfigManager.reload_config()
            self.update_widgets_from_config()
            self.settings_closed.emit()
            super().closeEvent(event)
        else:
            event.ignore()
