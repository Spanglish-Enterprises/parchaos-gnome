# ==============================================================================
# ParchaOS's GTK/GNOME Shell theme — real Tahoe-styled GTK3/GTK4 theme
# (dock, traffic-light window controls, translucent panels), forked
# from Pulsar OS's own fork
# (Inled-Pulsar-OS/MacTahoe-gtk-theme), which is itself a real fork of
# vinceliuice's well-known MacTahoe-gtk-theme (MIT) — the same trusted
# author whose WhiteSur-kde this project already ported for the KDE
# variant. Confirmed via `gh api` before writing this: Pulsar OS's own
# fork adds no real functional changes over upstream beyond
# accent-color/libadwaita integration tweaks in their own
# prepare-assets.sh; this spec ports directly from the REAL vinceliuice
# upstream instead of going through Pulsar's own fork+patches, since
# their patches are non-essential polish (dynamic accent-color wiring)
# this project can add later once the basic theme is verified working.
#
# License: MIT (matches upstream's own LICENSE/COPYING).
#
# Scoped to a single dark variant for v1 (matching Pulsar OS's own real
# choice: `-c dark`), not the theme's full light/dark x multiple-accent
# matrix — keeps this port narrow and testable rather than trying to
# ship every combination on the first pass.
#
# Uses upstream's own real install.sh (same real mechanism Pulsar OS's
# own packaging uses, confirmed via their prepare-assets.sh) rather
# than hand-copying files, since the script does real SCSS compilation
# (sassc) plus a nontrivial file-selection/renaming pipeline per
# variant that would be error-prone to reimplement by hand. Root/sudo
# checks patched out the same way Pulsar OS's own real prepare-assets.sh
# does it (`UID -ne 0` -> `false`), needed because install.sh normally
# refuses some operations when run as root, but running as root inside
# an RPM %%install/mock chroot is completely normal.
# ==============================================================================

Name:           parchaos-gtk-theme
Version:        2026.09.23
Release:        8%{?dist}
Summary:        ParchaOS's Tahoe-styled GTK3/GTK4 theme

License:        MIT
URL:            https://github.com/vinceliuice/MacTahoe-gtk-theme
# Pinned to a specific commit for reproducibility (checked via
# `gh api repos/vinceliuice/MacTahoe-gtk-theme/commits/main`, not a
# moving branch reference).
%global commit  09198632e789f72ed46574812ef6d389a53809f0
%global shortcommit %(c=%{commit}; echo ${c:0:7})
Source0:        %{url}/archive/%{commit}/MacTahoe-gtk-theme-%{shortcommit}.tar.gz

BuildArch:      noarch

BuildRequires:  sassc
BuildRequires:  git
# Real bug found via a real COPR build attempt (2026-09-23, build
# 11024750): install_theme_deps() (libs/lib-install.sh) auto-detects
# missing `glib-compile-resources` (glib2-devel) / `xmllint`
# (libxml2) and, before attempting a `sudo dnf install`, does a real
# internet-connectivity ping (prepare_deps() -> get_utc_epoch_time(),
# opens /dev/tcp/iana.org/80) -- which always fails in COPR's
# network-isolated build sandbox, and even if it somehow succeeded,
# the subsequent unattended `sudo dnf install` would hang forever on
# a password prompt. Our build VM test shell already has both tools
# installed, masking this from every local test until reproduced by
# explicitly hiding them from PATH.
BuildRequires:  glib2-devel
BuildRequires:  libxml2
# Real bug found via a real COPR build attempt (2026-09-23, build
# 11024653): lib-core.sh runs `set -Eeo pipefail` then, near its very
# top (before any output is printed), does
# `SUDO_BIN="$(command -v sudo)"` as a plain assignment -- if `sudo`
# isn't present, that command substitution's nonzero exit kills the
# whole script instantly and silently under errexit. Minimal COPR mock
# chroots don't guarantee `sudo` is present (unlike our own build VM test
# shell, which has it for its own SSH workflow -- that's why local
# testing never reproduced this). `sudo` itself is never actually
# invoked in our root-less RPM build path; it just needs to resolve so
# the assignment succeeds.
BuildRequires:  sudo
# Real bug found at ISO-build time (2026-09-23, not caught by COPR's
# own build since Requires: aren't resolved there): `gnome-themes-extra`
# doesn't exist as an installable package in Fedora 44 at all (`dnf
# repoquery '*gnome-themes*'` returns nothing) -- GNOME bundles Adwaita
# natively now, this package appears retired upstream. Nothing in
# MacTahoe-gtk-theme's own installed files actually needs it (it's a
# GTK3/GTK4 theme, self-contained); dropped rather than guessing at a
# replacement name.
Requires:       gtk-murrine-engine

