# ==============================================================================
# Liquid glass for the shell (ticket #135): Liquid Glass by ryohsuke1231, a
# GNOME Shell extension that draws panel menus, Quick Settings, notifications,
# the OSD and the dock as refractive glass with shaders. MIT licensed;
# independent of Inled's stack. The upstream repository ships the compiled
# JavaScript (dist/) next to its TypeScript source (src/); this package
# installs the compiled files, as upstream's own zip does.
#
# It is not turned on by any ParchaOS default yet. Upstream declares GNOME
# Shell 50 only; ParchaOS disables extension version validation.
# ==============================================================================

Name:           parchaos-liquid-glass
Version:        0
Release:        1%{?dist}
Summary:        Refractive glass effect for the shell

License:        MIT
URL:            https://github.com/ryohsuke1231/liquid-glass
%global commit  cc91e4784ba95639ddc735911daa9731571f5628
%global shortcommit %(c=%{commit}; echo ${c:0:7})
Source0:        %{url}/archive/%{commit}/liquid-glass-%{shortcommit}.tar.gz

BuildArch:      noarch
BuildRequires:  glib2

Requires:       gnome-shell >= 50
Requires:       dconf

%description
Draws the top-bar menus, Quick Settings, notifications, on-screen displays and
the dock as glass that blurs, tints and bends what is behind it, using shaders.
Wraps Liquid Glass, a GNOME Shell extension (MIT).

%prep
%autosetup -n liquid-glass-%{commit}

%build
glib-compile-schemas liquid-glass@thinkingcoding1231.gmail.com/schemas

%install
UUID=liquid-glass@thinkingcoding1231.gmail.com
DEST=%{buildroot}%{_datadir}/gnome-shell/extensions/$UUID
mkdir -p "$DEST"
cd "$UUID"
cp -r dist shaders icons preferences schemas "$DEST/"
install -m 0644 extension.js prefs.js metadata.json stylesheet.css resources.gresource "$DEST/"
rm -f "$DEST/schemas/"*.xml.orig

%files
%license LICENSE
%{_datadir}/gnome-shell/extensions/liquid-glass@thinkingcoding1231.gmail.com/

%changelog
* Wed Sep 30 2026 ParchaOS packaging - 0-1
- Initial package (ticket #135): Liquid Glass at commit cc91e47, MIT. Not
  enabled by default. Checked in an isolated headless GNOME Shell 50: it loads
  next to the ParchaOS extensions and draws the Parcha Controls panel as
  refractive glass.
