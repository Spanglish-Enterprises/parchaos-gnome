# ==============================================================================
# The Global Menu Bar (org.kde.plasma.appmenu) already works natively
# for Qt/KDE apps -- confirmed live via qdbus-qt6 showing org.kde.kappmenu
# genuinely active on the session bus (see docs/pearos-ui-reference or
# this project's own memory for the full investigation). GTK apps
# (Pafari, and any Flathub app a user installs) can't bridge their menus
# into it without a GTK module that exports GtkMenuBar/GMenuModel over
# the same protocol the global menu widget expects -- Fedora ships no
# such package under any name (`dnf list appmenu-gtk-module*` returns
# nothing).
#
# This is rocka/appmenu-gtk-module-wayland (LGPL-3.0), a Wayland-native
# port of the old Ubuntu Unity project's GTK module, explicitly built
# against KWin's own `org_kde_kwin_appmenu_manager` Wayland protocol
# extension -- matches this profile's default Wayland session exactly.
# Upstream's own README labels it "PoC" (proof of concept), which
# proved accurate: it did NOT build cleanly out of the box (see the
# patch below) and hasn't seen upstream activity validating it as
# production-hardened. Packaged anyway because: (1) the bug that broke
# the build was a normal, well-understood CMake mistake, not a sign of
# deeper rot; (2) once fixed, it was verified doing something real --
# loaded into a live GTK3 app on a real running Plasma session, it
# genuinely bound to KWin's `org_kde_kwin_appmenu_manager` Wayland
# global and exposed a `com.canonical.Unity` D-Bus interface (confirmed
# via `qdbus-qt6`), not just "compiled and did nothing." No GTK app's
# menu was confirmed rendering inside Plasma's actual top-bar appmenu
# widget end-to-end yet -- that needs a real installed system with a
# real GTK app open, not a synthetic tester binary over a serial
# console. Flagging this honestly rather than overclaiming full parity.
#
# Named parchaos-* (not pearos-*): this has no relationship to any
# pearOS/Pear-Project upstream repo at all.
#
# Vendors rocka/libdbusmenu (also LGPL-3.0, a CMake-buildable fork of
# JetBrains' fork of the original ayatana/libdbusmenu) as a second
# Source -- it's a git submodule upstream, which GitHub's tarball
# export doesn't include content for, so it's fetched and placed into
# the `libdbusmenu/` subdirectory manually in %prep instead.
# ==============================================================================

Name:           parchaos-appmenu-gtk-module
Version:        0.24.02
Release:        1%{?dist}
Summary:        GTK3 global-menu bridge for KWin's Wayland appmenu protocol

License:        LGPL-3.0-or-later
URL:            https://github.com/rocka/appmenu-gtk-module-wayland
Source0:        %{url}/archive/refs/heads/master.tar.gz#/appmenu-gtk-module-wayland-%{version}.tar.gz
Source1:        https://github.com/rocka/libdbusmenu/archive/refs/heads/master.tar.gz#/libdbusmenu-%{version}.tar.gz
Patch0:         0001-fix-pic-and-force-static-linking.patch
Patch1:         0002-skip-rpath-embedding.patch

BuildRequires:  cmake
BuildRequires:  gcc
# Found via a real COPR clean-chroot build (2026-09-22): neither
# CMakeLists.txt (this project's own or libdbusmenu's) declares
# `project(... LANGUAGES C)` explicitly, so CMake's default behavior
# enables BOTH C and CXX and tries to detect a C++ compiler even
# though this is a pure-C project with zero .cpp files anywhere --
# fails outright with "Could not find the compiler specified in the
# environment variable CXX: g++" if gcc-c++ isn't present. This was
# invisible building locally on the build VM, which already had gcc-c++
# installed from earlier, unrelated work in this project.
BuildRequires:  gcc-c++
BuildRequires:  pkgconfig(gtk+-3.0)
BuildRequires:  pkgconfig(glib-2.0)

