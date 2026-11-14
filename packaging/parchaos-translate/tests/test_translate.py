# SPDX-License-Identifier: GPL-3.0-or-later
# Tests for Parcha Translate (ticket #152). Run:
#   python3 packaging/parchaos-translate/tests/test_translate.py
# With PARCHAOS_TRANSLATE_DATA pointing at downloaded models and the engine importable, the
# last part also translates real sentences.
import importlib.machinery
import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
loader = importlib.machinery.SourceFileLoader('parchaos_translate', os.path.join(HERE, '..', 'parchaos-translate'))
spec = importlib.util.spec_from_loader('parchaos_translate', loader)
tr = importlib.util.module_from_spec(spec)
loader.exec_module(tr)

failures = 0


def check(ok, what):
    global failures
    if not ok:
        failures += 1
        print(f'FAIL {what}')


# Which language the text is in.
for text, want in (('Where is the library?', 'en'), ('¿Dónde está la biblioteca?', 'es'),
                   ('The meeting is on Friday.', 'en'), ('La reunión es el viernes.', 'es'),
                   ('Gracias', 'es'), ('thanks', 'en'), ('Mañana', 'es'), ('OK', 'en'),
                   ('Necesito devolver dos libros antes del lunes', 'es')):
    check(tr.detect(text) == want, f'detect {text!r}')
check(tr.target_for('es') == 'en' and tr.target_for('en') == 'es', 'into the other language')

# Sentences and paragraphs come back laid out as they were.
text = 'Hello there. How are you? Fine!\n\nSecond paragraph.\nThird line'
pieces = tr.split_text(text)
check([p for p, _g in pieces] == ['Hello there.', 'How are you?', 'Fine!', 'Second paragraph.', 'Third line'],
      f'split ({pieces})')
check(tr.join_text(pieces) == text, 'joined back exactly')
check(tr.join_text([(p.upper(), g) for p, g in pieces]) == text.upper(), 'layout kept around new text')
check(tr.join_text(tr.split_text('Dr. Smith arrived at 3 p.m. today. ¿Qué tal? Bien.')) ==
      'Dr. Smith arrived at 3 p.m. today. ¿Qué tal? Bien.', 'abbreviations: text survives the split')
check([p for p, _g in tr.split_text('Version 2.5 is out')] == ['Version 2.5 is out'], 'no split inside numbers')
check([p for p, _g in tr.split_text('¡Hola! ¿Cómo estás?')] == ['¡Hola!', '¿Cómo estás?'], 'Spanish openers')
check(tr.split_text('') == [] and tr.split_text('  \n ') == [], 'nothing to split')

# The download list: two directions, every file pinned with a size and a SHA-256.
check(set(tr.MODELS) == {'en-es', 'es-en'}, 'both directions')
for pair, (repo, rev, files) in tr.MODELS.items():
    check(len(rev) == 40 and all(len(sha) == 64 and size > 0 for _p, size, sha in files.values()),
          f'{pair} pinned')
    check({'encoder.onnx', 'decoder.onnx', 'source.spm', 'target.spm', 'vocab.json', 'config.json'} == set(files),
          f'{pair} files')
check(200e6 < tr.total_download() < 260e6, f'about 230 MB ({tr.total_download()})')

# Downloads are checked: a file that doesn't match is thrown away.
with tempfile.TemporaryDirectory() as d:
    saved = tr.DATA, tr.MODELS
    tr.DATA = d
    src = os.path.join(d, 'src')
    os.makedirs(os.path.join(src, 'r', 'resolve', 'v'))
    with open(os.path.join(src, 'r', 'resolve', 'v', 'a'), 'wb') as f:
        f.write(b'hello')
    import hashlib
    good = hashlib.sha256(b'hello').hexdigest()
    tr.MODELS = {'en-es': ('r', 'v', {'a': ('a', 5, good)})}
    tr.download(base='file://' + src + '/')
    check(open(os.path.join(d, 'en-es', 'a'), 'rb').read() == b'hello', 'a good file is kept')
    tr.MODELS = {'es-en': ('r', 'v', {'a': ('a', 5, '0' * 64)})}
    try:
        tr.download(base='file://' + src + '/')
        check(False, 'a bad file is refused')
    except RuntimeError:
        check(not os.listdir(os.path.join(d, 'es-en')), 'and nothing is left behind')
    tr.DATA, tr.MODELS = saved

# Real translations, when the engine and models are here.
if os.environ.get('PARCHAOS_TRANSLATE_DATA') and tr.status() == 'ready':
    src, to, out = tr.translate('Where is the library? I need to return two books before Monday.')
    check((src, to) == ('en', 'es') and 'biblioteca' in out and 'lunes' in out, f'en -> es ({out})')
    src, to, out = tr.translate('La computadora se reinició sola anoche.\n\nMañana revisamos los registros.')
    check((src, to) == ('es', 'en') and 'computer' in out.lower() and '\n\n' in out, f'es -> en ({out})')
    src, to, out = tr.translate('Hola', to='es')
    check((src, to) == ('en', 'es'), 'asking for the language it is already in translates from the other')
    print('translate: real model checked')

if failures:
    print(f'translate: {failures} failure(s)')
    sys.exit(1)
print('translate: all checks passed')
