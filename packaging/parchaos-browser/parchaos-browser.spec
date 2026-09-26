# ==============================================================================
# ParchaOS's rebranded Chromium browser -- a real user need distinct from
# `pafari` (this profile's other browser, a WebKitGTK/Epiphany fork):
# pafari is deliberately light and WebKit-based, but real-world Google
# services (Gmail chief among them) are Chrome/Blink-tuned and can behave
# worse on WebKitGTK. This package exists to give ParchaOS a genuine
# Chromium/Blink-engine option for that case, without inheriting
# Chromium's full RAM footprint reputation any more than necessary.
#
# Deliberately NOT a from-scratch Chromium rebuild (the way Thorium/Brave
# do a real custom product-name build) -- that's a many-hour, 30+GB-disk
# source compile completely unsuited to this project's fast COPR
# pipeline. Instead: a thin rebrand on top of Fedora's own real `chromium`
# package (confirmed via real `dnf list --available` on real hardware,
# 2026-09-24 -- `chromium-freeworld` from RPM Fusion, the package this was
# first planned around, does NOT exist for this Fedora release; plain
# `chromium` from Fedora's own `updates` repo does, and Fedora has shipped
# it with Google API keys already stripped since 2021, so there's no
# baked-in Sign-in/Sync nagging to begin with). H.264 support comes from
# the `fedora-cisco-openh264` repo this profile already enables, not from
# a rpmfusion nonfree codec package.
#
# Icon: `safari` -- a real, existing icon in the MacTahoe icon theme
# already ported to this profile (confirmed via `find` on real hardware,
# not created for this package), so no new icon asset was needed.
#
# Real, existing binary/desktop-file paths (confirmed via
# `dnf repoquery -l chromium` and the real installed
# chromium-browser.desktop on real hardware, not guessed):
# /usr/bin/chromium-browser, StartupWMClass=Chromium-browser (the
# Chromium binary itself sets this WM class regardless of which .desktop
# file launched it, so ours must match for window/taskbar grouping to
# work). Ships a NEW desktop file (es.parchaos.Browser.desktop) rather
# than overwriting chromium's own chromium-browser.desktop, so both can
# coexist without an RPM file conflict -- chromium's own generic entry
# stays available too, this is just ParchaOS's own branded launcher
# pointing at the same real binary.
#
# Naming: picked "Parcha Browser" (matching this project's established
# Parcha-prefixed branding, e.g. Parcha Dock) rather than echoing
# Pulsar OS's own "SeaFari" name -- SeaFari is a real Inled project
# (github.com/InledGroup/seafari) but it's a Firefox/Gecko rebrand, not
# Chromium, so reusing that name here for a different underlying engine
# would be actively misleading, not just a trademark-caution renaming
# (the same class of reasoning already applied to the dock's rebrand).
# ==============================================================================

Name:           parchaos-browser
Version:        1.0.0
Release:        5%{?dist}
Summary:        ParchaOS's rebranded Chromium browser (Blink engine, for full Google-service compatibility)

License:        GPL-3.0-or-later AND CC-BY-SA-4.0
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
BuildArch:      noarch

Source0:        es.parchaos.Browser.desktop
Source1:        parchaos-browser-mimeapps.list
# Original ParchaOS artwork (CC BY-SA 4.0), same file as in
# parchaos-icon-theme; shipped in hicolor so the icon works in any theme.
Source2:        parcha-browser.svg

# Parcha Browser replaces Pafari (pearOS's WebKitGTK/Epiphany fork, whose
# name is itself a Safari pun): obsoleting it removes it on dnf upgrade.
Obsoletes:      pafari < 1:26.8-7

Requires:       chromium
Requires:       desktop-file-utils

%description
A thin ParchaOS-branded launcher for Fedora's own real `chromium` package
-- gives ParchaOS a genuine Chromium/Blink-engine browser option
for real-world Google services like Gmail that are tuned for
Chrome/Blink. It is ParchaOS's default web browser (replacing Pafari). Not a
from-scratch Chromium rebuild; just a rebranded desktop entry pointing
at the real chromium-browser binary. See this spec's own banner comment
for the full reasoning.

%prep

%build

