# SPDX-License-Identifier: GPL-3.0-or-later
# Tests for Parcha Automations (ticket #186). Run:
#   python3 packaging/parchaos-automations/tests/test_automations.py
import datetime
import importlib.machinery
import importlib.util
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
loader = importlib.machinery.SourceFileLoader('parchaos_automations', os.path.join(HERE, '..', 'parchaos-automations'))
spec = importlib.util.spec_from_loader('parchaos_automations', loader)
au = importlib.util.module_from_spec(spec)
loader.exec_module(au)

failures = 0


def check(ok, what):
    global failures
    if not ok:
        failures += 1
        print(f'FAIL {what}')


D = datetime.datetime
# 2026-11-16 is a Monday.
MON_0830, MON_0930, MON_1800 = D(2026, 11, 16, 8, 30), D(2026, 11, 16, 9, 30), D(2026, 11, 16, 18, 0)
SAT_1000 = D(2026, 11, 21, 10, 0)

# Files: write, read back, tidy.
with tempfile.TemporaryDirectory() as tmp:
    a = {'name': 'Work Focus', 'enabled': True,
         'trigger': {'Kind': 'time', 'At': '09:00', 'Until': '17:00', 'Days': 'mon,tue,wed,thu,fri'},
         'actions': [{'Kind': 'focus', 'Mode': 'work'}, {'Kind': 'appearance', 'Style': 'dark'}]}
    path = au.save(dict(a), tmp)
    check(os.path.basename(path) == 'work-focus.ini', 'file named after the automation')
    back = au.load(path)
    check(back['name'] == 'Work Focus' and back['enabled'], 'name and switch read back')
    check(back['trigger'] == a['trigger'], 'trigger read back')
    check(back['actions'] == a['actions'], 'two actions read back in order')
    check(au.save(dict(a), tmp).endswith('work-focus-2.ini'), 'a second one with the same name gets its own file')
    check(len(au.load_all(tmp)) == 2, 'load_all finds both')
    with open(os.path.join(tmp, 'broken.ini'), 'w') as f:
        f.write('not an automation\n')
    check(len(au.load_all(tmp)) == 2, 'a file without a trigger is skipped')
    off = au.load(au.save({'name': 'Off', 'enabled': False, 'trigger': {'Kind': 'app', 'App': 'x.desktop'},
                           'actions': []}, tmp))
    check(off['enabled'] is False, 'Enabled=false read back')

t = au.tidy({'name': 'x', 'trigger': {'Kind': 'folder', 'At': '09:00', 'Folder': '/tmp', 'Pattern': ''},
             'actions': [{'Kind': 'move', 'Mode': 'work', 'To': '/x'}]})
check(t['trigger'] == {'Kind': 'folder', 'Folder': '/tmp'}, 'tidy drops keys of another trigger kind and empties')
check(t['actions'] == [{'Kind': 'move', 'To': '/x'}], 'tidy drops keys of another action kind')

# Days and times.
check(au.days_of({'Days': ''}) == set(range(7)), 'no days means every day')
check(au.days_of({'Days': 'Mon, wednesday,FRI'}) == {0, 2, 4}, 'day names, any case or length')
check(au.parse_hhmm('9:05') == (9, 5) and au.parse_hhmm('24:00') is None and au.parse_hhmm('x') is None, 'HH:MM')

work = {'Kind': 'time', 'At': '09:00', 'Until': '17:00', 'Days': 'mon,tue,wed,thu,fri'}
check(au.lasting(work) and not au.lasting({'Kind': 'time', 'At': '09:00'}), 'Until makes a time last')
check(not au.time_active(work, MON_0830), 'before 9:00 is off')
check(au.time_active(work, MON_0930), 'inside the period is on')
check(not au.time_active(work, MON_1800), 'after 17:00 is off')
check(not au.time_active(work, SAT_1000), 'Saturday is off')
night = {'Kind': 'time', 'At': '22:00', 'Until': '07:00'}
check(au.time_active(night, D(2026, 11, 17, 3, 0)), 'a period past midnight is on at 3:00')
check(not au.time_active(night, D(2026, 11, 17, 12, 0)), 'and off at noon')
weekly = {'Kind': 'time', 'At': '17:00', 'Days': 'fri'}
check(au.next_time(weekly, MON_0930) == D(2026, 11, 20, 17, 0), 'next Friday 17:00')
check(au.next_time(work, MON_1800, 'Until') == D(2026, 11, 17, 17, 0), 'next Until')
check(au.last_time(weekly, SAT_1000) == D(2026, 11, 20, 17, 0), 'last Friday 17:00')

# Catch-up: a run missed while the computer was off.
check(au.missed(weekly, SAT_1000, D(2026, 11, 20, 12, 0)) == D(2026, 11, 20, 17, 0), 'missed Friday runs on Saturday')
check(au.missed(weekly, SAT_1000, D(2026, 11, 20, 18, 0)) is None, 'not again once seen after it')
check(au.missed(weekly, SAT_1000, None) is None, 'nothing on the very first start')
check(au.missed(weekly, D(2026, 11, 28, 16, 0), D(2026, 11, 1)) == D(2026, 11, 27, 17, 0),
      'off for weeks: runs once, for the latest time only')

