# ==============================================================================
# ParchaOS's global menu — a real macOS-style global application menu in
# the GNOME top bar (Apple-menu-equivalent + per-app File/Edit/View...
# menus + power-off/restart dialogs), forked from Pulsar OS's in-house
# GNOME Shell extension. Real Inled original work (MIT-INLED license per
# the Inled-Pulsar-OS/PKG monorepo's own README license table — not a
# fork of stock GNOME code the way Nautilus/Dash-to-Dock are), sourced
# directly from that monorepo (no separate dedicated repo/submodule for
# this one — confirmed via the real repo tree before writing this).
#
# SCOPED DELIBERATELY NARROW, real security decision (2026-09-23): the
# real upstream package bundles this extension together with THREE
# genuinely unrelated, higher-risk pieces that this spec does NOT
# include:
#   1. A custom PAM-based lock-screen ("pulsaros-lock" PAM service +
#      `pamtester`), whose real Debian postinst does
#      `chmod u+s /usr/bin/pamtester` -- a SYSTEM-WIDE setuid-root bit
#      on a generic PAM-testing binary, just so this one extension's
#      lock screen can check passwords. That's a real, unscoped
#      privilege-escalation surface (any user, any purpose, not just
#      this lock screen) -- not something to blindly replicate. The
#      extension's own JS has real try/catch error handling around
#      every pamtester call, so shipping the JS as-is without the
#      setuid binary/PAM service fails this ONE feature safely at
#      runtime (no crash) rather than working -- lock-screen password
#      auth is a known, deliberately deferred gap, not an oversight.
#   2. A large pile of Arch/Debian-specific hibernation setup baked into
#      the same package's postinst: mkinitcpio HOOKS= editing
#      (Arch-only, meaningless on Fedora's dracut), NVIDIA
#      hibernate-resume modprobe options, and -- most importantly --
#      automatically REWRITING GRUB_CMDLINE_LINUX_DEFAULT and
#      re-running grub-mkconfig, plus editing rEFInd configs directly.
#      This project's own GRUB/dracut/Secure-Boot boot chain (the KDE
#      repo's docs/phase1-findings.md and phase4-findings.md) took
#      real, hard-won engineering to get right -- silently letting an
#      unrelated menu-bar extension's install script rewrite kernel
#      boot parameters is a real destabilization risk this project is
#      not taking on.
#   3. A polkit policy + helper binaries for power actions this
#      extension doesn't strictly need for its core menu functionality
#      (it already calls `systemctl reboot/poweroff/suspend` directly
#      via GLib.spawn_command_line_async, which works fine under a
#      normal logind session without any extra polkit grant).
#
# Renamed "Parcha Menu" / parchaos-global-menu@parchaos.org (from
# "Pulsar OS Global Menu" / pulsaros-global-menu@inled.es) for
# ParchaOS's own product identity, same reasoning as Parcher and Parcha
# Dock. Also swaps the extension's own top-left panel icon
# (pulsar-white-sf.png, Pulsar OS's own branding) for ParchaOS's real,
# licensed passion-fruit logo (branding/logo/parcha-logo-white.png,
# already committed to this repo, CC BY 3.0 attributed in
# branding/logo/CREDITS.md).
# ==============================================================================

Name:           parchaos-global-menu
Version:        1.0.134
Release:        2%{?dist}
Summary:        Parcha Menu — ParchaOS's macOS-style global application menu for GNOME Shell

License:        MIT
URL:            https://github.com/Inled-Pulsar-OS/PKG
Source0:        extension.js
Source1:        metadata.json
Source2:        stylesheet.css
Source3:        org.gnome.shell.extensions.parchaos-global-menu.gschema.xml
Source4:        parchaos-menu-icon.png

BuildArch:      noarch

BuildRequires:  glib2
Requires:       gnome-shell >= 45

