# ==============================================================================
# Parcher — Pulsar OS's real fork of GNOME Files (Nautilus), shipped
# upstream as "Finder".
# Real traffic-light window controls, a Tags sidebar (color-tag folders,
# per-color filtering), and cloud-drive sidebar integration — none of
# which are stock GNOME Files features. Source: real, public fork at
# https://github.com/Inled-Pulsar-OS/finder (a git submodule of the real
# Pulsar OS package monorepo, Inled-Pulsar-OS/PKG, at
# arch/pkgbuilds/nautilus/PKGBUILD — verified directly against that real
# PKGBUILD before writing this, not guessed).
#
# License: GPL-3.0-or-later (same as upstream GNOME Files — a GPL
# derivative work, not Pulsar OS's own MIT-INLED original code; this
# project is planning a public release, so this distinction matters and
# is being tracked carefully, same rigor as every other GPL-derived
# package in this project).
#
# Packaged directly from the real upstream fork's own source (meson/ninja
# build), NOT from Pulsar OS's Debian/Arch .deb/PKGBUILD output directly
# — same "port from real source, verify independently" pattern this
# project has used for every other component (liquid-gel, pearos-dock,
# WhiteSur-kde, etc.).
#
# Provides/Conflicts/Obsoletes stock `nautilus` — this IS Nautilus (same
# binary name, same D-Bus service name org.gnome.Nautilus, same
# libnautilus-extension ABI per the real PKGBUILD's own
# `provides=(libnautilus-extension)` / `conflicts=(libnautilus-extension)`
# / `replaces=(libnautilus-extension)` — a drop-in, not a side-by-side
# install), matching exactly how the real Pulsar OS package itself is
# structured.
#
# Named parcher, after the app, so COPR/dnf listings show ParchaOS's own
# build of the fork, distinct from Fedora's stock nautilus package it
# replaces. Until 48.7-11 the package was called parchaos-finder (renamed
# 2026-09-26 under the naming policy); Provides/Obsoletes below carry
# existing installs over.
#
# TRADEMARK NOTE (2026-09-22, real user directive ahead of a planned
# public release): the real upstream repo's own .desktop file already
# just says "Name=Files" (matching stock GNOME's own convention) --
# "Finder" only appears in Pulsar OS's own marketing copy/README, not
# baked into the installed app. Since this project plans to ship
# publicly and deliberately wants a MORE conservative trademark posture
# than either pearOS or Pulsar OS (both of which use "Finder"/"Spotlight"/
# "Time Machine" literally, and Pulsar OS's own assets reuse Apple's
# actual bitten-apple logo shape) -- overriding the shown app name to
# "Parcher" (Parcha + "-er", same naming family as ParchaOS itself, no
# reuse of Apple's actual product name) rather than "Finder" or even
# upstream's own "Files". This is a deliberate, real branding decision,
# not a guess -- same treatment planned for every other
# Apple-trademark-adjacent name in the Pulsar OS ecosystem this project
# ports (Spotlight, Time Machine, the "Apple Tahoe" SDDM theme name).
# ==============================================================================

Name:           parcher
Version:        48.7
Release:        15%{?dist}
Summary:        Parcher — ParchaOS's fork of GNOME Files (Nautilus)

License:        GPL-3.0-or-later
URL:            https://github.com/Inled-Pulsar-OS/finder
# Built from the GNOME Nautilus release Pulsar OS's Finder forked, plus
# Finder's changes as one patch per feature (split from Inled-Pulsar-OS/
# finder commit 351f6655, which is exactly Nautilus 48.7 plus these), so
# each feature can be ported to newer Nautilus on its own
# (docs/parcher-rebase-plan.md).
Source0:        https://download.gnome.org/sources/nautilus/48/nautilus-%{version}.tar.xz
# Color tags: live folder tinting and per-color filters.
Patch0:         0001-color-tags.patch
# Sidebar sections (colors, cloud drives).
Patch1:         0002-sidebar-sections.patch
# Toolbar and window layout.
Patch2:         0003-toolbar-window-layout.patch
# App identity.
Patch3:         0004-app-identity.patch