%description
A GTK3 module that strips a GTK3 app's own menu bar, converts it to a
DBusMenu, and registers it with KWin's Wayland appmenu protocol -- the
same mechanism org.kde.plasma.appmenu (Plasma's own global menu bar
widget, already active by default on this profile) reads from for
Qt/KDE apps. Activated system-wide via GTK_MODULES set to this
package's real installed path in /etc/environment (see
profiles/pearos/customize.sh) -- NOT via gtk-modules=... in a
settings.ini, which real testing on the build VM found does not actually
trigger the module despite looking like the more "correct" GTK3-native
approach (see customize.sh's own comment for the full story).

%prep
%setup -q -T -c -n %{name}-%{version}
tar xzf %{SOURCE0}
tar xzf %{SOURCE1}
mv appmenu-gtk-module-wayland-master appmenu-gtk-module-wayland
# libdbusmenu is a git submodule upstream -- GitHub's tarball export
# still creates an empty placeholder directory for it, so a plain `mv`
# here would nest libdbusmenu-master INSIDE that empty dir instead of
# replacing it (mv's own semantics: moving into an existing directory,
# not renaming to it). Remove the empty placeholder first.
rm -rf appmenu-gtk-module-wayland/libdbusmenu
mv libdbusmenu-master appmenu-gtk-module-wayland/libdbusmenu
cd appmenu-gtk-module-wayland
%patch -P0 -p1
%patch -P1 -p1

%build
cd appmenu-gtk-module-wayland
%cmake
%cmake_build

%install
cd appmenu-gtk-module-wayland
mkdir -p %{buildroot}%{_libdir}/gtk-3.0/modules
# Renamed at install time: the build output keeps the fork's own
# "-wayland" suffix; renamed to match the original (non-Wayland)
# project's conventional module filename for clarity. Activation is
# by direct full path (see %description and customize.sh), not GTK's
# own bare-module-name search, so this rename is cosmetic/for
# consistency rather than load-bearing for activation itself.
install -m 0755 %{_vpath_builddir}/libappmenu-gtk-module-wayland.so \
    %{buildroot}%{_libdir}/gtk-3.0/modules/libappmenu-gtk-module.so

%files
%license appmenu-gtk-module-wayland/LICENSE
%{_libdir}/gtk-3.0/modules/libappmenu-gtk-module.so

%changelog
* Tue Sep 22 2026 ParchaOS packaging - 0.24.02-1
- Initial package. Found and fixed real upstream build bugs, in order:
  1. libdbusmenu's CMakeLists.txt built its static libs without
     Position Independent Code, which fails to link into the main
     shared-object target with "recompile with -fPIC".
  2. Once that was fixed, the built .so's own real `ldd` output showed
     unsatisfiable runtime dependencies on libdbusmenu-glib.so and
     libdbusmenu-gtk.so -- neither exists anywhere on the system (real
     packages, checked via `rpm -q --whatprovides`) because
     dbusmenu-glib was explicitly declared SHARED upstream, and that
     shared-ness propagated through dbusmenu-gtk's own static link.
     Fixed by forcing both to STATIC explicitly (patch 0001 combines
     both fixes) so the final module has no external runtime
     dependency on anything this project doesn't ship or Fedora
     doesn't already provide.
  3. The resulting .so also embedded an absolute build-tree RPATH
     (rpmbuild's own check-rpaths QA check correctly rejected this as
     a packaging bug) -- fixed with CMAKE_SKIP_RPATH (patch 0002),
     confirmed unnecessary since fix #2 removed the only reason a
     custom runtime search path was ever needed.
  Verified the whole fix chain for real, not just "it compiled": ran a
  real RPM build to completion, inspected the actual installed .so's
  `ldd` output to confirm zero "not found" entries, and reloaded the
  final built module into a live GTK3 app (upstream's own
  unity-gtk-menu-tester) on a real running Plasma Wayland session,
  confirming via qdbus-qt6 that it genuinely bound to KWin's
  org_kde_kwin_appmenu_manager Wayland global.
  4. Real activation-mechanism finding: gtk-modules=appmenu-gtk-module
     in a settings.ini (tried both /etc/xdg/gtk-3.0/settings.ini and a
     real per-user ~/.config/gtk-3.0/settings.ini, and installing the
     module to both the version-agnostic and version-specific GTK
     module directories) looked like the correct, GTK3-native way to
     activate this, but real testing showed it silently never
     triggered the module -- the tester's own debug output never
     appeared. The one mechanism confirmed working, repeatedly, is
     GTK_MODULES set to the module's real direct full installed path
     (not a bare module name), which reliably produces the expected
     debug output every time. profiles/pearos/customize.sh activates
     it this way, via /etc/environment.
  Not yet confirmed rendering a real GTK app's menu inside Plasma's
  actual appmenu panel widget on an installed system (that needs a
  real GTK app open on a real install, not a synthetic tester binary)
  -- flagged honestly, not claimed as fully done.
  5. First real COPR clean-chroot submission failed outright (build
     11021730): neither CMakeLists.txt declares `project(...
     LANGUAGES C)` explicitly, so CMake's default of enabling both C
     and CXX tried to detect a C++ compiler for this pure-C project
     and failed with "Could not find the compiler specified in the
     environment variable CXX: g++" -- invisible on the build VM's own local
     build since gcc-c++ already happened to be installed there from
     earlier work. Added BuildRequires: gcc-c++.
