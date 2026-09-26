# ==============================================================================
# ParchaOS (GNOME) desktop meta-package -- exists for exactly one reason:
# real end-user feedback (2026-09-23) that `dnf update` alone does NOT
# pick up packages added to this profile after a user's already installed
# it. That's correct, standard dnf behavior -- `update`/`upgrade` only
# touches packages already installed; it never installs something new
# just because it now exists in an enabled repo. This project's own ISO
# build (engine/build-iso.sh Phase 5) installs every
# profiles/pulsaros/packages.sh entry as an individually, directly
# requested package -- there was no single thing tying them together
# that a later `dnf update` could expand.
#
# The fix is the standard RPM/dnf pattern for exactly this problem (the
# same shape as Debian/Ubuntu's `ubuntu-desktop`, or Fedora's own
# `@workstation-product-environment` comps group, just done as a plain
# meta-package instead of a comps group since this project's engine
# doesn't have comps.xml infrastructure and retrofitting one is a much
# bigger change than this deserves): a package with no real content of
# its own, just a `Requires:` line naming every package this profile
# ships. Once THIS package is installed on a real system, bumping its
# Release with an EXPANDED Requires: list (whenever a new package gets
# added to packages.sh) means a plain `sudo dnf update` on that real
# system will pull the new dependency in automatically as part of the
# same transaction that upgrades this package -- genuine "OTA blanket
# update" behavior, no manual `dnf install <new-package-name>` needed
# going forward.
#
# MAINTENANCE: whenever profiles/pulsaros/packages.sh gains or loses an
# entry, update the Requires: list below to match and bump Release. The
# two lists are NOT auto-generated from each other (deliberately kept
# simple rather than adding build-pipeline machinery for this) -- it's
# on whoever edits packages.sh to keep this spec in sync, same as any
# other two-places-must-agree convention already in this project (e.g.
# a package's %files list vs. what it actually installs).
#
# Deliberately excludes PROFILE_NVIDIA_PACKAGES (akmod-nvidia and
# friends) -- those are opt-in via --nvidia at build time for a real
# hardware-dependent reason (no point requiring NVIDIA kernel modules on
# a machine that doesn't have an NVIDIA GPU), not part of "the desktop".
#
# Also deliberately excludes parchaos-gnome-calamares-config, even
# though it IS one of packages.sh's PROFILE_REPO_PACKAGES entries. Real
# bug found 2026-09-24 (see docs/gnome-phase2-findings.md's sibling
# incident, fixed here): parchaos-gnome-calamares-config Requires:
# calamares, and this meta-package used to Require:
# parchaos-gnome-calamares-config in turn. The Calamares-removal
# shellprocess step (parchaos-remove-calamares-app, the very last exec
# step of a fresh install -- see
# packaging/parchaos-gnome-calamares-config's settings.conf) runs
# `dnf -y remove calamares --noautoremove` to get rid of the installer
# app icon after a real disk install finishes. Because of the Requires
# chain above, that single removal cascaded through
# parchaos-gnome-calamares-config and then through THIS package too,
# silently deregistering parchaos-desktop itself on every fresh
# install (caught live on real hardware: `dnf remove calamares` pulled
# parchaos-desktop into the same removal transaction). Calamares and
# its config package are install-time-only tooling with no purpose on
# an installed system, so they don't belong in the OTA meta-package's
# Requires: list at all, unlike everything else here which the user
# actually keeps using after install.
# ==============================================================================

Name:           parchaos-desktop
Version:        2026.09.23
Release:        18%{?dist}
Summary:        ParchaOS (GNOME) desktop meta-package -- installing/updating this pulls in the full profile

License:        NOASSERTION
URL:            https://github.com/alexgalicea/parchaos-gnome
BuildArch:      noarch
Requires(post): dconf
Requires(postun): dconf

