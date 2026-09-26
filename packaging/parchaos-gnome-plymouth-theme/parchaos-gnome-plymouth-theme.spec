# ==============================================================================
# ParchaOS (GNOME) boot splash -- Plymouth's own stock "two-step" module
# (ships with the `plymouth` package itself, no scripting engine
# needed), configured with ParchaOS's own colors/watermark rather than
# a from-scratch scripted theme (a much larger undertaking: animation
# timing, HiDPI handling, password-prompt rendering, etc. that Plymouth
# already solves generically).
#
# Built by taking Fedora's own stock "spinner" theme (part of the
# plymouth-theme-spinner package, GPL-2.0-or-later, confirmed via
# `rpm -q --qf '%{LICENSE}'`) and swapping out only two things:
#   1. watermark.png -- was the Fedora logo + wordmark; replaced with
#      ParchaOS's own real passion-fruit logo (derived from
#      branding/logo/) + "ParchaOS" wordmark, rendered with DejaVu Sans
#      (bundled with this build environment, a free/open font).
#   2. parcha-plymouth.plymouth (was spinner.plymouth) -- same
#      two-step module and layout, background color changed from pure
#      black to 0x1a1a1e (matches parchaos-gtk-theme's MacTahoe-Dark
#      palette / the Calamares slideshow background), Name/Description
#      updated.
#
# Everything else (the 30-frame spinning throbber animation, the
# password-prompt entry/lock/keyboard/capslock icons, the boot
# animation frames) is Fedora's own generic, unbranded, freely
# redistributable stock content -- kept as-is, same standard practice
# most themed Fedora remixes/spins use rather than reinventing a
# throbber animation from scratch.
#
# Not yet wired into profiles/pulsaros/customize.sh's Calamares
# post-install finalization script (parchaos-finalize-install already
# has a guarded `if [ -d .../parcha-plymouth ]` check pointing at this
# exact theme name, added in anticipation of this package) -- wiring
# happens once this package is confirmed building and installing
# correctly.
# ==============================================================================

Name:           parchaos-gnome-plymouth-theme
Version:        2026.09.23
Release:        3%{?dist}
Summary:        ParchaOS (GNOME) Plymouth boot splash theme

License:        GPL-2.0-or-later
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        parchaos-gnome-plymouth-theme-files.tar.gz
BuildArch:      noarch

Requires:       plymouth

%description
ParchaOS's own boot splash theme: Plymouth's stock two-step module with
a dark background matching the GTK/Shell theme's palette, Fedora's own
generic spinning-throbber animation, and ParchaOS's real passion-fruit
logo as the watermark.

%prep
%setup -q -c -n %{name}-%{version}

%install
mkdir -p %{buildroot}%{_datadir}/plymouth/themes
cp -a parcha-plymouth %{buildroot}%{_datadir}/plymouth/themes/

%files
%{_datadir}/plymouth/themes/parcha-plymouth/

%changelog
* Fri Sep 25 2026 ParchaOS packaging - 2026.09.23-3
- Reworded comments and changelog to describe user-reported issues
  instead of quoting them.
* Wed Sep 23 2026 ParchaOS packaging - 2026.09.23-2
- Real user feedback (logo looked slightly off-center): fixed
  at the source in branding/logo/ (see parchaos-global-menu's
  changelog for the full root-cause writeup) and regenerated
  watermark.png from the corrected source.
* Wed Sep 23 2026 ParchaOS packaging - 2026.09.23-1
- Initial theme: Fedora's own stock spinner theme (GPL-2.0-or-later)
  with ParchaOS's own watermark and a dark background color matching
  the GTK/Shell theme. Not yet build-tested or wired into
  customize.sh's default-theme-setting step.
