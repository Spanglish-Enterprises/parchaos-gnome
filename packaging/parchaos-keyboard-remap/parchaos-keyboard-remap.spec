# ==============================================================================
# ParchaOS's keyboard remap -- swaps Super<->Ctrl and adds a few
# Super-key conventions (Super-Left/Right as Home/End, Super-C/V/T/N/W/Q/F
# in the terminal, file-manager shortcuts), via xremap
# (github.com/xremap/xremap, MIT), a userspace evdev key remapper.
#
# ParchaOS's own configuration: /etc/xremap/config.yml and the dconf
# keybinding defaults (02-parchaos-keyboard-remap) were written for
# ParchaOS from a plain list of the shortcuts it wants (2026-09-26). The
# approach -- xremap with a system-wide user unit -- follows the idea of
# gnome-macos-remap-wayland, but no configuration or script from that
# project is used (its repositories carry no license).
#
# How this differs from a clone-and-run install script, and why:
#   - A clone-and-run installer is designed to be `git clone`d and run as an
#     interactive install.sh (downloads xremap's latest release at
#     install time, edits the CURRENT user's own systemd --user units
#     and gsettings via `sudo`/`$USER`). None of that is appropriate
#     for an RPM shipped on a live ISO where the eventual real user's
#     username isn't known until Calamares creates their account:
#       * xremap's binary is a pinned Source0 download (v0.15.13,
#         xremap-linux-x86_64-full.zip -- the "gnome" build only speaks
#         GNOME's own D-Bus desktop client, not --desktop=socket, which
#         the system-service split (below) needs) resolved at SRPM-build
#         time
#         (this project's own established Source0-URL convention, see
#         parchaos-dock/pearos-branding), not fetched live by a
#         postinst script -- reproducible, and works in COPR's
#         network-isolated mock build phase.
#       * The systemd --user unit is enabled via a real
#         /usr/lib/systemd/user-preset/*.preset drop-in (system-wide
#         "enable this for every user" mechanism) instead of the
#         installer's `systemctl --user enable` against
#         whichever single user happened to run install.sh -- this is
#         the real bug that approach would hit:
#         hardcoding to "liveuser" would silently do nothing for the
#         real username Calamares creates during a disk install.
#       * uinput access uses only the udev `TAG+="uaccess"` mechanism
#         (systemd-logind's dynamic per-session device ACL) instead of
#         an installer's static `gpasswd -a $USER input` --
#         same reasoning as above (no fixed username to add), and
#         uaccess is the modern, correct mechanism on any
#         systemd-logind system (Fedora always has been one).
#       * gsettings tweaks (Super+Tab app switching, overlay-key
#         disabled so it doesn't fight Super-combinations, GNOME
#         Terminal's Super-C/V/T/N/W/Q/F bindings, etc.) are
#         shipped as a system-wide dconf db drop-in (this project's
#         existing mechanism, see profiles/parchaos/customize.sh)
#         instead of one-shot `gsettings set` calls -- declarative,
#         applies to every user, survives a real disk install.
#   - config.yml only covers the apps ParchaOS ships with app-specific
#     rules (org.gnome.Nautilus for Parcher, org.gnome.Terminal).
#
# Depends on xremap's own real, separate GNOME Shell extension
# (xremap/xremap-gnome, GPLv2+, uuid xremap@k0kubun.com) to learn the
# focused app's WM_CLASS: it exposes a D-Bus interface (unused here) and,
# since it already speaks xremap's --desktop=socket protocol, answers
# focus queries over a Unix socket under /run/xremap/<uid> instead --
# the same directory the system-service split (below) already needs to
# exist per user, with no extra moving part on the GNOME Shell side.
# Pinned to
# commit de79b05989308d717429726dab503e116a141851 (no tagged releases
# exist upstream). NOT rebranded (unlike parcha-dock/global-menu) --
# this is a small, purely functional upstream helper extension with
# no user-visible branding of its own to replace.
# ==============================================================================

