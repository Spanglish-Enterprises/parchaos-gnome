# ==============================================================================
# ParchaOS (GNOME) default desktop wallpaper -- a single 4K (3840x2160)
# PNG, generated from branding/logo/: a dark vertical gradient (0x16161e
# to 0x26262e, matching parchaos-gtk-theme's MacTahoe-Dark palette) with
# ParchaOS's real passion-fruit logo centered as a very subtle (~6%
# opacity) watermark, not a loud centerpiece -- meant to look like a
# clean dark desktop background first, ParchaOS-branded second.
#
# Applied as both the light and dark picture-uri (GNOME only shows one
# wallpaper regardless of system theme unless picture-uri and
# picture-uri-dark differ; this image suits both, so both keys point
# at the same file) via customize.sh's existing dconf mechanism.
# ==============================================================================

Name:           parchaos-gnome-wallpaper
Version:        2026.09.23
Release:        3%{?dist}
Summary:        ParchaOS (GNOME) default desktop wallpaper

License:        NOASSERTION
URL:            https://github.com/alexgalicea/parchaos-gnome
Source0:        parchaos-gnome-wallpaper-files.tar.gz
BuildArch:      noarch

%description
ParchaOS's default desktop wallpaper: a dark gradient background with
ParchaOS's real passion-fruit logo as a subtle centered watermark,
generated from branding/logo/ in this repo.

%prep
%setup -q -c -n %{name}-%{version}

%install
mkdir -p %{buildroot}
cp -a usr %{buildroot}/

%files
%{_datadir}/backgrounds/parchaos/

%changelog
* Fri Sep 25 2026 ParchaOS packaging - 2026.09.23-3
- Reworded comments and changelog to describe user-reported issues
  instead of quoting them.
* Wed Sep 23 2026 ParchaOS packaging - 2026.09.23-2
- Real user feedback (logo looked slightly off-center): fixed
  at the source in branding/logo/ (see parchaos-global-menu's
  changelog for the full root-cause writeup) and regenerated the
  wallpaper's watermark from the corrected source.
* Wed Sep 23 2026 ParchaOS packaging - 2026.09.23-1
- Initial wallpaper: dark gradient with a subtle logo watermark,
  generated from branding/logo/. Not yet build-tested or wired into
  customize.sh.
