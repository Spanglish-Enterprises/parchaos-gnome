# ==============================================================================
# ParchaOS's keyboard remap -- swaps Super<->Ctrl and layers on a real
# set of Super-key conventions (Super-Left/Right as Home/End,
# Super-C/V/T/N/W/Q/F in the terminal, Parcher/Nautilus's Super-based file
# shortcuts, etc.), via xremap (github.com/xremap/xremap, MIT), a
# userspace evdev key remapper. Real upstream software, not
# hand-rolled: this is a Fedora repackaging of Pulsar OS's own
# gnome-macos-remap-wayland (Inled-Pulsar-OS/gnome-macos-remap-wayland,
# itself a fork of petrstepanov/gnome-macos-remap-wayland) -- same
# "repackage already-proven software" approach already used for this
# project's theme/dock/global-menu packages.
#
# What changed from the upstream install.sh, and why:
#   - The upstream project is designed to be `git clone`d and run as an
#     interactive install.sh (downloads xremap's latest release at
#     install time, edits the CURRENT user's own systemd --user units
#     and gsettings via `sudo`/`$USER`). None of that is appropriate
#     for an RPM shipped on a live ISO where the eventual real user's
#     username isn't known until Calamares creates their account:
#       * xremap's binary is a pinned Source0 download (v0.15.13,
#         xremap-linux-x86_64-gnome.zip) resolved at SRPM-build time
#         (this project's own established Source0-URL convention, see
#         parchaos-dock/pearos-branding), not fetched live by a
#         postinst script -- reproducible, and works in COPR's
#         network-isolated mock build phase.
#       * The systemd --user unit is enabled via a real
#         /usr/lib/systemd/user-preset/*.preset drop-in (system-wide
#         "enable this for every user" mechanism) instead of the
#         upstream script's `systemctl --user enable` against
#         whichever single user happened to run install.sh -- this is
#         the actual real bug the upstream approach would have hit:
#         hardcoding to "liveuser" would silently do nothing for the
#         real username Calamares creates during a disk install.
#       * uinput access uses only the udev `TAG+="uaccess"` mechanism
#         (systemd-logind's dynamic per-session device ACL) instead of
#         the upstream script's static `gpasswd -a $USER input` --
#         same reasoning as above (no fixed username to add), and
#         uaccess is the modern, correct mechanism on any
#         systemd-logind system (Fedora always has been one).
#       * gsettings tweaks (Super+Tab app switching, overlay-key
#         disabled so it doesn't fight Super-combinations, GNOME
#         Terminal's Super-C/V/T/N/W/Q/F bindings, etc.) are
#         shipped as a system-wide dconf db drop-in (this project's
#         existing mechanism, see profiles/pulsaros/customize.sh)
#         instead of one-shot `gsettings set` calls -- declarative,
#         applies to every user, survives a real disk install.
#   - config.yml trimmed to the apps this profile actually ships
#     (org.gnome.Nautilus/Parcher, org.gnome.Terminal -- confirmed via
#     packaging/parchaos-finder's spec and profiles/pulsaros/
#     packages.list, not assumed): dropped the upstream config's
#     GNOME Console/Ptyxis/Eclipse sections, which this profile
#     doesn't ship and which would just be dead config otherwise.
#
# Depends on xremap's own real, separate GNOME Shell extension
# (xremap/xremap-gnome, GPLv2+, uuid xremap@k0kubun.com) -- xremap's
# "gnome" feature build needs it to learn the focused app's WM_CLASS
# over a local D-Bus/socket, the same underlying mechanism GNOME
# Shell itself uses (see that repo's own extension.js). Pinned to
# commit de79b05989308d717429726dab503e116a141851 (no tagged releases
# exist upstream). NOT rebranded (unlike parcha-dock/global-menu) --
# this is a small, purely functional upstream helper extension with
# no user-visible branding of its own to replace.
# ==============================================================================

%global xremap_version 0.15.13
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
Release:        4%{?dist}
Summary:        ParchaOS keyboard remap: Super as Ctrl and friends, via xremap

License:        MIT AND GPL-2.0-or-later
URL:            https://github.com/xremap/xremap
Source0:        https://github.com/xremap/xremap/releases/download/v%{xremap_version}/xremap-linux-x86_64-gnome.zip
Source1:        https://github.com/xremap/xremap-gnome/archive/%{gnome_ext_commit}/xremap-gnome-%{gnome_ext_shortcommit}.tar.gz
Source2:        parchaos-keyboard-remap-files.tar.gz

ExclusiveArch:  x86_64

BuildRequires:  unzip

Requires:       systemd
Requires:       gnome-shell >= 45
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
Shell extension. Ported from Pulsar OS's own gnome-macos-remap-wayland,
adapted from an interactive per-user install script into a real,
declarative RPM (systemd user-preset, udev uaccess, dconf db) that
works correctly regardless of what username Calamares creates during
a real disk install.

%prep
%setup -q -c -T -n %{name}-%{version}
mkdir xremap-bin
(cd xremap-bin && unzip -o %{SOURCE0})
tar xzf %{SOURCE1}
tar xzf %{SOURCE2}

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
install -Dm0644 usr/lib/systemd/user/parchaos-keyboard-remap.service %{buildroot}%{_prefix}/lib/systemd/user/parchaos-keyboard-remap.service
install -Dm0644 usr/lib/systemd/user-preset/90-parchaos-keyboard-remap.preset %{buildroot}%{_prefix}/lib/systemd/user-preset/90-parchaos-keyboard-remap.preset
install -Dm0644 usr/lib/udev/rules.d/90-parchaos-keyboard-remap-uinput.rules %{buildroot}%{_prefix}/lib/udev/rules.d/90-parchaos-keyboard-remap-uinput.rules
install -Dm0644 usr/lib/modules-load.d/parchaos-keyboard-remap-uinput.conf %{buildroot}%{_prefix}/lib/modules-load.d/parchaos-keyboard-remap-uinput.conf
install -Dm0644 etc/dconf/db/local.d/02-parchaos-keyboard-remap %{buildroot}%{_sysconfdir}/dconf/db/local.d/02-parchaos-keyboard-remap

%post
udevadm control --reload-rules >/dev/null 2>&1 || :
dconf update >/dev/null 2>&1 || :
# Enables the unit globally for every user on first install -- including
# the upgrade from parchaos-macos-remap, whose users only had the old unit
# name enabled (per-user, by systemd's first-login preset run).
%systemd_user_post parchaos-keyboard-remap.service

%preun
%systemd_user_preun parchaos-keyboard-remap.service

%postun
dconf update >/dev/null 2>&1 || :

%files
%{_bindir}/xremap
%{_datadir}/gnome-shell/extensions/xremap@k0kubun.com/
%{_sysconfdir}/xremap/config.yml
%{_prefix}/lib/systemd/user/parchaos-keyboard-remap.service
%{_prefix}/lib/systemd/user-preset/90-parchaos-keyboard-remap.preset
%{_prefix}/lib/udev/rules.d/90-parchaos-keyboard-remap-uinput.rules
%{_prefix}/lib/modules-load.d/parchaos-keyboard-remap-uinput.conf
%{_sysconfdir}/dconf/db/local.d/02-parchaos-keyboard-remap

%changelog
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