BuildArch:      x86_64

Provides:       parchaos-finder = %{version}-%{release}
Obsoletes:      parchaos-finder < 48.7-12
Provides:       nautilus = %{version}-%{release}
Provides:       libnautilus-extension = %{version}-%{release}
Conflicts:      nautilus
# Any Fedora nautilus up to the next GNOME major: while Parcher is
# installed, a newer Fedora nautilus can't be installed alongside it or
# pulled in to replace it. Bump with each rebase (docs/parcher-rebase-plan.md).
Obsoletes:      nautilus < 51

BuildRequires:  gcc
BuildRequires:  meson
BuildRequires:  ninja-build
BuildRequires:  gettext
BuildRequires:  desktop-file-utils
BuildRequires:  gobject-introspection-devel
# Real bug found via a real build attempt (2026-09-22): the PKGBUILD's
# "libcloudproviders" dependency name doesn't match any real pkgconfig
# file. meson.build itself calls dependency('cloudproviders', ...) —
# confirmed both against the real meson.build source and Fedora's
# libcloudproviders-devel package (`dnf repoquery -l`), which ships
# cloudproviders.pc, not libcloudproviders.pc.
BuildRequires:  pkgconfig(cloudproviders)
BuildRequires:  pkgconfig(dconf)
BuildRequires:  pkgconfig(gdk-pixbuf-2.0)
# Real bug found in the upstream PKGBUILD itself (arch/pkgbuilds/nautilus/
# PKGBUILD's own %%prepare()): gexiv2 0.16+ renamed its pkgconfig file
# from gexiv2.pc to gexiv2-0.16.pc, and upstream meson.build still says
# dependency('gexiv2') — the real PKGBUILD works around this with a sed.
# Fedora's libgexiv2-devel ships gexiv2-0.16.pc (confirmed via a real
# `dnf repoquery -l libgexiv2-devel`), so this needs the identical sed
# fix, not just the right BuildRequires.
BuildRequires:  pkgconfig(gexiv2-0.16)
BuildRequires:  pkgconfig(glib-2.0)
BuildRequires:  pkgconfig(gnome-autoar-0)
BuildRequires:  pkgconfig(gnome-desktop-4)
BuildRequires:  pkgconfig(graphene-gobject-1.0)
BuildRequires:  pkgconfig(gstreamer-1.0)
BuildRequires:  pkgconfig(gstreamer-pbutils-1.0)
# Real bug found via a real build attempt: meson.build also requires
# gstreamer-tag-1.0 directly (missed on the first pass through the real
# dependency() list) — same gstreamer1-plugins-base-devel package
# already covers it, just needed the explicit pkgconfig() name too.
BuildRequires:  pkgconfig(gstreamer-tag-1.0)
BuildRequires:  pkgconfig(gtk4)
BuildRequires:  pkgconfig(libadwaita-1)
BuildRequires:  pkgconfig(libportal)
BuildRequires:  pkgconfig(libportal-gtk4)
BuildRequires:  pkgconfig(pango)
# Real bug found via a real build attempt: meson.build calls
# dependency('tracker-sparql-3.0', ...) — the OLD pre-rename pkgconfig
# name, not 'tinysparql-3.0'. Fedora's tinysparql-devel ships both
# tinysparql-3.0.pc AND a tracker-sparql-3.0.pc compat symlink
# (confirmed via `dnf repoquery -l tinysparql-devel`), so requiring the
# exact name meson actually looks for, not just "a" name that happens
# to pull in the same package.
BuildRequires:  pkgconfig(tracker-sparql-3.0)

