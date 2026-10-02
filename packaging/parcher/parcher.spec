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
Release:        34%{?dist}
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
# Natural-language search (ticket #120): "pdf from last week" in the search
# entry becomes a date range and file-type filter.
Patch4:         0005-natural-language-search.patch
# The sidebar header bar hides the app title (ticket #143): it was cut to
# "Parc..." beside the window buttons.
Patch5:         0006-sidebar-no-app-title.patch
# The toolbar shows the folder's icon and name as its title; the path opens
# from it (ticket "Parcher window layout").
Patch6:         0007-folder-title.patch
# A path bar and a status line under the files: item count (or selection),
# free space on the disk, and an icon-size slider.
Patch7:         0008-status-bar.patch
# Round search button, and a "more" menu (new folder, paste, select all, show
# hidden files, properties) in place of the hidden new-folder button.
Patch8:         0009-round-search-and-more-menu.patch
# Sidebar: sentence-case section headings, rounded rows.
Patch9:         0010-sidebar-polish.patch
# Quick Preview (spacebar): Sushi 50's ShowFile takes a fourth argument, the
# activation token, and rejects Nautilus 48's three-argument call.
Patch10:        0011-previewer-activation-token.patch
# ParchaOS's own look for the sidebar (appended to the stylesheet in %prep).
Source1:        parcher-own-layout.css

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
Parcher is ParchaOS's file manager: a real fork of GNOME Files
(Nautilus), not a theme on top of stock Files. It adds real
traffic-light window controls, folder color tags with a dedicated
per-color filter in the sidebar, and cloud drive integration in the
sidebar.

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

# Neutralize and remove third-party vendor references from embedded CSS, UI and C sources (ticket #109,
# naming policy; look-alike audit). One pass over every CSS, UI and C file, so a comment, a CSS class name or
# a string cannot slip past an edit aimed at one file (the old edit named the wrong .ui file and its
# trailing "|| :" hid that).
find src -type f \( -name '*.css' -o -name '*.ui' -o -name '*.c' -o -name '*.h' \) -exec sed -i \
    -e 's/Apple macOS Finder Styling/ParchaOS File Manager Styling/g' \
    -e 's/Segmented Finder Views (Icons, List, Sort) with macOS pill container/Segmented Parcher Views (Icons, List, Sort) with pill container/g' \
    -e 's/finder-pill-segmented/parcher-pill-segmented/g' \
    -e 's/finder-toolbar/parcher-toolbar/g' \
    -e 's/finder-pathbar-container/parcher-pathbar-container/g' \
    -e 's/Finder-like semantics/starred-state semantics/g' \
    -e 's/Finder Favorites/Favorites/g' \
    -e 's/\bFinder\b/Parcher/g' \
    {} +
! grep -rIq 'finder-' src

# ParchaOS's own look for the window (look-alike audit): the toolbar's capsules become small
# rounded rectangles (edits to the Parcher rules only, from their section heading to the end of
# the file; the upstream rules above stay as they are), the tag colours are ParchaOS's own, and the
# sidebar gets flat rows with an accent bar.
sed -i \
    -e '/Parcher Pill View Switcher/,$ s/border-radius: 9999px;/border-radius: 8px;/' \
    -e '/Parcher Pill View Switcher/,$ s/border-radius: 999px;/border-radius: 8px;/' \
    -e '/Parcher Pill View Switcher/,$ s/border: 1px solid alpha(currentColor, 0.12);/border: none;/' \
    -e '/Parcher Pill View Switcher/,$ s/min-width: 34px;/min-width: 30px;/' \
    -e '/Parcher Pill View Switcher/,$ s/min-height: 34px;/min-height: 30px;/' \
    -e 's/#ff453a/#e5586e/; s/#ff9f0a/#ee8f3a/; s/#ffd60a/#e6c34a/; s/#30d158/#4fb286/' \
    -e 's/#0a84ff/#4f8fd8/; s/#bf5af2/#8a6ce0/; s/#8e8e93/#8c8f99/' \
    src/resources/style.css
# Back and forward: two separate buttons (no shared capsule).
sed -i -e 's/<property name="spacing">0<\/property>/<property name="spacing">6<\/property>/' \
    -e 's/<class name="parcher-pill-segmented"\/>/<class name="parcher-history-buttons"\/>/' \
    src/resources/ui/nautilus-history-controls.ui
grep -q 'parcher-history-buttons' src/resources/ui/nautilus-history-controls.ui
cat %{SOURCE1} >> src/resources/style.css
# Parcher's own stylesheet must win over the GTK theme's per-user stylesheet (~/.config/gtk-4.0/gtk.css,
# installed by parchaos-gtk-theme at the same USER priority, which otherwise put the capsules back).
sed -i 's/GTK_STYLE_PROVIDER_PRIORITY_USER);/GTK_STYLE_PROVIDER_PRIORITY_USER + 1);/' src/nautilus-application.c
grep -q 'GTK_STYLE_PROVIDER_PRIORITY_USER + 1);' src/nautilus-application.c
! grep -q '#ff453a\|#0a84ff' src/resources/style.css
! ( sed -n '/Parcher Pill View Switcher/,$p' src/resources/style.css | grep -q 'border-radius: 9999px' )

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
* Fri Oct 02 2026 ParchaOS packaging - 48.7-34
- Parcher's stylesheet loads one step above the GTK theme's per-user stylesheet, which had the same priority and put the capsules back on a real desktop. The back/forward box has no background of its own.

