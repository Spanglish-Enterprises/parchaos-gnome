#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
# A minimal MPRIS media player on the session bus, for devshot plans (ticket #179). Test tool only.
#
#   fake-mpris.py "Title" "Artist" [seconds]   plays for that long (default 30), then stops

import sys

from gi.repository import Gio, GLib

XML = '''<node>
<interface name="org.mpris.MediaPlayer2">
  <method name="Raise"/><method name="Quit"/>
  <property name="Identity" type="s" access="read"/><property name="DesktopEntry" type="s" access="read"/>
  <property name="CanRaise" type="b" access="read"/><property name="CanQuit" type="b" access="read"/>
</interface>
<interface name="org.mpris.MediaPlayer2.Player">
  <method name="PlayPause"/><method name="Play"/><method name="Pause"/><method name="Next"/><method name="Previous"/>
  <property name="PlaybackStatus" type="s" access="read"/><property name="Metadata" type="a{sv}" access="read"/>
  <property name="CanPlay" type="b" access="read"/><property name="CanPause" type="b" access="read"/>
  <property name="CanGoNext" type="b" access="read"/><property name="CanGoPrevious" type="b" access="read"/>
</interface></node>'''
title, artist = sys.argv[1], sys.argv[2]
seconds = int(sys.argv[3]) if len(sys.argv) > 3 else 30
state = {'status': 'Playing'}
bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
PATH = '/org/mpris/MediaPlayer2'


def props(iface):
    if iface == 'org.mpris.MediaPlayer2':
        return {'Identity': GLib.Variant('s', 'Test Player'), 'DesktopEntry': GLib.Variant('s', 'org.gnome.Rhythmbox3'),
                'CanRaise': GLib.Variant('b', True), 'CanQuit': GLib.Variant('b', True)}
    return {'PlaybackStatus': GLib.Variant('s', state['status']),
            'Metadata': GLib.Variant('a{sv}', {'xesam:title': GLib.Variant('s', title),
                                               'xesam:artist': GLib.Variant('as', [artist]),
                                               'mpris:trackid': GLib.Variant('o', '/test/1')}),
            'CanPlay': GLib.Variant('b', True), 'CanPause': GLib.Variant('b', True),
            'CanGoNext': GLib.Variant('b', True), 'CanGoPrevious': GLib.Variant('b', True)}


def changed():
    bus.emit_signal(None, PATH, 'org.freedesktop.DBus.Properties', 'PropertiesChanged',
                    GLib.Variant('(sa{sv}as)', ('org.mpris.MediaPlayer2.Player',
                                                {'PlaybackStatus': GLib.Variant('s', state['status'])}, [])))


def call(conn, sender, path, iface, method, params, invocation):
    if method in ('PlayPause', 'Play', 'Pause'):
        state['status'] = 'Paused' if state['status'] == 'Playing' else 'Playing'
        print('status', state['status'], flush=True)
        changed()
    invocation.return_value(None)


for iface in Gio.DBusNodeInfo.new_for_xml(XML).interfaces:
    bus.register_object(PATH, iface, call, lambda c, s, p, i, n: props(i)[n], None)
Gio.bus_own_name_on_connection(bus, 'org.mpris.MediaPlayer2.devshot', Gio.BusNameOwnerFlags.NONE, None, None)
GLib.timeout_add_seconds(seconds, lambda: GLib.MainLoop().quit() or sys.exit(0))
GLib.MainLoop().run()
