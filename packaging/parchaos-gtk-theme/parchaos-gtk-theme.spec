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
Release:        2%{?dist}
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
Requires:       gnome-themes-extra
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
    sed -i 's/! -w "\/root"/false/g' libs/lib-core.sh
fi
if [ -f libs/lib-install.sh ]; then
    sed -i 's/UID -ne 0/false/g; s/EUID -ne 0/false/g' libs/lib-install.sh
fi

%build
# install.sh does the real work (SCSS compile via sassc, file assembly)
# directly into the destination we pass -- nothing to build separately.

%install
./install.sh -c dark -d %{buildroot}%{_datadir}/themes --silent-mode

%files
%license COPYING
%doc README.md
%{_datadir}/themes/*

%changelog
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