* Fri Oct 02 2026 ParchaOS packaging - 48.7-33
- Look-alike audit (own layout): back and forward are two separate rounded buttons instead of one joined capsule.

* Fri Oct 02 2026 ParchaOS packaging - 48.7-32
- Look-alike audit (own layout): the toolbar's capsules (view switcher, back/forward, search, more, entries) are small rounded rectangles; the tag colours are ParchaOS's own palette instead of another platform's system colours; the sidebar has flat rows and an accent bar on the selected place.

* Fri Oct 02 2026 ParchaOS packaging - 48.7-31
- Look-alike audit: the vendor-name clean-up covers every CSS, UI and C source (it aimed at one file and missed a comment in nautilus-view-controls.ui); the toolbar CSS classes are parcher-* instead of another product's name.

* Fri Oct 02 2026 ParchaOS packaging - 48.7-30
- Ticket #167: no longer pinned to x86_64, so it builds for aarch64 as well.

* Wed Sep 30 2026 ParchaOS packaging - 48.7-29
- Quick Preview (ticket #153): pressing the spacebar did nothing. Sushi 50's
  ShowFile takes a fourth argument (an activation token) and refused
  Nautilus 48's three-argument call without a word. The call now sends it.

* Wed Sep 30 2026 ParchaOS packaging - 48.7-28
- Sidebar polish (ticket #145, stage 4): section headings in sentence case,
  rows with rounded corners and a little space between them.

* Wed Sep 30 2026 ParchaOS packaging - 48.7-27
- The more button gets the same round look as the search button.

* Wed Sep 30 2026 ParchaOS packaging - 48.7-26
- The round search and more buttons now override the header bar styling, so
  they really are round and larger.

* Wed Sep 30 2026 ParchaOS packaging - 48.7-25
- The search button is round and larger, and the toolbar has a "more" menu
  (New Folder, Paste, Select All, Show Hidden Files, Properties) that is
  always there (ticket #145, stage 3).

* Wed Sep 30 2026 ParchaOS packaging - 48.7-24
- The path bar under the files is wired to the folder being shown (it only
  showed an overflow button in 48.7-23).

* Wed Sep 30 2026 ParchaOS packaging - 48.7-23
- A path bar and a status line now sit under the files: the folder's
  item count (or how many are selected), the free space on its disk, and
  an icon-size slider (ticket #145, stage 2).

* Wed Sep 30 2026 ParchaOS packaging - 48.7-22
- The toolbar title shows a folder icon (it showed the view-mode icon in
  48.7-21) and stays centred at its natural width.

* Wed Sep 30 2026 ParchaOS packaging - 48.7-21
- The toolbar now shows the current folder's icon and name as its title,
  with an arrow; clicking it opens the folder path (the breadcrumb) in a
  popover.

* Wed Sep 30 2026 ParchaOS packaging - 48.7-20
- Ticket #143: the sidebar header bar now hides the app name, which
  was cut to "Parc..." next to the window buttons. The folder name stays in
  the toolbar.

* Tue Sep 29 2026 ParchaOS packaging - 48.7-19
- Ticket #120: natural-language search. In the search entry, text that
  names a time range ("pdf from last week", "photos yesterday", "invoice
  this month") sets the date range and file-type filters and searches the
  remaining words in file names, with tags showing what was understood.
  The tags show the phrase as typed ("Last week"). Ordinary searches are unchanged. The phrase reader is parcher-natural-
  search.c, tested by tests/natural-search-test.c.
* Mon Sep 28 2026 ParchaOS packaging - 48.7-17
- Remove third-party vendor references from embedded CSS/UI
  comments (ticket #109, naming policy).
* Mon Sep 28 2026 ParchaOS packaging - 48.7-16
- Rewrote %description to be user-facing and neutral (ticket
  #105): dropped internal build-diligence notes and lineage
  wording toward other distributions. Upstream project credit
  (authors, licenses) is kept.
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
  no-patch form). The premise was never verified against clean design
  criteria; modern desktop sidebars use monochrome/tinted symbolic icons
  throughout (Applications, Desktop, Documents, Downloads, Cloud Drives,
  local drives, Network, Trash). GNOME's existing -symbolic icon
  convention was already correct; full-color icons caused visual clutter.
  Leaving this entry in place rather than silently deleting the
  48.7-7 one, per this project's record policy -- the lesson is to
  verify UI styling against clean design criteria rather than ad-hoc
  assumptions.
* Fri Sep 25 2026 ParchaOS packaging - 48.7-7
- Sidebar icon styling experiment: tested swapping the sidebar's main row
  icons (Home, Desktop, Network, Trash, Recents, Starred, cloud bookmarks,
  mounted volumes/drives, and user-added bookmarks) from their monochrome
  -symbolic variants to full-color icons. Added Patch0: renames the
  hardcoded ICON_NAME_* constants and literal icon-name strings, swaps
  g_mount/g_volume/g_drive's _get_symbolic_icon() calls for their real
  _get_icon() counterparts, adds nautilus_trash_monitor_get_icon(), and
  rebinds user bookmark rows to NautilusBookmark's existing "icon"
  property instead of "symbolic-icon". Left ICON_NAME_EJECT and
  ICON_NAME_NETWORK_VIEW symbolic. (Reverted in 48.7-8).

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
