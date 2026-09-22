# ==============================================================================
# Real pearOS's own shipped skel kdeglobals sets
# `LookAndFeelPackage=com.github.vinceliuice.WhiteSur-dark` -- a real,
# legitimate third-party GPL-3.0 KPackage from vinceliuice/WhiteSur-kde
# (an actively maintained project, MacOS-like KDE theme, matching this
# project's whole premise). Real upstream pearOS (an Arch package)
# simply depends on the AUR whitesur-kde-git package to provide this;
# Fedora ships nothing under any name, so without this package the
# reference in skel's kdeglobals resolves to nothing and KDE silently
# falls back to stock Breeze for anything that isn't already covered by
# pearOS's own explicit config -- this was the real root cause behind
# a 2026-09-22 user report of "icons don't seem macOS themed" and
# "small UI weirdness" on a live screenshot.
#
# Scoped DELIBERATELY narrow: only the two `plasma/look-and-feel/`
# KPackage directories (light + dark) are packaged here, matching this
# project's own existing pearOS-light/pearOS-dark look-and-feel
# packages in pearos-settings.spec. The REST of upstream WhiteSur-kde
# (its own Kvantum theme, SDDM theme, GTK theme, cursors, wallpapers,
# aurorae decorations) is deliberately NOT packaged -- this project
# already ships its own pearOS-branded equivalents for every one of
# those (pearos-gtk-theme, pearos-sddm-theme, pearos-aurorae-theme,
# pearos-wallpapers, the Kvantum theme in pearos-settings' skel), and
# pulling in WhiteSur's versions of the same pieces would conflict
# with/duplicate our own real branding rather than complete it.
#
# Real value of packaging this component, checked directly against its
# own contents/defaults file (2026-09-22): every single key it would
# set (ColorScheme, Icons, cursor theme, widgetStyle, kwin decoration,
# plasma desktop theme) is ALREADY independently, explicitly set by
# pearOS's own real kdeglobals/kwinrc -- so this is not "the thing that
# actually themes pearOS". The real, concrete effect of having this
# package installed is:
#   1. The `LookAndFeelPackage=` reference in skel's kdeglobals now
#      resolves to something real instead of nothing, which is what
#      Plasma's own System Settings > Appearance > Global Theme page
#      reads to show which theme is "currently applied" -- previously
#      this page would have shown nothing/an error for a fresh pearOS
#      install.
#   2. contents/splash/ (boot splash screen QML) and contents/logout/
#      (logout/shutdown dialog QML) are real, distinct assets neither
#      pearOS nor this project ships anywhere else -- these get used
#      directly by ksplashqml / ksmserver via the same
#      LookAndFeelPackage= key, independent of whether the theme's
#      `defaults` overrides ever actually get re-applied.
#   3. If a user ever manually re-applies this Global Theme later via
#      System Settings (as opposed to just booting the static skel
#      snapshot this profile ships), contents/defaults and
#      contents/layouts/org.kde.plasma.desktop-layout.js become live
#      and would reset the panel layout to WhiteSur's own -- NOT
#      exercised or relied on by this profile's own default boot path,
#      which never runs "Apply Global Theme" and instead boots directly
#      from a pre-baked appletsrc snapshot (see pearos-settings.spec).
#      Shipped as-is (unmodified) for correctness/fidelity in case a
#      user does this intentionally, not because this profile depends
#      on it.
#
# Named parchaos-* (not pearos-*) since, unlike the content in
# pearos-settings.spec, this is genuinely third-party WhiteSur-kde
# content with no relationship to the pearOS project itself -- same
# reasoning already used for parchaos-appmenu-gtk-module.
#
# Packaged directly from vinceliuice/WhiteSur-kde's real upstream repo
# (GPL-3.0, confirmed via `gh api repos/vinceliuice/WhiteSur-kde`,
# actively maintained). Verified the real repo tree directly (not
# assumed) before writing this: `plasma/look-and-feel/` contains
# com.github.vinceliuice.WhiteSur (light), .WhiteSur-dark, .WhiteSur-alt,
# .WhiteSurLiquid, and .WhiteSurLiquid-dark -- only the first two
# (matching this project's own existing light/dark pattern) are
# packaged; -alt and the Liquid glass variants are out of scope.
# ==============================================================================

Name:           parchaos-whitesur-lookandfeel
Version:        2026.09.22
Release:        1%{?dist}
Summary:        WhiteSur (macOS-like) Plasma look-and-feel package, light and dark

License:        GPL-3.0-or-later
URL:            https://github.com/vinceliuice/WhiteSur-kde
Source0:        %{url}/archive/refs/heads/master.tar.gz#/WhiteSur-kde-%{version}.tar.gz
BuildArch:      noarch

Requires:       plasma-workspace

%description
The WhiteSur Plasma "Global Theme" (look-and-feel) KPackage, light and dark
variants, from vinceliuice/WhiteSur-kde -- the real upstream dependency
pearOS's own shipped kdeglobals references. Provides the splash screen and
logout/shutdown dialog assets, and lets Plasma's Global Theme page in
System Settings resolve correctly. Scoped to just the look-and-feel
component; none of WhiteSur-kde's own GTK/SDDM/Kvantum/cursor/wallpaper
assets are included here since this project ships its own pearOS-branded
equivalents for all of those.

%prep
# GitHub's branch-archive tarball always extracts to <repo>-<branch>
# regardless of %%{version}, same pattern already established in
# pearos-settings.spec.
%autosetup -n WhiteSur-kde-master

%build
# Nothing to build -- pure QML/JS + static assets, no compiled content.

%install
mkdir -p %{buildroot}%{_datadir}/plasma/look-and-feel
cp -a "plasma/look-and-feel/com.github.vinceliuice.WhiteSur" \
      %{buildroot}%{_datadir}/plasma/look-and-feel/
cp -a "plasma/look-and-feel/com.github.vinceliuice.WhiteSur-dark" \
      %{buildroot}%{_datadir}/plasma/look-and-feel/

%files
%license LICENSE
%doc README.md
%{_datadir}/plasma/look-and-feel/com.github.vinceliuice.WhiteSur/
%{_datadir}/plasma/look-and-feel/com.github.vinceliuice.WhiteSur-dark/

%changelog
* Tue Sep 22 2026 ParchaOS packaging - 2026.09.22-1
- Initial package, in direct response to a real user-reported bug (live
  screenshot showing non-macOS-themed icons and top-bar layout issues):
  pearOS's own shipped skel kdeglobals references
  LookAndFeelPackage=com.github.vinceliuice.WhiteSur-dark, which
  resolved to nothing on Fedora since no package provided it under any
  name. Scoped to just the plasma/look-and-feel/ KPackage directories
  (light + dark), verified directly against the real upstream repo
  tree -- deliberately excludes the rest of WhiteSur-kde's theme suite,
  which this project's own pearOS-branded packages already cover.
