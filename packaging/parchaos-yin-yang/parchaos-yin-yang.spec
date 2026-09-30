# ==============================================================================
# Auto dark/light theme switching with real sunrise/sunset support
# (oskarsh/Yin-Yang, MIT) -- chosen over Koi (the other real candidate
# found via research) since Koi's own sunrise/sunset support is still
# "planned/scheduled" upstream, while Yin-Yang's is real today. Has
# dedicated plugins for kvantum, system (Plasma color scheme), gtk,
# icons, wallpaper, konsole -- a strong match for this profile's exact
# theming stack (Kvantum + KDE + our own conventions).
#
# Packaged properly via Fedora's standard pyproject macros (poetry-core
# backend, fully supported) -- NOT via upstream's own install.sh, which
# dumps the entire repo into /opt/yin_yang/ with a venv and has a
# self-acknowledged "TODO this copies a bunch of unnecessary files"
# comment. The .ui files are already compiled to committed .py source
# (main_window.py, resources_rc.py), so no UI-compile build step is
# needed -- PySide6-Essentials/Addons are only a *dev* dependency
# upstream for regenerating those from raw .ui files, not needed here.
#
# Deliberately does NOT package the Firefox native-messaging-host
# extension integration (a secondary feature, out of scope for "switch
# the desktop theme") -- only the core app.
#
# IMPORTANT architecture note, found via a real functional test
# (2026-09-22): this app does NOT expect a statically pre-installed
# systemd unit at all. It self-manages its own timer:
# yin_yang/daemon_handler.py's create_files() copies bundled resource
# templates into ~/.local/share/systemd/user/ on first real config
# change, then REWRITES specific lines in that copy (the OnCalendar=/
# OnStartupSec= values) to match whatever schedule the user actually
# configured in the GUI (fixed times or real sunrise/sunset), and
# calls `systemctl --user start/stop` itself. So this package does NOT
# install or preset-enable any unit directly -- it ships the resource
# *templates* the app's own code copies from
# (/usr/share/parchaos-yin-yang/resources/), and nothing runs until
# the user opens the app once and picks a mode (same "respect user
# choice, don't force a personal-preference default" reasoning already
# used for hot corners in this project).
#
# Real bug found in upstream's own code along the way: create_files()
# hardcoded `shutil.copy('./resources/yin_yang.timer', ...)` -- a
# relative path that only works under upstream's own /opt/yin_yang/
# install convention (their install.sh literally dumps the whole repo
# there and runs from inside it), which crashes outright under any
# real distro-packaged install. Confirmed via a real functional test
# (`yin_yang --systemd`): FileNotFoundError. Fixed with patch 0002,
# using upstream's own existing helpers.get_usr() abstraction (already
# used elsewhere in their code for Flatpak's /usr path) rather than
# inventing a new convention -- this was a genuine gap in their own
# existing pattern, not a packaging-specific workaround.
# ==============================================================================

%global pypi_name yin_yang

Name:           parchaos-yin-yang
# Real bug found via a real curl (14-byte GitHub 404 page): the git
# tag is v4.0.1, not v4.0.0 -- pyproject.toml's own internal version
# string still says "4.0.0" even at that tag (a real upstream
# versioning inconsistency, not a typo on this end), confirmed by
# checking pyproject.toml's content at the v4.0.1 ref directly.
Version:        4.0.1
Release:        5%{?dist}
Summary:        Automatic light/dark theme switching with real sunrise/sunset support

