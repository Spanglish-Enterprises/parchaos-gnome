# ==============================================================================
# ParchaOS's dock — a real fork of the well-known GNOME Shell extension
# Dash-to-Dock (micheleg/dash-to-dock, GPL-2.0), further forked by Pulsar
# OS as "Pulsar Dock" (Inled-Pulsar-OS/dash-to-dock) with macOS-style
# hover magnification, launch bounce animations, a downloads-folder
# stack, and live minimized-window previews — real, substantial
# functional additions on top of stock Dash-to-Dock, not just a
# reskin. Confirmed via the real repo's own metadata.json (fetched
# directly, not guessed).
#
# License: GPL-2.0 (inherited from upstream Dash-to-Dock; a real
# derivative work, distinct from Pulsar OS's own MIT-INLED original
# code — tracked carefully here since this project plans a public
# release, same rigor as parchaos-finder).
#
# Rebranded "Parcha Dock" / uuid parcha-dock@parchaos.org (was "Pulsar
# Dock" / pulsar-dock@inled.es) for ParchaOS's own product identity —
# not an Apple-trademark concern (Dash-to-Dock/"Pulsar Dock" aren't
# Apple names), just the same "ship our own branding, not verbatim
# upstream branding" reasoning already applied to the logo and Parcher.
# Different UUID also avoids ever colliding with a real, separately
# installed "pulsar-dock@inled.es" on the same system.
#
# Packaged as an architecture-independent GNOME Shell extension (JS +
# CSS + gschema, no compiled binaries) built via the real upstream
# Makefile's own `make _build` target — verified directly against that
# Makefile before writing this (sassc for the SCSS->CSS stylesheet
# compile, msgfmt for .po->.mo translations, glib-compile-schemas for
# the gschema), not guessed.
# Patch0: real, reproducible crash found via log-based live testing
# 2026-09-25 (first misattributed to parchaos-desktop-icons/DING, whose
# activity just happened to coincide with it -- see
# docs/gnome-phase1-findings.md). dash.js's getAppIcons() includes the
# "Show Applications" grid button alongside real app icons (needed so
# hover-magnification/drag reordering treat it consistently), but
# _updateNumberOverlay()/toggleNumberOverlay() call
# icon.setNumberOverlay()/icon.toggleNumberOverlay() on every icon
# unconditionally -- methods that only exist on DockAbstractAppIcon,
# not on the Show Apps button's own class (DockShowAppsIcon extends
# Dash.ShowAppsIcon). Confirmed this is a real upstream bug, not
# something this fork introduced: the exact same shape exists in
# micheleg/dash-to-dock's own current master (dash.js's getAppIcons/
# _updateNumberOverlay, appIcons.js's DockShowAppsIcon), fetched
# directly and compared line-for-line, not assumed. It fires on nearly
# every dash redisplay (any app opened/closed) whenever the Show Apps
# button is visible, i.e. by default, essentially always -- silent
# rather than fatal only because GNOME Shell's own extension-callback
# wrapper swallows the exception, which is why it only ever showed up
# as log noise. Fixed by guarding both call sites with a
# typeof-is-function check before calling.
# Patch0 also fixes a second real bug found via log-based live testing
# 2026-09-25 (real user report: "the notification badge on the dock
# stays put and doesn't move with the icon while hovering"). Root
# cause, confirmed against GNOME Shell's own real appDisplay.js: the
# Hot-Key number-overlay badge (_numberOverlayBin) is added as a
# sibling of the icon inside _iconContainer, not a descendant of the
# icon graphic itself -- but this fork's custom macOS-style hover
# magnification (_onDockMotionEvent) only ever applies its scale/
# translation transform to the icon graphic (icon._iconBin), never to
# that sibling badge, so the badge stayed visually fixed while the
# icon scaled and moved underneath it. Fixed by mirroring the same
# transform onto _numberOverlayBin wherever the icon's own transform
# is applied or reset.
# ==============================================================================

Name:           parchaos-dock
Version:        106
Release:        5%{?dist}
Summary:        Parcha Dock — ParchaOS's macOS-styled fork of the Dash-to-Dock GNOME Shell extension

License:        GPL-2.0-only
URL:            https://github.com/Inled-Pulsar-OS/dash-to-dock
%global commit  f761ebe9a795262b42a18cf57cccd4afe9d3d5a4
%global shortcommit %(c=%{commit}; echo ${c:0:7})
Source0:        %{url}/archive/%{commit}/parchaos-dock-%{shortcommit}.tar.gz
Patch0:         0001-fix-showappsicon-number-overlay-crash.patch

BuildArch:      noarch

BuildRequires:  sassc
BuildRequires:  gettext
BuildRequires:  glib2
BuildRequires:  make

Requires:       gnome-shell >= 45
Requires:       dconf

%description
Parcha Dock is ParchaOS's build of a real macOS-style fork of the
well-known Dash-to-Dock GNOME Shell extension: hover magnification,
launch bounce animations, a downloads-folder stack, and live
minimized-window previews. Enabled by default as ParchaOS's dock.

%prep
%autosetup -n dash-to-dock-%{commit} -p1

