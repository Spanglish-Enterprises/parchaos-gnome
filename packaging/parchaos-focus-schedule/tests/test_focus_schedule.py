# SPDX-License-Identifier: GPL-3.0-or-later
# Tests for the scheduled Do Not Disturb time logic (tickets #63, #70). Run:
#   python3 packaging/parchaos-focus-schedule/tests/test_focus_schedule.py
import importlib.machinery
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, '..', 'files', 'usr', 'bin', 'parchaos-focus-schedule')
loader = importlib.machinery.SourceFileLoader('focus_schedule', PATH)
spec = importlib.util.spec_from_loader('focus_schedule', loader)
try:
    fs = importlib.util.module_from_spec(spec)
    loader.exec_module(fs)
except (ImportError, ValueError) as err:
    print(f'focus-schedule: skipped (GLib bindings unavailable: {err})')
    sys.exit(0)

failures = 0


def check(ok, what):
    global failures
    if not ok:
        failures += 1
        print(f'FAIL {what}')


def main():
    m = fs.minutes
    for text, want in (('22:00', 1320), ('08:00', 480), ('00:00', 0), ('23:59', 1439), (' 07:30 ', 450), ('7:05', 425)):
        check(m(text) == want, f'minutes({text!r}) == {want}, got {m(text)}')
    for bad in ('', '24:00', '12:60', 'noon', '12', '12:xx', '-1:00', '12:30:00'):
        check(m(bad) is None, f'minutes({bad!r}) is None, got {m(bad)}')

    w = fs.in_window
    # Same-day window 09:00 to 17:00: start is in, end is out.
    check(w(540, 540, 1020), 'the start minute is inside')
    check(not w(1020, 540, 1020), 'the end minute is outside')
    check(w(600, 540, 1020) and not w(539, 540, 1020) and not w(1200, 540, 1020), 'a same-day window')
    # Window past midnight, 22:00 to 08:00.
    start, end = m('22:00'), m('08:00')
    check(w(m('23:30'), start, end), '23:30 is inside 22:00-08:00')
    check(w(m('00:00'), start, end), 'midnight is inside 22:00-08:00')
    check(w(m('07:59'), start, end), '07:59 is inside 22:00-08:00')
    check(not w(m('08:00'), start, end), '08:00 is outside 22:00-08:00')
    check(not w(m('12:00'), start, end), 'noon is outside 22:00-08:00')
    check(w(m('22:00'), start, end), '22:00 is inside 22:00-08:00')
    check(not w(m('21:59'), start, end), '21:59 is outside 22:00-08:00')
    # Start equal to end means no focus time at all (never all day).
    check(not any(w(t, 480, 480) for t in range(1440)), 'start equal to end is never on')

    print('focus-schedule: all checks passed' if failures == 0 else f'focus-schedule: {failures} check(s) failed')
    return 0 if failures == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
