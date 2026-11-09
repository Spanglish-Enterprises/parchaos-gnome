# SPDX-License-Identifier: GPL-3.0-or-later
# Tests for parchaos-app-leftovers with stub flatpak, notify-send and gio (no desktop needed).
import os
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, '..', 'files', 'usr', 'libexec', 'parchaos-app-leftovers')

STUBS = {
    'flatpak': '#!/bin/bash\n[ "$1" = info ] && { [ "$3" = org.example.Here ]; exit; }\n'
               '[ "$1" = remote-info ] && { echo "        Name: Gone App"; exit 0; }\nexit 1\n',
    'notify-send': '#!/bin/bash\n[ "$1" = --help ] && { echo "  -A, --action"; exit 0; }\n'
                   'printf "%s\\n" "$@" >> "$LOG"; echo "$CHOICE"\n',
    'gio': '#!/bin/bash\n[ "$1" = trash ] && mv "$2" "$TRASH/"\n',
}


class Leftovers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.home = os.path.join(self.tmp, 'home')
        self.apps = os.path.join(self.home, '.var', 'app')
        for name in ('org.example.Gone', 'org.example.Here', 'org.example.Kept', 'junk'):
            os.makedirs(os.path.join(self.apps, name))
        self.state = os.path.join(self.home, '.local', 'state')
        os.makedirs(os.path.join(self.state, 'parchaos'))
        with open(os.path.join(self.state, 'parchaos', 'app-leftovers-kept'), 'w') as f:
            f.write('org.example.Kept\n')
        bindir = os.path.join(self.tmp, 'bin')
        os.makedirs(bindir)
        for name, body in STUBS.items():
            path = os.path.join(bindir, name)
            with open(path, 'w') as f:
                f.write(body)
            os.chmod(path, 0o755)
        self.trash = os.path.join(self.tmp, 'trash')
        os.makedirs(self.trash)
        self.env = dict(os.environ, HOME=self.home, XDG_STATE_HOME=self.state, LOG=os.path.join(self.tmp, 'log'),
                        TRASH=self.trash, PATH=bindir + os.pathsep + os.environ['PATH'], LANGUAGE='C')

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_script(self, *args, choice=''):
        return subprocess.run(['bash', SCRIPT, *args], env=dict(self.env, CHOICE=choice),
                              capture_output=True, text=True, check=True).stdout

    def test_lists_only_uninstalled_flatpak_folders(self):
        self.assertEqual(self.run_script('--list').split(), ['org.example.Gone'])

    def test_dismissed_banner_changes_nothing(self):
        self.run_script()
        self.assertTrue(os.path.isdir(os.path.join(self.apps, 'org.example.Gone')))

    def test_keep_is_remembered(self):
        self.run_script(choice='keep')
        self.assertEqual(self.run_script('--list').split(), [])
        self.assertTrue(os.path.isdir(os.path.join(self.apps, 'org.example.Gone')))

    def test_trash_moves_the_folder_to_the_trash(self):
        self.run_script(choice='trash')
        self.assertFalse(os.path.exists(os.path.join(self.apps, 'org.example.Gone')))
        self.assertEqual(os.listdir(self.trash), ['org.example.Gone'])
        self.assertTrue(os.path.isdir(os.path.join(self.apps, 'org.example.Here')))

    def test_message_names_the_app(self):
        self.run_script()
        with open(self.env['LOG']) as f:
            self.assertIn('Gone App was uninstalled', f.read())


if __name__ == '__main__':
    unittest.main()
