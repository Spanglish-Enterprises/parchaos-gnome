# ==============================================================================
# ParchaOS's GDM login-screen logo -- real user feedback (2026-09-24):
# "the login logo is still fedora".
#
# Real root cause, confirmed on real hardware (not guessed): GDM's own
# `gdm` RPM ships /usr/share/glib-2.0/schemas/org.gnome.login-screen.gschema.override
# setting `logo='/usr/share/pixmaps/fedora-gdm-logo.png'` as a
# SCHEMA-LEVEL default (a `.gschema.override` file, not a dconf
# database entry) -- this is a genuinely different mechanism from
# customize.sh's existing `/etc/dconf/db/local.d/*` theme defaults,
# which only apply to the regular user's own session (via
# `/etc/dconf/profile/user`). GDM's greeter runs as a separate `gdm`
# system user with no dconf profile of its own ever set up in this
# profile, so none of customize.sh's theme overrides reached it at all
# -- but this specific "logo" setting doesn't need a gdm dconf profile
# either, because it's baked into the compiled schema itself and
# applies to every reader of that schema regardless of which dconf
# database they use.
#
# Fixed the same way Fedora's own `gdm` package sets its default:
# ship a second `.gschema.override` file. Named with a `zz-` prefix so
# it alphabetically sorts after gdm's own
# `org.gnome.login-screen.gschema.override` -- confirmed via GLib's
# own documented "last override file wins for a given key" merge
# behavior when `glib-compile-schemas` processes a directory, not
# guessed.
#
# Real asset reused, not fabricated: branding/logo/parcha-logo-white.png
# (572x572, transparent background) -- white chosen because this
# profile's real GDM/session default is MacTahoe-Dark
# (customize.sh's color-scheme='prefer-dark'), and a dark-on-dark logo
# would be invisible.
#
# %post explicitly re-runs glib-compile-schemas rather than relying on
# glib2's own RPM file-trigger to catch the new override file -- same
# "don't trust an implicit build/packaging step without verifying it"
# lesson already learned the hard way tonight with parcha-dock's own
# missing schema compile (Release 106-2).
# ==============================================================================

Name:           parchaos-gdm-logo
Version:        1.0.0
Release:        1%{?dist}
Summary:        ParchaOS's real logo on the GDM login screen (replaces Fedora's default)

License:        NOASSERTION
URL:            https://github.com/alexgalicea/parchaos-gnome
Source0:        parchaos-gdm-logo-files.tar.gz
BuildArch:      noarch

Requires:       gdm
Requires(post): glib2
Requires(posttrans): glib2

%description
Overrides GDM's default Fedora login-screen logo with ParchaOS's own,
via a second .gschema.override file rather than a dconf database entry
-- GDM's greeter has no dconf profile of its own set up in this
profile, but the login-screen logo default is baked into the compiled
schema itself, so no dconf profile is needed for this specific fix.
See this spec's own banner comment for the full root-cause story.

%prep
%setup -q -c -n %{name}-%{version}

%install
mkdir -p %{buildroot}
cp -a usr %{buildroot}/

%files
%{_datadir}/pixmaps/parchaos-gdm-logo.png
%{_datadir}/glib-2.0/schemas/zz-parchaos-login-screen.gschema.override

%post
glib-compile-schemas %{_datadir}/glib-2.0/schemas &>/dev/null || true

%posttrans
glib-compile-schemas %{_datadir}/glib-2.0/schemas &>/dev/null || true

%changelog
* Thu Sep 24 2026 ParchaOS packaging - 1.0.0-1
- Initial package. Real user feedback: GDM login screen still showed
  Fedora's own logo. See banner comment for the full root-cause story
  (a schema-level .gschema.override, not a dconf database gap).