%install
mkdir -p %{buildroot}%{_datadir}/applications
install -m 0644 %{SOURCE0} %{buildroot}%{_datadir}/applications/es.parchaos.Browser.desktop
# Default browser: GNOME reads gnome-mimeapps.list, then mimeapps.list,
# from /etc/xdg before the /usr/share copies that name uninstalled apps.
install -Dm 0644 %{SOURCE1} %{buildroot}%{_sysconfdir}/xdg/gnome-mimeapps.list
install -Dm 0644 %{SOURCE1} %{buildroot}%{_sysconfdir}/xdg/mimeapps.list
install -Dm 0644 %{SOURCE2} %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/es.parchaos.Browser.svg

# Parcha Browser *is* Chromium, so Chromium's own launcher entry is a
# duplicate in the app grid and launcher. Hide it (NoDisplay=true in its
# main section only) at install and again whenever chromium is updated,
# since an update replaces its .desktop file. Links and "Open With" keep
# going to es.parchaos.Browser.desktop through the mimeapps defaults.
%post
f=%{_datadir}/applications/chromium-browser.desktop
if [ -f "$f" ] && ! sed -n '0,/^\[Desktop Action/p' "$f" | grep -q '^NoDisplay=true'; then
    sed -i '0,/^\[Desktop Entry\]/s//[Desktop Entry]\nNoDisplay=true/' "$f"
fi
update-desktop-database %{_datadir}/applications &>/dev/null || :

%triggerin -- chromium
f=%{_datadir}/applications/chromium-browser.desktop
if [ -f "$f" ] && ! sed -n '0,/^\[Desktop Action/p' "$f" | grep -q '^NoDisplay=true'; then
    sed -i '0,/^\[Desktop Entry\]/s//[Desktop Entry]\nNoDisplay=true/' "$f"
fi
update-desktop-database %{_datadir}/applications &>/dev/null || :

%postun
# Removing Parcha Browser: show Chromium's own entry again.
if [ $1 -eq 0 ]; then
    f=%{_datadir}/applications/chromium-browser.desktop
    [ -f "$f" ] && sed -i '0,/^\[Desktop Action/{/^NoDisplay=true$/d}' "$f"
    update-desktop-database %{_datadir}/applications &>/dev/null || :
fi

%files
%{_datadir}/applications/es.parchaos.Browser.desktop
%config(noreplace) %{_sysconfdir}/xdg/gnome-mimeapps.list
%config(noreplace) %{_sysconfdir}/xdg/mimeapps.list
%{_datadir}/icons/hicolor/scalable/apps/es.parchaos.Browser.svg

%changelog
* Fri Sep 25 2026 ParchaOS packaging - 1.0.0-5
- Hide Chromium's own launcher entry (NoDisplay=true, re-applied on
  chromium updates, undone on removal): it duplicated Parcha Browser in
  the launcher and app grid.
* Fri Sep 25 2026 ParchaOS packaging - 1.0.0-4
- Launch with CHROME_DESKTOP=es.parchaos.Browser.desktop so Chromium
  uses es.parchaos.Browser as its Wayland app ID; the dock and app
  switcher now show its windows as Parcha Browser instead of matching
  them to Chromium's own launcher entry.
* Fri Sep 25 2026 ParchaOS packaging - 1.0.0-3
- Icon v2: fruit-globe on a white tile with a soft violet rind, matching
  the MacTahoe palette (same artwork as parchaos-icon-theme).
* Fri Sep 25 2026 ParchaOS packaging - 1.0.0-2
- Replace Pafari: Obsoletes pafari so dnf upgrade removes it.
- Make Parcha Browser the default for web links via /etc/xdg defaults;
  the /usr/share defaults named Epiphany and Firefox, neither installed.
- Own icon name (es.parchaos.Browser, original artwork in hicolor)
  instead of the theme's "safari" icon.
- License set: GPL-3.0-or-later (packaging) AND CC-BY-SA-4.0 (icon).
* Thu Sep 24 2026 ParchaOS packaging - 1.0.0-1
- Initial package. Real user request: a Chromium-based browser for full
  Gmail/Google-service compatibility, distinct from pafari's WebKitGTK
  engine. Confirmed `chromium-freeworld` doesn't exist on this Fedora
  release before basing this on plain `chromium` instead -- see the
  banner comment above.
