# SPDX-License-Identifier: GPL-3.0-or-later
# Translation checks for ParchaOS Settings (ticket #53). Run:
#   python3 packaging/parchaos-settings/tests/test_i18n.py
#  1. every string shown to the user goes through _();
#  2. po/parchaos-settings.pot lists exactly the strings in the code;
#  3. a catalog for another language really changes what _() returns.
import ast
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, '..', 'files', 'parchaos-settings')
POT = os.path.join(HERE, '..', 'po', 'parchaos-settings.pot')
KEYWORDS = {'title', 'subtitle', 'description', 'placeholder_text'}
SETTERS = {'set_title', 'set_subtitle'}
failures = 0


def check(ok, what):
    global failures
    if not ok:
        failures += 1
        print(f'FAIL {what}')


def is_gettext_call(node):
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == '_'


def unwrapped_strings(tree):
    """Constant strings given to user-visible parameters without _()."""
    found = []

    def visit(node, line):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.strip():
            found.append((node.lineno, node.value))
        elif isinstance(node, ast.IfExp):
            visit(node.body, line)
            visit(node.orelse, line)
        elif isinstance(node, ast.BoolOp):
            for v in node.values:
                visit(v, line)
        elif isinstance(node, ast.JoinedStr):
            found.append((node.lineno, 'f-string'))

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for kw in node.keywords:
            if kw.arg in KEYWORDS:
                visit(kw.value, kw.value.lineno)
        if isinstance(node.func, ast.Attribute) and node.func.attr in SETTERS and node.args:
            visit(node.args[0], node.args[0].lineno)
    return found


def main():
    with open(SCRIPT, encoding='utf-8') as f:
        source = f.read()
    tree = ast.parse(source)

    for line, text in unwrapped_strings(tree):
        check(False, f'line {line}: "{text}" is shown to the user without _()')
    check("gettext.textdomain('parchaos-settings')" in source, 'the gettext domain is set')
    check('_ = gettext.gettext' in source, '_ is defined')
    check(not re.search(r"_\(f['\"]", source), 'no f-string is passed to _() (it cannot be extracted)')

    if shutil.which('xgettext') is None:
        print('i18n: skipped the template and catalog checks (xgettext not installed)')
        return 1 if failures else 0

    with tempfile.TemporaryDirectory() as tmp:
        fresh = os.path.join(tmp, 'fresh.pot')
        subprocess.run(['xgettext', '--language=Python', '--from-code=UTF-8', '--keyword=_', '--add-comments',
                        '--package-name=parchaos-settings',
                        '--msgid-bugs-address=https://github.com/Spanglish-Enterprises/parchaos-gnome/issues',
                        '-o', fresh, SCRIPT], check=True)

        def msgids(path):
            with open(path, encoding='utf-8') as f:
                return sorted(re.findall(r'(?m)^msgid (.*)$', f.read()))
        check(msgids(fresh) == msgids(POT), 'po/parchaos-settings.pot is out of date: run packaging/parchaos-settings/update-pot.sh')

        # A catalog for a made-up language changes what _() returns.
        po = os.path.join(tmp, 'xx.po')
        with open(POT, encoding='utf-8') as f:
            text = f.read()
        text = re.sub(r'(?m)^msgstr ""\n(?!")', 'msgstr ""\n', text)
        entries = re.findall(r'(?m)^msgid "(.+)"\nmsgstr ""$', text)
        with open(po, 'w', encoding='utf-8') as f:
            f.write('msgid ""\nmsgstr ""\n"Content-Type: text/plain; charset=UTF-8\\n"\n"Language: xx\\n"\n\n')
            f.write('msgid "Keyboard"\nmsgstr "[Keyboard]"\n')
        mo_dir = os.path.join(tmp, 'locale', 'xx', 'LC_MESSAGES')
        os.makedirs(mo_dir)
        subprocess.run(['msgfmt', po, '-o', os.path.join(mo_dir, 'parchaos-settings.mo')], check=True)
        probe = ('import gettext, os;'
                 'gettext.bindtextdomain("parchaos-settings", os.environ["LOC"]);'
                 'gettext.textdomain("parchaos-settings");'
                 'print(gettext.gettext("Keyboard"), gettext.gettext("Not translated"))')
        out = subprocess.run([sys.executable, '-c', probe], capture_output=True, text=True,
                             env={**os.environ, 'LOC': os.path.join(tmp, 'locale'), 'LANGUAGE': 'xx', 'LC_ALL': 'C.UTF-8'}).stdout.strip()
        check(out == '[Keyboard] Not translated', f'a catalog changes translated strings only (got: {out})')

    print('i18n: all checks passed' if failures == 0 else f'i18n: {failures} check(s) failed')
    return 0 if failures == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
