#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
# A stand-in for UPower (one laptop battery) and power-profiles-daemon on a private bus, for
# testing the battery menu headless (ticket #174). Run on the bus given as the shell's system bus:
#
#   DBUS_SYSTEM_BUS_ADDRESS=... fake-power.py [percentage] [state]
#
# state is a UPower device state: 1 charging, 2 discharging, 4 fully charged. The active power
# profile is written to $FAKE_POWER_LOG whenever it changes, so a test can check the switch.

import os
import sys

from gi.repository import Gio, GLib

DEVICE_XML = '''<node><interface name="org.freedesktop.UPower.Device">
  <property name="Type" type="u" access="read"/>
  <property name="IsPresent" type="b" access="read"/>
  <property name="Percentage" type="d" access="read"/>
  <property name="State" type="u" access="read"/>
  <property name="TimeToEmpty" type="x" access="read"/>
  <property name="TimeToFull" type="x" access="read"/>
  <property name="IconName" type="s" access="read"/>
  <property name="IsRechargeable" type="b" access="read"/>
  <property name="PowerSupply" type="b" access="read"/>
  <property name="BatteryLevel" type="u" access="read"/>
  <property name="WarningLevel" type="u" access="read"/>
</interface></node>'''

UPOWER_XML = '''<node><interface name="org.freedesktop.UPower">
  <method name="GetDisplayDevice"><arg name="device" type="o" direction="out"/></method>
  <method name="EnumerateDevices"><arg name="devices" type="ao" direction="out"/></method>
  <method name="GetCriticalAction"><arg name="action" type="s" direction="out"/></method>
  <property name="OnBattery" type="b" access="read"/>
  <property name="LidIsPresent" type="b" access="read"/>
  <property name="LidIsClosed" type="b" access="read"/>
  <property name="DaemonVersion" type="s" access="read"/>
</interface></node>'''

PROFILES_XML = '''<node><interface name="org.freedesktop.UPower.PowerProfiles">
  <property name="ActiveProfile" type="s" access="readwrite"/>
  <property name="Profiles" type="aa{sv}" access="read"/>
  <property name="PerformanceDegraded" type="s" access="read"/>
  <property name="Actions" type="as" access="read"/>
  <property name="ActiveProfileHolds" type="aa{sv}" access="read"/>
</interface></node>'''

DISPLAY = '/org/freedesktop/UPower/devices/DisplayDevice'
pct = float(sys.argv[1]) if len(sys.argv) > 1 else 64
state = int(sys.argv[2]) if len(sys.argv) > 2 else 2
icon = f'battery-level-{int(pct // 10 * 10)}{"-charging" if state == 1 else ""}-symbolic'
device = {
    'Type': GLib.Variant('u', 2), 'IsPresent': GLib.Variant('b', True), 'Percentage': GLib.Variant('d', pct),
    'State': GLib.Variant('u', state), 'TimeToEmpty': GLib.Variant('x', 12000 if state == 2 else 0),
    'TimeToFull': GLib.Variant('x', 2700 if state == 1 else 0), 'IconName': GLib.Variant('s', icon),
    'IsRechargeable': GLib.Variant('b', True), 'PowerSupply': GLib.Variant('b', True),
    'BatteryLevel': GLib.Variant('u', 1), 'WarningLevel': GLib.Variant('u', 1),
}
upower = {
    'OnBattery': GLib.Variant('b', state == 2), 'LidIsPresent': GLib.Variant('b', True),
    'LidIsClosed': GLib.Variant('b', False), 'DaemonVersion': GLib.Variant('s', '1.90.9'),
}
profile = {'value': 'balanced'}


def profiles_props():
    choices = [{'Profile': GLib.Variant('s', p), 'Driver': GLib.Variant('s', 'placeholder')}
               for p in ('power-saver', 'balanced', 'performance')]
    return {
        'ActiveProfile': GLib.Variant('s', profile['value']), 'Profiles': GLib.Variant('aa{sv}', choices),
        'PerformanceDegraded': GLib.Variant('s', ''), 'Actions': GLib.Variant('as', []),
        'ActiveProfileHolds': GLib.Variant('aa{sv}', []),
    }


def log_profile():
    if os.environ.get('FAKE_POWER_LOG'):
        with open(os.environ['FAKE_POWER_LOG'], 'w') as f:
            f.write(profile['value'] + '\n')


def main():
    bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)

    def register(path, xml, props, methods=None, settable=False):
        iface = Gio.DBusNodeInfo.new_for_xml(xml).interfaces[0]

        def call(conn, sender, obj, iface_name, method, params, invocation):
            invocation.return_value(methods[method]())

        def get(conn, sender, obj, iface_name, name):
            return props()[name]

        def set_(conn, sender, obj, iface_name, name, value):
            if not settable or name != 'ActiveProfile':
                return False
            profile['value'] = value.unpack()
            log_profile()
            conn.emit_signal(None, obj, 'org.freedesktop.DBus.Properties', 'PropertiesChanged',
                             GLib.Variant('(sa{sv}as)', (iface_name, {name: value}, [])))
            return True
        bus.register_object(path, iface, call, get, set_)

    register(DISPLAY, DEVICE_XML, lambda: device)
    register('/org/freedesktop/UPower', UPOWER_XML, lambda: upower, {
        'GetDisplayDevice': lambda: GLib.Variant('(o)', (DISPLAY,)),
        'EnumerateDevices': lambda: GLib.Variant('(ao)', ([],)),
        'GetCriticalAction': lambda: GLib.Variant('(s)', ('PowerOff',)),
    })
    register('/org/freedesktop/UPower/PowerProfiles', PROFILES_XML, profiles_props, settable=True)
    for name in ('org.freedesktop.UPower', 'org.freedesktop.UPower.PowerProfiles'):
        Gio.bus_own_name_on_connection(bus, name, Gio.BusNameOwnerFlags.NONE, None, None)
    log_profile()
    GLib.MainLoop().run()


if __name__ == '__main__':
    main()