License:        MIT
URL:            https://github.com/oskarsh/Yin-Yang
Source0:        %{url}/archive/refs/tags/v%{version}.tar.gz#/%{pypi_name}-%{version}.tar.gz
Source1:        parchaos-yin-yang-files.tar.gz
# Real dependency-pin mismatches found via a real build (2026-09-22):
# upstream's Poetry-locked pyproject.toml wants suntime~=1.3.2 (i.e.
# <1.4) but the only suntime available anywhere is 1.4.0 (packaged
# separately as python3-suntime), and requests==2.32.3 exactly, but
# Fedora ships 2.33.1. Both are legitimate, working versions for this
# app's actual needs -- Poetry's exact/tilde pins are meant for a
# fully isolated venv, not a distro-integrated package. Standard
# Fedora practice for Poetry-based packages: relax the pins to match
# what the distro actually provides.
#
# Also relaxed requires-python (">=3.10, <3.14" -> "<3.15") since
# Fedora 44 ships Python 3.14.7, which the build otherwise refused
# outright. This one carries slightly more real risk than the two
# above -- a Python major-version exclusion *could* reflect a genuine
# incompatibility upstream hasn't fixed yet, not just an overcautious
# pin, and this hasn't been runtime-tested against 3.14 beyond "it
# builds and installs." Worth watching for real 3.14-specific bugs if
# they surface, not assumed impossible.
Patch0:         0001-relax-fedora-package-version-pins.patch
Patch1:         0002-fix-broken-relative-resource-paths.patch
# Real gap found via real desktop usage 2026-09-25 (testing on the
# real desktop -- launching yin_yang directly showed "Plugin
# Colors has no support for your desktop environment yet!" and the
# same for "Icons"). Checked the real upstream source before assuming
# anything was broken on our end: Colors is genuinely KDE-only by
# design upstream (plasma-apply-colorscheme has no GNOME equivalent
# concept, not a gap worth patching around). Icons, though, has real,
# working GNOME-Shell-based implementations for MATE/Cinnamon/Budgie
# via plain `gsettings set org.gnome.desktop.interface icon-theme` --
# upstream simply never wired up a `Desktop.GNOME` case despite
# Budgie's own implementation being identical to what plain GNOME
# needs. Separately, even the GTK plugin (which DID report working)
# only sets gtk-theme, never color-scheme -- meaning GTK4/libadwaita
# apps (Nautilus, Calculator, Settings, half of a real GNOME desktop)
# would silently ignore yin-yang's light/dark switch even when the
# plugin "worked". Both fixed with a real patch, not a packaging
# workaround, following this package's own established pattern of
# patching real upstream gaps (see Patch0/Patch1's own history).
Patch2:         0003-add-gnome-icons-support-and-color-scheme-sync.patch
# Real bug found via live testing on real hardware (2026-09-25): on
# GNOME every plugin defaults to disabled, so the tray toggle and
# `yin_yang -t` changed nothing at all out of the box. Enabling GTK
# alone wouldn't have helped either: its defaults were 'Default'/'Default'
# (no such theme), and identical light/dark names made Patch2's
# color-scheme check always choose prefer-dark. The System (shell theme)
# plugin had no default theme names at all ('Theme "" is invalid').
# Patch3 ships the real MacTahoe light/dark GTK, icon and shell theme
# names, enables those three plugins by default on GNOME only, and seeds
# a fresh config's dark_mode from the real color-scheme so the first
# toggle on the (dark by default) desktop isn't a silent no-op.
Patch3:         0004-gnome-real-default-themes-and-enabled-plugins.patch

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  pyproject-rpm-macros

Requires:       python3-pyside6
Requires:       python3-shiboken6
Requires:       python3-psutil
Requires:       python3-systemd
Requires:       python3-requests
Requires:       python3-dateutil
Requires:       python3-suntime
Requires:       systemd

%description
Automatically switches between light and dark themes at fixed times or
real sunrise/sunset times for your location, with plugins for Plasma's
own color scheme, Kvantum, GTK, icons, wallpaper, and Konsole. A
manual switch is also available via its system tray icon.

%prep
%autosetup -n Yin-Yang-%{version} -p1
tar xzf %{SOURCE1} -C %{_builddir}/Yin-Yang-%{version}
# Real bug found via a real build (2026-09-22): communicate.py's own
# shebang is the version-ambiguous `#!/usr/bin/env python`, which
# Fedora's brp-mangle-shebangs %%install policy hard-fails on outright
# -- same class of bug already found/fixed once before in this
# project (a different bundled plasmoid, see pearos-settings.spec's
# own history). Fix at the source before %%build, not after, since the
# ambiguous shebang would otherwise get packaged into the wheel as-is.
sed -i '1s|^#!/usr/bin/env python$|#!/usr/bin/env python3|' yin_yang/communicate.py

%generate_buildrequires
%pyproject_buildrequires

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files %{pypi_name}
# Real bug found via a real run (2026-09-22): the auto-generated
# /usr/bin/yin_yang wrapper (from [project.scripts] yin_yang =
# "yin_yang:__main__" in pyproject.toml) crashes outright --
# TypeError: 'module' object is not callable. yin_yang.__main__ is a
# MODULE (meant to run as top-level script code via `python3 -m
# yin_yang`, which is genuinely how upstream's own resources/yin_yang
# wrapper script invokes it), not a callable function -- this
# entry-point declaration looks like it was never actually exercised
# by upstream's own real deployment (their install.sh's own wrapper
# bypasses it entirely). Overwrite the broken generated wrapper with
# one that actually works, using upstream's own real invocation.
cat > %{buildroot}%{_bindir}/yin_yang <<'WRAPEOF'
#!/bin/bash
exec python3 -m yin_yang "$@"
WRAPEOF
chmod 0755 %{buildroot}%{_bindir}/yin_yang
mkdir -p %{buildroot}%{_datadir}/applications
mkdir -p %{buildroot}%{_datadir}/icons/hicolor/scalable/apps
mkdir -p %{buildroot}%{_datadir}/parchaos-yin-yang/resources
install -m 0644 usr/share/applications/sh.oskar.yin_yang.desktop \
    %{buildroot}%{_datadir}/applications/
install -m 0644 usr/share/icons/hicolor/scalable/apps/sh.oskar.yin_yang.svg \
    %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/
install -m 0644 usr/share/parchaos-yin-yang/resources/yin_yang.service \
    %{buildroot}%{_datadir}/parchaos-yin-yang/resources/