%description
Parcha Menu is ParchaOS's real macOS-style global application menu for
the GNOME top bar: an Apple-menu equivalent plus per-app File/Edit/
View/Window/Help menus and power-off/restart dialogs. Forked from
Pulsar OS's in-house GNOME Shell extension, scoped narrowly to just the
menu-bar functionality — this package deliberately does NOT include
upstream's setuid-root lock-screen authentication helper or its
GRUB/hibernation system-mutation logic (see this spec's own banner
comment for the full reasoning). Lock-screen password authentication is
a known, deliberately deferred feature gap, not a bug.

%prep
mkdir -p src
cd src
cp %{SOURCE0} %{SOURCE1} %{SOURCE2} %{SOURCE3} %{SOURCE4} .

# ParchaOS branding rebrand (see banner comment above).
sed -i \
    -e "s/pulsaros-global-menu@inled\.es/parchaos-global-menu@parchaos.org/g" \
    -e 's/"name": "Pulsar OS Global Menu"/"name": "Parcha Menu"/' \
    -e 's#"url": "https://inled\.es"#"url": "https://github.com/alexgalicea/parchaos-gnome"#' \
    -e 's/org\.gnome\.shell\.extensions\.pulsaros-global-menu/org.gnome.shell.extensions.parchaos-global-menu/g' \
    metadata.json extension.js org.gnome.shell.extensions.parchaos-global-menu.gschema.xml
sed -i "s/pulsar-white-sf\.png/parchaos-menu-icon.png/" extension.js

# Real bug found via a real boot test (2026-09-23): the extension's own
# JS hardcodes the literal string "Finder" as the idle-state app name
# (shown in the menu bar itself when no window has focus, matching real
# macOS's "Finder is the default app" behavior) -- 13 occurrences,
# every one the same concept (display label + the matching
# `appName === "Finder"` state comparison), confirmed via a full grep
# before this blanket rename so it wouldn't accidentally touch an
# unrelated meaning of the word. The earlier UUID/schema-only sed above
# missed this entirely since it wasn't part of any identifier string.
sed -i 's/Finder/Parcher/g' extension.js

%build
mkdir -p schemas
glib-compile-schemas --targetdir=schemas src 2>/dev/null || true
cd src
mkdir -p schemas
cp org.gnome.shell.extensions.parchaos-global-menu.gschema.xml schemas/
glib-compile-schemas schemas/

%install
UUID=parchaos-global-menu@parchaos.org
DEST=%{buildroot}%{_datadir}/gnome-shell/extensions/$UUID
mkdir -p "$DEST/schemas"
install -m 0644 src/extension.js "$DEST/"
install -m 0644 src/metadata.json "$DEST/"
install -m 0644 src/stylesheet.css "$DEST/"
install -m 0644 src/parchaos-menu-icon.png "$DEST/"
install -m 0644 src/schemas/org.gnome.shell.extensions.parchaos-global-menu.gschema.xml "$DEST/schemas/"
install -m 0644 src/schemas/gschemas.compiled "$DEST/schemas/"

%files
%{_datadir}/gnome-shell/extensions/parchaos-global-menu@parchaos.org/

%changelog
* Wed Sep 23 2026 ParchaOS packaging - 1.0.134-2
- Real trademark bug found via a real boot test: the shipped menu bar
  literally read "Finder File Edit View Go Window Help" on the idle
  desktop -- the earlier UUID/schema rename missed 13 hardcoded
  "Finder" string literals inside extension.js entirely (not part of
  any identifier, so the earlier sed's scope never touched them). Fixed
  with a verified-safe blanket word rename.
* Wed Sep 23 2026 ParchaOS packaging - 1.0.134-1
- Initial package, real upstream source (Inled-Pulsar-OS/PKG monorepo,
  MIT-INLED license), rebranded "Parcha Menu". Deliberately scoped to
  exclude upstream's setuid-root lock-screen auth helper and
  GRUB/hibernation system-mutation postinst logic — see banner comment.
  Not yet build-tested.
