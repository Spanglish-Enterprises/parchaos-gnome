# SPDX-License-Identifier: GPL-3.0-or-later
# Tests for Parcha Reader (ticket #184). Run:
#   python3 packaging/parchaos-reader/tests/test_reader.py
import importlib.machinery
import importlib.util
import os
import sys
import tempfile
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
try:
    loader = importlib.machinery.SourceFileLoader('parchaos_reader', os.path.join(HERE, '..', 'parchaos-reader'))
    spec = importlib.util.spec_from_loader('parchaos_reader', loader)
    reader = importlib.util.module_from_spec(spec)
    loader.exec_module(reader)
except (ImportError, ValueError) as err:
    print(f'reader: skipped (GTK bindings unavailable: {err})')
    sys.exit(0)

failures = 0


def check(ok, what):
    global failures
    if not ok:
        failures += 1
        print(f'FAIL {what}')


# Pieces cover the text from the start point, in order, cut at sentence or paragraph ends.
text = ('First sentence here. ' * 80) + '\n\n' + ('Second paragraph words. ' * 80)
pieces = reader.chunks(text, 0, size=400)
check(''.join(p for _o, p in pieces) == text, 'pieces cover the whole text')
check(all(text[o:o + len(p)] == p for o, p in pieces), 'offsets match the text')
check(all(len(p) <= 400 for _o, p in pieces), 'no piece is too long')
check(all(p.endswith((' ', '\n')) for _o, p in pieces[:-1]), 'cut after a sentence or a line')
later = reader.chunks(text, 1000, size=400)
check(later[0][0] == 1000, 'starts where asked')
check(reader.chunks('   \n\n  ') == [], 'blank text gives nothing')

words = [(0, 4, 0), (5, 3, 400), (9, 5, 800)]
check(reader.word_at(words, 0) == (0, 4), 'first word at once')
check(reader.word_at(words, 650) == (5, 3), 'the word that has started')
check(reader.word_at(words, 5000) == (9, 5), 'the last word stays until the end')
check(reader.word_at([], 100) is None, 'no words')

# The real voice, when espeak-ng is installed: words come back with their places in the text.
try:
    voice = reader.Voice()
except OSError:
    voice = None
if voice is not None:
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, 'p.wav')
        piece = 'Hola, ¿cómo estás? El café está listo.'
        spoken = voice.speak_to_file(piece, 'es-419', 165, path)
        check([piece[s:s + n] for s, n, _ms in spoken][:3] == ['Hola', 'cómo', 'estás'], f'word places (got {spoken})')
        check(all(a[2] <= b[2] for a, b in zip(spoken, spoken[1:])), 'moments in order')
        with wave.open(path) as w:
            check(w.getnframes() > w.getframerate() // 2, 'audio written')
else:
    print('reader: voice checks skipped (espeak-ng not installed)')

print('reader: all checks passed' if failures == 0 else f'reader: {failures} check(s) failed')
sys.exit(0 if failures == 0 else 1)
