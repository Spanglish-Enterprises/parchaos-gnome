# SPDX-License-Identifier: GPL-3.0-or-later
# Tests for parchaos-policy (ticket #168). Run:
#   python3 packaging/parchaos-policy/tests/test_policy.py
import importlib.machinery
import importlib.util
import io
import os
import sys
import tempfile
import tomllib
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = tempfile.mkdtemp()
os.environ['PARCHAOS_POLICY_ROOT'] = ROOT
loader = importlib.machinery.SourceFileLoader('parchaos_policy', os.path.join(HERE, '..', 'parchaos-policy'))
spec = importlib.util.spec_from_loader('parchaos_policy', loader)
pol = importlib.util.module_from_spec(spec)
loader.exec_module(pol)

failures = 0


def check(ok, what):
    global failures
    if not ok:
        failures += 1
        print(f'FAIL {what}')


TYPES = {
    '/org/parchaos/desktop/style': 's', '/org/parchaos/desktop/icon-style': 's', '/org/parchaos/desktop/phone-link': 'b',
    '/org/gnome/desktop/interface/color-scheme': 's', '/org/gnome/desktop/interface/accent-color': 's',
    '/org/gnome/desktop/interface/clock-format': 's',
    '/org/gnome/desktop/background/picture-uri': 's', '/org/gnome/desktop/background/picture-uri-dark': 's',
    '/org/gnome/desktop/session/idle-delay': 'u', '/org/gnome/desktop/screensaver/lock-enabled': 'b',
    '/org/gnome/system/location/enabled': 'b', '/org/gnome/desktop/privacy/disable-camera': 'b',
    '/org/gnome/shell/allow-extension-installation': 'b', '/org/gnome/shell/favorite-apps': 'as',
}
schemas = pol.Schemas(TYPES)


def plan_of(text):
    return pol.plan(tomllib.loads(text), schemas)


def problems(text):
    try:
        plan_of(text)
    except pol.PolicyError as e:
        return str(e)
    return ''


# The example shipped with the package is valid.
with open(os.path.join(HERE, '..', 'policy.example.toml'), 'rb') as f:
    example = tomllib.load(f)
p = pol.plan(example, schemas)
check(p['dconf']['/org/gnome/desktop/session/idle-delay'] == 'uint32 600', 'minutes become seconds, as uint32')
check(p['dconf']['/org/gnome/desktop/interface/color-scheme'] == "'prefer-light'", 'light colour scheme')
check(p['dconf']['/org/gnome/desktop/background/picture-uri'].startswith("'file:///"), 'wallpaper path becomes a file URI')
check('/org/gnome/desktop/background/picture-uri-dark' in p['locks'], 'locking the wallpaper locks both variants')
check('/org/gnome/desktop/interface/accent-color' not in p['locks'], 'accent is only a default')
check(p['dconf']['/org/gnome/shell/favorite-apps'].startswith("['es.parchaos.Browser.desktop'"), 'dock as a list')
check(p['browser']['URLBlocklist'] == ['example-games.com'], 'browser policies pass through')
check(p['updates'] == {'mode': 'install', 'when': 'Sat 03:00', 'reboot': 'never', 'security_only': False}, 'updates')
check(p['managed']['name'] == 'Escuela Ejemplo', 'organisation name')

# Inverted switches read the natural way.
p = plan_of('[privacy]\ncamera = false\n')
check(p['dconf']['/org/gnome/desktop/privacy/disable-camera'] == 'true', 'camera = false disables the camera')

# Mistakes are reported, all at once, in words.
e = problems('[appearence]\nstyle = "glass"\n')
check('unknown section' in e, f'misspelt section ({e})')
e = problems('[appearance]\nstyle = "shiny"\naccent = "gold"\n')
check('style: should be one of glass, classic' in e and 'accent' in e, f'bad choices both reported ({e})')
e = problems('[screen]\nlock_after_minutes = "ten"\n')
check('whole number of minutes' in e, f'bad number ({e})')
e = problems('[screen]\nlock_after = 5\n')
check('lock_after: unknown' in e, f'unknown setting ({e})')
e = problems('[appearance]\naccent = "red"\nlock = ["wallpaper"]\n')
check('locked but not set' in e, f'locking something not set ({e})')
e = problems('[updates]\nmode = "sometimes"\n')
check('mode: off, notify' in e, f'bad update mode ({e})')
e = problems('[updates]\nmode = "install"\nwhen = "every blue moon"\n')
check('not a time systemd understands' in e, f'bad time ({e})')
e = problems('[browser]\nhomepage = "x"\n')
check('Chromium policy names' in e, f'bad browser policy name ({e})')
e = problems('[settings]\n"clock-format" = "24h"\n')
check('write keys as' in e, f'raw key without a path ({e})')
e = problems('[appearance]\nwallpaper = "pictures/a.png"\n')
check('full path' in e, f'relative wallpaper ({e})')
check(problems('') == '', 'an empty policy is fine')