%global xremap_version 0.15.13
# xremap-crate-licenses.txt carries the license and copyright notices of
# the Rust crates statically linked into the xremap binary. Regenerate it
# whenever xremap_version changes:
#   scripts/xremap-crate-licenses.py VERSION > \
#       packaging/parchaos-keyboard-remap/xremap-crate-licenses.txt
%global gnome_ext_commit de79b05989308d717429726dab503e116a141851
%global gnome_ext_shortcommit %(c=%{gnome_ext_commit}; echo ${c:0:7})

# xremap ships as a prebuilt release binary (Source0), not compiled by
# this spec -- it has no ELF build-id note (added by Fedora's own
# linker flags, which never touch this binary), which makes rpm's
# find-debuginfo fail outright (real error hit on a local rpmbuild
# --rebuild test: "No build ID note found in .../usr/bin/xremap").
# Disabling debuginfo generation is the standard fix for a
# prebuilt-binary package, same as e.g. any other repackaged
# proprietary/prebuilt binary RPM.
%global debug_package %{nil}

Name:           parchaos-keyboard-remap
Version:        %{xremap_version}
Release:        15%{?dist}
Summary:        ParchaOS keyboard remap: Super as Ctrl and friends, via xremap

License:        MIT AND GPL-2.0-or-later AND GPL-3.0-or-later AND (MIT OR Apache-2.0) AND Apache-2.0 AND BSD-3-Clause AND (Apache-2.0 OR BSL-1.0) AND Unicode-3.0 AND (Unlicense OR MIT)
URL:            https://github.com/xremap/xremap
Source0:        https://github.com/xremap/xremap/releases/download/v%{xremap_version}/xremap-linux-x86_64-full.zip
Source1:        https://github.com/xremap/xremap-gnome/archive/%{gnome_ext_commit}/xremap-gnome-%{gnome_ext_shortcommit}.tar.gz
Source2:        parchaos-keyboard-remap-files.tar.gz
Source90:       LICENSE
Source91:       GPL-2.0.txt
Source92:       THIRD-PARTY-LICENSES.md
Source93:       https://raw.githubusercontent.com/xremap/xremap/v%{xremap_version}/LICENSE#/xremap-LICENSE
Source94:       xremap-crate-licenses.txt

ExclusiveArch:  x86_64

BuildRequires:  unzip

Requires:       systemd
Requires:       python3-gobject-base
Requires:       acl
Requires:       gnome-shell >= 45
Requires:       acl
Requires(post): systemd-udev
BuildRequires:  systemd-rpm-macros
%{?systemd_requires}

# Renamed from parchaos-macos-remap (0.15.13-3): keep "macOS" out of
# shipped product names. Obsoletes/Provides let `dnf upgrade` swap it in.
Obsoletes:      parchaos-macos-remap < %{version}-%{release}
Provides:       parchaos-macos-remap = %{version}-%{release}

%description
ParchaOS's keyboard remap: swaps Super and Ctrl and layers on a set of
Super-key conventions (Super-Left/Right as Home/End,
Super-C/V/T/N/W/Q/F in the terminal, Parcher's Super-based file shortcuts,
app switching on Super-Tab) system-wide, via xremap -- a real, actively
maintained userspace evdev key remapper -- and its companion GNOME
Shell extension. Runs as its own unprivileged system service (not the
logged-in user), so no real user account ever needs raw keyboard/uinput
access. Packaged declaratively (sysusers, systemd system unit, udev,
dconf defaults), so it works for whatever user account the installer
creates.

%prep
%setup -q -c -T -n %{name}-%{version}
mkdir xremap-bin
(cd xremap-bin && unzip -o %{SOURCE0})
tar xzf %{SOURCE1}
tar xzf %{SOURCE2}
cp -p %{SOURCE90} %{SOURCE91} %{SOURCE92} %{SOURCE93} %{SOURCE94} .

