# ==============================================================================
# ParchaOS's global menu -- a global application menu in the
# GNOME top bar (an app-name menu with About/Hide/Quit, standard
# File/Edit/View/Go/Window/Help menus, a system logo menu with real power
# actions, and a weather indicator).
#
# REWRITTEN FROM SCRATCH, 2026-09-25. The previous version of this package
# was a direct fork of Inled's own `pulsaros-global-menu` (fetched from
# Inled-Pulsar-OS/PKG and rebranded at build time). Reading Inled's actual
# license text at license.inled.es (not just the "MIT-INLED" name) turned
# up real restrictions beyond standard MIT that a fork of their in-house
# work would carry: a non-compete clause covering "direct and unfair
# competition," a clause requiring any derivative work to stay licensed
# exclusively under MIT-INLED, and a clause requiring derivative works to
# grant "all rights and benefits exclusively to the original authors."
# ParchaOS is a directly competing Linux desktop product, so
# continuing to ship a fork of their code was real, live exposure, not a
# theoretical one.
#
# This version is an original implementation written against
# docs/global-menu-rewrite-spec.md (a plain-English feature description)
# and GNOME Shell's own public, documented extension APIs -- it does not
# read, reference, or adapt Inled's source in any way. It intentionally
# does not replicate every feature of the old version (most notably, no
# custom full-screen lock screen with video-wallpaper playback -- this
# profile uses GNOME's own stock lock screen instead); see the spec doc
# for exactly what's in scope and what's deliberately deferred.
#
# Versioning reset to 2.0.0 to reflect that this is a new, independent
# codebase, not a continuation of the old fork's own version numbering
# (which had been inherited from Inled's upstream releases).
# ==============================================================================

Name:           parchaos-global-menu
Version:        2.1.0
Release:        33%{?dist}
Summary:        ParchaOS's global application menu bar for GNOME Shell

License:        GPL-3.0-or-later AND CC-BY-SA-4.0
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        extension.js
Source1:        metadata.json
Source2:        stylesheet.css
Source3:        parchaos-menu-icon-symbolic.svg
Source4:        org.parchaos.globalmenu.gschema.xml
Source90:       LICENSE
Source91:       LICENSE-ARTWORK

BuildRequires:  glib2
BuildArch:      noarch

Requires:       gnome-shell >= 45
# Reference comparison, 2026-09-25: a permanent weather indicator in
# the top bar, like the reference desktop's (GNOME has no
# built-in panel weather integration at all -- Weather is only ever a
# standalone app upstream). Verified end-to-end live on real hardware
# with a standalone gjs script before writing any extension code: real
# IP-based location via Geoclue.Simple (the same public API
# gnome-weather's own real currentLocationController.ts uses, read
# directly for reference -- a different, independent GNOME project, not
# Inled's) resolved a real city, and GWeather.Info fetched real live
# conditions using the free MET_NO/METAR providers -- no API key
# needed.
Requires:       libgweather
Requires:       geoclue2
# About card: graphics adapter name.
Requires:       pciutils

%description
ParchaOS's global application menu bar for GNOME Shell: an
app-name menu with About/Hide/Quit, standard File/Edit/View/Go/Window/
Help menus, a system logo menu with real power actions, and a weather
indicator. An original implementation -- see this spec's own banner
comment and docs/global-menu-rewrite-spec.md in the main repo for why
and how.

%prep
mkdir -p src
cd src
cp %{SOURCE0} %{SOURCE1} %{SOURCE2} %{SOURCE3} %{SOURCE4} .
# %%prep works in src/; %%license reads from the build directory.
cp -p %{SOURCE90} ..
cp -p %{SOURCE91} ..

%build
# Nothing to compile: plain JS/JSON/CSS, no gschema in this version (the
# old fork's one settings key, fullscreen-spaces auto-hide,
# isn't implemented by this rewrite -- see the spec doc's "explicitly
# not in scope" section. A future genuinely-original implementation of
# that feature would add its own schema back.)

