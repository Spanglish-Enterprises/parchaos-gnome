# SPDX-License-Identifier: GPL-3.0-or-later
# Tests for the pure helpers in parchaos-gaming (no display, no flatpak needed).
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
    print('gaming: skipped (needs GTK 4 and libadwaita for Python)')
    sys.exit(0)

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, '..', 'files', 'parchaos-gaming')
loader = importlib.machinery.SourceFileLoader('parchaos_gaming', PATH)
spec = importlib.util.spec_from_loader('parchaos_gaming', loader)
gaming = importlib.util.module_from_spec(spec)
loader.exec_module(gaming)


class Helpers(unittest.TestCase):
    def test_runtime_of(self):
        text = '        ID: com.valvesoftware.Steam\n   Runtime: org.freedesktop.Platform/x86_64/26.08\n'
        self.assertEqual(gaming.runtime_of(text), 'org.freedesktop.Platform/x86_64/26.08')
        self.assertEqual(gaming.runtime_of('nothing here'), '')

    def test_layer_branches_only_freedesktop(self):
        runtimes = ['org.freedesktop.Platform/x86_64/26.08', 'org.gnome.Platform/x86_64/51',
                    'org.freedesktop.Platform/x86_64/26.08', '', 'org.freedesktop.Platform/x86_64/25.08']
        self.assertEqual(gaming.layer_branches(runtimes), ['25.08', '26.08'])

    def test_layer_refs(self):
        self.assertEqual(gaming.layer_refs(['26.08']), [
            'runtime/org.freedesktop.Platform.VulkanLayer.MangoHud/x86_64/26.08',
            'runtime/org.freedesktop.Platform.VulkanLayer.gamescope/x86_64/26.08'])

    def test_install_command_is_system_and_noninteractive(self):
        cmd = gaming.install_command(['com.valvesoftware.Steam'])
        self.assertIn('--system', cmd)
        self.assertIn('--noninteractive', cmd)
        self.assertEqual(cmd[-2:], ['flathub', 'com.valvesoftware.Steam'])

    def test_steam_is_the_only_default(self):
        defaults = [app_id for app_id, _n, _d, on in gaming.LAUNCHERS if on]
        self.assertEqual(defaults, ['com.valvesoftware.Steam'])


if __name__ == '__main__':
    unittest.main()
