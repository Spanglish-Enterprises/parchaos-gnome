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
Release:        16%{?dist}
Summary:        ParchaOS icon theme

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
# Batch 2 (ticket #13): original icons for the most visible apps, generated
# by parchaos-icons/generate.py, replacing MacTahoe's copies of Apple's.
Source5:        parchaos-calendar.svg
Source6:        parchaos-clock.svg
Source7:        parchaos-calculator.svg
Source8:        parchaos-contacts.svg
Source9:        parchaos-mail.svg
Source10:        parchaos-settings.svg
Source11:        parchaos-terminal.svg
Source12:        parchaos-text-editor.svg
Source13:        parchaos-weather.svg
Source14:        parchaos-screenshot.svg
Source15:        parchaos-system-monitor.svg
Source16:        parchaos-disks.svg
# Batch 3 (ticket #13): folders and trash (places), generated too.
Source17:       parchaos-folder.svg
Source18:       parchaos-folder-open.svg
Source19:       parchaos-folder-documents.svg
Source20:       parchaos-folder-download.svg
Source21:       parchaos-folder-music.svg
Source22:       parchaos-folder-images.svg
Source23:       parchaos-folder-videos.svg
Source24:       parchaos-folder-desktop.svg
Source25:       parchaos-folder-home.svg
Source26:       parchaos-folder-templates.svg
Source27:       parchaos-folder-public.svg
Source28:       parchaos-folder-remote.svg
Source29:       parchaos-trash.svg
Source30:       parchaos-trash-full.svg
# Batch 4 (ticket #13).
Source31:       parchaos-preview.svg
Source32:       parchaos-archive.svg
Source33:       parchaos-firmware.svg
# The ParchaOS mark, replacing MacTahoe's Apple-logo start-here icons.
Source34:       parchaos-logo.svg
Source35:       parchaos-logo-symbolic.svg
# Original keyboard glyph; MacTahoe draws input-keyboard-symbolic as the
# reference desktop's command-key symbol.
Source36:       parchaos-keyboard-symbolic.svg
# Original file-type icons (one per kind) and the script that maps
# MacTahoe's file-type icons onto them.
Source37:       mime-map.py
# ParchaOS's cloud icon, in place of MacTahoe's icloud.svg.
Source38:       parchaos-cloud.svg
# Removes every MacTahoe app icon ParchaOS hasn't replaced, and MacTahoe's
# drawings of Apple hardware and file types (see the script's docstring).
Source70:       prune-apps.py
Source71:       allowlist.txt
Source40:       parchaos-mime-generic.svg
Source41:       parchaos-mime-text.svg
Source42:       parchaos-mime-code.svg
Source43:       parchaos-mime-document.svg
Source44:       parchaos-mime-spreadsheet.svg
Source45:       parchaos-mime-presentation.svg
Source46:       parchaos-mime-pdf.svg
Source47:       parchaos-mime-image.svg
Source48:       parchaos-mime-audio.svg
Source49:       parchaos-mime-video.svg
Source50:       parchaos-mime-archive.svg
Source51:       parchaos-mime-package.svg
Source52:       parchaos-mime-disk.svg
Source53:       parchaos-mime-font.svg
Source54:       parchaos-mime-certificate.svg
Source55:       parchaos-mime-contact.svg
Source56:       parchaos-mime-calendar.svg
Source57:       parchaos-mime-mail.svg
Source58:       parchaos-mime-web.svg
Source59:       parchaos-mime-database.svg

BuildArch:      noarch
BuildRequires:  python3

# Real bug found via a real COPR build attempt (2026-09-23): install.sh
# calls gtk-update-icon-cache internally after installing each variant
# -- real installed variants confirmed via that same build's log
# ("Installing '.../icons/MacTahoe'", "MacTahoe-light", "MacTahoe-dark")
# before it failed on this missing command.
BuildRequires:  gtk-update-icon-cache

