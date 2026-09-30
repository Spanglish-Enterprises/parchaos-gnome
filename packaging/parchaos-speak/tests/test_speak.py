# SPDX-License-Identifier: GPL-3.0-or-later
# Tests for parchaos-speak-say (ticket #162). Run:
#   python3 packaging/parchaos-speak/tests/test_speak.py
import importlib.machinery
import importlib.util
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, '..', 'parchaos-speak-say')
loader = importlib.machinery.SourceFileLoader('parchaos_speak_say', SCRIPT)
spec = importlib.util.spec_from_loader('parchaos_speak_say', loader)
tool = importlib.util.module_from_spec(spec)
loader.exec_module(tool)

failures = 0


def check(ok, what):
    global failures
    if not ok:
        failures += 1
        print(f'FAIL {what}')


V = tool.voice_for
check(V('The quick brown fox jumps over the lazy dog and it was fine.') == 'en-us', 'english')
check(V('El perro corre por el parque con la niña y su mamá.') == 'es-419', 'spanish')
check(V('¿Dónde está la biblioteca?') == 'es-419', 'spanish question')
check(V('Hola') == 'en-us' or V('Hola') == 'es-419', 'short text does not crash')
check(V('12345 !!!') == 'en-us', 'no words -> english')
check(V('I said sí to the plan that we have') == 'en-us', 'mostly english with one Spanish word')

check(tool.clean('see https://example.com/a?b=1 now\n\n  ok') == 'see link now ok', 'links and space')
check(len(tool.clean('a ' * 50000)) <= tool.MAX_CHARS, 'length cap')

# End to end with a stand-in engine that records what it was given.
tmp = tempfile.mkdtemp()
engine = os.path.join(tmp, 'espeak-ng')
log = os.path.join(tmp, 'log')
with open(engine, 'w') as f:
    f.write(f'#!/bin/sh\necho "$@" > {log}\ncat >> {log}\n')
os.chmod(engine, 0o755)
env = dict(os.environ, PATH=tmp + ':' + os.environ['PATH'])
r = subprocess.run([SCRIPT, '--speed', '500'], input=b'Hola, \xc2\xbfc\xc3\xb3mo est\xc3\xa1s? Yo estoy muy bien.',
                   env=env)
said = open(log).read()
check(r.returncode == 0, 'runs')
check('-v es-419' in said and '-s 300' in said, 'voice and capped speed: ' + said.splitlines()[0])
check('Yo estoy muy bien' in said, 'text passed on stdin')
r = subprocess.run([SCRIPT], input=b'   ', env=env)
check(r.returncode == 0, 'empty text is fine')

sys.exit(1 if failures else 0)
