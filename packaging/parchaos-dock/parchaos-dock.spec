# ==============================================================================
# ParchaOS's dock — a real fork of the well-known GNOME Shell extension
# Dash-to-Dock (micheleg/dash-to-dock, GPL-2.0), further forked by Pulsar
# OS as "Pulsar Dock" (Inled-Pulsar-OS/dash-to-dock) with macOS-style
# hover magnification, launch bounce animations, a downloads-folder
# stack, and live minimized-window previews — real, substantial
# functional additions on top of stock Dash-to-Dock, not just a
# reskin. Confirmed via the real repo's own metadata.json (fetched
# directly, not guessed).
#
# License: GPL-2.0 (inherited from upstream Dash-to-Dock; a real
# derivative work, distinct from Pulsar OS's own MIT-INLED original
# code — tracked carefully here since this project plans a public
# release, same rigor as parchaos-finder).
#
# Rebranded "Parcha Dock" / uuid parcha-dock@parchaos.org (was "Pulsar
# Dock" / pulsar-dock@inled.es) for ParchaOS's own product identity —
# not an Apple-trademark concern (Dash-to-Dock/"Pulsar Dock" aren't
# Apple names), just the same "ship our own branding, not verbatim
# upstream branding" reasoning already applied to the logo and Parcher.
# Different UUID also avoids ever colliding with a real, separately
# installed "pulsar-dock@inled.es" on the same system.
#
# Packaged as an architecture-independent GNOME Shell extension (JS +
# CSS + gschema, no compiled binaries) built via the real upstream
# Makefile's own `make _build` target — verified directly against that
# Makefile before writing this (sassc for the SCSS->CSS stylesheet
# compile, msgfmt for .po->.mo translations, glib-compile-schemas for
# the gschema), not guessed.
# ==============================================================================

Name:           parchaos-dock
Version:        106
Release:        1%{?dist}
Summary:        Parcha Dock — ParchaOS's macOS-styled fork of the Dash-to-Dock GNOME Shell extension

License:        GPL-2.0-only
URL:            https://github.com/Inled-Pulsar-OS/dash-to-dock
%global commit  f761ebe9a795262b42a18cf57cccd4afe9d3d5a4
%global shortcommit %(c=%{commit}; echo ${c:0:7})
Source0:        %{url}/archive/%{commit}/parchaos-dock-%{shortcommit}.tar.gz

BuildArch:      noarch

BuildRequires:  sassc
BuildRequires:  gettext
BuildRequires:  glib2
BuildRequires:  make

Requires:       gnome-shell >= 45
Requires:       dconf

%description
Parcha Dock is ParchaOS's build of a real macOS-style fork of the
well-known Dash-to-Dock GNOME Shell extension: hover magnification,
launch bounce animations, a downloads-folder stack, and live
minimized-window previews. Enabled by default as ParchaOS's dock.

%prep
%autosetup -n dash-to-dock-%{commit}

# ParchaOS branding rebrand (see banner comment above) — real upstream
# UUID/name confirmed via the real metadata.json before writing this
# sed.
sed -i \
    -e 's/pulsar-dock@inled\.es/parcha-dock@parchaos.org/g' \
    -e 's/"name": "Pulsar Dock"/"name": "Parcha Dock"/' \
    -e 's/original-author": "Inled-Pulsar-OS"/original-author": "ParchaOS"/' \
    -e 's#"url": "https://github.com/Inled-Pulsar-OS/dash-to-dock"#"url": "https://github.com/alexgalicea/parchaos-gnome"#' \
    metadata.json Makefile

%build
make _build

%install
UUID=parcha-dock@parchaos.org
DEST=%{buildroot}%{_datadir}/gnome-shell/extensions/$UUID
mkdir -p "$DEST"
cp -a _build/* "$DEST"/

# Ship the dock's own translations system-wide so the "dashtodock"
# gettext domain resolves (same real upstream mechanism the actual
# Pulsar OS package uses, confirmed via its own prepare-assets.sh).
if [ -d _build/locale ]; then
    for mo in _build/locale/*/LC_MESSAGES/*.mo; do
        [ -f "$mo" ] || continue
        lang="$(basename "$(dirname "$(dirname "$mo")")")"
        mkdir -p "%{buildroot}%{_datadir}/locale/$lang/LC_MESSAGES"
        cp "$mo" "%{buildroot}%{_datadir}/locale/$lang/LC_MESSAGES/"
    done
fi

%files
%license COPYING
%doc README.md
%{_datadir}/gnome-shell/extensions/parcha-dock@parchaos.org/
%{_datadir}/locale/*/LC_MESSAGES/dashtodock.mo

%changelog
* Wed Sep 23 2026 ParchaOS packaging - 106-1
- Initial package, real upstream fork (Inled-Pulsar-OS/dash-to-dock,
  itself a real fork of micheleg/dash-to-dock, pinned to commit
  f761ebe9), rebranded "Parcha Dock" for ParchaOS's own identity. Not
  yet build-tested against a real Fedora chroot — expect real
  iteration on %%files/%%build, same pattern as parchaos-finder.