Requires:       parchaos-finder
Requires:       parchaos-dock
Requires:       parchaos-global-menu
Requires:       parchaos-gtk-theme
Requires:       parchaos-icon-theme
Requires:       parchaos-gnome-plymouth-theme
Requires:       parchaos-gnome-wallpaper
Requires:       parchaos-keyboard-remap
Requires:       parchaos-cloud
Requires:       parchaos-focus-schedule
Requires:       parchaos-yin-yang
Requires:       parchaos-tmog
Requires:       parchaos-browser
Requires:       parchaos-app-renames
Requires:       parchaos-notification-position
Requires:       parchaos-magic-lamp-effect
Requires:       parchaos-wiggle
Requires:       parchaos-ui-tune
Requires:       parchaos-gdm-logo
Requires:       parchaos-hblock
Requires:       parchaos-hanabi
Requires:       parchaos-desktop-icons
Requires:       parchaos-launcher
Requires:       parchaos-controls
Requires:       parchaos-settings

%description
A real, no-content meta-package: installing it (or updating it) simply
pulls in every package this ParchaOS GNOME profile ships, via a plain
Requires: list kept in sync with profiles/pulsaros/packages.sh. Exists
so a plain `sudo dnf update` becomes a genuine "OTA" mechanism for this
project's own packages going forward -- without this, `dnf update`
never installs a package that's new since the user's own install, only
upgrades ones already present. See this spec's own banner comment for
the full reasoning and the maintenance rule (keep Requires: in sync
with packages.sh, bump Release on every change).

%prep
%build
%install
mkdir -p %{buildroot}%{_sysconfdir}/dconf/db/local.d
# Desktop defaults that must also reach existing installs over OTA
# (profiles/pulsaros/customize.sh only affects freshly built ISOs).
# Default extensions for new user accounts. Previously written only by the
# ISO build (customize.sh), so older installs kept an outdated list. Plain
# (non-%%config) file so RPM replaces the old unowned copy on upgrade.
# hanabi-extension is installed but deliberately not enabled: with no
# video configured it fails and retries at every login.
# disable-extension-version-validation lets extensions whose metadata
# stops at an older GNOME version (e.g. notification-position) load.
cat > %{buildroot}%{_sysconfdir}/dconf/db/local.d/00-parchaos-extensions <<'DCONF'
[org/gnome/shell]
enabled-extensions=['parcha-dock@parchaos.org', 'parchaos-global-menu@parchaos.org', 'parchaos-launcher@parchaos.org', 'parchaos-controls@parchaos.org', 'user-theme@gnome-shell-extensions.gcampax.github.com', 'xremap@k0kubun.com', 'appindicatorsupport@rgcjonas.gmail.com', 'blur-my-shell@aunetx', 'just-perfection-desktop@just-perfection', 'no-overview@fthx', 'notification-banner-reloaded@marcinjakubowski.github.com', 'compiz-alike-magic-lamp-effect@hermes83.github.com', 'wiggle@mechtifs', 'gnome-ui-tune@itstime.tech', 'ding@rastersoft.com']
disable-user-extensions=false
disable-extension-version-validation=true
DCONF

cat > %{buildroot}%{_sysconfdir}/dconf/db/local.d/05-parchaos-desktop <<'DCONF'
# GNOME hides "Log Out" from the system menu on single-user machines;
# a desktop OS should always offer it.
[org/gnome/shell]
always-show-log-out=true

# blur-my-shell's application blur draws a rectangular blurred copy of
# the wallpaper behind each window, with one fixed corner radius. Window
# radii differ per toolkit (libadwaita, GTK3, Chromium), so the blurred
# square showed outside the rounded top corners. Windows are fully
# opaque here (opacity=255), so the blur was only ever visible there.
[org/gnome/shell/extensions/blur-my-shell/applications]
blur=false
DCONF

%post
dconf update >/dev/null 2>&1 || :

%postun
dconf update >/dev/null 2>&1 || :

%files
%{_sysconfdir}/dconf/db/local.d/00-parchaos-extensions
%{_sysconfdir}/dconf/db/local.d/05-parchaos-desktop

