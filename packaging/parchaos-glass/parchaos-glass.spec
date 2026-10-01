# ==============================================================================
# ParchaOS glass (ticket #135): our own refractive "liquid glass" for GNOME Shell
# extensions: a GlassPane actor that shows a refracted, blurred, tinted copy of the
# desktop behind it, with a curved-bezel lens, rim light and a soft shadow. Shared by
# Parcha Controls (tile glass) and, next, the menus and the dock.
# ==============================================================================

Name:           parchaos-glass
Version:        1.0.0
Release:        6%{?dist}
Summary:        ParchaOS's own liquid glass for the desktop

License:        GPL-3.0-or-later AND MIT
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        glass.js
Source1:        NOTICE
Source90:       LICENSE

BuildArch:      noarch

Requires:       gnome-shell >= 48
# The third-party glass extension this replaces.
Obsoletes:      parchaos-glass-effects < 1
Provides:       parchaos-glass-effects = 1

%description
A shared library for ParchaOS shell extensions: panes of glass that bend, blur and
tint what is behind them. The optical model follows the MIT-licensed liquid-glass
GNOME extension (see NOTICE).

%prep
cp -p %{SOURCE90} .
cp -p %{SOURCE1} NOTICE

%build

%install
install -Dm0644 %{SOURCE0} %{buildroot}%{_datadir}/parchaos-glass/glass.js
install -Dm0644 %{SOURCE1} %{buildroot}%{_datadir}/parchaos-glass/NOTICE

%files
%license LICENSE
%license NOTICE
%{_datadir}/parchaos-glass/

%changelog
* Thu Oct 01 2026 ParchaOS packaging - 1.0.0-6
- Replaces the third-party glass extension package (parchaos-glass-effects): obsoletes it so an upgrade removes it.

* Thu Oct 01 2026 ParchaOS packaging - 1.0.0-5
- Brighter backdrops get a warm grey veil dark enough for white text (menus on light wallpapers).

* Thu Oct 01 2026 ParchaOS packaging - 1.0.0-4
- Ticket #135: much softer drop shadow and inner edge shadow (they were far stronger than the reference).

* Thu Oct 01 2026 ParchaOS packaging - 1.0.0-3
- Ticket #135: The tint follows the backdrop: smoky on a dark wallpaper, a light milky veil on a bright one (the reference's light and dark looks).

* Thu Oct 01 2026 ParchaOS packaging - 1.0.0-2
- Stronger edge lens and rim, smokier body (tuned against the reference).

* Thu Oct 01 2026 ParchaOS packaging - 1.0.0-1
- Initial package (ticket #135): the GlassPane library, used by Parcha Controls for tile glass.
