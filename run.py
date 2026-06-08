import os
import sys
import subprocess
from dotenv import load_dotenv

# Add all nvidia CUDA DLLs (cuDNN, cuBLAS, etc.) to PATH so ctranslate2 can find them
_nvidia_dir = os.path.normpath(os.path.join(os.path.dirname(sys.executable), '..', 'Lib', 'site-packages', 'nvidia'))
if os.path.isdir(_nvidia_dir):
    for _pkg in os.listdir(_nvidia_dir):
        _bin = os.path.join(_nvidia_dir, _pkg, 'bin')
        if os.path.isdir(_bin):
            os.environ['PATH'] = _bin + os.pathsep + os.environ.get('PATH', '')

_ROOT = os.path.dirname(os.path.abspath(__file__))

# Suppress huggingface_hub noise: symlink warning (Windows without Developer Mode)
# and unauthenticated-request notice (not needed for public model downloads).
os.environ.setdefault('HF_HUB_DISABLE_SYMLINKS_WARNING', '1')
os.environ.setdefault('HF_HUB_VERBOSITY', 'error')

print('Starting WhisperWriter...')
load_dotenv()
subprocess.run([sys.executable, os.path.join(_ROOT, 'src', 'main.py')], cwd=_ROOT)
