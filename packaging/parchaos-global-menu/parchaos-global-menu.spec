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
Release:        4%{?dist}
Summary:        ParchaOS's global application menu bar for GNOME Shell

License:        MIT
URL:            https://github.com/alexgalicea/parchaos-gnome
Source0:        extension.js
Source1:        metadata.json
Source2:        stylesheet.css
Source3:        parchaos-menu-icon-symbolic.svg

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
cp %{SOURCE0} %{SOURCE1} %{SOURCE2} %{SOURCE3} .

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

%files
%{_datadir}/gnome-shell/extensions/parchaos-global-menu@parchaos.org/

%changelog
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
