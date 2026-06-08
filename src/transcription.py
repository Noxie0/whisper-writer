import os
import warnings
import numpy as np
from faster_whisper import WhisperModel

# faster-whisper passes deprecated local_dir_use_symlinks to snapshot_download
warnings.filterwarnings('ignore', message='.*local_dir_use_symlinks.*', category=UserWarning)

from utils import ConfigManager
from vocabulary import apply_vocabulary

_LOCAL_MODELS_DIR = os.path.join(os.path.expanduser("~"), ".cache", "whisperwriter_models")


def _model_cached_locally(model_name):
    local_dir = os.path.join(_LOCAL_MODELS_DIR, model_name.replace("/", "--"))
    return os.path.isfile(os.path.join(local_dir, "model.bin")), local_dir


def _validate_model_dir(local_dir):
    """Raise RuntimeError if model.bin is missing or empty (broken HF symlink cache)."""
    model_bin = os.path.join(local_dir, 'model.bin')
    if not os.path.isfile(model_bin):
        raise RuntimeError(
            f'model.bin not found in {local_dir}. '
            'Download may have failed — delete the folder and restart.')
    size = os.path.getsize(model_bin)
    if size == 0:
        raise RuntimeError(
            f'model.bin is 0 bytes in {local_dir}. '
            'HuggingFace symlink cache is broken — delete the folder and restart.')
    ConfigManager.console_print(f'model.bin OK ({size // 1024 // 1024} MB).')


def _download_without_symlinks(model_name):
    """Download model to flat local dir — bypasses WinError 1314 symlink restriction."""
    from faster_whisper.utils import download_model as fw_download
    cached, local_dir = _model_cached_locally(model_name)
    os.makedirs(local_dir, exist_ok=True)
    if not cached:
        ConfigManager.console_print(f'Downloading {model_name} to local cache: {local_dir}')
        fw_download(model_name, output_dir=local_dir)
        ConfigManager.console_print('Download complete.')
    else:
        ConfigManager.console_print(f'Using local model cache: {local_dir}')
    _validate_model_dir(local_dir)
    return local_dir


def create_local_model():
    ConfigManager.console_print('Creating local model...')
    local_model_options = ConfigManager.get_config_section('model_options')['local']
    compute_type = local_model_options['compute_type']
    model_path = local_model_options.get('model_path') or ''
    model_name = local_model_options['model']
    device = local_model_options['device']

    ConfigManager.console_print(f'Device: {device}, compute_type: {compute_type}')

    # Always use our flat local cache — avoids HF hub symlink cache which can produce
    # a broken directory structure on Windows without Developer Mode (WinError 1314).
    if model_path:
        load_path = model_path
        ConfigManager.console_print(f'Loading model from: {model_path}')
    else:
        load_path = _download_without_symlinks(model_name)

    ConfigManager.console_print(f'Initializing WhisperModel from {load_path}...')
    try:
        model = WhisperModel(load_path, device=device, compute_type=compute_type)
    except Exception as e:
        ConfigManager.console_print(f'Error loading model ({e}). Retrying with cpu/int8.')
        try:
            model = WhisperModel(load_path, device='cpu', compute_type='int8')
        except Exception as e2:
            raise RuntimeError(f'WhisperModel failed to load: {e2}') from e2

    ConfigManager.console_print('Local model created.')
    return model


def transcribe_local(audio_data, local_model=None):
    if not local_model:
        local_model = create_local_model()
    model_options = ConfigManager.get_config_section('model_options')

    audio_data_float = audio_data.astype(np.float32) / 32768.0

    response = local_model.transcribe(audio=audio_data_float,
                                      language=model_options['common']['language'],
                                      initial_prompt=model_options['common']['initial_prompt'],
                                      condition_on_previous_text=model_options['local']['condition_on_previous_text'],
                                      temperature=model_options['common']['temperature'],
                                      vad_filter=model_options['local']['vad_filter'],)
    return ''.join([segment.text for segment in list(response[0])])


def post_process_transcription(transcription):
    transcription = transcription.strip()
    transcription = apply_vocabulary(transcription)

    post_processing = ConfigManager.get_config_section('post_processing')
    if post_processing['remove_trailing_period'] and transcription.endswith('.'):
        transcription = transcription[:-1]
    if post_processing['add_trailing_space']:
        transcription += ' '
    if post_processing['remove_capitalization']:
        transcription = transcription.lower()

    return transcription


def transcribe(audio_data, local_model=None):
    if audio_data is None:
        return ''
    return post_process_transcription(transcribe_local(audio_data, local_model))
