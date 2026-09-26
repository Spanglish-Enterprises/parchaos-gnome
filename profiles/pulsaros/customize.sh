# ==============================================================================
# pulsaros profile — branding/session customization (sourced by
# engine/build-iso.sh)
# ==============================================================================
# Defines profile_customize(), called by the engine in Phase 5.5, after
# PROFILE_REPO_PACKAGES are installed. Skipped entirely by --skip-branding
# (see engine/build-iso.sh) — used for the unbranded-baseline checkpoint,
# same methodology the pearos (KDE) profile used successfully in its own
# Phase 1. Kept deliberately minimal for now: only DE-agnostic identity +
# the one GNOME-specific piece needed for a passwordless live session to
# actually work (GDM autologin). Theme/branding wiring (GTK theme, GNOME
# Shell theme/extensions, Nautilus branding, etc.) gets added here once
# those pieces are actually ported — see profiles/pearos/customize.sh for
# the shape that'll eventually take.
# ==============================================================================

profile_customize() {
    # Same real bug class already found/fixed in the KDE profile: without
    # this, /etc/os-release stays untouched Fedora, which a real
    # install+reboot test found showing up verbatim in the installed
    # system's own GRUB boot menu (GRUB's BLS title generation reads
    # os-release's PRETTY_NAME).
    echo "--- Branding /etc/os-release as ParchaOS ---"
    sed -i \
        -e 's|^NAME=.*|NAME="ParchaOS"|' \
        -e 's|^PRETTY_NAME=.*|PRETTY_NAME="ParchaOS 44"|' \
        -e 's|^ID=.*|ID=parchaos|' \
        -e 's|^ANSI_COLOR=.*|ANSI_COLOR="0;38;2;93;0;147"|' \
        -e 's|^HOME_URL=.*|HOME_URL="https://github.com/alexgalicea/parchaos-gnome"|' \
        "$ROOTFS_TARGET/etc/os-release"
    grep -q '^ID_LIKE=' "$ROOTFS_TARGET/etc/os-release" || \
        echo 'ID_LIKE=fedora' >> "$ROOTFS_TARGET/etc/os-release"

    echo "--- Setting default hostname: parchaos ---"
    echo "parchaos" > "$ROOTFS_TARGET/etc/hostname"

    # NOTE: unlike an earlier draft of this file, deliberately NOT
    # hand-writing /etc/gdm/custom.conf's autologin section here. The
    # KDE (pearos) profile's own real bug/fix for this exact problem
    # (passwordless live-session login) was resolved entirely by setting
    # PROFILE_LIVESYS_SESSION correctly in profile.conf — livesys-scripts'
    # own sessions.d/livesys-{kde,gnome} hook is what actually writes the
    # display manager's autologin config at first boot, and the KDE
    # profile never needed to duplicate that by hand. Trusting the same
    # mechanism here (PROFILE_LIVESYS_SESSION="gnome") rather than
    # guessing at GDM's config format pre-emptively — verify via a real
    # boot test before adding anything manual here, per this project's
    # own established pattern of not assuming a fix works without
    # checking.

    # Enabling ParchaOS's GNOME Shell extensions by default. GNOME Shell
    # extensions are inert until listed in org.gnome.shell's
    # "enabled-extensions" gsettings key — real, standard Fedora/GNOME
    # system-wide-default mechanism (GNOME's own admin documentation,
    # not guessed): a dconf "system" database compiled from
    # /etc/dconf/db/local.d/*, layered under the user's own db via
    # /etc/dconf/profile/user, compiled with `dconf update`. Extensions
    # list starts with just Parcha Dock (packages.sh) — more UUIDs get
    # appended here as more GNOME Shell extensions are ported (blur,
    # global menu, etc.), matching the KDE profile's own pattern of
    # growing customize.sh alongside packages.sh.
    echo "--- Enabling ParchaOS's GNOME Shell extensions by default ---"
    mkdir -p "$ROOTFS_TARGET/etc/dconf/profile"
    cat > "$ROOTFS_TARGET/etc/dconf/profile/user" <<EOF
user-db:user
system-db:local
EOF
    mkdir -p "$ROOTFS_TARGET/etc/dconf/db/local.d"
    # user-theme@gnome-shell-extensions.gcampax.github.com is the real,
    # stock Fedora extension (gnome-shell-extension-user-theme package,
    # UUID confirmed via its own installed metadata.json on the build VM, not
    # assumed) -- GNOME Shell itself only reads the Shell theme's own
    # gnome-shell/ subdirectory through this extension; GTK apps read
    # gtk-theme directly and don't need it.
    # Real gap found 2026-09-24 (real user feedback: keep auditing the
    # theming): cross-checked this profile's extension list against
    # Pulsar OS's own real dconf defaults (Inled-Pulsar-OS/PKG's
    # pulsaros-gnome/etc/dconf/db/local.d/00-pulsaros-theme, fetched
    # directly) -- they ship ~15 extensions for their full desktop
    # polish; this profile only shipped 5. Four of Pulsar's real
    # extensions are, confirmed via `dnf list --available` on real
    # hardware, genuine official Fedora packages with the exact same
    # UUIDs Pulsar OS's own config uses (verified via each extension's
    # real installed metadata.json, not assumed):
    # appindicatorsupport@rgcjonas.gmail.com, blur-my-shell@aunetx,
    # just-perfection-desktop@just-perfection, no-overview@fthx. Added
    # all four (packages.list). The rest of Pulsar's list
    # (compiz-alike-magic-lamp-effect, notification-position, wiggle,
    # gnome-ui-tune, ding) has no Fedora package -- would need
    # individual packaging from extensions.gnome.org the way parcha-dock
    # was, not done in this pass.
    cat > "$ROOTFS_TARGET/etc/dconf/db/local.d/00-parchaos-extensions" <<EOF
[org/gnome/shell]
always-show-log-out=true
enabled-extensions=['parcha-dock@parchaos.org', 'parchaos-global-menu@parchaos.org', 'user-theme@gnome-shell-extensions.gcampax.github.com', 'xremap@k0kubun.com', 'appindicatorsupport@rgcjonas.gmail.com', 'blur-my-shell@aunetx', 'just-perfection-desktop@just-perfection', 'no-overview@fthx', 'notification-banner-reloaded@marcinjakubowski.github.com', 'compiz-alike-magic-lamp-effect@hermes83.github.com', 'wiggle@mechtifs', 'gnome-ui-tune@itstime.tech', 'ding@rastersoft.com']
# Real bug found live on real hardware 2026-09-25 (user report: the
# hanabi extension popped up automatically at login): hanabi-extension@jeffshee.github.io launches its
# renderer at enable-time regardless of the change-wallpaper toggle
# (confirmed false by default) or video-path (empty by default) --
# with nothing configured, it repeatedly fails at login with
# `GstPlay.PlayError: Failed to play undefined` (a literal JS
# `undefined` video path), retrying every couple seconds. This project
# has no default video asset to ship (a real video file is a real
# licensing/size question this project hasn't solved), so rather than
# ship a live-wallpaper extension that visibly fails on every fresh
# install, it's deliberately NOT in the default enabled-extensions list
# above -- parchaos-hanabi is still installed (packages.sh), just not
# auto-enabled. A user who wants it can enable it and pick a real video
# file via its own preferences (GNOME Extensions app) themselves.
disable-user-extensions=false
# Real compatibility gap found 2026-09-24 (packaging/parchaos-notification-position/'s
# own spec has the full story): that extension's metadata.json only
# declares shell-version support through 49, but this profile's real
# GNOME Shell is 50.5 (confirmed via `gnome-shell --version` on real
# hardware) -- without this, GNOME Shell silently refuses to load it.
# Pulsar OS's own real config already sets this same key (same
# 00-pulsaros-theme fetch used for button-layout/blur-my-shell), so
# it's general hardening against the same class of gap for anything
# added later too, not just this one extension.
disable-extension-version-validation=true
EOF
    # Real, working tuning values -- Pulsar OS's own real defaults for
    # these exact same extensions (same fetch as above), adapted to
    # this profile's own dock (blur-my-shell's "dash-to-dock" module
    # blurs behind whatever real Dash-to-Dock-derived extension is
    # active -- parcha-dock is a real Dash-to-Dock fork with the same
    # internal structure, confirmed this integration target is correct
    # by extension, not re-verified pixel-for-pixel). Dropped Pulsar's
    # kiwimenu/support-notifier-* keys -- this profile doesn't ship
    # kiwimenu, and the notifier keys are just Just Perfection's own
    # internal "have I shown this changelog" tracking, not a real
    # user-facing setting.
    cat > "$ROOTFS_TARGET/etc/dconf/db/local.d/02-parchaos-extensions-tuning" <<EOF
[org/gnome/shell/extensions/blur-my-shell/appfolder]
brightness=0.6
sigma=30

[org/gnome/shell/extensions/blur-my-shell/applications]
blur=true
blur-on-overview=false
corner-when-maximized=true
dynamic-opacity=false
enable-all=true
opacity=255
sigma=23
# Real, documented interaction: with enable-all=true above (every app
# blurred by default), Hanabi's own renderer window (the live-wallpaper
# extension, packaging/parchaos-hanabi/) gets caught by that blanket
# rule and goes semi-transparent -- Hanabi's own README says exactly
# this and names the fix (its renderer's real app ID). The
# ding/DING/org.gnome.Shell.Extensions.DING entries match Pulsar OS's
# own real, working config exactly (same fetch used for the
# button-layout/blur-my-shell defaults throughout this project) --
# Desktop Icons NG's own desktop-grid window needs the same exception,
# not re-derived independently here.
blacklist=['io.github.jeffshee.HanabiRenderer', 'ding', 'DING', 'org.gnome.Shell.Extensions.DING', '*ding*', '*DING*']

[org/gnome/shell/extensions/blur-my-shell/dash-to-dock]
blur=true
brightness=0.64
override-background=true
pipeline='pipeline_default_rounded'
sigma=0
static-blur=true
style-dash-to-dock=2
unblur-in-overview=true

[org/gnome/shell/extensions/blur-my-shell/panel]
blur=false
brightness=0.6
corner-radius=0
force-light-text=false
override-background=false
pipeline='pipeline_default'
sigma=30

[org/gnome/shell/extensions/blur-my-shell/window-list]
brightness=0.6
sigma=30

[org/gnome/shell/extensions/just-perfection]
activities-button=false
clock-menu-position=1
clock-menu-position-offset=12
panel-size=32
panel-button-padding-size=10
panel-indicator-padding-size=10
animation=1
startup-status=0
dash-icon-size=0

# Default: top-right, sliding in from the right edge (matching the
# reference desktop's notification behavior), with a small edge inset
# rather than flush-to-corner. anchor-vertical=0/anchor-horizontal=1
# confirmed against the extension's own real extension.js source
# (0=top/1=bottom/2=center for vertical, 0=left/1=right/2=center for
# horizontal -- not guessed from the schema's bare integers alone).
[org/gnome/shell/extensions/notification-banner-reloaded]
anchor-vertical=0
anchor-horizontal=1
padding-vertical=8
padding-horizontal=8
animation-direction=1
EOF
    # ParchaOS's Tahoe-styled GTK/Shell theme and icon theme, both
    # confirmed via `rpm -qlp` on their real built RPMs (not assumed):
    # /usr/share/themes/MacTahoe-Dark and
    # /usr/share/icons/{MacTahoe,MacTahoe-light,MacTahoe-dark} -- the
    # "-dark" icon variant pairs with the dark GTK theme.
    # Real gaps found 2026-09-24 (real user feedback: the terminal
    # didn't follow the top-left traffic-light button rules),
    # cross-checked directly against Pulsar OS's own real, working
    # dconf defaults (Inled-Pulsar-OS/PKG's
    # pulsaros-gnome/etc/dconf/db/local.d/00-pulsaros-theme, fetched
    # directly, not guessed) since they've already solved this exact
    # problem:
    #   - button-layout was never set at all, so GNOME fell back to
    #     Fedora's stock 'appmenu:close' -- a single close button on
    #     the RIGHT, no traffic lights, no minimize/maximize. This is
    #     a WM/Mutter-level setting, not something a GTK theme's CSS
    #     can control on its own -- a theme can recolor/reshape the
    #     buttons GNOME decides to draw, but not which ones or which
    #     side. Matches Pulsar OS's own real value exactly.
    #   - cursor-theme was never set, even though MacTahoe-dark
    #     genuinely bundles a real cursors/ directory (confirmed via
    #     `find /usr/share/icons -iname cursors` on real hardware,
    #     not assumed) -- it was just never wired into dconf, so the
    #     system silently fell back to the stock Adwaita cursor.
    #   - color-scheme was never set. gtk-theme only affects legacy
    #     GTK3 CSS theme selection; GTK4/libadwaita apps (Nautilus,
    #     Calculator, Terminal's newer libadwaita-based preferences
    #     dialogs, etc.) pick light/dark purely from color-scheme,
    #     independent of gtk-theme.
    cat > "$ROOTFS_TARGET/etc/dconf/db/local.d/01-parchaos-theme" <<EOF
[org/gnome/desktop/interface]
gtk-theme='MacTahoe-Dark'
icon-theme='MacTahoe-dark'
cursor-theme='MacTahoe-dark'
color-scheme='prefer-dark'
# Real gap found via a live reference-desktop comparison 2026-09-25: the
# top bar's clock read "Sep 25", missing the day-of-week the reference
# always shows ("Wed Sep 16"). Fedora's own default already has
# clock-show-date=true (confirmed live, not this profile's own
# setting) -- clock-show-weekday is the one real GNOME key still at
# its stock default (false).
clock-show-weekday=true

# Reference-desktop comparison, 2026-09-25: the new weather
# indicator (parcha-global-menu) needs real location data via Geoclue
# to work at all, matching the reference desktop's out-of-the-box
# menu-bar weather. GNOME's own stock default for this is off (a real,
# deliberate privacy default upstream) -- enabling it here is a
# genuine user-facing tradeoff this profile is choosing to make for
# the built-in weather feature, not a silent override; a user who
# doesn't want it can turn it back off in Settings like any other
# GNOME install.
[org/gnome/system/location]
enabled=true

[org/gnome/desktop/wm/preferences]
theme='MacTahoe-Dark'
button-layout='close,minimize,maximize:'

[org/gnome/shell/extensions/user-theme]
name='MacTahoe-Dark'

[org/gnome/desktop/background]
picture-uri='file:///usr/share/backgrounds/parchaos/parchaos-wallpaper.png'
picture-uri-dark='file:///usr/share/backgrounds/parchaos/parchaos-wallpaper.png'
picture-options='zoom'

[org/gnome/desktop/screensaver]
picture-uri='file:///usr/share/backgrounds/parchaos/parchaos-wallpaper.png'
EOF
    run_in_target dconf update

    # ParchaOS's own Plymouth boot splash (packages.list ships
    # plymouth-theme-spinner as the base/fallback theme; this makes our
    # own the live session's actual default). Must run before
    # engine/build-iso.sh's own dracut regeneration step (right after
    # this function returns) or the old theme stays baked into the
    # initramfs -- same ordering requirement as Calamares'
    # parchaos-finalize-install script uses for installed systems.
    echo "--- Setting ParchaOS's Plymouth theme as default ---"
    run_in_target plymouth-set-default-theme parcha-plymouth

    # Flathub remote (system-wide), same as the KDE profile — deliberately
    # does NOT pre-install any Flatpak app during the build to keep the
    # build itself fast; GNOME Software (already installed, native
    # Flatpak support) can install/update from this remote once booted.
    echo "--- Adding the Flathub remote ---"
    run_in_target flatpak remote-add --system --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo

    echo "--- Syncing Flatpak appstream metadata ---"
    run_in_target flatpak update --system --appstream || true
}
