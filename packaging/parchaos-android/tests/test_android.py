# SPDX-License-Identifier: GPL-3.0-or-later
# Tests for the Waydroid output parsers in parchaos-android (no display, no Waydroid needed).
import importlib.machinery
import importlib.util
import os
import sys
import unittest

try:
    import gi
    gi.require_version('Gtk', '4.0')
    gi.require_version('Adw', '1')
except (ImportError, ValueError):
    print('android: skipped (needs GTK 4 and libadwaita for Python)')
    sys.exit(0)

HERE = os.path.dirname(os.path.abspath(__file__))
loader = importlib.machinery.SourceFileLoader('parchaos_android', os.path.join(HERE, '..', 'files', 'parchaos-android'))
spec = importlib.util.spec_from_loader('parchaos_android', loader)
android = importlib.util.module_from_spec(spec)
loader.exec_module(android)

STATUS_RUNNING = 'Session:\tRUNNING\nContainer:\tRUNNING\nVendor type:\tMAINLINE\nIP address:\t192.168.240.112\n'
APP_LIST = '''Name: Settings
packageName: com.android.settings
categories:
\tandroid.intent.category.LAUNCHER
Name: F-Droid
packageName: org.fdroid.fdroid
categories:
\tandroid.intent.category.LAUNCHER
Name: aTalk
packageName: org.atalk.android
categories:
'''


class Parsers(unittest.TestCase):
    def test_status(self):
        s = android.parse_status(STATUS_RUNNING)
        self.assertEqual(s['Session'], 'RUNNING')
        self.assertEqual(s['Vendor type'], 'MAINLINE')
        self.assertEqual(android.parse_status('WayDroid is not initialized'), {})

    def test_apps_sorted_by_name(self):
        self.assertEqual(android.parse_apps(APP_LIST), [
            ('aTalk', 'org.atalk.android'), ('F-Droid', 'org.fdroid.fdroid'), ('Settings', 'com.android.settings')])

    def test_apps_empty_or_garbage(self):
        self.assertEqual(android.parse_apps(''), [])
        self.assertEqual(android.parse_apps('[gbinder] Service manager /dev/binder has appeared\n'), [])

    def test_last_line(self):
        self.assertEqual(android.last_line('a\n\nb error\n\n'), 'b error')
        self.assertEqual(android.last_line(''), '')


if __name__ == '__main__':
    unittest.main()