%build
# Nothing to compile: xremap ships as a prebuilt binary (Source0), and
# xremap-gnome (Source1) is plain JS + JSON with no build step -- its
# own package.sh (checked before writing this) just zips extension.js
# and metadata.json verbatim, no glib-compile-schemas or similar.

%install
install -Dm0755 xremap-bin/xremap %{buildroot}%{_bindir}/xremap

EXTDIR=%{buildroot}%{_datadir}/gnome-shell/extensions/xremap@k0kubun.com
install -d "$EXTDIR"
install -Dm0644 xremap-gnome-%{gnome_ext_commit}/extension.js "$EXTDIR"/extension.js
install -Dm0644 xremap-gnome-%{gnome_ext_commit}/metadata.json "$EXTDIR"/metadata.json

install -Dm0644 etc/xremap/config.yml %{buildroot}%{_sysconfdir}/xremap/config.yml
install -Dm0644 usr/lib/systemd/system/parchaos-keyboard-remap.service %{buildroot}%{_prefix}/lib/systemd/system/parchaos-keyboard-remap.service
install -Dm0644 "usr/lib/systemd/system/user@.service.d/90-parchaos-keyboard-remap.conf" "%{buildroot}%{_prefix}/lib/systemd/system/user@.service.d/90-parchaos-keyboard-remap.conf"
install -Dm0755 usr/libexec/parchaos-keyboard-remap-socket-dir %{buildroot}%{_prefix}/libexec/parchaos-keyboard-remap-socket-dir
install -Dm0755 usr/libexec/parchaos-keyboard-remap-watch %{buildroot}%{_prefix}/libexec/parchaos-keyboard-remap-watch
install -Dm0644 usr/lib/systemd/system/parchaos-keyboard-remap-dirs.service %{buildroot}%{_prefix}/lib/systemd/system/parchaos-keyboard-remap-dirs.service
# Enabled by a packaged link: %%systemd_post does not enable a unit that is
# new on an upgrade.
install -d %{buildroot}%{_prefix}/lib/systemd/system/multi-user.target.wants
ln -s ../parchaos-keyboard-remap-dirs.service %{buildroot}%{_prefix}/lib/systemd/system/multi-user.target.wants/parchaos-keyboard-remap-dirs.service
install -Dm0644 usr/share/polkit-1/rules.d/49-parchaos-keyboard-remap.rules %{buildroot}%{_datadir}/polkit-1/rules.d/49-parchaos-keyboard-remap.rules
install -Dm0644 usr/lib/udev/rules.d/90-parchaos-keyboard-remap-uinput.rules %{buildroot}%{_prefix}/lib/udev/rules.d/90-parchaos-keyboard-remap-uinput.rules
install -Dm0644 usr/lib/modules-load.d/parchaos-keyboard-remap-uinput.conf %{buildroot}%{_prefix}/lib/modules-load.d/parchaos-keyboard-remap-uinput.conf
install -Dm0644 etc/dconf/db/local.d/02-parchaos-keyboard-remap %{buildroot}%{_sysconfdir}/dconf/db/local.d/02-parchaos-keyboard-remap
# Per-user choice between Super-as-Ctrl (default) and standard key roles;
# used by Parcha Controls' "Super as Ctrl" tile.
install -Dm0755 usr/bin/parchaos-keyboard-style %{buildroot}%{_bindir}/parchaos-keyboard-style

%pre
%sysusers_create_inline u xremap - "ParchaOS keyboard remap service" - -
%sysusers_create_inline m xremap input

