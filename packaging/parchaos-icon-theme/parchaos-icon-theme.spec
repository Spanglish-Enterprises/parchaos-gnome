# ==============================================================================
# ParchaOS's icon theme — real Tahoe-styled icon theme, ported directly
# from vinceliuice's real upstream MacTahoe-icon-theme (GPL-3.0, same
# trusted author as MacTahoe-gtk-theme/parchaos-gtk-theme and
# WhiteSur-kde already used in the KDE variant). Pulsar OS ships the
# same theme via their own thin fork; porting from the real upstream
# directly per this project's established pattern.
#
# Uses upstream's own real install.sh (-d DEST -t VARIANT), which
# (unlike the GTK theme's installer) doesn't refuse to run as root —
# it just changes its DEST_DIR default based on $UID, which this spec
# overrides explicitly with -d anyway. No root-check patching needed.
#
# "default" color variant chosen (neutral/monochrome-leaning) rather
# than upstream's own "blue" default, to pair with the dark GTK theme
# rather than introduce a second, uncoordinated accent color.
# ==============================================================================

Name:           parchaos-icon-theme
Version:        2026.09.23
Release:        3%{?dist}
Summary:        ParchaOS's Tahoe-styled icon theme

License:        GPL-3.0-or-later
URL:            https://github.com/vinceliuice/MacTahoe-icon-theme
%global commit  839848b9a8a38a92a6936e30c4abe35cc6f2546d
%global shortcommit %(c=%{commit}; echo ${c:0:7})
Source0:        %{url}/archive/%{commit}/MacTahoe-icon-theme-%{shortcommit}.tar.gz
# Original ParchaOS icons replacing MacTahoe's copies of Apple's own app
# icons (Finder, App Store, Safari): see parchaos-icons/README.md.
Source1:        parcher.svg
Source2:        parcha-store.svg
Source3:        pafari.svg
Source4:        parcha-browser.svg

BuildArch:      noarch

# Real bug found via a real COPR build attempt (2026-09-23): install.sh
# calls gtk-update-icon-cache internally after installing each variant
# -- real installed variants confirmed via that same build's log
# ("Installing '.../icons/MacTahoe'", "MacTahoe-light", "MacTahoe-dark")
# before it failed on this missing command.
BuildRequires:  gtk-update-icon-cache

Requires:       hicolor-icon-theme

%description
ParchaOS's real Tahoe-styled icon theme, built from vinceliuice's real
upstream MacTahoe-icon-theme using its own install.sh. Default
(neutral) color variant.

%prep
%autosetup -n MacTahoe-icon-theme-%{commit}

%build
# install.sh does the real work directly into the destination we pass.

%install
mkdir -p %{buildroot}%{_datadir}/icons
./install.sh -t default -d %{buildroot}%{_datadir}/icons

# Replace the Apple-look icons. MacTahoe points every alias (e.g.
# org.gnome.Nautilus, system-file-manager, org.gnome.Software, epiphany)
# at these four files, so replacing the targets covers all of them.
# MacTahoe-light's apps/ dir is a symlink to MacTahoe's.
for theme in MacTahoe MacTahoe-dark; do
    d=%{buildroot}%{_datadir}/icons/$theme/apps/scalable
    for pair in file-manager:%{SOURCE1} softwarecenter:%{SOURCE2} \
                web-browser:%{SOURCE3} safari:%{SOURCE4}; do
        name=${pair%%%%:*}; src=${pair#*:}
        if [ -e "$d/$name.svg" ] || [ -L "$d/$name.svg" ]; then
            rm -f "$d/$name.svg"
            install -m 0644 "$src" "$d/$name.svg"
        fi
    done
done

%files
%license COPYING
%doc README.md
%{_datadir}/icons/*

%changelog
* Fri Sep 25 2026 ParchaOS packaging - 2026.09.23-3
- Replace MacTahoe's reproductions of Apple's Finder, App Store and
  Safari icons with original ParchaOS artwork for Parcher, Parcha Store,
  Pafari/generic browsers and Parcha Browser (keeps Apple trade dress out
  of the shipped system, per the naming policy).
* Wed Sep 23 2026 ParchaOS packaging - 2026.09.23-2
- Real bug found via a real COPR build attempt: install.sh calls
  gtk-update-icon-cache internally, missing BuildRequires. Icon
  variants themselves installed correctly before this failure.
* Wed Sep 23 2026 ParchaOS packaging - 2026.09.23-1
- Initial package, real upstream source (vinceliuice/MacTahoe-icon-theme,
  GPL-3.0-or-later), pinned to commit 839848b, default color variant.
  Not yet build-tested.
