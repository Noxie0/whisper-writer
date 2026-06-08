import os
import re
import yaml

VOCAB_FILE = os.path.join(os.path.dirname(__file__), 'vocabulary.yaml')

_vocab = None


def load_vocabulary():
    global _vocab
    if os.path.exists(VOCAB_FILE):
        with open(VOCAB_FILE, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
            _vocab = data.get('replacements', [])
    else:
        _vocab = []
    return _vocab


def save_vocabulary(replacements):
    global _vocab
    _vocab = replacements
    with open(VOCAB_FILE, 'w', encoding='utf-8') as f:
        yaml.dump({'replacements': replacements}, f, default_flow_style=False, allow_unicode=True)


def get_vocabulary():
    global _vocab
    if _vocab is None:
        load_vocabulary()
    return _vocab


def apply_vocabulary(text):
    for entry in get_vocabulary():
        from_word = entry.get('from', '').strip()
        to_word = entry.get('to', '').strip()
        if from_word:
            pattern = re.compile(re.escape(from_word), re.IGNORECASE)
            text = pattern.sub(to_word, text)
    return text
