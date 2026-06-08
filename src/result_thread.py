import time
import traceback
import numpy as np
import sounddevice as sd
import tempfile
import wave
import webrtcvad
from PyQt5.QtCore import QThread, QMutex, pyqtSignal
from collections import deque
from threading import Event

from transcription import transcribe
from utils import ConfigManager


def _resolve_device(name):
    """Resolve a device name to a specific device index.

    When multiple devices share the same name (MME/DirectSound/WASAPI), prefer
    MME (hostapi 0) because it resamples for us, avoiding sample-rate mismatches.
    Returns None (system default) when name is None/empty.
    """
    if not name:
        return None
    try:
        devices = sd.query_devices()
        hostapis = sd.query_hostapis()
        mme_idx = next((i for i, h in enumerate(hostapis) if h['name'] == 'MME'), None)
        ds_idx  = next((i for i, h in enumerate(hostapis) if 'DirectSound' in h['name']), None)

        candidates = [d for d in devices if d['max_input_channels'] > 0
                      and (name in d['name'] or d['name'] in name)]
        for preferred_hostapi in (mme_idx, ds_idx):
            match = next((d for d in candidates if d['hostapi'] == preferred_hostapi), None)
            if match:
                return match['index']
        if candidates:
            return candidates[0]['index']
    except Exception:
        pass
    return name


class ResultThread(QThread):
    """
    A thread class for handling audio recording, transcription, and result processing.

    This class manages the entire process of:
    1. Recording audio from the microphone
    2. Detecting speech and silence
    3. Saving the recorded audio as numpy array
    4. Transcribing the audio
    5. Emitting the transcription result

    Signals:
        statusSignal: Emits the current status of the thread (e.g., 'recording', 'transcribing', 'idle')
        resultSignal: Emits the transcription result
    """

    statusSignal = pyqtSignal(str)
    resultSignal = pyqtSignal(str)
    audioLevelSignal = pyqtSignal(float)

    def __init__(self, local_model=None):
        """
        Initialize the ResultThread.

        :param local_model: Local transcription model (if applicable)
        """
        super().__init__()
        self.local_model = local_model
        self.is_recording = False
        self.is_running = True
        self.sample_rate = None
        self.mutex = QMutex()
        self._last_level = 0.0

    def stop_recording(self):
        """Stop the current recording session."""
        self.mutex.lock()
        self.is_recording = False
        self.mutex.unlock()

    def stop(self):
        """Stop the entire thread execution."""
        self.mutex.lock()
        self.is_running = False
        self.mutex.unlock()
        self.statusSignal.emit('idle')
        self.wait()

    def run(self):
        """Main execution method for the thread."""
        try:
            if not self.is_running:
                return

            self.mutex.lock()
            self.is_recording = True
            self.mutex.unlock()

            self.statusSignal.emit('recording')
            ConfigManager.console_print('Recording...')
            audio_data = self._record_audio()

            if not self.is_running:
                return

            if audio_data is None:
                self.statusSignal.emit('idle')
                return

            self.statusSignal.emit('transcribing')
            ConfigManager.console_print('Transcribing...')

            # Time the transcription process
            start_time = time.time()
            result = transcribe(audio_data, self.local_model)
            end_time = time.time()

            transcription_time = end_time - start_time
            ConfigManager.console_print(f'Transcription completed in {transcription_time:.2f} seconds. Post-processed line: {result}')

            if not self.is_running:
                return

            self.statusSignal.emit('idle')
            self.resultSignal.emit(result)

        except Exception as e:
            traceback.print_exc()
            self.statusSignal.emit('error')
            self.resultSignal.emit('')
        finally:
            self.stop_recording()

    def _record_audio(self):
        """
        Record audio from the microphone and save it to a temporary file.

        :return: numpy array of audio data, or None if the recording is too short
        """
        recording_options = ConfigManager.get_config_section('recording_options')
        self.sample_rate = recording_options.get('sample_rate') or 16000
        frame_duration_ms = 30  # 30ms frame duration for WebRTC VAD
        frame_size = int(self.sample_rate * (frame_duration_ms / 1000.0))
        silence_duration_ms = recording_options.get('silence_duration') or 900
        silence_frames = int(silence_duration_ms / frame_duration_ms)
        min_duration_ms = recording_options.get('min_duration') or 100

        initial_frames_to_skip = int(0.15 * self.sample_rate / frame_size)

        recording_mode = recording_options.get('recording_mode') or 'continuous'
        sound_device_name = recording_options.get('sound_device') or '(system default)'
        device = _resolve_device(recording_options.get('sound_device'))

        ConfigManager.console_print(
            f'Recording config: mode={recording_mode!r}, sample_rate={self.sample_rate} Hz, '
            f'frame_size={frame_size} samples ({frame_duration_ms} ms), '
            f'silence_timeout={silence_duration_ms} ms ({silence_frames} frames), '
            f'min_duration={min_duration_ms} ms, '
            f'initial_skip={initial_frames_to_skip} frames'
        )
        ConfigManager.console_print(
            f'Audio device: {sound_device_name!r} → resolved index={device!r}'
        )

        vad = None
        if recording_mode in ('voice_activity_detection', 'continuous'):
            vad = webrtcvad.Vad(2)  # VAD aggressiveness: 0 to 3, 3 being the most aggressive
            speech_detected = False
            silent_frame_count = 0
            ConfigManager.console_print('VAD enabled (aggressiveness=2).')
        else:
            ConfigManager.console_print('VAD disabled for this recording mode.')

        audio_buffer = deque(maxlen=frame_size)
        recording = []

        data_ready = Event()

        def audio_callback(indata, frames, time, status):
            if status:
                ConfigManager.console_print(f"Audio callback status: {status}")
            audio_buffer.extend(indata[:, 0])
            rms = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2))) / 32768.0
            log_level = (np.log10(max(rms, 1e-5)) + 5.0) / 5.0
            self._last_level = float(np.clip(log_level, 0.0, 1.0))
            data_ready.set()

        with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype='int16',
                            blocksize=frame_size, device=device,
                            callback=audio_callback):
            ConfigManager.console_print('Audio stream opened. Listening...')
            while self.is_running and self.is_recording:
                data_ready.wait()
                data_ready.clear()
                self.audioLevelSignal.emit(self._last_level)

                if len(audio_buffer) < frame_size:
                    continue

                # Save frame
                frame = np.array(list(audio_buffer), dtype=np.int16)
                audio_buffer.clear()
                recording.extend(frame)

                # Avoid trying to detect voice in initial frames
                if initial_frames_to_skip > 0:
                    initial_frames_to_skip -= 1
                    continue

                if vad:
                    if vad.is_speech(frame.tobytes(), self.sample_rate):
                        silent_frame_count = 0
                        if not speech_detected:
                            ConfigManager.console_print("Speech detected.")
                            speech_detected = True
                    else:
                        silent_frame_count += 1

                    if speech_detected and silent_frame_count > silence_frames:
                        break

        audio_data = np.array(recording, dtype=np.int16)
        duration = len(audio_data) / self.sample_rate

        ConfigManager.console_print(
            f'Recording finished. Samples: {audio_data.size}, '
            f'Duration: {duration:.3f}s, min_duration: {min_duration_ms} ms'
        )

        if (duration * 1000) < min_duration_ms:
            ConfigManager.console_print(f'Discarded due to being too short.')
            return None

        return audio_data