# ParchaOS branding rebrand (see banner comment above) — real upstream
# UUID/name confirmed via the real metadata.json before writing this
# sed.
sed -i \
    -e 's/pulsar-dock@inled\.es/parcha-dock@parchaos.org/g' \
    -e 's/"name": "Pulsar Dock"/"name": "Parcha Dock"/' \
    -e 's/original-author": "Inled-Pulsar-OS"/original-author": "ParchaOS"/' \
    -e 's#"url": "https://github.com/Inled-Pulsar-OS/dash-to-dock"#"url": "https://github.com/alexgalicea/parchaos-gnome"#' \
    metadata.json Makefile

%build
make _build

%install
UUID=parcha-dock@parchaos.org
DEST=%{buildroot}%{_datadir}/gnome-shell/extensions/$UUID
mkdir -p "$DEST"
cp -a _build/* "$DEST"/

# Real bug found on real hardware 2026-09-24: the extension was
# installed and enabled (present in dconf's enabled-extensions) but
# never actually rendered -- `gnome-extensions show` reported
# `State: ERROR`, and journalctl showed GLib.FileError: Failed to open
# "$UUID/schemas/gschemas.compiled": No such file or directory,
# thrown from docking.js's DockManager constructor the moment
# extension.js called enable(). Root cause, confirmed directly against
# the real upstream Makefile: `make _build`'s _build target only
# copies the RAW schemas/*.gschema.xml into _build/schemas/ -- the
# actual compiled binary GNOME Shell loads at runtime is produced by a
# separate `extension:`/`./schemas/gschemas.compiled:` target that
# only the Makefile's own `install`/`install-local` targets depend on,
# and this spec's %install never called either of those, just a plain
# `cp -a _build/*`. Fixed the same way Fedora's own GNOME extension
# packages do it: compile the schema directly into place here, so the
# extension is fully self-contained (works the same whether GNOME
# Shell resolves schemas from the extension's own directory or not,
# no dependency on a system-wide glib-2.0/schemas install+recompile).
glib-compile-schemas "$DEST/schemas"

# Ship the dock's own translations system-wide so the "dashtodock"
# gettext domain resolves (same real upstream mechanism the actual
# Pulsar OS package uses, confirmed via its own prepare-assets.sh).
if [ -d _build/locale ]; then
    for mo in _build/locale/*/LC_MESSAGES/*.mo; do
        [ -f "$mo" ] || continue
        lang="$(basename "$(dirname "$(dirname "$mo")")")"
        mkdir -p "%{buildroot}%{_datadir}/locale/$lang/LC_MESSAGES"
        cp "$mo" "%{buildroot}%{_datadir}/locale/$lang/LC_MESSAGES/"
    done
fi

%files
%license COPYING
%doc README.md
%{_datadir}/gnome-shell/extensions/parcha-dock@parchaos.org/
%{_datadir}/locale/*/LC_MESSAGES/dashtodock.mo

%changelog
* Fri Sep 25 2026 ParchaOS packaging - 106-5
- Fixed a second real bug found via log-based live testing (same
  Patch0): the dock's notification/Hot-Key number-overlay badge stayed
  fixed in place instead of tracking the icon during hover
  magnification, since it's a sibling of the icon actor, not a
  descendant, and the magnification code never transformed it.
  Mirrored the icon's scale/translation onto the badge in both the
  apply and reset paths. See spec banner comment for the trace.
* Fri Sep 25 2026 ParchaOS packaging - 106-4
- Release 106-3's Patch0 was malformed (a hand-transcribed diff --git
  header confused GNU patch's git-diff heuristic into thinking dash.js
  was being newly created, so the patch silently failed the COPR
  build: "The next patch would create the file dash.js, which already
  exists!"). Regenerated the patch mechanically from a real diff -u
  run and confirmed it applies cleanly against a fresh, pristine
  extraction (plain unified-diff header, no diff --git/index lines)
  before resubmitting. Same fix as 106-3, this time verified working.
* Fri Sep 25 2026 ParchaOS packaging - 106-3
- Fixed a real, reproducible crash (TypeError: icon.setNumberOverlay
  is not a function) found via log-based live testing, first
  misattributed to parchaos-desktop-icons/DING. Confirmed as a genuine
  upstream dash-to-dock bug (also present in micheleg/dash-to-dock's
  own master, checked directly): the Show Apps grid button lacks the
  number-overlay methods that getAppIcons() assumes every icon has.
  Patch0 guards both call sites. See spec banner comment and
  docs/gnome-phase1-findings.md for the full trace.
* Thu Sep 24 2026 ParchaOS packaging - 106-2
- Real bug found on real hardware: the dock was enabled in dconf but
  crashed at enable() with State: ERROR (missing
  schemas/gschemas.compiled -- the upstream Makefile's _build target
  never produces it, only its install/install-local targets do, which
  this spec never called). Added an explicit `glib-compile-schemas`
  call in %install. See the comment above %install for the full
  root-cause trace.
* Wed Sep 23 2026 ParchaOS packaging - 106-1
- Initial package, real upstream fork (Inled-Pulsar-OS/dash-to-dock,
  itself a real fork of micheleg/dash-to-dock, pinned to commit
  f761ebe9), rebranded "Parcha Dock" for ParchaOS's own identity. Not
  yet build-tested against a real Fedora chroot — expect real
  iteration on %%files/%%build, same pattern as parchaos-finder.