%post
udevadm control --reload-rules >/dev/null 2>&1 || :
# uinput is created at module load, not hot-plugged -- reloading the
# rules alone doesn't touch its already-existing device node. Retrigger
# it so the new GROUP/MODE (and the dropped uaccess tag) apply without a
# reboot.
udevadm trigger --subsystem-match=misc --sysname-match=uinput >/dev/null 2>&1 || :
dconf update >/dev/null 2>&1 || :
# This unit is new (it replaces a --user unit of the same name, a
# genuinely different unit path and type, not a same-name file swap), so
# %%systemd_post's usual "only auto-enable on a first install" rule would
# leave it disabled and stopped on every real-world `dnf upgrade` --
# nothing carries an old --user unit's enabled state forward to it.
# Enable and start it unconditionally instead.
systemctl daemon-reload >/dev/null 2>&1 || :
systemctl enable --now parchaos-keyboard-remap.service >/dev/null 2>&1 || :
# Ticket #132: (re)creates each logged-in user's socket directory on login.
systemctl restart parchaos-keyboard-remap-dirs.service >/dev/null 2>&1 || :
# Security fix (ticket #22): on an upgrade from a version that ran as a
# --user unit, stop that now-orphaned per-user process (removing its unit
# file doesn't stop an already-running instance) and take real users out
# of the `input` group -- membership there is exactly the raw-keyboard-
# access bug this release closes, so an upgrade must not leave it in
# place until each user's next login.
#
# Signal the old process by pid rather than reaching into that user's own
# --user manager over D-Bus (`runuser ... systemctl --user stop`): tried
# first, and on real hardware it silently did nothing, almost certainly
# because dnf5 runs %%post scriptlets inside their own systemd scope,
# which the old session's D-Bus socket isn't reliably reachable from.
# Any *real* uid running xremap is necessarily the old per-user instance
# -- the new system service always runs as the unprivileged `xremap`
# account, well under 1000.
if [ "$1" -gt 1 ] 2>/dev/null; then
    for pid in $(pgrep -x xremap 2>/dev/null); do
        puid=$(awk '/^Uid:/{print $2}' "/proc/$pid/status" 2>/dev/null)
        if [ -n "$puid" ] && [ "$puid" -ge 1000 ] 2>/dev/null && [ "$puid" -lt 60000 ] 2>/dev/null; then
            kill "$pid" >/dev/null 2>&1 || :
        fi
    done
    getent passwd | awk -F: '$3 >= 1000 && $3 < 60000 {print $1}' | while read -r u; do
        gpasswd -d "$u" input >/dev/null 2>&1 || :
    done
fi

%preun
%systemd_preun parchaos-keyboard-remap.service parchaos-keyboard-remap-dirs.service

%postun
dconf update >/dev/null 2>&1 || :
%systemd_postun_with_restart parchaos-keyboard-remap.service parchaos-keyboard-remap-dirs.service

%files
%license LICENSE
%license GPL-2.0.txt
%license THIRD-PARTY-LICENSES.md
%license xremap-LICENSE
%license xremap-crate-licenses.txt
%{_bindir}/xremap
%{_bindir}/parchaos-keyboard-style
%{_prefix}/libexec/parchaos-keyboard-remap-socket-dir
%{_prefix}/libexec/parchaos-keyboard-remap-watch
%{_datadir}/gnome-shell/extensions/xremap@k0kubun.com/
%{_datadir}/polkit-1/rules.d/49-parchaos-keyboard-remap.rules
%{_sysconfdir}/xremap/config.yml
%{_prefix}/lib/systemd/system/parchaos-keyboard-remap.service
%{_prefix}/lib/systemd/system/parchaos-keyboard-remap-dirs.service
%{_prefix}/lib/systemd/system/multi-user.target.wants/parchaos-keyboard-remap-dirs.service
%{_prefix}/lib/systemd/system/user@.service.d/90-parchaos-keyboard-remap.conf
%{_prefix}/lib/udev/rules.d/90-parchaos-keyboard-remap-uinput.rules
%{_prefix}/lib/modules-load.d/parchaos-keyboard-remap-uinput.conf
%{_sysconfdir}/dconf/db/local.d/02-parchaos-keyboard-remap

%changelog
* Tue Sep 29 2026 ParchaOS packaging - %{xremap_version}-15
- Ticket #132: per-app remaps no longer depend on user@.service restarting.
  New parchaos-keyboard-remap-dirs.service (root) watches systemd-logind and
  creates each logged-in user's /run/xremap/<uid> on every login and at
  start. Chosen over the PAM/authselect hook the ticket sketched: it needs no
  change to the authentication stack, so it cannot block or slow a login.
  The user@.service.d hook stays as a second path (the helper is idempotent).