Requires:       gvfs
Requires:       hicolor-icon-theme
Requires:       shared-mime-info
# Real, hard crash found on real hardware 2026-09-25 (user report: home
# folder icon and the file browser both failed to open at all):
# nautilus_global_preferences_init aborts the whole process with
# SIGABRT the instant it's launched, every single time, no window ever
# appears. journalctl showed the real cause right before every crash:
# "Settings schema 'org.freedesktop.Tracker3.Miner.Files' is not
# installed" -- GLib's g_settings_new() calls g_error() (fatal abort)
# when a schema it's given is completely absent from the compiled
# schema database, and Nautilus's own preferences init unconditionally
# instantiates a GSettings object for Tracker's file-indexing miner
# schema. Confirmed via `dnf provides` that the real Fedora package
# providing this schema is `localsearch` (Fedora's rename of
# tracker-miners) -- never installed here because this profile
# deliberately doesn't pull in Fedora's full comps.xml package bundle
# (see the project's development notes own reasoning for that choice),
# so this hard dependency was simply missing.
Requires:       localsearch

# Real bug found via log-based live testing 2026-09-25 (real user
# report: no live image previews in the thumbnail view).
# Root-caused with a small standalone C program calling
# GnomeDesktopThumbnailFactory directly (python-gi isn't installed on
# this profile at all, so this was verified against the real API, not
# guessed): gnome_desktop_thumbnail_factory_can_thumbnail() returned
# FALSE and generate_thumbnail() failed with "Could not find
# thumbnailer for mime-type 'image/png'" -- confirmed reproducible for
# both a real screenshot and a plain small PNG, so this is systemic,
# not file-specific. GdkPixbuf itself decodes PNG fine; the factory
# still needs an explicit .thumbnailer registration file before it will
# even attempt it. Fedora ships that registration (glycin-image-rs.thumbnailer,
# covering image/png, image/jpeg, and friends) in the `glycin-thumbnailer`
# subpackage, not bundled with gdk-pixbuf or gnome-desktop itself --
# same missing-subpackage pattern as `localsearch` above, never pulled
# in because this profile doesn't use Fedora's full comps.xml bundle.
# Installing it live and re-running the same C test confirmed the fix
# (can_thumbnail=1, generate_thumbnail succeeded) before adding this.
Requires:       glycin-thumbnailer

%description
Parcher is ParchaOS's real, working fork of GNOME Files
(Nautilus), built from Pulsar OS's real public fork: real traffic-light
window controls, live folder color tagging with a dedicated per-color
filter sidebar section, and cloud drive sidebar integration — a genuine
derivative work of GNOME Files, not a theme applied on top of stock
Nautilus. Renamed from upstream's own "Files" (itself derived from
Pulsar OS's own "Finder" branding) to avoid trademark exposure ahead of
a planned public release — see this spec's own banner comment.

%prep
%autosetup -n nautilus-%{version} -p1
# Same real fix the upstream PKGBUILD itself applies (see BuildRequires
# comment above) — gexiv2's pkgconfig name changed upstream, meson.build
# didn't catch up.
sed -i "s/dependency('gexiv2'/dependency('gexiv2-0.16'/" meson.build

# ParchaOS branding / trademark-avoidance rename — see the banner
# comment above. Real upstream file confirmed to say "Name=Files"
# (checked directly against the real repo before writing this, not
# guessed) — overriding to our own name rather than either upstream's
# own default or Apple's "Finder".
sed -i 's/^Name=Files$/Name=Parcher/' data/org.gnome.Nautilus.desktop.in.in
grep -q '^Name=Parcher$' data/org.gnome.Nautilus.desktop.in.in