# Raw settings: native values or GVariant text; unknown keys are noted, not refused.
p = plan_of('[settings]\n"org/gnome/desktop/interface/clock-format" = "24h"\n"org/x/y/z" = "uint32 5"\nlock = true\n')
check(p['dconf']['/org/gnome/desktop/interface/clock-format'] == "'24h'", 'a text setting is quoted')
check(p['dconf']['/org/x/y/z'] == 'uint32 5' and p['notes'], 'unknown key written as given, with a note')
check(set(p['locks']) == {'/org/gnome/desktop/interface/clock-format', '/org/x/y/z'}, 'lock = true locks all of [settings]')

# Files: the dconf keyfile groups keys by folder; locks list the keys.
p = plan_of('[screen]\nlock_after_minutes = 5\nlock_enabled = true\nlock = ["lock_enabled"]\n')
files = pol.files_for(p)
key = files[pol.DCONF_FILE]
check('[org/gnome/desktop/session]\nidle-delay=uint32 300' in key, 'keyfile group and value')
check(files[pol.DCONF_LOCKS].splitlines()[1:] == ['/org/gnome/desktop/screensaver/lock-enabled'], 'only the locked key')
check(files[pol.CHROMIUM] is None and files[pol.AUTOMATIC] is None, 'nothing else written')
check('apply_updates = no' in pol.automatic_conf({'mode': 'download', 'reboot': 'never', 'security_only': True})
      and 'upgrade_type = security' in pol.automatic_conf({'mode': 'download', 'reboot': 'never', 'security_only': True}),
      'download only, security only')

# Apply and remove in a scratch root; an administrator's own automatic.conf comes back.
os.makedirs(os.path.join(ROOT, 'etc/dnf/dnf5-plugins'))
with open(os.path.join(ROOT, pol.AUTOMATIC), 'w') as f:
    f.write('# mine\n')
policy = os.path.join(ROOT, 'policy.toml')
with open(policy, 'w') as f:
    f.write('[organisation]\nname = "Test"\n[updates]\nmode = "install"\nwhen = "daily"\n[appearance]\naccent = "red"\n')
out = io.StringIO()
with redirect_stdout(out):
    pol.apply(policy, schemas)
check(open(os.path.join(ROOT, pol.AUTOMATIC)).read().startswith('# Written by parchaos-policy'), 'automatic.conf replaced')
check(os.path.exists(os.path.join(ROOT, pol.TIMER_DROPIN)), 'timer drop-in written')
check(os.path.exists(os.path.join(ROOT, pol.MANAGED)), 'managed.json written')
check('(would run) systemctl enable --now dnf5-automatic.timer' in out.getvalue(), 'the timer is switched on')

with open(policy, 'w') as f:
    f.write('[appearance]\naccent = "red"\n')
out = io.StringIO()
with redirect_stdout(out):
    pol.apply(policy, schemas)
check(not os.path.exists(os.path.join(ROOT, pol.TIMER_DROPIN)), 'updates dropped from the policy: drop-in removed')
check(open(os.path.join(ROOT, pol.AUTOMATIC)).read() == '# mine\n', 'and the administrator\'s automatic.conf is back')
check(not os.path.exists(os.path.join(ROOT, pol.MANAGED)), 'organisation dropped: managed.json removed')
check('disable --now dnf5-automatic.timer' in out.getvalue(), 'and the timer switched off')

os.remove(policy)
with redirect_stdout(io.StringIO()):
    pol.apply(policy)                               # the file is gone: undo everything
check(not os.path.exists(os.path.join(ROOT, pol.DCONF_FILE)), 'policy file removed: settings removed')
check(not os.path.exists(os.path.join(ROOT, pol.RECORD)), 'and the record')

if failures:
    print(f'policy: {failures} failure(s)')
    sys.exit(1)
print('policy: all checks passed')
