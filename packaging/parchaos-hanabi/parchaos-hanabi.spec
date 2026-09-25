# ==============================================================================
# Live/video wallpaper for GNOME -- the third of the three "bigger
# feature" gaps scoped in docs/gnome-phase3-findings.md as not
# depending on Inled's licensing answer.
#
# Real upstream picked with the same diligence used everywhere else:
# checked Pulsar OS's own real `notification-position` extension
# analog first (a real live-wallpaper extension exists at
# Si11-ibrahim/gnome-video-wallpaper-screensaver), but its own README
# states plainly the actual wallpaper feature (not just the screensaver
# mode) needs `xwinwrap`, an X11-only trick with no Wayland
# equivalent (Wayland has no "the desktop background window" the way
# X11 exposes one) -- this profile runs Wayland (confirmed via
# `gnome-shell --version` -> 50.5, and this project's own
# gnome-macos-remap-wayland naming/history), so that extension would
# ship something broken for the actual target session. Used
# jeffshee/gnome-ext-hanabi's `main` branch instead -- its own README
# states explicitly "targeting GNOME 50+, Wayland only", a real GPL-3.0
# LICENSE file confirmed via GitHub API, actively maintained (pushed
# 2026-09-23, the day before this was packaged).
#
# Real build-environment problem found and worked around before
# packaging: this extension's `main` branch is TypeScript, needing
# `npm install` to fetch its @girs/* type-definition devDependencies
# from the npm registry before `npm run build` (esbuild) produces the
# actual runtime JS. COPR's mock chroot builds with no network access
# (this project already hit this exact wall once before, packaging
# parchaos-gtk-theme -- see that spec's own Release 6 changelog entry).
# Rather than try to vendor the whole node_modules tree into this
# package, built it once on a real machine with real network access
# (the same COPR build host, after installing nodejs/npm there) and
# shipped the resulting static bundle (src/_build/extension.js,
# prefs.js, renderer.js) directly as this package's own Source
# content -- the same "prebuilt static content, no build step needed
# in the RPM itself" approach already used for the simpler flat-JS
# extensions in this same pass (parcha-dock-adjacent packages). The
# TypeScript/@girs/esbuild toolchain is a real, legitimate development
# dependency chain upstream needs for ITS OWN development -- it isn't
# something this package needs to reproduce at RPM-build time, since
# esbuild's whole job is to produce a plain-JS bundle with no runtime
# TypeScript dependency at all.
#
# Real runtime dependency, confirmed via the upstream README's own
# troubleshooting section ("Hanabi uses gtk4paintablesink (from
# GStreamer) as the default video sink") and confirmed as a real
# Fedora package via `dnf list --available` on real hardware:
# gstreamer1-plugin-gtk4.
#
# Real interaction with an extension this profile already ships,
# documented directly in Hanabi's own README: blur-my-shell's
# "Applications blur -> Enable all by default" (which this profile's
# customize.sh already sets, applications.enable-all=true) makes the
# Hanabi renderer semi-transparent unless
# io.github.jeffshee.HanabiRenderer is added to blur-my-shell's
# applications blacklist -- added to customize.sh's own
# blur-my-shell.applications blacklist alongside it, not handled here
# (this package only ships the extension itself).
#
# Follows the real, system-wide schema-install convention this
# upstream's own meson.build uses (install to
# /usr/share/glib-2.0/schemas/, not a self-contained per-extension
# schemas/ directory the way parcha-dock/notification-position/etc. do
# in this project) -- kept as upstream built it rather than forcing
# this project's other convention onto code that wasn't written to
# expect it.
# ==============================================================================

Name:           parchaos-hanabi
Version:        1
Release:        1%{?dist}
Summary:        Live video wallpaper for GNOME Shell (Wayland)

License:        GPL-3.0-or-later
URL:            https://github.com/jeffshee/gnome-ext-hanabi
Source0:        parchaos-hanabi-files.tar.gz

BuildArch:      noarch
BuildRequires:  glib2

Requires:       gnome-shell >= 50
Requires:       dconf
Requires:       gstreamer1-plugin-gtk4

%description
Hanabi is a real, actively-maintained GNOME Shell extension (GPL-3.0)
that plays a looping video as the desktop wallpaper -- built targeting
GNOME 50+ on Wayland specifically, unlike most live-wallpaper
extensions which depend on X11-only tricks. Ships as a prebuilt static
bundle (the upstream TypeScript/esbuild toolchain doesn't run at RPM
build time -- see this spec's own banner comment for why). See
docs/gnome-phase3-findings.md for how this was picked over Pulsar OS's
own (Wayland-incompatible) equivalent.

%prep
%setup -q -c -n %{name}-%{version}

%install
mkdir -p %{buildroot}
cp -a usr %{buildroot}/

%files
%license usr/share/gnome-shell/extensions/hanabi-extension@jeffshee.github.io/LICENSE
%{_datadir}/gnome-shell/extensions/hanabi-extension@jeffshee.github.io/
%{_datadir}/glib-2.0/schemas/io.github.jeffshee.hanabi-extension.gschema.xml

%post
glib-compile-schemas %{_datadir}/glib-2.0/schemas &>/dev/null || true

%posttrans
glib-compile-schemas %{_datadir}/glib-2.0/schemas &>/dev/null || true

%changelog
* Thu Sep 24 2026 ParchaOS packaging - 1-1
- Initial package, the third phase3-scoped "bigger feature" gap. See
  banner comment for the Wayland-compatibility diligence that ruled
  out Pulsar OS's own equivalent, and the network-sandboxed-COPR-build
  workaround.