* Sun Sep 27 2026 ParchaOS packaging - %{xremap_version}-14
- Real bug found logging out and back in to test -13 on real hardware:
  the journal showed "This variant of xremap doesn't support 'Socket'.
  Supported: GNOME" and "application-client: none (supported: false)" --
  the "gnome" release build only speaks xremap's own GNOME D-Bus client,
  not the generic --desktop=socket protocol the system-service split
  needs. It ran, and the plain Super<->Ctrl swap kept working (no
  per-app scoping needed), but every per-app rule (Terminal, Parcher)
  silently stopped matching anything -- no crash, so this was easy to
  miss without checking the journal. Source0 now pulls xremap's "full"
  release build instead, which the socket feature actually needs.
* Sun Sep 27 2026 ParchaOS packaging - %{xremap_version}-13
- Real bug found installing -12 on real hardware: the old --user
  instance was still running after the upgrade (confirmed by `ps`, two
  live xremap processes) because `runuser -u ... systemctl --user stop`
  in %%post silently did nothing -- reaching into another already-running
  session's D-Bus from a root scriptlet isn't reliable under dnf5's own
  scriptlet sandboxing. Kill the old process by pid instead (any *real*
  uid running xremap is necessarily the old instance; the new system
  service always runs as the unprivileged `xremap` account). Verified
  live: exactly one xremap process, owned by `xremap`, after the upgrade.
* Sun Sep 27 2026 ParchaOS packaging - %{xremap_version}-12
- Real bug found installing -11 on real hardware: the new system unit is
  genuinely new (it replaces a --user unit of the same name, not a
  same-name file swap), so %%systemd_post's "only auto-enable on a first
  install" rule left it disabled and stopped on the upgrade that
  introduced it -- nothing carries the old --user unit's enabled state
  forward to a differently-typed unit with the same name. %%post now
  enables and starts it unconditionally, and also stops the old, now file
  -less --user instance in every logged-in real user's own session
  (removing a unit's file doesn't stop an already-running instance of
  it) before dropping them from `input`, instead of leaving both the old
  process and the group membership in place until their next login.