%changelog
* Fri Sep 25 2026 ParchaOS packaging - 2026.09.23-18
- Require parchaos-settings (ParchaOS Settings app).
* Fri Sep 25 2026 ParchaOS packaging - 2026.09.23-17
- Ship the default enabled-extensions list (00-parchaos-extensions),
  previously written only by the ISO build: older installs gave new user
  accounts just the dock, global menu and theme. customize.sh no longer
  writes it.
* Fri Sep 25 2026 ParchaOS packaging - 2026.09.23-16
- Require parchaos-controls, the new Parcha Controls control center.
* Fri Sep 25 2026 ParchaOS packaging - 2026.09.23-15
- Require parchaos-launcher, the new full-screen app launcher.
* Fri Sep 25 2026 ParchaOS packaging - 2026.09.23-14
- Turn off blur-my-shell application blur: its rectangular blur showed
  behind the rounded top corners of windows (worst in Chromium).
* Fri Sep 25 2026 ParchaOS packaging - 2026.09.23-13
- Drop pafari: Parcha Browser replaces it (and Obsoletes it).
* Fri Sep 25 2026 ParchaOS packaging - 2026.09.23-12
- Ship a dconf default so existing installs get it over OTA:
  always-show-log-out=true (GNOME hides Log Out on single-user machines;
  found when the user couldn't find a way to log out).
* Fri Sep 25 2026 ParchaOS packaging - 2026.09.23-11
- Require parchaos-keyboard-remap, the new name of parchaos-macos-remap.
* Fri Sep 25 2026 ParchaOS packaging - 2026.09.23-10
- Added Requires: parchaos-desktop-icons -- real Desktop Icons NG,
  closing another gap from the earlier Pulsar-config extension diff.
* Thu Sep 24 2026 ParchaOS packaging - 2026.09.23-9
- Added Requires: parchaos-hanabi -- the third and final phase3-scoped
  "bigger feature" gap, real live/video wallpaper for GNOME Wayland.
* Thu Sep 24 2026 ParchaOS packaging - 2026.09.23-8
- Added Requires: parchaos-hblock -- real, independent hosts-file
  ad-blocker, one of the phase3-scoped "bigger feature" gaps that
  doesn't depend on Inled's licensing answer.
* Thu Sep 24 2026 ParchaOS packaging - 2026.09.23-7
- Added Requires: parchaos-gdm-logo -- real user feedback, GDM login
  screen still showed Fedora's logo.
* Thu Sep 24 2026 ParchaOS packaging - 2026.09.23-6
- Added Requires: parchaos-magic-lamp-effect, parchaos-wiggle,
  parchaos-ui-tune -- three more real, licensed extensions matching
  Pulsar OS's own config.
* Thu Sep 24 2026 ParchaOS packaging - 2026.09.23-5
- Added Requires: parchaos-notification-position (real user priority
  request), packaging/parchaos-notification-position/.
* Thu Sep 24 2026 ParchaOS packaging - 2026.09.23-4
- Added Requires: parchaos-app-renames (packaging/parchaos-app-renames/),
  the new Loupe/Clocks/Geary display-name overrides.
* Thu Sep 24 2026 ParchaOS packaging - 2026.09.23-3
- Added Requires: parchaos-browser (packaging/parchaos-browser/), the
  new Chromium-based browser rebrand added to packages.sh.
* Thu Sep 24 2026 ParchaOS packaging - 2026.09.23-2
- Dropped Requires: parchaos-gnome-calamares-config. Real bug found on
  real hardware: it cascade-removed this whole meta-package (and
  parchaos-gnome-calamares-config itself) the moment a fresh install's
  finalize step ran `dnf remove calamares`, since calamares config
  Requires calamares. Install-time-only tooling doesn't belong in this
  meta-package's Requires: list. See the banner comment above.
* Wed Sep 23 2026 ParchaOS packaging - 2026.09.23-1
- Initial package, in direct response to real user feedback that
  `dnf update` alone doesn't pick up newly-added ParchaOS packages.
  Requires: list matches profiles/pulsaros/packages.sh's
  PROFILE_REPO_PACKAGES as of this date (14 packages).
