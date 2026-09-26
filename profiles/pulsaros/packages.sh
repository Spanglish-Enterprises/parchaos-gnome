# ==============================================================================
# pulsaros profile — package groupings (sourced by engine/build-iso.sh)
# ==============================================================================
# Installed in Phase 5, against the repo set up by profile_setup_repo()
# in repo.sh (this profile's own COPR + RPM Fusion).
# ==============================================================================

PROFILE_REPO_PACKAGES=(
    # Parcher — ParchaOS's build of Pulsar OS's real, working
    # fork of GNOME Files/Nautilus (packaging/parchaos-finder/). Real
    # traffic-light window controls, live folder color tagging, cloud
    # drive sidebar integration. Renamed from upstream's "Files"/Pulsar
    # OS's own "Finder" branding to avoid Apple trademark exposure ahead
    # of a planned public release (see the spec's own banner comment).
    # Obsoletes/Conflicts/Provides stock nautilus directly (not listed in
    # packages.list's base set) -- a real drop-in replacement, same as
    # the actual Pulsar OS package itself.
    parchaos-finder

    # Parcha Dock — ParchaOS's rebrand of Pulsar OS's real fork of the
    # well-known Dash-to-Dock GNOME Shell extension (hover
    # magnification, launch bounce, downloads-folder stack, live
    # minimized-window previews). Enabled by default via customize.sh's
    # dconf override (GNOME Shell extensions are inert until listed in
    # org.gnome.shell's enabled-extensions key).
    parchaos-dock

    # Parcha Menu — ParchaOS's rebrand of Pulsar OS's real in-house
    # global menu GNOME Shell extension. Deliberately
    # scoped to exclude upstream's setuid-root lock-screen auth helper
    # and GRUB/hibernation postinst mutations -- see the spec's own
    # banner comment. Enabled by default via customize.sh.
    parchaos-global-menu

    # ParchaOS Launcher -- full-screen app launcher replacing the
    # overview app grid (packaging/parchaos-launcher/). Enabled by
    # default via customize.sh.
    parchaos-launcher

    # Parcha Controls -- control center replacing the Quick Settings
    # menu (packaging/parchaos-controls/). Enabled by default via
    # customize.sh.
    parchaos-controls

    # ParchaOS's Tahoe-styled GTK3/GTK4 + GNOME Shell theme
    # (packaging/parchaos-gtk-theme/), real upstream vinceliuice
    # MacTahoe-gtk-theme (MIT), dark variant. Installs as
    # /usr/share/themes/MacTahoe-Dark. Applied by default via
    # customize.sh's dconf override -- GTK apps read
    # org.gnome.desktop.interface gtk-theme directly, but GNOME Shell
    # itself needs the user-theme extension (below) to pick up its own
    # gnome-shell/ subdirectory.
    parchaos-gtk-theme

    # ParchaOS's Tahoe-styled icon theme (packaging/parchaos-icon-theme/),
    # real upstream vinceliuice MacTahoe-icon-theme (GPL-3.0). Installs
    # three real variants (MacTahoe, MacTahoe-light, MacTahoe-dark --
    # confirmed via rpm -qlp on the built RPM); MacTahoe-dark is applied
    # by default via customize.sh to pair with the dark GTK theme.
    parchaos-icon-theme

    # ParchaOS's own real branding for the Calamares installer --
    # passion-fruit logo/icon/welcome/slideshow images (derived from
    # branding/logo/), install-sequence module config, and the three
    # real BIOS-boot/kernel/EFI install-time fixes ported wholesale
    # from the KDE (pearos) variant's own pearos-calamares-config
    # (100% DE-agnostic content, found via that variant's own real
    # end-to-end install+reboot tests -- see the spec's own banner
    # comment). Without this, Calamares would install and boot fine
    # but show generic/no branding and lack those fixes.
    parchaos-gnome-calamares-config

    # ParchaOS's own boot splash (packaging/parchaos-gnome-plymouth-theme/),
    # Plymouth's stock two-step module with a dark background matching
    # the GTK theme and ParchaOS's real logo as the watermark. Applied
    # as the live session's default via customize.sh (the live ISO
    # ships plymouth-theme-spinner in packages.list as a fallback/base
    # dependency; this overrides it) and by Calamares'
    # parchaos-finalize-install script for installed systems.
    parchaos-gnome-plymouth-theme

    # ParchaOS's default desktop wallpaper
    # (packaging/parchaos-gnome-wallpaper/) -- a dark gradient with the
    # real logo as a subtle centered watermark, installed to
    # /usr/share/backgrounds/parchaos/ and applied by default via
    # customize.sh's dconf override.
    parchaos-gnome-wallpaper

    # ParchaOS's keyboard remap (packaging/parchaos-keyboard-remap/, formerly
    # parchaos-macos-remap) -- swaps Super<->Ctrl and layers on Super-key conventions
    # (Super-Left/Right as Home/End, Super-C/V/T/N/W/Q/F in the terminal,
    # Parcher's Super-based file shortcuts, Super-Tab app switching) via
    # xremap + its companion GNOME Shell extension, repackaged from
    # Pulsar OS's gnome-macos-remap-wayland as a real declarative RPM
    # (systemd user-preset, udev uaccess, dconf db) instead of an
    # interactive per-user install script -- see the spec's own banner
    # comment. The xremap@k0kubun.com extension it ships is enabled by
    # default via customize.sh.
    parchaos-keyboard-remap

    # ParchaOS's cloud drives (packaging/parchaos-cloud/) -- rclone-backed
    # cloud storage (Google Drive, OneDrive, iCloud, or any other rclone
    # backend) mounted under ~/Cloud/<name> via a per-account systemd
    # user unit, plus a real Activities-searchable "Add Cloud Account"
    # launcher. Real Pulsar OS original work (GPL-3.0-or-later),
    # rebranded and repackaged -- see the spec's own banner comment for
    # why the upstream package's OneDrive/Google Drive logo files were
    # deliberately dropped (real trademarks, never actually used by the
    # script itself).
    parchaos-cloud

    # Nightly Focus/Do Not Disturb schedule (packaging/parchaos-focus-schedule/)
    # -- two systemd --user timers (22:00/08:00 by default) calling the
    # real freedesktop.org Notifications Inhibit/UnInhibit D-Bus
    # methods. Built and verified working against KDE Plasma originally
    # (docs/phase0-findings.md in the KDE repo); genuinely 100%
    # DE-agnostic (pure D-Bus spec calls via gdbus, no toolkit
    # dependency at all) -- carried over unchanged for this GNOME
    # profile, no porting needed. Enabled by default via its own
    # systemd user-preset.
    parchaos-focus-schedule

    # Auto light/dark theme switching with real sunrise/sunset support
    # (packaging/parchaos-yin-yang/, real upstream oskarsh/Yin-Yang,
    # MIT) -- a cross-desktop PySide6/Qt app (its own UI toolkit is
    # independent of GNOME vs KDE), with dedicated GTK/icon-theme/
    # wallpaper plugins that are directly relevant to this profile
    # (its Kvantum/Plasma-color-scheme/Konsole plugins are inert no-ops
    # under GNOME, harmless). User-configured, not forced on by
    # default -- same "respect user choice" reasoning as this
    # project's other optional personal-preference features; nothing
    # runs until the user opens the app once and picks a schedule (see
    # the spec's own banner comment for the real upstream
    # daemon-self-management architecture this relies on).
    parchaos-yin-yang

    # TMOG (Task Manager OG) launcher (packaging/parchaos-tmog/) -- a
    # .desktop entry + first-run-fetch wrapper for Dave Plummer's
    # closed-source native system monitor. Does not bundle TMOG's own
    # binary at all (its license page reserves distribution rights);
    # the wrapper downloads the official AppImage directly from
    # tmog.org on first launch and caches it, same as a user clicking
    # a "Download" button themselves -- ParchaOS/its COPR never hosts
    # or redistributes the binary. Genuinely DE-agnostic (AppImage +
    # .desktop launcher, no KDE dependency at all); already
    # end-to-end verified once under an earlier product name (real
    # download confirmed, real Qt init reached) per the spec's own
    # changelog.
    parchaos-tmog

    # Parcha Browser (packaging/parchaos-browser/) -- ParchaOS's web
    # browser and the default for web links: a thin rebrand of Fedora's
    # own real `chromium` package. It replaced Pafari (pearOS's Epiphany
    # fork) and Obsoletes it, so existing installs drop Pafari on update.
    # Requires: chromium pulls the actual browser engine in from
    # packages.list's base set.
    parchaos-browser

    # ParchaOS app-display-name overrides (packaging/parchaos-app-renames/)
    # -- Loupe -> Preview, GNOME Clocks -> Clock, Geary -> Mail. Their
    # icons already come from the MacTahoe icon theme for free; this is
    # display-name-only, via a %post sed on the real installed .desktop
    # files (see the spec's own banner comment for why, and for Amberol/
    # Music being deliberately left out -- no native Fedora RPM).
    parchaos-app-renames

    # Notification banner positioning (packaging/parchaos-notification-position/)
    # -- real user priority request. Real upstream picked with the same
    # license diligence used everywhere else (Pulsar OS's own real
    # extension has no LICENSE file at all -- see the spec's own
    # banner comment for the full story and the real fork used
    # instead).
    parchaos-notification-position

    # Three more real, licensed third-party extensions matching Pulsar
    # OS's own config exactly (packaging/parchaos-magic-lamp-effect/,
    # packaging/parchaos-wiggle/, packaging/parchaos-ui-tune/) -- the
    # genie/magic-lamp minimize effect, cursor-magnify-on-shake, and
    # Overview UI tuning. See each spec's own banner comment for the
    # license diligence.
    parchaos-magic-lamp-effect
    parchaos-wiggle
    parchaos-ui-tune

    # ParchaOS's real logo on the GDM login screen, replacing Fedora's
    # default (packaging/parchaos-gdm-logo/) -- real user feedback
    # (the login screen still showed the Fedora logo).
    parchaos-gdm-logo

    # Hosts-file ad-blocker (packaging/parchaos-hblock/) -- one of the
    # three "bigger feature" gaps that doesn't depend on Inled's
    # licensing answer (docs/gnome-phase3-findings.md). Built from the
    # real, independent hectorm/hblock upstream directly, not Pulsar
    # OS's own (blocked) pulsaros-hblock.
    parchaos-hblock

    # Live/video wallpaper (packaging/parchaos-hanabi/) -- the third
    # "bigger feature" gap that doesn't depend on Inled's licensing
    # answer (docs/gnome-phase3-findings.md). Built from the real,
    # actively-maintained jeffshee/gnome-ext-hanabi upstream, picked
    # over Pulsar OS's own live-wallpaper analog after confirming that
    # one needs X11-only xwinwrap and doesn't work on this profile's
    # real Wayland session at all -- see the spec's own banner comment
    # for the full diligence.
    parchaos-hanabi

    # Desktop Icons NG (packaging/parchaos-desktop-icons/) -- real
    # icons on the desktop background, one more piece of Pulsar OS's
    # extension list this profile didn't ship yet
    # (docs/gnome-phase1-findings.md's extension-polish pass flagged
    # it as needing a heavier meson build; turned out simpler than
    # feared once actually read -- see the spec's own banner comment).
    parchaos-desktop-icons

    # ParchaOS desktop meta-package (packaging/parchaos-desktop/) -- a
    # real, standard-pattern no-content package whose only job is a
    # Requires: line naming every package above. Exists in direct
    # response to real user feedback: `dnf update` alone never installs
    # a package that's new since the user's own install, only upgrades
    # ones already present -- installing this meta-package (which
    # happens automatically as part of this same Phase 5 install) means
    # a plain `sudo dnf update` becomes genuine OTA for future additions
    # to this list, since bumping this meta-package's Release with an
    # expanded Requires: pulls the new dependency in on update. MUST be
    # kept in sync by hand whenever this array changes -- see the
    # spec's own banner comment for the full reasoning and the
    # maintenance rule.
    parchaos-desktop
)

# Pulled in only with --nvidia, from RPM Fusion nonfree (enabled
# unconditionally by profile_setup_repo() in repo.sh).
PROFILE_NVIDIA_PACKAGES=(
    akmod-nvidia
    xorg-x11-drv-nvidia-cuda
    xorg-x11-drv-nvidia-power
)
