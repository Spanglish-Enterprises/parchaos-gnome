import importlib.machinery
import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE = """Changelogs for parchaos-controls-1.0.0-12.fc44.noarch
* Wed Sep 30 12:00:00 2026 ParchaOS packaging - 1.0.0-12
- Ticket #135: the Glass style now looks better. A clear pane over the
  blurred background. Classic is unchanged.

* Tue Sep 29 12:00:00 2026 ParchaOS packaging - 1.0.0-11
- Ticket #130: a working Screenshot app.

Changelogs for parchaos-controls-1.0.0-13.fc44.noarch
* Wed Sep 30 13:00:00 2026 ParchaOS packaging - 1.0.0-13
- Glass values now follow the reference kit. More detail here.

Changelogs for glib2-2.90.0-1.fc44.x86_64
* Mon Sep 28 12:00:00 2026 Someone - 2.90.0-1
- Update to 2.90.0

Changelogs for parcher-48.7-28.fc44.x86_64
* Wed Sep 30 12:00:00 2026 ParchaOS packaging - 48.7-28
- Sidebar polish (ticket #145, stage 4): section headings in sentence case,
  rows with rounded corners.
"""


def load():
    path = os.path.join(HERE, '..', 'files', 'usr', 'bin', 'parchaos-updates-whatsnew')
    loader = importlib.machinery.SourceFileLoader('whatsnew', path)
    spec = importlib.util.spec_from_loader('whatsnew', loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class WhatsNew(unittest.TestCase):
    def test_only_parchaos_packages_and_newest_entry(self):
        items = load().parse(SAMPLE)
        self.assertEqual([p for p, _s in items], ['parchaos-controls', 'parcher'])

    def test_ticket_numbers_are_dropped_and_first_sentence_kept(self):
        items = dict(load().parse(SAMPLE))
        self.assertEqual(items['parchaos-controls'], 'Glass values now follow the reference kit.')
        self.assertEqual(items['parcher'], 'Sidebar polish: section headings in sentence case, rows with rounded corners.')


if __name__ == '__main__':
    unittest.main()