install -m 0644 usr/share/parchaos-yin-yang/resources/yin_yang.timer \
    %{buildroot}%{_datadir}/parchaos-yin-yang/resources/

%files -f %{pyproject_files}
%license LICENSE
%doc README.md
%{_bindir}/yin_yang
%{_datadir}/applications/sh.oskar.yin_yang.desktop
%{_datadir}/icons/hicolor/scalable/apps/sh.oskar.yin_yang.svg
%{_datadir}/parchaos-yin-yang/resources/yin_yang.service
%{_datadir}/parchaos-yin-yang/resources/yin_yang.timer

%changelog
* Wed Sep 30 2026 ParchaOS packaging - 4.0.1-5
- Fedora 45 prep (ticket #37): accept systemd-python 236 (upstream pins
  exactly 235) and Python 3.15 in the relaxed pins.
* Fri Sep 25 2026 ParchaOS packaging - 4.0.1-4
- Reworded comments and changelog to describe user-reported issues
  instead of quoting them.
* Fri Sep 25 2026 ParchaOS packaging - 4.0.1-3
- Real bug found via live testing on real hardware: toggling did nothing
  on GNOME because every plugin defaulted to disabled, the GTK/Icons
  defaults named a nonexistent 'Default' theme (and identical light/dark
  names forced prefer-dark), and System had no defaults at all. Patch0004
  ships real MacTahoe light/dark defaults and enables GTK, Icons and
  System by default on GNOME; a fresh config now starts from the real
  color-scheme so the first toggle isn't a no-op. Verified by toggling back and forth on the
  live desktop and reading back color-scheme, gtk-theme, icon-theme and
  the user-theme name each time.
* Fri Sep 25 2026 ParchaOS packaging - 4.0.1-2
- Real bug found via real desktop usage: the Icons plugin never had a
  GNOME case wired up upstream (Budgie's identical implementation was
  right there unused), and the GTK plugin never set color-scheme
  alongside gtk-theme, silently leaving GTK4/libadwaita apps out of
  yin-yang's light/dark switch. Patch0003 fixes both. Colors staying
  unsupported is confirmed a real, deliberate KDE-only upstream design,
  not something to patch around.
* Tue Sep 22 2026 ParchaOS packaging - 4.0.1-1
- Initial package. Verified all runtime dependencies except suntime
  are real Fedora packages -- packaged python3-suntime separately for
  the one that wasn't. Real bugs found and fixed via an actual build +
  install + run, not just "it compiled":
  1. Wrong git tag assumed (v4.0.0 doesn't exist, real tag is v4.0.1;
     pyproject.toml's own internal version string still says "4.0.0"
     at that tag, a real upstream inconsistency).
  2. Poetry-locked dependency pins too strict for what Fedora actually
     ships (suntime~=1.3.2 vs the only available 1.4.0; requests==2.32.3
     exact vs Fedora's 2.33.1; requires-python <3.14 vs Fedora 44's
     3.14.7) -- relaxed via patch 0001, standard practice for
     Fedora-packaging Poetry projects.
  3. Ambiguous `#!/usr/bin/env python` shebang in communicate.py, same
     class of bug already hit once before in this project -- fixed at
     the source in %%prep.
  4. The auto-generated /usr/bin/yin_yang console-script wrapper (from
     [project.scripts] yin_yang = "yin_yang:__main__") crashes outright
     -- TypeError: 'module' object is not callable. yin_yang.__main__
     is a module meant to run via `python3 -m yin_yang` (upstream's own
     real invocation, used by their own resources/yin_yang wrapper
     script), not a callable entry-point function -- this declaration
     looks unexercised by upstream's own real deployment. Overwrote the
     broken generated wrapper with one that actually works.
  5. Real architecture bug in upstream's own code, found by actually
     running `yin_yang --systemd`: daemon_handler.py's create_files()
     hardcoded a relative path (./resources/yin_yang.timer) that only
     works under upstream's own /opt/yin_yang/ install convention --
     crashes with FileNotFoundError under any real distro package.
     Fixed with patch 0002 using upstream's own existing
     helpers.get_usr() abstraction (already used elsewhere in their
     code for Flatpak's /usr path) -- a genuine gap in their own
     pattern, not a packaging-specific workaround. This package ships
     the resource *templates* at
     /usr/share/parchaos-yin-yang/resources/ and does NOT install or
     enable any systemd unit directly -- the app self-manages its own
     ~/.local/share/systemd/user/yin_yang.timer once the user opens
     the GUI and picks a mode, same as upstream's own real design.
  Verified: real RPM build succeeds, install succeeds, `import
  yin_yang` and plugin imports succeed, `yin_yang --systemd` runs
  without crashing after the daemon_handler fix. Not yet verified: the
  GUI itself opening/rendering (needs a real display), and the full
  create-timer-then-actually-switch-the-theme cycle end to end on an
  installed system.
