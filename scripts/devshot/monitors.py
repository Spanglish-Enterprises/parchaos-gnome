#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Turns the virtual monitors of a devshot shell on and off through Mutter's DisplayConfig API,
# like unplugging and re-plugging a screen (ticket #181). Test tool only.
#
#   monitors.py first   only the first monitor
#   monitors.py all     every monitor, side by side

import sys

from gi.repository import Gio, GLib

bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)


def call(method, args=None, sig=None):
    return bus.call_sync('org.gnome.Mutter.DisplayConfig', '/org/gnome/Mutter/DisplayConfig',
                         'org.gnome.Mutter.DisplayConfig', method, args, sig and GLib.VariantType(sig),
                         Gio.DBusCallFlags.NONE, -1, None).unpack()


serial, monitors, _logical, _props = call('GetCurrentState')
chosen = monitors[:1] if sys.argv[1] == 'first' else monitors
layout, x = [], 0
for (connector, _vendor, _product, _serial), modes, _mprops in chosen:
    mode = next((m for m in modes if m[6].get('is-current')), None) or \
        next((m for m in modes if m[6].get('is-preferred')), modes[0])
    layout.append((x, 0, 1.0, 0, x == 0, [(connector, mode[0], {})]))
    x += mode[1]
call('ApplyMonitorsConfig', GLib.Variant('(uua(iiduba(ssa{sv}))a{sv})', (serial, 1, layout, {})))
print('monitors:', len(layout))