%install
UUID=parchaos-global-menu@parchaos.org
DEST=%{buildroot}%{_datadir}/gnome-shell/extensions/$UUID
mkdir -p "$DEST"
install -m 0644 src/extension.js "$DEST/"
install -m 0644 src/metadata.json "$DEST/"
install -m 0644 src/stylesheet.css "$DEST/"
install -m 0644 src/parchaos-menu-icon-symbolic.svg "$DEST/"
mkdir -p "$DEST/schemas"
install -m 0644 src/org.parchaos.globalmenu.gschema.xml "$DEST/schemas/"
glib-compile-schemas "$DEST/schemas"

%files
%license LICENSE-ARTWORK
%license LICENSE
%{_datadir}/gnome-shell/extensions/parchaos-global-menu@parchaos.org/

%changelog
* Fri Oct 02 2026 ParchaOS packaging - 2.1.0-33
- Look-alike audit: the File menu item is Quick Preview (was named after another company's feature); internal shortcut id renamed to match.

* Fri Oct 02 2026 ParchaOS packaging - 2.1.0-32
- Ticket #173: the menu-bar weather opens a popover: place and temperature, condition and the day's range, a warning row, the next five hours (the chance of rain where the forecast gives one, else the rainfall), up to two other places, then Open Weather and the data credit. Parcha Sky supplies the data (`parchaos-sky --snapshot`, refreshed every 15 minutes and when opened); without it GWeather fills the top. The panel icon turns into a warning triangle while an alert is active.

* Fri Oct 02 2026 ParchaOS packaging - 2.1.0-31
- Ticket #192: the menu-bar weather opens Parcha Sky (GNOME Weather where Parcha Sky is not installed).

* Thu Oct 01 2026 ParchaOS packaging - 2.1.0-30
- Window > Zoom and the Move Window to Left/Right Half items work again on GNOME 50: Mutter 18 removed get_maximized() and the MaximizeFlags argument, so every click threw. The smoke test now drives these items on a real window.

* Wed Sep 30 2026 ParchaOS packaging - 2.1.0-29
- Ticket #135, checked against the reference menus: icons on About, System Settings and Parcha Store; Force Quit, Lock Screen and Log Out show their shortcuts and now answer to them (Ctrl+Alt+Esc, Ctrl+Super+Q, Ctrl+Shift+Q as the compositor sees them; a keyboard shortcut schema org.parchaos.globalmenu ships with the extension); the Force Quit dialog lists all running apps and wraps its text.

* Wed Sep 30 2026 ParchaOS packaging - 2.1.0-28
- Ticket #135: Shortcut hints dimmed and the update badge drawn as a pill; glyphs spaced like the kit.

* Wed Sep 30 2026 ParchaOS packaging - 2.1.0-27
- Ticket #135: Menu shortcut and badge text use the kit's 13 px medium weight and the row's own dimmed colour.

* Wed Sep 30 2026 ParchaOS packaging - 2.1.0-26
- Finished the menu bar menus (ticket #135 reference). Logo menu: About, System Settings with an update count, Parcha Store, Recent Items, Force Quit, Sleep, Restart, Shut Down, Lock Screen, Log Out <name>. App menu: About, Settings, Hide, Hide Others, Show All, Quit, with shortcuts shown right-aligned (symbols with the Super-as-Ctrl keyboard style, key names otherwise). File, Edit, View, Go and Window menus are filled in for the file manager (New Folder, Get Info, Quick Look, Move to Trash, Go to Folder, tiling, open windows list ...). Items the focused app cannot do stay greyed.

* Wed Sep 30 2026 ParchaOS packaging - 2.1.0-25
- Declares GNOME Shell 51 support (Fedora 45 prep, ticket #37).

* Wed Sep 30 2026 ParchaOS packaging - 2.1.0-24
- Fedora 45 prep (ticket #37): synthetic keyboard input finds its backend the
  way GNOME Shell 51 expects (Clutter.get_default_backend() is gone), still
  working on 50.

* Tue Sep 29 2026 ParchaOS packaging - 2.1.0-23
- Adaptive bar tint: promisify Gio.File read_async/load_contents_async
  explicitly. The tint awaited them, but GJS only allows that after the
  method has been promisified, and nothing here did it -- it worked in a
  full session only because some other code had. In a shell with just the
  ParchaOS extensions it logged "At least 3 arguments required" and the bar
  never tinted. The new smoke check ("menu bar tint follows the wallpaper")
  fails without this change and passes with it.
* Mon Sep 28 2026 ParchaOS packaging - 2.1.0-22
- Help menu: "ParchaOS Help" opens the support page (ticket #136), which
  is the channel the README, LEGAL and SOURCES docs already point at.
  It previously opened the site's front page and stopped there. The FAQ
  stays reachable as its own item instead of being lost behind the change.
* Sat Sep 26 2026 ParchaOS packaging - 2.1.0-21
- Adaptive menu bar: samples the wallpaper under the bar and switches
  between light and dark text for contrast; light text
  again in the overview and lock screen.
- No per-item fills: the shell theme's solid box behind every panel
  button and the clock is removed while the menu bar runs; items only
  get a highlight on hover or while their menu is open.
* Sat Sep 26 2026 ParchaOS packaging - 2.1.0-20
- Revised ParchaOS logo: the rind has an open gap and the seeds are
  irregular (no radial symmetry), after a WIPO image search.
* Sat Sep 26 2026 ParchaOS packaging - 2.1.0-19
- New original ParchaOS logo (halved passion fruit), generated by
  branding/logo/make-brand.py; artwork CC BY-SA 4.0. Replaces the
  adapted third-party icon.
* Sat Sep 26 2026 ParchaOS packaging - 2.1.0-18
- About card: Legal and Privacy button. Weather: clicking shows Open
  Weather and the MET Norway data credit.
* Sat Sep 26 2026 ParchaOS packaging - 2.1.0-17
- Rebuild: install the license file from the build directory (the
  previous build failed to find it).
* Sat Sep 26 2026 ParchaOS packaging - 2.1.0-16
- Ship the license text (%license) with an accurate SPDX License tag.
  Relicensed GPL-3.0-or-later like the rest of ParchaOS's code.
* Sat Sep 26 2026 ParchaOS packaging - 2.1.0-15
- Menus built from one data table (MENU_TABLE) by a generic loop; the
  logo menu too. Focus tracking, the app-name lookup (now via .desktop
  info) and the os-release reader rewritten; no code lines in common
  with the extension it replaced (scripts/similarity-check.py). Help
  links go to parchaos.org.
* Sat Sep 26 2026 ParchaOS packaging - 2.1.0-14
- Weather: location being turned off is logged as debug output, not an
  error.
* Sat Sep 26 2026 ParchaOS packaging - 2.1.0-13
- About card no longer blocks the desktop (GNOME version from the shell itself, graphics looked up in the background); shows the full-color ParchaOS mark. Weather cancels its location lookup and disconnects on disable. Replace deprecated vertical: true.
* Sat Sep 26 2026 ParchaOS packaging - 2.1.0-12
- Help opens the ParchaOS website FAQ, and the weather service contact and extension link point at the website instead of the private source repository.
* Sat Sep 26 2026 ParchaOS packaging - 2.1.0-11
- Edit, View, File and Go items send each kind of app the right keys:
  Ctrl+Shift+C/V in terminals, file-view items only in the file
  manager, Redo as Ctrl+Shift+Z; items an app lacks are greyed out.
- Quit asks the whole app to quit; Hide minimizes all its windows.
- Close Window closes the window directly.
- One virtual keyboard, released on disable.
* Sat Sep 26 2026 ParchaOS packaging - 2.1.0-10
- Follow the ParchaOS style setting live; classic: an even frosted bar,
  no text glow, rounded-rectangle highlights.
* Sat Sep 26 2026 ParchaOS packaging - 2.1.0-9
- New About ParchaOS card: large logo, name, version with the GNOME
  release, a spec sheet (computer, processor, graphics, memory rounded to
  the installed size, storage, kernel), and More Info… (Settings → About).
* Fri Sep 25 2026 ParchaOS packaging - 2.1.0-8
- Menu bar styling tuned to classic reference spacing: 11 px item padding
  (22 px gaps), bold app name, a soft text glow and a light darkening that
  fades down from the top edge, for legibility over bright wallpapers.
* Fri Sep 25 2026 ParchaOS packaging - 2.1.0-7
- Menu bar measured against a reference UI kit: 9 px padding per item
  with no extra gap, 10 px for the app name, 33 px logo item; menu items
  semibold (600) and the app name extra-bold (800).
- Hover/open highlight is a ~24 px tall pill (was the theme's full-height
  inset shadow), and plain keyboard focus no longer highlights the logo.
* Fri Sep 25 2026 ParchaOS packaging - 2.1.0-6
- Menu bar spacing matches the reference bar: buttons set their own
  horizontal padding (6 px, 8 px for the logo) instead of inheriting a
  panel-wide 10 px, so gaps are ~22 px instead of ~29 px.
- Menu labels are white like the app name, not dimmed.
- Logo redrawn on whole pixels: a solid 2 px stem and a fuller leaf, so
  neither renders as a faint half-pixel line.
* Fri Sep 25 2026 ParchaOS packaging - 2.1.0-5
- Fix the new menu bar logo rendering at ~28 px on the real desktop: set
  its size in code (icon_size) and pin width/height, since the shell
  theme's panel icon rules overrode the CSS icon-size.
* Fri Sep 25 2026 ParchaOS packaging - 2.1.0-4
- Menu bar logo is now a symbolic SVG drawn for 16 px (was a 570 px PNG
  scaled down): crisp edges, follows the panel text color, and vertically
  centered with the menu labels.
* Fri Sep 25 2026 ParchaOS packaging - 2.1.0-3
- Fix Log Out/Restart/Shut Down doing nothing: ConfirmDialog subclassed
  ModalDialog without GObject.registerClass, so constructing it threw
  "Tried to construct an object without a GType" (found in the journal
  after a real failed log-out).
- Wire up "About <App>", which had no handler at all: activates the app's
  own "about" action over org.gtk.Actions, falling back to a simple
  dialog from the app's .desktop info. Both verified in an isolated
  headless gnome-shell (confirm dialog renders; Calculator's own About
  window opens from the menu).
* Fri Sep 25 2026 ParchaOS packaging - 2.1.0-2
- Reworded summary/description/comments to describe features instead of
  naming macOS, per the project's trademark-caution naming policy.
* Fri Sep 25 2026 ParchaOS packaging - 2.1.0-1
- Added "Report a Bug or Feature Request..." to the Help menu, linking
  to the website's new /support page (backed by the Spanglish Tickets
  system). No secret token is embedded here -- the OS only opens a
  browser link; the website's server-side route holds the token.

* Fri Sep 25 2026 ParchaOS packaging - 2.0.0-1
- Rewritten from scratch as an original implementation, replacing the
  previous fork of Inled's pulsaros-global-menu. See this spec's own
  banner comment and docs/global-menu-rewrite-spec.md for the full
  reasoning (a real licensing exposure found by reading Inled's actual
  MIT-INLED license text) and exactly what's covered vs. deliberately
  deferred (no custom lock screen in this pass). Carries over the
  weather indicator, which was already original code before this
  rewrite. Version reset to 2.0.0 since this is a new, independent
  codebase.