# Displays.
laptop = {'connector': 'eDP-1', 'vendor': 'BOE', 'product': 'x', 'serial': '1', 'name': 'Built-in', 'builtin': True}
desk = {'connector': 'DP-3', 'vendor': 'ACI', 'product': 'ASUS VN247', 'serial': 'D6', 'name': 'ASUS 24"'}
proj = {'connector': 'HDMI-1', 'vendor': 'EPS', 'product': 'EPSON PJ', 'serial': '', 'name': 'Epson 14"'}
usual = {'Kind': 'display', 'Ignore': au.monitor_key(desk)}
check(not au.display_matches(usual, laptop), 'the built-in screen never counts')
check(not au.display_matches(usual, desk), 'a usual display does not count')
check(au.display_matches(usual, proj), 'a new display counts')
check(au.display_matches({'Kind': 'display', 'Match': 'epson'}, proj), 'Match by name, any case')
check(not au.display_matches({'Kind': 'display', 'Match': 'epson'}, desk), 'Match leaves others out')
tpl = au.templates([laptop, desk])
check(len(tpl) == 3, 'three ready-made automations')
check(tpl[2]['trigger']['Ignore'] == au.monitor_key(desk), 'the projector template treats current displays as usual')

# Networks and apps.
check(au.network_matches({'Name': 'The Force'}, {'The Force', 'Wired connection 1'}), 'network by name')
check(not au.network_matches({'Name': ''}, {'x'}), 'no name never matches')
procs = [('bash', ['/bin/bash']), ('gnome-calculato', ['/usr/bin/gnome-calculator']),
         ('bwrap', ['bwrap', '--args', '40', 'org.mozilla.firefox'])]
check(au.app_matches({'Exec': 'gnome-calculator'}, procs), 'app by its program')
check(au.app_matches({'App': 'org.mozilla.firefox.desktop'}, procs), 'a Flatpak app by its id')
check(not au.app_matches({'Exec': 'gimp'}, procs), 'an app that is not open')

# Folders and files.
check(au.file_matches({'Pattern': '*.pdf;*.PNG'}, 'Scan.png'), 'patterns, any case')
check(not au.file_matches({'Pattern': '*.pdf'}, 'a.png'), 'pattern leaves others out')
check(not au.file_matches({}, 'video.mp4.part') and not au.file_matches({}, '.hidden'), 'partial and hidden files wait')

with tempfile.TemporaryDirectory() as tmp:
    shots = os.path.join(tmp, 'Screenshots')
    os.makedirs(shots)
    old = time.mktime((2026, 10, 3, 12, 0, 0, 0, 0, -1))
    for name in ('Screenshot 1.png', 'Screenshot 2.png', 'notes.txt', 'new.png'):
        with open(os.path.join(shots, name), 'w') as f:
            f.write(name)
        if name != 'new.png':
            os.utime(os.path.join(shots, name), (old, old))
    os.makedirs(os.path.join(shots, '2026-10'))
    with open(os.path.join(shots, '2026-10', 'Screenshot 1.png'), 'w') as f:
        f.write('already there')
    move = {'Kind': 'move', 'From': shots, 'Pattern': '*.png', 'To': shots + '/{year}-{month}', 'OlderThan': '1'}
    n = au.move_files(move, [], D(2026, 11, 14, 17, 0))
    check(n == 2, f'moved the two old screenshots (moved {n})')
    left = sorted(os.listdir(shots))
    check(left == ['2026-10', 'new.png', 'notes.txt'], f'new and other files stay ({left})')
    month = sorted(os.listdir(os.path.join(shots, '2026-10')))
    check(month == ['Screenshot 1 2.png', 'Screenshot 1.png', 'Screenshot 2.png'], f'a taken name gets a number ({month})')
    with open(os.path.join(shots, '2026-10', 'Screenshot 1.png')) as f:
        check(f.read() == 'already there', 'nothing is overwritten')

    renamed = au.rename_file({'Name': '{date} {name}'}, os.path.join(shots, 'new.png'), D(2026, 11, 14))
    check(os.path.basename(renamed).endswith(' new.png') and os.path.exists(renamed), f'renamed with the date ({renamed})')

check(au.fill('{year}/{name}.{ext}', '', D(2026, 1, 2)) == '2026/.', 'fill without a file uses the time')
check(au.short_path(os.path.expanduser('~/Pictures')) == '~/Pictures', 'home shown as ~')

# Words.
check(au.describe_trigger(work) == 'From 09:00 to 17:00 on weekdays', au.describe_trigger(work))
check(au.describe_trigger(weekly) == 'At 17:00 on Fridays', au.describe_trigger(weekly))
check(au.describe_trigger({'Kind': 'time', 'At': '8:00', 'Days': 'sat,mon'}) == 'At 8:00 on Mon, Sat', 'two days')
check(au.describe_action({'Kind': 'focus', 'Mode': 'work'}) == 'Turn on Work Focus', 'focus words')
check(au.describe_action(tpl[1]['actions'][0]) ==
      'Move PNG, JPG, WEBM and MP4 files from Pictures/Screenshots into a folder for each month',
      au.describe_action(tpl[1]['actions'][0]))
check(au.describe_action({'Kind': 'move', 'From': '/x', 'Pattern': 'Scan*', 'To': '/y'}) ==
      'Move files like Scan* from /x to /y', 'odd patterns as written')

if failures:
    print(f'automations: {failures} failure(s)')
    sys.exit(1)
print('automations: all checks passed')