# Real bug found via log-based live testing 2026-09-25 (real user
# report: the file manager's window title said "Finder").
# Root cause: the .desktop rename above was never the whole story --
# Pulsar OS's own real upstream fork (this package's actual Source0,
# not stock GNOME Files) already hardcoded the literal string "Finder"
# in THREE places, confirmed by reading the real source directly, not
# guessed: the window's own AdwWindowTitle property (a static title,
# not the dynamic per-folder title stock Nautilus normally shows --
# that's a real Pulsar OS design choice this fork inherits), the
# "_About Finder" menu item label, and the About dialog's application
# name. The banner comment above only ever accounted for the .desktop
# file's app-launcher identity, missing these in-UI strings entirely.
sed -i 's/"Finder"/"Parcher"/' src/nautilus-window.c
grep -q '"Parcher"' src/nautilus-window.c
sed -i 's/_About Finder/_About Parcher/; s/>Finder</>Parcher</' src/resources/ui/nautilus-window.ui
grep -q '_About Parcher' src/resources/ui/nautilus-window.ui

# About dialog: send users to ParchaOS for help and bug reports instead
# of the upstream fork's site, and describe where Parcher comes from.
# The upstream developer credits and both copyright lines stay; a
# ParchaOS line is added.
sed -i \
    -e 's#_("File manager for Pulsar OS, a derivative work based on GNOME Files (Nautilus).")#_("The ParchaOS file manager, based on the Pulsar OS file manager by Inled, a derivative of GNOME Files (Nautilus).")#' \
    -e 's#"https://github.com/Inled-Pulsar-OS/finder/issues"#"https://github.com/Spanglish-Enterprises/parchaos-gnome/issues"#' \
    -e 's#"https://github.com/Inled-Pulsar-OS/finder"#"https://parchaos.org"#' \
    -e 's#set_support_url (ADW_ABOUT_DIALOG (dialog), "https://os.inled.es")#set_support_url (ADW_ABOUT_DIALOG (dialog), "https://parchaos.org/support")#' \
    -e 's#"© 2026 Inled / Pulsar OS Contributors\\n© 1999-2026 The Nautilus Authors"#"© 2026 Spanglish Enterprises LLC (ParchaOS changes)\\n© 2026 Inled / Pulsar OS Contributors\\n© 1999-2026 The Nautilus Authors"#' \
    -e 's#"JaimeGH (Inled)",#"ParchaOS contributors",\n        "JaimeGH (Inled)",#' \
    src/nautilus-window.c
grep -q 'The ParchaOS file manager' src/nautilus-window.c
grep -q '"https://parchaos.org/support"' src/nautilus-window.c
grep -q 'Spanglish-Enterprises/parchaos-gnome/issues' src/nautilus-window.c
grep -q 'Spanglish Enterprises LLC (ParchaOS changes)' src/nautilus-window.c
grep -q '"ParchaOS contributors",' src/nautilus-window.c
grep -q '© 1999-2026 The Nautilus Authors' src/nautilus-window.c
! grep -q 'Inled-Pulsar-OS/finder\|os\.inled\.es")' src/nautilus-window.c

# The sidebar's cloud section header named Apple's cloud service. Use a
# neutral title (naming policy). Labels for a folder or mount the user
# connected from that service keep the service's own name, like any other
# provider's.
sed -i 's/_("iCloud & Cloud Drives")/_("Cloud Drives")/' src/gtk/nautilusgtkplacessidebar.c
grep -q '_("Cloud Drives")' src/gtk/nautilusgtkplacessidebar.c

%build
%meson -Ddocs=false -Dtests=none
%meson_build

%install
%meson_install

# Real bug found via a real COPR build (2026-09-22): %%find_lang needs
# the actual gettext translation domain name, which stays "nautilus"
# (upstream's own po/ catalog, untouched by our Parcher rename) -- NOT
# %%{name} (parcher). Confirmed via the real build log showing
# every .mo file installed as .../LC_MESSAGES/nautilus.mo.
%find_lang nautilus --with-gnome

