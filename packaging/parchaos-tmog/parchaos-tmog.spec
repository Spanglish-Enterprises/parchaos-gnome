# ==============================================================================
# TMOG (Task Manager OG, https://tmog.org) is Dave Plummer's native
# cross-platform system monitor -- closed-source freemium software (free
# edition + paid Pro tier), NOT part of the pearOS/Pear-Project family.
# Its own license page explicitly disclaims "continued distribution of
# either edition," which reads as the author reserving distribution
# rights, not granting them -- so unlike every other package in this
# project, ParchaOS does NOT bundle TMOG's actual binary in this repo,
# its SRPM, or the COPR build. This package ships only a .desktop
# launcher and a small wrapper script (files/usr/bin/parchaos-tmog-launch)
# that downloads the real, official AppImage directly from tmog.org's
# own download URL the first time the user launches it, and runs the
# cached copy after that. ParchaOS/its COPR never hosts or
# redistributes the TMOG binary itself -- the end user's own machine
# fetches it straight from the vendor, same as a "Download X" button
# would.
#
# Named parchaos-tmog, not pearos-tmog: the pearos-* prefix elsewhere
# in this project (pearos-dock, pearos-settings, pearos-liquidgel,
# etc.) marks a genuine port/fork of real pearOS-archlinux/Pear-Project
# upstream source -- it names which upstream flavor is being ported,
# not the product (see README's Branding section). TMOG has no
# connection to pearOS at all; this is a product-original addition, so
# it gets the product's own prefix. RENAMED 2026-09-22 from an earlier
# plumos-tmog draft, itself renamed from a first pearos-tmog draft --
# neither of those two earlier names was ever referenced by
# packages.sh before being corrected, so there's no real history lost
# here, just the naming settling on the actual current product name
# (plumOS was already taken; ParchaOS replaces it).
#
# Like pearos-calamares-config, there's no upstream release tarball for
# this package (it's ParchaOS's own small integration script, not a
# port of any pearOS/Pear-Project source) -- Source0 is a local tarball
# built FROM this directory's checked-in files/ tree at package-build
# time:
#   tar czf parchaos-tmog-files.tar.gz -C files .
# into ~/rpmbuild/SOURCES/ before `rpmbuild -bs`.
# ==============================================================================

Name:           parchaos-tmog
Version:        1.0.0
Release:        2%{?dist}
Summary:        Launcher for TMOG (Task Manager OG), fetched from the official vendor on first run

License:        NOASSERTION
URL:            https://tmog.org
Source0:        parchaos-tmog-files.tar.gz
BuildArch:      noarch

Requires:       curl
# AppImages need FUSE to mount themselves; the wrapper script falls back
# to --appimage-extract-and-run if this isn't present, so this is a soft
# dependency, not a hard Requires.
Recommends:     fuse

%description
Adds a "TMOG" entry to the application menu. TMOG (Task Manager OG) is a
native, non-Electron system monitor by Dave Plummer (original author of
Windows Task Manager) covering CPU, memory, disk, network, and power
consumption -- see https://tmog.org. This package does not contain
TMOG's own binary: the first launch downloads the official AppImage
directly from tmog.org and caches it under
~/.local/share/parchaos-tmog/, exactly as if the user had downloaded and
run it themselves.

%prep
%setup -q -c -n %{name}-%{version}

%install
mkdir -p %{buildroot}
cp -a usr %{buildroot}/
chmod 0755 %{buildroot}%{_bindir}/parchaos-tmog-launch

%files
%{_bindir}/parchaos-tmog-launch
%{_datadir}/applications/org.parchaos.TMOG.desktop

%changelog
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-2
- Verify the downloaded TMOG AppImage against a pinned SHA-256 before
  running it, and keep launch errors in a private temporary file instead
  of a fixed name in /tmp.
* Tue Sep 22 2026 ParchaOS packaging - 1.0.0-1
- Initial package under the parchaos-* name (product rebrand from
  plumOS to ParchaOS). .desktop launcher + first-run-fetch wrapper
  script for TMOG. Confirmed the official AppImage download URL
  (https://tmog.org/downloads/TaskManagerOG-0.1.4-x86_64.AppImage)
  resolves with a real 200 response, content-type
  application/vnd.appimage, ~35MB, served via Cloudflare directly from
  tmog.org. Verified end-to-end on a real build under the previous
  plumos-tmog name: installed the RPM, confirmed the .desktop file
  validates, confirmed a real first-run download (33.58MB, matches
  vendor content-length), confirmed the AppImage reaches real Qt
  initialization (only fails on "no display", expected over SSH), and
  confirmed a second run reuses the cache without re-downloading. Not
  yet re-verified under this exact package name (rename-only diff from
  the already-verified plumos-tmog, no logic changes).
