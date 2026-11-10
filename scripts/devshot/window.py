#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
# A plain test window with the given title, for devshot plans. Test tool only.
import sys

import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk  # noqa: E402

app = Gtk.Application(application_id=None)
app.connect('activate', lambda a: Gtk.ApplicationWindow(application=a, title=sys.argv[1],
                                                         default_width=500, default_height=320).present())
app.run([])