* Sun Sep 27 2026 ParchaOS packaging - %{xremap_version}-11
- Security fix (ticket #22, High): xremap moves from a --user unit to
  its own system service running as a new unprivileged `xremap` account
  (systemd-sysusers), and the uinput udev rule drops the `uaccess` tag.
  No real user account is in the `input` group or has /dev/uinput access
  any more -- an upgrade removes existing users from `input` directly, in
  the same package, since normal typing goes through Mutter/libinput's
  own independent seat access and never depended on that group; only the
  Super<->Ctrl remap did.
- Per-app remaps (Terminal, Parcher) keep working over xremap's own
  `--desktop=socket` feature: the xremap-gnome extension already speaks
  it (checked against the exact pinned commit), answering only "what app
  is focused" over a socket under /run/xremap/<uid>, which the system
  service connects into. A new user@.service.d drop-in and
  parchaos-keyboard-remap-socket-dir create and ACL that one directory
  to that one uid at login, with no per-username packaging step and no
  supplementary-group login-timing race.
- parchaos-keyboard-style now controls the system unit over D-Bus
  (systemctl, not systemctl --user), authorized for the active local
  session by a new polkit rule scoped to this one unit -- Super-as-Ctrl
  toggling still needs no password, but is now machine-wide rather than
  per-user, since the remap itself is now one process for the whole
  machine. Acceptable given ParchaOS is a single-real-user desktop.
- Needs real-hardware verification before this reaches every install:
  confirm the remap still works after a clean login and after
  `dnf upgrade`, and that Super-as-Ctrl toggling still works, before
  wider rollout.
* Sat Sep 26 2026 ParchaOS packaging - %{xremap_version}-10
- Ship the license and copyright notices of the Rust crates linked into
  the xremap binary (xremap-crate-licenses.txt).
* Sat Sep 26 2026 ParchaOS packaging - 0.15.13-9
- ParchaOS's own remap configuration and keybinding defaults, written
  from a plain list of the wanted shortcuts; the key mappings are
  unchanged.
* Sat Sep 26 2026 ParchaOS packaging - 0.15.13-8
- Ship the license text (%license) with an accurate SPDX License tag.
  Includes xremap's MIT license and a third-party notice for xremap and
  xremap-gnome.
* Sat Sep 26 2026 ParchaOS packaging - 0.15.13-7
- Rebuild with the current parchaos-keyboard-style (0.15.13-6 was built
  from a stale copy of the packaged files, so the style names super-ctrl
  and standard weren't accepted).
* Sat Sep 26 2026 ParchaOS packaging - 0.15.13-6
- parchaos-keyboard-style: the styles are now named super-ctrl and
  standard; the old names mac and windows are still accepted, and a
  saved choice is read under the new names.
* Fri Sep 25 2026 ParchaOS packaging - %{xremap_version}-5
- Add parchaos-keyboard-style: each user can switch between Super as Ctrl
  (the remap plus ParchaOS shortcuts, default) and standard key roles
  (remap masked for that user, GNOME's stock shortcuts restored), applied
  immediately.
* Fri Sep 25 2026 ParchaOS packaging - 0.15.13-4
- Describe the remapped key as Super (the key it actually is on PC
  keyboards) in the summary, description, service description and config
  comments, instead of the reference desktop's key name. No behavior
  change.
* Fri Sep 25 2026 ParchaOS packaging - 0.15.13-3
- Renamed from parchaos-macos-remap to parchaos-keyboard-remap (and the
  unit, preset, udev rule, modules-load and dconf files with it), per the
  project's policy of keeping Apple trademarks out of shipped names.
  Obsoletes/Provides the old name so `dnf upgrade` replaces it. Added
  %%systemd_user_post so the renamed unit is enabled for existing users,
  who only had the old unit name enabled.
* Thu Sep 24 2026 ParchaOS packaging - 0.15.13-2
- Real bug found trying to install this package directly on a real,
  freshly-installed system on actual hardware (2026-09-24): `sudo dnf
  install parchaos-macos-remap` failed with "nothing provides
  systemd-udevd" -- this package's own `Requires(post):` line named a
  package that doesn't exist under that name. Confirmed via
  `rpm -qf $(which udevadm)` on the real system that the actual
  package providing udev/udevadm is `systemd-udev` (no trailing d) --
  a one-character typo in the original spec. This also silently broke
  `parchaos-desktop` (the meta-package `Requires:` this package,
  transitively failing the same way) and meant none of this package's
  five siblings in the same `dnf install` transaction
  (parchaos-cloud, parchaos-focus-schedule, parchaos-yin-yang,
  parchaos-tmog, pafari) could install either, since dnf resolves a
  multi-package request as one transaction.

* Wed Sep 23 2026 ParchaOS packaging - 0.15.13-1
- Initial package: xremap v0.15.13 (MIT, prebuilt x86_64/gnome release
  binary) + xremap-gnome@de79b05 (GPLv2+) for the WM_CLASS lookup,
  config.yml trimmed to this profile's real apps (Parcher/Nautilus,
  GNOME Terminal), systemd user-preset + udev uaccess + dconf db
  wiring adapted from Pulsar OS's own interactive install.sh into
  real, username-independent RPM mechanisms. Wired into
  packages.sh/customize.sh.
- Real bug found via a local `rpmbuild --rebuild` test before ever
  submitting to COPR: find-debuginfo fails outright on the prebuilt
  xremap binary ("No build ID note found") since it's not compiled by
  this spec and carries no ELF build-id note. Fixed with
  `%%global debug_package %%{nil}`.
