# ==============================================================================
# Glass effects for the shell (ticket #135): the "liquid-glass" GNOME Shell
# extension by ryohsuke1231, which draws panel menus, Quick Settings,
# notifications, the OSD and the dock as refractive glass with shaders. It is
# offered as an opt-in setting, never on by default. MIT licensed;
# independent of Inled's stack. The upstream repository ships the compiled
# JavaScript (dist/) next to its TypeScript source (src/); this package
# installs the compiled files, as upstream's own zip does.
#
# Upstream declares GNOME Shell 50 only; ParchaOS disables extension version
# validation. The extension's internal identifiers keep upstream's names (its
# id and settings schema); the names people see are reworded below.
# ==============================================================================

Name:           parchaos-glass-effects
Version:        0
Release:        3%{?dist}
Summary:        Optional refractive glass effects for the shell

License:        MIT
URL:            https://github.com/ryohsuke1231/liquid-glass
%global commit  cc91e4784ba95639ddc735911daa9731571f5628
%global shortcommit %(c=%{commit}; echo ${c:0:7})
Source0:        %{url}/archive/%{commit}/liquid-glass-%{shortcommit}.tar.gz
Source1:        parchaos-glass-effects.css

BuildArch:      noarch
BuildRequires:  glib2
BuildRequires:  python3

Requires:       gnome-shell >= 50
Requires:       dconf

%description
Draws the top-bar menus, Quick Settings, notifications, on-screen displays and
the dock as glass that blurs, tints and bends what is behind it, using shaders.
Off until you turn it on in ParchaOS Settings. Wraps an independent GNOME
Shell extension (MIT).

%prep
%autosetup -n liquid-glass-%{commit}
# Names people see: the extension list and its settings window.
UUID=liquid-glass@thinkingcoding1231.gmail.com
sed -i 's/"name": "Liquid Glass"/"name": "Glass Effects"/; s/liquid glass/glass/Ig' $UUID/metadata.json
sed -i "s/Liquid Glass/Glass Effects/g; s/liquid glass/glass/g" $UUID/prefs.js $UUID/preferences/*.js
sed -i 's/Liquid Glass/Glass Effects/g; s/liquid glass/glass/g' $UUID/extension.js

# Keep the round icon badges of the toggles (upstream clears the background of
# everything inside a toggle, badges included) and add ParchaOS's own rules.
python3 - <<'PY'
p = 'liquid-glass@thinkingcoding1231.gmail.com/dist/quickSettings/toggleStyles.js'
s = open(p).read()
old = "            if (actor instanceof St.Widget)\n                found.push(actor);"
new = "            if (actor instanceof St.Widget && !actor.has_style_class_name('quick-toggle-icon'))\n                found.push(actor);"
assert old in s
open(p, 'w').write(s.replace(old, new, 1))
PY
# GNOME Shell 51 removed Clutter.get_default_backend().
sed -i 's/Clutter\.get_default_backend()/(global.stage.context?.get_backend?.() ?? Clutter.get_default_backend())/' \
    liquid-glass@thinkingcoding1231.gmail.com/dist/actors/textureBlit.js \
    liquid-glass@thinkingcoding1231.gmail.com/dist/liquidEffect.js
cat %{SOURCE1} >> liquid-glass@thinkingcoding1231.gmail.com/stylesheet.css

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
* Wed Sep 30 2026 ParchaOS packaging - 0-3
- Fedora 45 prep (ticket #37): works on GNOME Shell 51 (backend lookup).

* Wed Sep 30 2026 ParchaOS packaging - 0-2
- Toggle badges keep their round white background; text on a switched-on
  toggle is dark; the top buttons are true circles; the dock's own
  background steps aside for the glass.
* Wed Sep 30 2026 ParchaOS packaging - 0-1
- Initial package (ticket #135): the glass-effects extension at commit
  cc91e47, MIT, off by default. Checked in an isolated headless GNOME Shell
  50: it loads next to the ParchaOS extensions and draws the Parcha Controls
  panel as refractive glass.
