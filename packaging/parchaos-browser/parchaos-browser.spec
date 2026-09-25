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
Release:        1%{?dist}
Summary:        ParchaOS's rebranded Chromium browser (Blink engine, for full Google-service compatibility)

License:        NOASSERTION
URL:            https://github.com/alexgalicea/parchaos-gnome
BuildArch:      noarch

Source0:        es.parchaos.Browser.desktop

Requires:       chromium
Requires:       desktop-file-utils

%description
A thin ParchaOS-branded launcher for Fedora's own real `chromium` package
-- gives ParchaOS a genuine Chromium/Blink-engine browser option
alongside pafari (this profile's WebKitGTK-based one), for real-world
Google services like Gmail that are tuned for Chrome/Blink. Not a
from-scratch Chromium rebuild; just a rebranded desktop entry pointing
at the real chromium-browser binary. See this spec's own banner comment
for the full reasoning.

%prep

%build

%install
mkdir -p %{buildroot}%{_datadir}/applications
install -m 0644 %{SOURCE0} %{buildroot}%{_datadir}/applications/es.parchaos.Browser.desktop

%files
%{_datadir}/applications/es.parchaos.Browser.desktop

%changelog
* Thu Sep 24 2026 ParchaOS packaging - 1.0.0-1
- Initial package. Real user request: a Chromium-based browser for full
  Gmail/Google-service compatibility, distinct from pafari's WebKitGTK
  engine. Confirmed `chromium-freeworld` doesn't exist on this Fedora
  release before basing this on plain `chromium` instead -- see the
  banner comment above.
