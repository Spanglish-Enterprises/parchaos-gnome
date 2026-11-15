# ==============================================================================
# Clipboard history for the top bar (ticket #124).
#
# Packages Clipboard Indicator (clipboard-indicator@tudmotu.com), a real,
# independent, actively maintained GNOME Shell extension by Yotam Bar-On and
# contributors (MIT, confirmed from its LICENSE.rst). It lists what you copied
# (text and images) in a searchable menu from a top-bar icon, with pin and
# favourite, edit, a private mode and per-app exclusion. Picked over the other
# GNOME 50 candidate (Clipboard History by SUPERCILEX) because that project is
# in maintenance mode and being replaced.
#
# Unmodified upstream at a pinned commit. Default shortcuts are Ctrl+F8..F12,
# which do not clash with the Super-key remap. The extension keeps its own
# UUID, as the other third-party extensions here do.
# ==============================================================================

Name:           parchaos-clipboard
Version:        1
Release:        3%{?dist}
Summary:        Clipboard history in the top bar

License:        MIT
URL:            https://github.com/Tudmotu/gnome-shell-extension-clipboard-indicator
%global commit  c880c7fb88dc7232a61a5864d125989a4f375daa
%global shortcommit %(c=%{commit}; echo ${c:0:7})
Source0:        %{url}/archive/%{commit}/clipboard-indicator-%{shortcommit}.tar.gz

BuildArch:      noarch
BuildRequires:  glib2
BuildRequires:  gettext

Requires:       gnome-shell >= 46
Requires:       dconf

%description
Keeps a searchable history of what you copy, text and images, in a menu
from an icon in the top bar. Pin or favourite entries, edit them, turn on
private mode while you handle something sensitive, and choose apps whose
copies are never recorded. Wraps Clipboard Indicator, a GNOME Shell
extension (MIT).

%prep
%autosetup -n gnome-shell-extension-clipboard-indicator-%{commit}

# GNOME Shell 51 removed Clutter.get_default_backend().
grep -rl 'Clutter.get_default_backend()' *.js | xargs -r sed -i 's/Clutter\.get_default_backend()/(global.stage.context?.get_backend?.() ?? Clutter.get_default_backend())/'
# GNOME Shell 51 also removed St.BoxLayout's "vertical" property (GNOME 50
# already has "orientation"). With it, building the menu threw inside a
# promise nobody caught: on Fedora 45 the clipboard menu never appeared and
# the top bar showed the placeholder "Text will be here" (found on a real
# 44 -> 45 upgrade in a VM).
sed -i -E 's/\bvertical: true\b/orientation: Clutter.Orientation.VERTICAL/; s/\bvertical: false\b/orientation: Clutter.Orientation.HORIZONTAL/' extension.js confirmDialog.js
! grep -nE '\bvertical:' extension.js confirmDialog.js

%build
# Upstream ships compiled catalogs; rebuild them from the .po files so the
# package does not depend on prebuilt binaries.
for po in locale/*/LC_MESSAGES/*.po; do
    [ -e "$po" ] && msgfmt "$po" -o "${po%.po}.mo"
done
glib-compile-schemas schemas

%install
UUID=clipboard-indicator@tudmotu.com
DEST=%{buildroot}%{_datadir}/gnome-shell/extensions/$UUID
mkdir -p "$DEST/schemas"
install -m 0644 extension.js prefs.js constants.js confirmDialog.js keyboard.js registry.js metadata.json stylesheet.css "$DEST/"
install -m 0644 schemas/*.gschema.xml schemas/gschemas.compiled "$DEST/schemas/"
for mo in locale/*/LC_MESSAGES/*.mo; do
    lang=$(basename "$(dirname "$(dirname "$mo")")")
    install -Dm 0644 "$mo" "$DEST/locale/$lang/LC_MESSAGES/$(basename "$mo")"
done

%files
%license LICENSE.rst
%doc README.md
%{_datadir}/gnome-shell/extensions/clipboard-indicator@tudmotu.com/

%changelog
* Sun Nov 15 2026 ParchaOS packaging - 1-3
- GNOME 51: use "orientation" instead of the removed "vertical" property;
  the clipboard menu failed to build on Fedora 45 (ticket #37).

* Wed Sep 30 2026 ParchaOS packaging - 1-2
- Fedora 45 prep (ticket #37): loads on GNOME Shell 51.

* Tue Sep 29 2026 ParchaOS packaging - 1-1
- Initial package (ticket #124): Clipboard Indicator at commit c880c7f,
  enabled by default through parchaos-desktop. Checked in a headless GNOME
  Shell 50: the menu lists copied entries with search, edit, pin, favourite,
  delete, private mode, settings and clear history.