%files -f nautilus.lang
%license LICENSE
%doc README.md NEWS
%{_bindir}/nautilus
%{_bindir}/nautilus-autorun-software
%{_datadir}/applications/*.desktop
%{_datadir}/dbus-1/services/*.service
%{_datadir}/gnome-shell/search-providers/*.ini
%{_datadir}/icons/hicolor/*/*/*
%{_datadir}/metainfo/*.xml
%{_datadir}/glib-2.0/schemas/*.gschema.xml
%{_libdir}/nautilus/
%{_libdir}/libnautilus-extension.so
%{_libdir}/libnautilus-extension.so.4*
%{_libdir}/girepository-1.0/*.typelib
%{_includedir}/nautilus/
%{_libdir}/pkgconfig/*.pc
%{_datadir}/gir-1.0/*.gir
%{_datadir}/nautilus/

%changelog
* Sat Sep 26 2026 ParchaOS packaging - 48.7-15
- About dialog: website, issue and support links go to ParchaOS;
  ParchaOS copyright and contributors added while keeping the Inled and
  Nautilus credits. The build fails if the edits stop applying.
* Sat Sep 26 2026 ParchaOS packaging - 48.7-14
- Build from the GNOME Nautilus 48.7 release plus Pulsar OS Finder's
  changes as one patch per feature (color tags, sidebar sections,
  toolbar and window layout, app identity); the result is the same
  source tree as before.
* Sat Sep 26 2026 ParchaOS packaging - 48.7-13
- Obsolete any Fedora nautilus before 51, so a newer Fedora nautilus
  can't replace Parcher before its rebase.
* Sat Sep 26 2026 ParchaOS packaging - 48.7-12
- Renamed from parchaos-finder to parcher under the naming policy
  (Provides and Obsoletes parchaos-finder, so existing installs switch
  over on update).
* Fri Sep 25 2026 ParchaOS packaging - 48.7-11
- Sidebar cloud section header is now "Cloud Drives" instead of naming
  Apple's cloud service (naming policy).
* Fri Sep 25 2026 ParchaOS packaging - 48.7-10
- Reworded comments and changelog to describe user-reported issues
  instead of quoting them.
* Fri Sep 25 2026 ParchaOS packaging - 48.7-9
- Reworded summary/description/comments to describe features instead of
  naming macOS, per the project's trademark-caution naming policy.
* Fri Sep 25 2026 ParchaOS packaging - 48.7-8
- Correction to 48.7-7: that release's Patch0 was wrong, reverted here
  entirely (Patch0 line and file removed, %%autosetup back to plain
  no-patch form). The premise -- "real macOS Finder uses full-color
  sidebar icons" -- was never actually checked against the real
  reference screenshot the user provided; when directly re-examined at
  the user's prompt, every icon in it (Applications, Desktop,
  Documents, Downloads, iCloud Drive, Dropbox, the home folder,
  Macintosh HD, AirDrop, Network, Trash) is monochrome/tinted, not
  full-color -- real modern macOS (Big Sur onward) sidebar design.
  GNOME's existing -symbolic icon convention was already correct; this
  patch was moving away from real macOS fidelity, not toward it.
  Leaving this entry in place rather than silently deleting the
  48.7-7 one, per this project's own "don't silently rewrite what
  wasn't verified" rule -- the lesson is to re-check the actual
  reference image directly before making a UI-fidelity claim, not
  rely on general assumptions about what a version of macOS looks
  like.
* Fri Sep 25 2026 ParchaOS packaging - 48.7-7
- Real macOS reference comparison: the sidebar's main row icons (Home,
  Desktop, Network, Trash, Recents, Starred, cloud-provider bookmarks,
  mounted volumes/drives, and user-added bookmarks) were all forced to
  their monochrome -symbolic variants -- real macOS Finder uses
  full-color icons throughout. Confirmed ParchaOS-dark ships real
  non-symbolic equivalents for every icon name changed here (checked
  directly against the real installed theme, not assumed) before
  patching. Added Patch0: renames the hardcoded ICON_NAME_* constants
  and literal icon-name strings, swaps g_mount/g_volume/g_drive's
  _get_symbolic_icon() calls for their real _get_icon() counterparts,
  adds a new nautilus_trash_monitor_get_icon() (non-symbolic sibling of
  the existing symbolic-only getter, used by both the sidebar's
  creation path and its update_trash_icon() live-update path, which
  was silently reverting the icon back to symbolic on every trash
  state change), and rebinds user bookmark rows to NautilusBookmark's
  existing "icon" property instead of "symbolic-icon". Left
  ICON_NAME_EJECT and ICON_NAME_NETWORK_VIEW symbolic on purpose: eject
  matches real macOS's own small subtle glyph there, and this theme
  has no colored "network-computer" icon to switch to.

* Fri Sep 25 2026 ParchaOS packaging - 48.7-6
- Fixed a real bug found via log-based live testing: image thumbnails
  never generated in icon/grid view. Root-caused with a direct C test
  against GnomeDesktopThumbnailFactory (python-gi isn't installed on
  this profile): "Could not find thumbnailer for mime-type
  'image/png'" -- Fedora splits the actual thumbnailer registration
  for common raster formats into `glycin-thumbnailer`, not bundled
  with gdk-pixbuf/gnome-desktop, same missing-subpackage pattern as
  localsearch. Added Requires: glycin-thumbnailer; confirmed live
  (can_thumbnail=1, generate_thumbnail succeeded) before shipping.
* Fri Sep 25 2026 ParchaOS packaging - 48.7-5
- Fixed a real bug found via log-based live testing: the file browser
  window's own titlebar said "Finder", not "Parcher". Root cause:
  Pulsar OS's own real upstream fork hardcodes "Finder" in the
  AdwWindowTitle property (a static title, not stock Nautilus's usual
  dynamic per-folder one), the "_About Finder" menu label, and the
  About dialog's application name -- the earlier .desktop rename never
  touched these in-UI strings. Renamed all three to "Parcher".
* Fri Sep 25 2026 ParchaOS packaging - 48.7-4
- Real bug found on real hardware: nautilus crashed with SIGABRT on
  every single launch (both the desktop's Home folder icon and the
  dock/app-grid launcher), no window ever appeared. Root cause:
  missing `localsearch` (org.freedesktop.Tracker3.Miner.Files schema),
  which nautilus_global_preferences_init needs unconditionally. See
  the Requires: localsearch line's own comment for the full trace.
* Wed Sep 23 2026 ParchaOS packaging - 48.7-3
- Real "installed but unpackaged files" error from the third real COPR
  attempt: the main libnautilus-extension.so/.so.4 shared library files
  (distinct from the plugin .so files already covered by
  %%{_libdir}/nautilus/) and the whole %%{_datadir}/nautilus/ ontology
  directory were both missing from %%files entirely.
* Tue Sep 22 2026 ParchaOS packaging - 48.7-2
- Real bugs found via two real COPR build attempts: %%find_lang needed
  the gettext domain "nautilus" (untouched by the Parcher rename), not
  %%{name}; %%license file is really named LICENSE, not COPYING (checked
  against the real repo listing after guessing wrong); real installed
  extension headers land at %%{_includedir}/nautilus/, not
  %%{_includedir}/nautilus-extension-4/. First attempt's actual compile
  and %%install succeeded cleanly on the very first try — these were
  packaging-metadata mismatches only, not build issues.
* Tue Sep 22 2026 ParchaOS packaging - 48.7-1
- Initial package, real upstream fork (Inled-Pulsar-OS/finder, pinned to
  commit 351f6655), for ParchaOS's GNOME variant. Not yet build-tested —
  file listing above is a best-effort guess based on the real
  meson.build's install() calls and stock Fedora nautilus's own %%files
  section; expect a real rpmbuild attempt to surface "unpackaged files"
  or "file not found" errors that need reconciling against what actually
  gets installed, same as every other package in this project's history.