Requires:       hicolor-icon-theme
# Apps whose MacTahoe icon was removed fall back to GNOME's icons.
Requires:       adwaita-icon-theme

%description
ParchaOS's icon theme: original ParchaOS artwork for apps, folders and
file types, on a base built from vinceliuice's MacTahoe-icon-theme
using its own install.sh. Default
(neutral) color variant.

%prep
%autosetup -n MacTahoe-icon-theme-%{commit}

%build
# install.sh does the real work directly into the destination we pass.

%install
mkdir -p %{buildroot}%{_datadir}/icons
./install.sh -t default -d %{buildroot}%{_datadir}/icons

# Replace the Apple-look icons with original ParchaOS artwork. MacTahoe
# points every alias (e.g. org.gnome.Nautilus, org.gnome.Calendar,
# org.gnome.Settings) at one target file per design, so replacing the
# targets covers all of them.
# MacTahoe-light's apps/ dir is a symlink to MacTahoe's.
for theme in MacTahoe MacTahoe-dark; do
    d=%{buildroot}%{_datadir}/icons/$theme/apps/scalable
    for pair in file-manager:%{SOURCE1} softwarecenter:%{SOURCE2} \
                web-browser:%{SOURCE3} safari:%{SOURCE4} \
                calendar:%{SOURCE5} preferences-system-time:%{SOURCE6} calc:%{SOURCE7} \
                addressbook:%{SOURCE8} internet-mail:%{SOURCE9} preferences-system:%{SOURCE10} \
                terminal:%{SOURCE11} text-editor:%{SOURCE12} indicator-weather:%{SOURCE13} \
                accessories-screenshot:%{SOURCE14} utilities-system-monitor:%{SOURCE15} gnome-disks:%{SOURCE16} \
                org.gnome.Loupe:%{SOURCE31} file-roller:%{SOURCE32} hwinfo:%{SOURCE33} \
                icloud:%{SOURCE38}; do
        name=${pair%%%%:*}; src=${pair#*:}
        if [ -e "$d/$name.svg" ] || [ -L "$d/$name.svg" ]; then
            rm -f "$d/$name.svg"
            install -m 0644 "$src" "$d/$name.svg"
        fi
    done
done

# Places: violet ParchaOS folders and the trash replace MacTahoe's
# Apple-look ones. Unlike apps/, each variant has its own places/ dir.
# The fixed-size copies (16/22/24) are overwritten with the same scalable
# SVGs (other icons link to them), so the new art shows at every size.
for theme in MacTahoe MacTahoe-dark MacTahoe-light; do
    d=%{buildroot}%{_datadir}/icons/$theme/places/scalable
    for pair in \
                folder:%{SOURCE17} folder-open:%{SOURCE18} folder-documents:%{SOURCE19} \
                folder-download:%{SOURCE20} folder-music:%{SOURCE21} folder-images:%{SOURCE22} \
                folder-videos:%{SOURCE23} user-desktop:%{SOURCE24} user-home:%{SOURCE25} \
                folder-templates:%{SOURCE26} folder-public:%{SOURCE27} folder-html:%{SOURCE28} \
                user-trash:%{SOURCE29} user-trash-full:%{SOURCE30}; do
        name=${pair%%%%:*}; src=${pair#*:}
        if [ -e "$d/$name.svg" ] || [ -L "$d/$name.svg" ]; then
            rm -f "$d/$name.svg"
            install -m 0644 "$src" "$d/$name.svg"
        fi
    done
    for size in 16 22 24; do
        sd=%{buildroot}%{_datadir}/icons/$theme/places/$size
        [ -d "$sd" ] || continue
        for pair in \
                folder:%{SOURCE17} folder-open:%{SOURCE18} folder-documents:%{SOURCE19} \
                folder-download:%{SOURCE20} folder-music:%{SOURCE21} folder-images:%{SOURCE22} \
                folder-videos:%{SOURCE23} user-desktop:%{SOURCE24} user-home:%{SOURCE25} \
                folder-templates:%{SOURCE26} folder-public:%{SOURCE27} folder-html:%{SOURCE28} \
                user-trash:%{SOURCE29} user-trash-full:%{SOURCE30}; do
            name=${pair%%%%:*}; src=${pair#*:}
            # Overwrite the small copy in place (other icons link to it);
            # the SVG scales cleanly to these sizes.
            if [ -e "$sd/$name.svg" ] && [ ! -L "$sd/$name.svg" ]; then
                install -m 0644 "$src" "$sd/$name.svg"
            fi
        done
    done
done

# The Apple logo: MacTahoe draws it as start-here (the distributor/menu
# logo) and the Budgie launcher applet. Overwrite every real file (the
# aliases link to them) with the ParchaOS mark, symbolic where the name
# asks for it. folder-apple gets the plain ParchaOS folder.
find %{buildroot}%{_datadir}/icons/MacTahoe* -type f \
    \( -name 'start-here*.svg' -o -name 'budgie-app-launcher-applet*.svg' \) |
while read -r f; do
    case "$f" in
        *-symbolic.svg|*/symbolic/*) install -m 0644 %{SOURCE35} "$f" ;;
        *) install -m 0644 %{SOURCE34} "$f" ;;
    esac
done
find %{buildroot}%{_datadir}/icons/MacTahoe* -type f -name 'folder-apple*.svg' |
while read -r f; do
    case "$f" in
        *-symbolic.svg) install -m 0644 %{SOURCE35} "$f" ;;
        *) install -m 0644 %{SOURCE17} "$f" ;;
    esac
done

find %{buildroot}%{_datadir}/icons/MacTahoe* -type f -name 'input-keyboard-symbolic.svg' |
while read -r f; do
    install -m 0644 %{SOURCE36} "$f"
done

# File-type icons: MacTahoe's page-style ones imitate the reference
# desktop's document icons; replace each with ParchaOS's own for its kind.
python3 %{SOURCE37} %{buildroot}%{_datadir}/icons %{_sourcedir}

# Drop MacTahoe's weather-*-large/-small condition icons. GNOME Weather
# draws these at ~200px, and most of MacTahoe's embed small raster
# images, so they came out dotted/pixelated. Without them the lookup
# falls through to hicolor, where GNOME Weather ships crisp scalable
# originals. The *-symbolic weather icons are untouched.
find %{buildroot}%{_datadir}/icons/MacTahoe* \
    \( -name 'weather-*-large.svg' -o -name 'weather-*-small.svg' \) \
    \( -type f -o -type l \) -delete

# Keep only ParchaOS's own app icons: everything else falls back to
# GNOME's (Adwaita, hicolor). Fails the build if an excluded name survives.
python3 %{SOURCE70} %{buildroot}%{_datadir}/icons %{SOURCE71}
for theme in MacTahoe MacTahoe-dark MacTahoe-light; do
    sed -i 's/^Inherits=.*/Inherits=Adwaita,hicolor/' %{buildroot}%{_datadir}/icons/$theme/index.theme
done
grep -q '^Inherits=Adwaita,hicolor' %{buildroot}%{_datadir}/icons/MacTahoe/index.theme

# ParchaOS uses GNOME's Adwaita cursors; MacTahoe's copy the reference
# desktop's cursor designs, so they aren't shipped.
rm -rf %{buildroot}%{_datadir}/icons/MacTahoe*/cursors

# install.sh built icon-theme.cache before the edits above; rebuild it so
# it matches what we actually ship.
for theme in MacTahoe MacTahoe-dark MacTahoe-light; do
    gtk-update-icon-cache -f -q %{buildroot}%{_datadir}/icons/$theme
done

%files
%license COPYING
%doc README.md
%{_datadir}/icons/*

%changelog
* Sat Sep 26 2026 ParchaOS packaging - 2026.09.23-16
- New original ParchaOS logo (halved passion fruit), generated by
  branding/logo/make-brand.py; artwork CC BY-SA 4.0. Replaces the
  adapted third-party icon.
* Sat Sep 26 2026 ParchaOS packaging - 2026.09.23-15
- Keep only ParchaOS's own app icons: every other MacTahoe app icon is
  removed (apps fall back to Adwaita/hicolor), Apple-named files get
  neutral names, and MacTahoe's drawings of Apple hardware and file
  types are removed. The build fails if an excluded name survives.
  Inherits Adwaita,hicolor.
* Sat Sep 26 2026 ParchaOS packaging - 2026.09.23-14
- Stop shipping MacTahoe's cursors (ParchaOS uses Adwaita's); neutral
  summary.
* Sat Sep 26 2026 ParchaOS packaging - 2026.09.23-13
- File-type icons: programs no longer get the spreadsheet icon,
  Makefiles the disk icon, or Word templates the code icon (tighter
  matching, with a self-test).
* Sat Sep 26 2026 ParchaOS packaging - 2026.09.23-12
- Replace MacTahoe's icloud.svg with ParchaOS's cloud icon.
* Sat Sep 26 2026 ParchaOS packaging - 2026.09.23-11
- Original file-type icons: MacTahoe's page-style file icons (which
  imitate the reference desktop's document icons) are replaced with
  ParchaOS's own, one design per kind of file (text, code, documents,
  spreadsheets, presentations, PDF, images, audio, video, archives,
  packages, disk images, fonts, certificates, contacts, calendars, mail,
  web, databases).
* Sat Sep 26 2026 ParchaOS packaging - 2026.09.23-10
- Replace MacTahoe's command-key symbol used as the keyboard icon
  (input-keyboard-symbolic) with an original keyboard glyph.
* Sat Sep 26 2026 ParchaOS packaging - 2026.09.23-9
- Replace the Apple-logo start-here, Budgie launcher and folder-apple icons with the ParchaOS mark (a halved passion fruit) and the ParchaOS folder.
* Sat Sep 26 2026 ParchaOS packaging - 2026.09.23-8
- Original icons for the image viewer (Preview), Archive Manager and
  Firmware; MacTahoe's copied Apple's Preview and Archive Utility, and its
  Firmware icon carried a chip maker's logo (ticket #13).
* Sat Sep 26 2026 ParchaOS packaging - 2026.09.23-7
- Original ParchaOS folders (violet with a gold tab, with glyphs for
  Documents, Downloads, Music, Pictures, Videos, Desktop, Home, Templates,
  Public and remote folders) and trash (empty/full), replacing MacTahoe's
  Apple-look places icons in all three variants, including their
  fixed-size copies (ticket #13).
* Sat Sep 26 2026 ParchaOS packaging - 2026.09.23-6
- Original ParchaOS icons for Calendar, Clock, Calculator, Contacts, Mail,
  Settings, Terminal, Text Editor, Weather, Screenshot, System Monitor and
  Disks, replacing MacTahoe's reproductions of Apple's icons (ticket #13).
* Fri Sep 25 2026 ParchaOS packaging - 2026.09.23-5
- Remove MacTahoe's weather condition icons (-large/-small), which
  embed low-resolution raster images and looked pixelated in GNOME
  Weather; the app's own scalable icons from hicolor are used instead.
- Regenerate icon-theme.cache after the spec's icon changes.
* Fri Sep 25 2026 ParchaOS packaging - 2026.09.23-4
- Icon v2: redraw Parcher, Parcha Store and Parcha Browser in the
  MacTahoe palette (folder blues, white tiles, soft violet) so they sit
  naturally in the dock; the v1 gold/magenta palette clashed. Parcher is
  now a white folder on a blue tile (chosen from two drafts).
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