%description
ParchaOS's real Tahoe-styled GTK3/GTK4 theme (dock, traffic-light
window controls, translucent panels), built from vinceliuice's real
upstream MacTahoe-gtk-theme (MIT) using its own install.sh — the same
underlying theme Pulsar OS ships (Inled's own fork adds only
non-essential accent-color polish this package doesn't yet replicate).
Dark variant only for this initial release.

%prep
%autosetup -n MacTahoe-gtk-theme-%{commit}

# Root/sudo-check patches — same real mechanism Pulsar OS's own
# packaging uses (confirmed against their real prepare-assets.sh)
# because install.sh assumes it's never run as root, but an RPM build
# environment always is. Real bug found via a real COPR build attempt
# (2026-09-23): the first pass here only patched install.sh/tweaks.sh/
# lib-install.sh's UID/EUID checks, but --silent-mode's actual root
# gate lives in a DIFFERENT function (full_sudo(), in libs/lib-core.sh)
# checking `[[ ! -w "/root" ]]` -- a check Pulsar OS's own real
# prepare-assets.sh specifically neutralizes too (confirmed by
# re-reading their script), which this spec's first draft missed.
sed -i 's/UID -ne 0/false/g; s/EUID -ne 0/false/g' install.sh tweaks.sh 2>/dev/null || true
if [ -f libs/lib-core.sh ]; then
    # NOTE (real bug found 2026-09-23, root-caused via BASH_XTRACEFD
    # tracing that survives install.sh's own internal `exec 2>` fd
    # reassignment): a naive `s/! -w "\/root"/false/` here produces
    # `if [[ false ]]; then`, but bash has no boolean literals --
    # `[[ false ]]` is a single-word test, i.e. an implicit `-n false`
    # (is the STRING "false" non-empty?), which is always TRUE. That
    # patch was silently making full_sudo()'s root-check fire
    # unconditionally regardless of actual root status -- the real
    # explanation for why testing as genuine root never helped. Using
    # a real always-false relational test instead.
    sed -i 's/! -w "\/root"/1 -eq 2/g' libs/lib-core.sh
fi
if [ -f libs/lib-install.sh ]; then
    sed -i 's/UID -ne 0/false/g; s/EUID -ne 0/false/g' libs/lib-install.sh
fi

%build
# install.sh does the real work (SCSS compile via sassc, file assembly)
# directly into the destination we pass -- nothing to build separately.

%install
# Real bug found via a real COPR build attempt (2026-09-23, build
# 11024717): install.sh's own -d validation (check_param) requires the
# destination to already exist and be writable -- it doesn't create
# it. Every local verification this session implicitly worked around
# this by mkdir -p'ing the test destination by hand before invoking
# install.sh, masking the fact that the spec itself never did.
# parchaos-icon-theme's spec already does this correctly; this one
# didn't.
mkdir -p %{buildroot}%{_datadir}/themes
./install.sh -c dark -d %{buildroot}%{_datadir}/themes --silent-mode

# Real gap found 2026-09-24 (real user feedback: "we don't seem to have
# a light mode and we should provide both"): install.sh's own
# COMMAND_COLOR_VARIANTS (libs/lib-core.sh) is
# ('light' 'dark') -- light was always a real, fully-supported
# upstream variant (a genuine gtk-Light.scss compile path, not a
# reskin of dark), this spec just never built it. The banner comment
# above this %install section even already flagged "dark variant only"
# as a known gap before this. Building it as a second, separate
# install.sh invocation rather than passing both colors to one call:
# install.sh's own default behavior when given multiple -c values is
# to build every combination of ALL variant axes (opacity/theme-accent/
# scheme) for EACH color, multiplying build time and output size far
# beyond what this profile ships (only the default Tahoe-style,
# standard-scheme, normal-opacity combination) -- two separate calls,
# each still implicitly scoped to that one default combination, stay
# fast and produce exactly MacTahoe-Dark and MacTahoe-Light, nothing
# more.
./install.sh -c light -d %{buildroot}%{_datadir}/themes --silent-mode

%files
%license COPYING
%doc README.md
%{_datadir}/themes/*

%changelog
* Thu Sep 24 2026 ParchaOS packaging - 2026.09.23-8
- Real user feedback: no light mode was ever shipped. Confirmed
  upstream's own libs/lib-core.sh has always supported a real 'light'
  color variant (COMMAND_COLOR_VARIANTS=('light' 'dark')) -- this spec
  only ever built 'dark'. Added a second install.sh -c light
  invocation; %files' existing %{_datadir}/themes/* wildcard already
  picks up the new MacTahoe-Light output with no further changes
  needed.
* Wed Sep 23 2026 ParchaOS packaging - 2026.09.23-7
- Real fifth root cause found -- this time not from a COPR build (which
  doesn't resolve Requires:), but from the ISO build's own package
  install: "nothing provides gnome-themes-extra needed by
  parchaos-gtk-theme". Confirmed via `dnf repoquery` that this package
  doesn't exist in Fedora 44 at all (retired upstream, GNOME bundles
  Adwaita natively now). Nothing in the theme's own installed files
  needs it; dropped the Requires rather than guessing a replacement.
* Wed Sep 23 2026 ParchaOS packaging - 2026.09.23-6
- Real fourth root cause found via the actual COPR build log
  (11024750 failed with "DEPS ERROR: You have an internet connection
  issue"): install_theme_deps() auto-detects missing
  glib-compile-resources/xmllint and, before auto-installing them,
  does a real internet-connectivity ping that always fails in COPR's
  network-isolated sandbox (and would otherwise hang on an unattended
  sudo password prompt). the build VM's test shell already had both tools,
  masking this locally. Reproduced by hiding them from PATH; fixed
  with BuildRequires: glib2-devel, libxml2.
* Wed Sep 23 2026 ParchaOS packaging - 2026.09.23-5
- Real third root cause found via the actual COPR build log (11024717
  failed with "'-d' ERROR: You have no permission to access that
  directory."): install.sh's check_param validates `-d` via
  `[[ ! -w "${value}" && ! -w "$(dirname ${value})" ]]` -- a
  nonexistent dest is fine as long as its PARENT exists and is
  writable (it auto-mkdir's just the leaf). But rpmbuild only creates
  the bare %{buildroot} itself, not %{buildroot}%{_datadir}/themes's
  intermediate usr/share/ parents, so BOTH checks failed. Every local
  verification this session used `mkdir -p` on a destination whose
  parent already existed (e.g. /tmp/...), masking this. Reproduced
  exactly with a deeply-nested nonexistent path (parent also missing);
  fixed by mkdir -p'ing the full destination before invoking
  install.sh, matching what parchaos-icon-theme's spec already does.
* Wed Sep 23 2026 ParchaOS packaging - 2026.09.23-4
- Real second root cause found via the actual COPR build log (11024653
  failed with zero install.sh output before "Bad exit status"):
  lib-core.sh's `SUDO_BIN="$(command -v sudo)"` runs under
  `set -Eeo pipefail` near the very top of the script, before any
  output is printed -- if `sudo` isn't present, that assignment's
  nonzero exit kills the whole script instantly and silently. Minimal
  COPR mock chroots don't guarantee `sudo`, unlike our own build VM test
  shell (which has it for SSH workflow use, hiding this locally).
  Reproduced exactly (zero output, exit 1) by stripping sudo from
  PATH; fixed by adding `BuildRequires: sudo` so the assignment
  resolves. sudo itself is never actually invoked in this root-less
  RPM build path.
* Wed Sep 23 2026 ParchaOS packaging - 2026.09.23-3
- REAL ROOT CAUSE FOUND (via BASH_XTRACEFD tracing that survives
  install.sh's own internal `exec 2> error_log.txt` fd reassignment,
  which was hiding the real trace from earlier bash -x attempts): the
  -2 patch's `s/! -w "\/root"/false/` produced `if [[ false ]]; then`,
  but bash has no boolean literals -- `[[ false ]]` is a single-word
  test (implicit `-n false`, is the STRING "false" non-empty?), which
  is always TRUE. That patch made full_sudo()'s check fire
  unconditionally, explaining why testing as genuine verified root
  never helped. Fixed with a real always-false relational test
  (`1 -eq 2`). Verified clean (exit 0) locally as a normal non-root
  user: produces real MacTahoe-Dark / MacTahoe-Dark-solid (+ hdpi/xhdpi
  density variants) directories.
* Wed Sep 23 2026 ParchaOS packaging - 2026.09.23-2
- Real bug found via a real COPR build attempt: --silent-mode's actual
  root check lives in libs/lib-core.sh's full_sudo() (`[[ ! -w "/root"
  ]]`), a different file/check than the UID/EUID patches already
  applied elsewhere -- fixed, matching a check Pulsar OS's own real
  packaging script specifically neutralizes too.
* Wed Sep 23 2026 ParchaOS packaging - 2026.09.23-1
- Initial package, real upstream source (vinceliuice/MacTahoe-gtk-theme,
  MIT), dark variant only. Not yet build-tested -- the install.sh
  invocation and root-check patches are based on Pulsar OS's own real
  prepare-assets.sh usage, but this project's own build environment
  (mock/COPR chroot, not their exact debootstrap/pacstrap setup) hasn't
  been verified to behave identically. Expect real iteration.
