# GNOME variant phase 1 findings — the real-hardware crisis night

Status date: 2026-09-24. This picks up from `docs/gnome-phase0-findings.md`,
whose own "What's next" section flagged real Calamares-launcher/mouse-click
verification as the last open question before this variant was ready for
its first real install. That install happened overnight on 2026-09-24 —
this doc is the real, verified record of everything that broke, why, and
how it got fixed, following this project's own convention of writing down
what actually happened rather than what should have worked.

## Summary: what's real and working right now

ParchaOS GNOME has had a **complete, real, end-to-end install on the
actual physical machine it's meant to ship to** (an MSI B650 GAMING PLUS
WIFI / AM5 desktop, hostname `the test desktop`): Calamares install, reboot,
login, a real desktop session, working wired networking, working WiFi,
and (after a round of live-patching, now folded back into the ISO) all
of Pulsar OS's ported apps installed and process-verified. This closes
phase 0's last open question (the real mouse click through Calamares'
polkit dialog) and finds a genuinely long chain of real bugs beyond it —
some in this project's own packaging, several in Fedora's own
package-splitting conventions, one in the target machine's own clock.

Fifteen ISO builds happened this session (v5 through v19 by this
project's own informal versioning); the ones that actually matter are
summarized below by what they fixed, not by number — see the COPR
build history / this repo's commit log for the full blow-by-blow if
needed.

## The boot chain: five real, independently-verified bugs

The first several hours were a single, real, recurring bug on real UEFI
hardware: install completes with no error, but the machine won't boot
afterward. Root-caused as a **chain** of separate bugs, each verified
directly before moving to the next (not assumed from reading code):

1. **`efibootmgr -l` needs an ESP-relative path, not a full mountpoint
   path.** Calamares' own stock `bootloader` module passes the full
   chroot path (`/boot/efi/EFI/fedora/shimx64.efi`); `efibootmgr`
   doesn't strip the mountpoint prefix, producing an NVRAM entry whose
   UEFI device path points at a file that doesn't exist on the ESP's
   own filesystem. Fixed with a corrective `shellprocess` step
   (`parchaos-fix-efi-bootentry`) that creates a second, correct entry
   after Calamares' own (broken) one.
2. **The ESP never got the grub2-efi-x64/shim "master" files at all** —
   `parchaos-install-kernel`'s `find -maxdepth 2` was one level too
   shallow for these packages' real on-disk layout
   (`/usr/lib/efi/grub2/<ver>/EFI/fedora/`, three levels deep), and its
   `cp -a` calls failed outright on FAT32 (which can't represent the
   hard links between `shimx64.efi`/`shim.efi`). Fixed: `-maxdepth 3`,
   `cp -a` → `cp -r`.
3. **Kernel cmdline (root=/rootflags=) wasn't being written** before
   `kernel-install add` ran, since `unpackfs`'s squashfs source ships
   no kernel of its own — fixed by staging `root=UUID=... rootflags=subvol=...`
   into `/etc/kernel/cmdline` before kernel-install runs.
4. **btrfs named-subvolume layout and GRUB's own filesystem driver
   disagree about where the root subvolume lives.** This project's
   `mount.conf` creates `@root`/`@boot`/`@home` as sibling subvolumes;
   GRUB's own `search --fs-uuid` lands at the filesystem's neutral top
   level, invisible to content inside any subvolume unless that
   subvolume is the filesystem's *default* subvolume. Setting `@root`
   as default subvolume fixed this at the real kernel-mount level
   (verified: mounting the raw partition with no `-o subvol=` showed
   `@root`'s content directly) — but GRUB's own btrfs driver (a
   from-scratch reimplementation, not the kernel's) still didn't
   resolve it the same way.
5. **The real fix for #4 turned out to be a layer up**: Fedora's
   default `grub2-mkconfig` (BLS/`blscfg` enabled) generates a
   `grub.cfg` that dynamically reads `/boot/loader/entries/*.conf` at
   boot time — this is the mechanism that couldn't find the real OS
   entry, independent of the subvolume-default fix. Setting
   `GRUB_ENABLE_BLSCFG=false` before `grub2-mkconfig` runs forces
   Fedora's older, static `/etc/grub.d/10_linux` menuentry generator
   instead, which correctly embeds real `/@root/`-prefixed
   `linux`/`initrd` lines. **This is the fix that actually got the
   machine booting**, confirmed via a real, clean install + single
   reboot with no manual intervention.

An earlier attempt at #4/#5 (writing a hand-rolled static `menuentry`
into `custom.cfg` to bypass `blscfg`) didn't resolve the real symptom
and was abandoned once the `GRUB_ENABLE_BLSCFG=false` fix was found —
left in place as harmless, redundant insurance, not removed.

## A real regression in fixing bug #5, caught before it shipped

The first attempt at "remove Calamares from the finished install" (see
below) put `dnf -y remove calamares` inside `parchaos-finalize-install`,
which runs *early* in the install sequence (right before `dracut`, for
Plymouth-theme-timing reasons). `parchaos-gnome-calamares-config`
itself `Requires: calamares`, so removing "calamares" cascade-removed
this package too — wiping `/etc/calamares/scripts/` mid-install and
breaking every *later* shellprocess step that still needed a script
from it (`parchaos-disable-blscfg` itself, ironically, plus
`parchaos-fix-efi-bootentry` and `parchaos-write-grub-menuentry`).
Caught by a real fresh-install regression test before it reached the
user — fixed by moving the Calamares removal into its own script
(`parchaos-remove-calamares-app`) that runs as the *last* shellprocess
step in the exec sequence, after everything else from the same package
has already run.

**Update 2026-09-24, a second instance of the same cascade found live**:
after the six-package `parchaos-desktop` OTA meta-package (see its own
spec's banner comment) was wired up, its `Requires:` list included
`parchaos-gnome-calamares-config` — meaning the same Calamares removal
step, unchanged since the fix above, now cascaded one link further:
`calamares` → `parchaos-gnome-calamares-config` → `parchaos-desktop`.
Every *fresh* install since that meta-package was added has been
silently deregistering `parchaos-desktop` itself at the very last step
of install, without any error (the removal script's `|| true` on the
`dnf remove` swallows it). Caught live on the real machine (user
reported "I still see the install system app" from an install that
predated even the original fix's ISO — while fixing that live, the same
`dnf remove calamares --noautoremove` reproduced the newer regression
on the spot, pulling `parchaos-desktop` into the same transaction).
Fixed the same way as the original: `parchaos-desktop.spec` no longer
`Requires: parchaos-gnome-calamares-config` (Release 2), on the same
reasoning as the NVIDIA-packages exclusion already in that spec —
install-time-only tooling isn't part of "the desktop" an OTA
meta-package should track. Rebuilt via COPR (build 11032596,
succeeded), and reinstalled on the real machine to restore its
`parchaos-desktop` registration without re-pulling Calamares. Verified:
`rpm -q calamares` → not installed, both `calamares.desktop` copies
gone, `parchaos-desktop-2026.09.23-2.fc44` present, and a repeat
`dnf remove calamares --noautoremove` no longer touches
`parchaos-desktop` (only cascades to `parchaos-gnome-calamares-config`
and `calamares-libs`, both expected and harmless).

## Post-boot bugs: a real desktop that didn't quite work right

Getting the machine to boot just uncovered the next layer. All of the
following were found via genuine real-hardware testing (not VM-only),
several of them via the user's own hands-on troubleshooting relayed
live:

- **Calamares stayed installed and launchable after install completed**
  — a real footgun (re-running it would attempt to reinstall over the
  running system). Fixed as `parchaos-remove-calamares-app` above,
  removes the launcher `.desktop`/script and the `calamares` package
  itself.
- **GNOME Terminal and Nautilus both failed** — Terminal spun forever
  with no window ever appearing; Files did nothing. Root-caused by
  mounting the installed system's disk *offline* via `qemu-nbd` from
  the hypervisor and reading its journal directly (no live access
  needed): `gnome-terminal-server` exits immediately with `"Locale not
  supported."` because `en_US.UTF-8` was never actually generated —
  Fedora ships locale data in per-language `glibc-langpack-<lang>` RPMs,
  none of which were in this profile's package list. This also explains
  the `setlocale` warnings seen on every login all night, and was the
  likely cause of Nautilus's own repeated ABRT crashes in the same
  journal window. Fixed: added `glibc-langpack-en`.
- **System-wide font rendering was subtly wrong** — real user-caught
  feedback ("the letter spacing in the terminal is strange"). Both
  "Adwaita Sans" (this profile's configured UI font) and "Adwaita Mono"
  (monospace default) were configured but never actually installed —
  `fc-match` fell back to Cantarell for UI text and, worse, the
  *proportional* Noto Sans for monospace requests, which is what broke
  VTE's fixed-width cell rendering. Not just the terminal: every window
  title, menu, and label had been silently rendering in the wrong font
  since the very first branded build. Fixed: added
  `adwaita-sans-fonts`/`adwaita-mono-fonts`.
- **Bluetooth firmware missing entirely** — dmesg flooded with `Direct
  firmware load for mediatek/BT_RAM_CODE_MT7922_1_1_hdr.bin failed`
  every ~0.5s, forever, which also degraded general desktop
  responsiveness (kernel/udev churn from the retry loop). Fixed: added
  `mt7xxx-firmware` (confirmed via `rpm -qf` that this MediaTek
  firmware lives in its own subpackage, not the base `linux-firmware`
  metapackage).
- **WiFi showed as `unmanaged` in NetworkManager even after installing
  `wpa_supplicant`.** Real root cause, found via research once live
  troubleshooting stalled: `NetworkManager-wifi` is a *separate*
  subpackage from base `NetworkManager` (confirmed via
  `dnf repoquery NetworkManager-*`) — without it, NetworkManager has no
  WiFi device-management code loaded at all, independent of whether a
  supplicant backend is present. This exact failure mode is a known,
  historical Fedora bug class (RHBZ #1230223, from Fedora 23-era
  netinst) that official spins avoid because their kickstarts pull in
  Fedora's own `comps.xml` groups, which bundle the NetworkManager
  submodules; this project's hand-curated `packages.list` never had
  that bundling. Also added `wireless-regdb` (regulatory database,
  same missing-subpackage pattern), `iw`, and
  `NetworkManager-config-connectivity-fedora` while investigating.
  **Fully confirmed working end to end** on real hardware via direct
  SSH: `nmcli device wifi list` returned real scan results, and
  `nmcli device wifi connect` completed with a real DHCP lease.
- **Basic diagnostic tools were missing** — `lspci`, `ethtool` both
  "command not found" on a fresh install, which made debugging the
  above significantly harder than necessary. Diffed this profile's
  package list against Fedora's own `standard`/`hardware-support`
  comps groups (deliberately *not* adopting the full official spin
  bundle wholesale — see below) and added the genuinely relevant
  subset: `ethtool`, `pciutils`, `usbutils`, `net-tools`, filesystem
  drivers for removable media (`exfatprogs`/`ntfs-3g`/`dosfstools` —
  likely also the real cause of an earlier USB-drive mounting problem
  during the crisis, before a full network path existed), network
  diagnostics (`tcpdump`/`mtr`/`traceroute`/`nmap-ncat`), general
  utilities (`rsync`/`unzip`/`zip`/`tree`/`lsof`/`smartmontools`), and
  firmware for WiFi/audio/GPU vendors other than this specific
  machine's own AMD/MediaTek/Realtek combo (Intel/Atheros/Broadcom/
  Marvell/Cirrus/NVIDIA) — relevant for this being a general-purpose
  daily-driver distro, not tuned to one board.
- **`openssh-server` isn't installed/enabled by default** on this
  Workstation-style spin — added so a user (or an agent helping them)
  can get direct remote access for troubleshooting without a manual
  package-download cycle, which is exactly how the rest of this
  session's real-hardware verification ended up happening (see below).

## On not adopting Fedora's full official spin bundle

Real question asked directly: given how many of the bugs above were
"a package Fedora's own official Budgie/Workstation spins would have
included," should this profile just switch to installing from Fedora's
own `comps.xml` groups (`@workstation-product-environment` or similar)
instead of a hand-curated list? **Decided against it**: roughly doubles
image size, and creates real conflicts with branding already built
against this minimal base (stock GNOME defaults — Firefox,
`gnome-tour`, `gnome-connections` — would need explicit removal, some
could collide with Pulsar OS's own replacements). Chose instead to
**diff against the specific comps groups that actually caused real
bugs** (`standard`, `hardware-support`) and cherry-pick the relevant
subset, which closes the same class of bug without the size/branding
cost. Cross-checked whether Pulsar OS's own upstream package reference
(`Inled-Pulsar-OS/PKG`) had already solved any of this — it hadn't,
because it's Arch-based and Arch doesn't split `NetworkManager` (or
much else) into per-feature subpackages the way Fedora does; this
entire bug class is structurally specific to the Fedora port and
wasn't something to have caught by porting Pulsar OS's own config more
carefully.

## The clock: a real, subtle, easy-to-misdiagnose bug

Late in the session, installing the six previously-unwired
Pulsar-OS-ported packages (see below) directly onto the real,
now-online machine failed with `Signature verification failed` /
`Failed to read package header from file` — looked exactly like RPM
corruption or a COPR GPG-trust problem, and cost real time chasing
both (downloading the same RPM fresh from COPR onto a different host
and confirming it was byte-valid there; re-uploading a known-good copy
directly to the target machine and hitting the *identical* failure).
The actual error, once looked at directly instead of trusting dnf's
summary line: `rpm -qp` on the target machine gave
`signature is not alive because: Not live until 2026-09-24T17:59:58Z`
— **the machine's system clock was ~5 hours behind real time**,
because it had been offline all evening (the entire reason this crisis
existed) and had no NTP client installed at all to correct it once
network finally came up. RPM's OpenPGP signature verification is
time-window-based; a signature freshly created by COPR minutes earlier
looks "not yet valid" to a clock that thinks it's still 5 hours in the
past. Fixed immediately on the real machine (`timedatectl set-time` +
`hwclock --systohc`, then `chrony` installed and enabled), and added
`chrony` to `packages.list` so every future device self-corrects as
soon as it has network, instead of hitting this same failure mode.
**Worth remembering**: a signature-verification failure that looks like
corruption or a trust problem is worth checking the system clock
before assuming either.

## The six-package wiring gap — a sync gap, not a packaging bug

`profiles/pulsaros/packages.sh`'s `PROFILE_REPO_PACKAGES` array already
listed `parchaos-macos-remap`, `parchaos-cloud`,
`parchaos-focus-schedule`, `parchaos-yin-yang`, `parchaos-tmog`,
`pafari`, and the `parchaos-desktop` meta-package (phase 0's own "fold
these into the next rebuild" item, apparently already done in this
repo checkout at some point) — but none of them were actually present
on the real installed system. Root cause: this session's crisis work
only ever pushed `packages.list` to the build host, never
`packages.sh`, so every crisis-driven rebuild (v13 through v18) kept
using the build host's stale, pre-six-package copy without anyone
noticing (the base-package fixes all worked fine, since those *were*
being synced, masking the separate staleness of this file). Confirmed
directly by grepping the build host's own copy of the file mid-session.
Fixed by syncing it for real and rebuilding (v19).

**A related, real (but ultimately not-a-bug) finding**: after manually
installing the six packages directly onto the real machine (bypassing
a full ISO rebuild, since the machine already had network), the
`parchaos-macos-remap.service` (the xremap keyboard-remap daemon) and
the `xremap@k0kubun.com` GNOME Shell extension both showed as
disabled/not-enabled despite the RPM shipping a systemd user-preset
file and a dconf default specifically to avoid needing manual
enablement. This is *not* a packaging bug: both mechanisms only get
applied automatically on a genuinely fresh user's first login,
and the real machine's `alex` account had already logged in (during
the original overnight install, hours before these six packages ever
existed on the system) — so neither the preset nor the dconf default
ever got their one chance to apply. A truly fresh install with these
packages already present in the ISO (as v19 now has) would not hit
this. Manually enabled both for the current session
(`systemctl --user enable --now parchaos-macos-remap.service`, added
`xremap@k0kubun.com` to `enabled-extensions`) to match what a fresh
install would already give a real user.

**One genuine spec bug found and fixed in the process**:
`parchaos-macos-remap.spec` had `Requires(post): systemd-udevd` — a
one-character typo (Fedora's real package is `systemd-udev`, confirmed
via `rpm -qf $(which udevadm)`). This silently broke installing the
*entire* six-package transaction (dnf resolves a multi-package request
as one transaction; `parchaos-desktop`'s own `Requires:` on
`parchaos-macos-remap` meant the whole thing failed together). Fixed,
rebuilt (Release 2), reconfirmed installable.

## What's verified vs. what still needs a human

**Verified directly** (real hardware, real SSH access once the machine
had network): all six packages plus `parchaos-desktop` install cleanly;
`rclone`/`parchaos-cloud`, `pafari`, and `yin_yang` binaries are present;
`pafari` and `yin_yang` launch and stay running (process-level, no
immediate crash); the focus-schedule systemd timers are loaded and will
fire on their configured 22:00/08:00 schedule.

**Correction, 2026-09-24**: the line above used to also claim
"`parchaos-macos-remap.service` xremap daemon is active" as verified.
That was wrong — `systemctl --user status` does say `active`, but
`journalctl` showed it was actually crash-looping the entire time
(`Restart=on-failure`/`RestartSec=10` masks a crash loop as "active"
between restarts). See "Two more real bugs found live" below for the
real state and the fix. Leaving this correction in place rather than
silently rewriting the earlier claim, per this project's own "don't
assert what wasn't verified" rule — the lesson is that `systemctl
status` alone isn't enough; check the restart counter and the actual
journal output before calling a service "working."

**Still needs a real person at the keyboard** (not mechanically
verifiable over SSH, same class of limitation phase 0 hit with the
Calamares mouse click): does Cmd actually act as Ctrl on a real
keypress; does `pafari` visually render a real page; does yin-yang's
theme switch actually change the GTK/icon/wallpaper correctly; does
TMOG's real first-run AppImage download complete; does the
`parchaos-cloud choose` → rclone OAuth → mount-under-`~/Cloud` flow
work end to end; does the focus-schedule's notification inhibit
actually suppress a real popup during its scheduled window.

**Genuinely unresolved, not a packaging bug found tonight**: the
original wired-NIC symptom that kicked off part of this session ("link
up, DHCP never completes") was never root-caused with certainty — the
RTL8125 firmware was confirmed already present in the base
`linux-firmware` package (ruling out the first guess), and NetworkManager's
own logs showed a clean 45-second DHCP timeout with zero response, not
a malformed reply — consistent with something between the machine and
the router (bad cable/port) rather than an OS bug. It started working
correctly at some point later in the session without a specific fix
being applied to it; unclear whether a cable/port was changed, or
whether the machine simply got lucky on a retry. If it recurs, start
from `ip link`/`ethtool`/`journalctl -u NetworkManager` output on a
real DHCP attempt, not from assuming it's the same class of bug as
tonight's other fixes.

## Two more real bugs found live, 2026-09-24: the dock and keyboard remap

Prompted by real user feedback ("the theming is still lacking... the
dock should have options and should be on by default like a Mac
would"). Checked the real machine directly rather than guessing at a
theming/CSS explanation, and found two unrelated, genuine bugs — not a
theming issue at all:

**The dock was crashing, not "off."** `parcha-dock@parchaos.org` was
correctly installed and correctly enabled in dconf (the "on by
default" mechanism already worked), but `gnome-extensions show`
reported `State: ERROR`. `journalctl` had the real cause:
`GLib.FileError: Failed to open file
".../schemas/gschemas.compiled": open() failed: No such file or
directory`, thrown from `docking.js`'s `DockManager` constructor.
Root-caused against the real upstream Dash-to-Dock Makefile (fetched
directly, not guessed): its `_build` target only stages the *raw*
`schemas/*.gschema.xml`; the actual compiled binary GNOME Shell needs
at runtime is produced by a separate `install`/`install-local` target
that `parchaos-dock.spec`'s `%install` never called — it just did a
plain `cp -a _build/*`. Fixed by adding an explicit
`glib-compile-schemas "$DEST/schemas"` call to `%install` (Release
106-2, COPR build 11032634, succeeded). Separately, `gnome-extensions-app`
was missing from `packages.list` entirely — modern GNOME (45+) has no
other way to reach any extension's preferences UI, so even a
correctly-running dock would have had no reachable settings. Added it.

**The keyboard remap had been crash-looping since boot.**
`parchaos-macos-remap.service` (xremap) was in a `Restart=on-failure`
crash loop the entire time this machine had been up — restart counter
was at 2353 by the time this was checked. Real error: `Failed to
prepare input devices: No device was selected!`. Root cause: the
installed user account was never a member of the `input` group, and
`/dev/input/event*` nodes are `root:input 0660` — Fedora's own
`70-uaccess.rules` deliberately grants dynamic per-session device
access for joysticks but *not* for keyboards/mice, a real, intentional
security boundary, not an oversight. Checked Pulsar OS's own
`gnome-macos-remap-wayland` install script first (same "check what
they already solved" approach used throughout this project) — it
doesn't need this fix at all because it depends on `xremap-gnome-bin`,
a GNOME-portal-based variant, not the generic evdev-grab `xremap` this
project's `parchaos-macos-remap.spec` actually uses. Fixed at the
correct layer: added `files/etc/calamares/modules/users.conf`
(overriding Calamares' stock `defaultGroups` to add `input`) to
`parchaos-gnome-calamares-config` (Release 20, COPR build 11032637,
succeeded) — this is the right place because Calamares creates the
user account (and its groups) at install time, before any package's
own `%post` could ever know the eventual username, the same
which-user/what-lifecycle-stage gap already documented above for the
systemd user-preset and dconf-default mechanisms. A udev rule was
considered and rejected: it would have had to weaken the uaccess
boundary for every local user on the system, not just grant the one
real account Calamares creates.

**Both fixes only take effect for *this* real machine after a logout
or reboot**, not immediately: Linux supplementary-group membership is
resolved once per login session (a live `usermod -aG input alex` was
applied immediately, but the already-running session's processes,
including `systemd --user` itself, keep the group list they started
with), and GNOME Shell caches an extension's `ERROR` state until a
fresh Shell process starts (Wayland has no live shell-restart the way
X11's `Alt+F2 r` does). The packaging fixes themselves are verified
correct at the file level (compiled schema present, `usermod` applied
live); the on-screen/running-state confirmation needs an actual reboot
by a real person, same class of limitation as the interactive checklist
below.

## Traffic lights, light mode, and app rebrands, 2026-09-24

Prompted by real user feedback ("the terminal is not following our
rules of traffic lights", "we don't seem to have a light mode",
"what other apps can we do similar" [to the browser rebrand]).

- **Traffic lights**: `button-layout` was never set at all
  (`org/gnome/desktop/wm/preferences`), so GNOME fell back to Fedora's
  stock `appmenu:close` -- a single right-aligned close button, no
  traffic lights, no minimize/maximize. Cross-checked directly against
  Pulsar OS's own real dconf defaults
  (`Inled-Pulsar-OS/PKG`'s `pulsaros-gnome/etc/dconf/db/local.d/00-pulsaros-theme`,
  fetched directly): `button-layout='close,minimize,maximize:'`. Added
  the same value, plus `cursor-theme='MacTahoe-dark'` (the icon theme
  genuinely bundles a real `cursors/` dir, confirmed via `find`, just
  never wired into dconf) and `color-scheme='prefer-dark'` (needed for
  GTK4/libadwaita apps, which don't read `gtk-theme` at all) to
  `customize.sh`. Applied live via `gsettings` too.
- **Light mode**: confirmed via upstream MacTahoe-gtk-theme's own
  `libs/lib-core.sh` that `light` has always been a real, fully-built
  color variant (`COMMAND_COLOR_VARIANTS=('light' 'dark')`) --
  `parchaos-gtk-theme.spec` only ever built `dark`. Added a second
  `install.sh -c light` call; both `MacTahoe-Dark` and `MacTahoe-Light`
  now ship (Release 106-2).
- **Browser rebrand** (`packaging/parchaos-browser/`): real user
  request for a Chromium-based browser (Gmail and other Google
  services are Chrome/Blink-tuned; pafari, this profile's other
  browser, is WebKitGTK-based). Confirmed via real `dnf list
  --available` that `chromium-freeworld` (RPM Fusion) doesn't exist on
  this Fedora release -- based on plain Fedora `chromium` instead
  (API keys already stripped since 2021; H.264 via the
  `fedora-cisco-openh264` repo this profile already enables). A thin
  desktop-entry rebrand, not a from-scratch Chromium build. Named
  "Parcha Browser" rather than echoing Pulsar OS's own "SeaFari" --
  checked their real repo (`InledGroup/seafari`) first and confirmed
  it's a Firefox/Gecko rebrand, not Chromium, so reusing that name for
  a different engine would be misleading. Icon reuses a real, existing
  `safari.svg` already in the MacTahoe icon theme -- no new asset
  needed.
- **App display-name rebrands** (`packaging/parchaos-app-renames/`):
  audited icon coverage for every stock app with a macOS equivalent
  (Calculator, Calendar, Weather, Loupe, Contacts, Clocks, Geary,
  Amberol) and found the MacTahoe icon theme already covers all of
  them by real app ID (`org.gnome.Loupe.svg`, `org.gnome.Geary.svg`,
  etc.) -- zero new icon work needed, only display names were off.
  Renamed Loupe -> Preview, GNOME Clocks -> Clock, Geary -> Mail (added
  to packages.list) via a `%post` sed on the real installed `.desktop`
  files. **Real bug found and fixed within the same session**: the
  first version of that sed had no line-range restriction, so on
  Geary's desktop file (the only one of the three with `[Desktop
  Action ...]` blocks) it also renamed the "Compose Message" and "New
  Window" actions to "Mail". Fixed with GNU sed's `0,/re/` range form
  to stop before the first `[Desktop Action` line; caught and repaired
  live before this doc entry was written. Amberol (Music.app
  equivalent) deliberately NOT renamed -- confirmed via `dnf list
  --available amberol` that it has no native Fedora RPM at all
  (Flatpak-only), a different mechanism this profile's ISO build
  doesn't currently support at build time.

## Extension polish gap closed (partially), 2026-09-24

Following up on "what other apps/theming are we missing" -- diffed
this profile's `enabled-extensions` against Pulsar OS's own real
config (`00-pulsaros-theme`, same fetch as the button-layout fix
above). Pulsar ships ~15 extensions for the full "feels like macOS"
polish; this profile only shipped 5. Four of Pulsar's real extensions
are, confirmed via `dnf list --available` on real hardware, genuine
official Fedora packages with the exact same UUIDs Pulsar's config
uses (verified via each one's real installed `metadata.json`):
`appindicatorsupport@rgcjonas.gmail.com`, `blur-my-shell@aunetx`,
`just-perfection-desktop@just-perfection`, `no-overview@fthx`. Added
all four to `packages.list`, enabled them in `customize.sh`, and
carried over Pulsar's own real tuning values for blur-my-shell/Just
Perfection (dropping their kiwimenu/support-notifier-* keys, which
don't apply here). Applied live via `gsettings` too.

**Not done in this pass** -- the rest of Pulsar's list has no Fedora
package at all: `compiz-alike-magic-lamp-effect` (the genie minimize
effect), `notification-position`, `wiggle`, `gnome-ui-tune`, `ding`
(Desktop Icons NG). Each would need individual packaging from
extensions.gnome.org, the same way `parcha-dock` was built from its
real upstream source -- not started.

**Update, same day: notification positioning done** (real user
priority request). Pulsar OS's own real extension
(`notification-position@drugo.dev`,
`brunodrugowick/notification-position-gnome-extension`) has no LICENSE
file at all -- confirmed via its GitHub API record (`license: null`)
and a full 28-file tree search, same blocker class as Sayri -- so it
wasn't packaged. Checked two real forks: `Ahmed-Sinkeat/Notification-position`
(real MIT license, but stale since 2024-08) and
`marcinjakubowski/notification-position-reloaded` (real GPL-2.0
LICENSE file confirmed present, actively maintained, last pushed
2025-12-08). Packaged the latter as `parchaos-notification-position`.
Found a second real gap before shipping: its `metadata.json` only
declares GNOME Shell support through version 49, but this profile's
real installed Shell is 50.5 -- would have silently refused to load.
Pulsar OS's own config already sets
`disable-extension-version-validation=true` for exactly this reason;
added the same key to `customize.sh`, both as the fix for this
extension and as general hardening for anything added later. Default
position set to top-right with an 8px inset, sliding in from the
right edge (matching real macOS notification behavior, confirmed
against the extension's own `extension.js` source for what the
anchor/animation-direction integers actually mean, not guessed from
the bare gschema). Applied live via `dconf write` rather than
`gsettings set` -- this extension (like `parcha-dock`) uses a
self-contained local schema in its own directory, which the generic
`gsettings` CLI can't see at all (`No such schema` for every key), but
`dconf write` operates directly on the dconf path without needing a
system-registered schema, and the extension itself reads from that
same path at runtime regardless of which tool wrote it.

**Confirmed real limitation, not a bug**: neither the dconf default
nor a live `gsettings set enabled-extensions` change makes a newly
*installed* extension usable in an already-running GNOME Shell
session -- `gnome-extensions enable <uuid>` returned "does not exist"
for all four until the machine picks up the newly-installed
extension directories, which (same as the dock/keyboard-remap fixes
earlier tonight) needs a logout or reboot, not just a shell restart.
All four are correctly wired at the file/config/dconf level; the
on-screen confirmation is bundled with the other pending
logout/reboot verification from earlier tonight.

## GDM login logo still showed Fedora, 2026-09-24

Real user feedback: "the login logo is still fedora". Root cause,
confirmed on real hardware: the `gdm` package itself ships
`/usr/share/glib-2.0/schemas/org.gnome.login-screen.gschema.override`
setting `logo='/usr/share/pixmaps/fedora-gdm-logo.png'` as a
**schema-level** default -- a genuinely different mechanism from
customize.sh's existing `/etc/dconf/db/local.d/*` theme overrides,
which only reach the regular user's own session (via
`/etc/dconf/profile/user`). GDM's greeter runs as its own separate
system user with no dconf profile ever set up in this profile at all --
but this specific setting doesn't need one, since it's baked into the
compiled schema itself, applying to any reader of that schema
regardless of which dconf database they use.

Fixed the same way Fedora's own `gdm` package sets its default: shipped
a second override file (`packaging/parchaos-gdm-logo/`), named with a
`zz-` prefix so it alphabetically sorts after gdm's own file and wins
(GLib's own documented "last override file wins for a given key" merge
behavior, not guessed). Reused the real
`branding/logo/parcha-logo-white.png` asset (white, since this
profile's real default is MacTahoe-Dark). Verified live: `gsettings get
org.gnome.login-screen logo` now returns
`/usr/share/pixmaps/parchaos-gdm-logo.png` immediately, no
logout/reboot needed for the *setting* to take effect (unlike
everything else in this session's queue) -- but GDM itself is a
long-running system service, so seeing it on the actual login screen
still needs a `gdm.service` restart or reboot, joining the same queue.
Deliberately did not restart `gdm.service` directly -- that would kill
the current graphical session immediately without warning, a
disruptive action not taken unilaterally.

## Remaining extension gap closed, 2026-09-24

Following "what else is Pulsar using that we don't have" -- a full diff
against Pulsar's real config found three more extensions with real,
independently-maintained (not Inled-original) upstreams, each checked
for a real LICENSE file before packaging the same way as everything
else: `compiz-alike-magic-lamp-effect@hermes83.github.com` (the genie
minimize effect, real GPL-3.0), `wiggle@mechtifs` (cursor magnify on
shake, real GPL-2.0), `gnome-ui-tune@itstime.tech` (Overview UI tuning
-- hides search until typing, restores wallpaper on workspace
thumbnails, real GPL-3.0, UUID cross-checked to confirm it's genuinely
the same extension Pulsar's config references and not a same-named
different project). Packaged as `parchaos-magic-lamp-effect`,
`parchaos-wiggle`, `parchaos-ui-tune`. All three confirmed built,
schemas compiled, installed on real hardware, and added to
`enabled-extensions` live. This profile now ships 12 of Pulsar's ~15
extensions.

**Genuinely not portable**: Pulsar's own `pulsaros-spotlight-launcher`
and `pulsar-circle-to-search` live inside the same `Inled-Pulsar-OS/PKG`
monorepo as Sayri/pulsaros-timemachine/etc. -- same repo-wide
`license: null`, same blocker, not a packaging question. Desktop Icons
NG (`ding@rastersoft.com`, `gitlab.com/rastersoft/desktop-icons-ng`) has
a real license (confirmed via a real `COPYING` file in its GitLab repo
tree) but uses a real meson build system plus an apparmor profile --
substantially more packaging work than the other three, not started in
this pass.

**parchaos-cloud, deprioritized (user directed)**: see
`docs/gnome-phase2-findings.md`'s own update -- already shipped before
the licensing-audit habit started, same no-LICENSE gap as the rest of
Inled's original work. Left installed, not pulled, but no further work
goes into it; ParchaOS's own replacement is the intended long-term path
whenever there's time for it, not contingent on Inled's answer.

## Real human confirmation, 2026-09-24 -- the first since reboot

After the reboot every fix in this doc had been waiting on, the user
confirmed two of them visually on the real machine: **the dock looks
right** (parcha-dock rendering correctly, genie-effect-capable, real
traffic-light window controls visible elsewhere too) and **notification
banners are appearing top-right** (parchaos-notification-position's
real fix, not just a config value that looked right on paper). First
genuine on-screen confirmation for this whole batch of session
fixes -- closes the "on-screen confirmation" gap noted throughout this
doc for the dock and notification-position specifically. The rest of
tonight's queue (keyboard remap, the other extensions, GDM logo, light
mode, app renames) still awaits the same kind of direct confirmation.

## Update 2026-09-25: Desktop Icons NG shipped, extension list now complete

The one extension gap left open above (`ding`, Desktop Icons NG) turned
out much simpler than feared once actually read: no npm/TypeScript
toolchain at all, just plain JS and a normal meson build (unlike
`parchaos-hanabi`'s TypeScript build, which genuinely needed the
prebuild-on-a-network-host workaround). Packaged as
`parchaos-desktop-icons`.

Two real things found by reading the source directly instead of
assuming: (1) DING has a real, hard runtime dependency on a literal
`nautilus` binary -- it spawns `nautilus --version` at startup and
shows a blocking "mandatory" error if that fails. Confirmed
`parchaos-finder` (this profile's real nautilus replacement) installs
its binary at the literal path `/usr/bin/nautilus` and matches
`nautilus`'s own Epoch 0, so `Requires: nautilus` resolves correctly
via its Provides with no repeat of the pafari/epiphany-runtime epoch
saga from earlier tonight. (2) `apparmor/meson.build` installs an
AppArmor profile whenever the prefix is `/usr` -- dropped it in
`%install`, since Fedora uses SELinux, not AppArmor; that file could
never do anything on this distro.

Also carried over Pulsar OS's own real `blur-my-shell` blacklist
entries for DING (`ding`, `DING`, `org.gnome.Shell.Extensions.DING`
and wildcard variants) alongside the Hanabi renderer exception already
added, matching their proven config rather than guessing new values.

This profile now ships all of Pulsar OS's real, licensed extensions
that have a Fedora-buildable path -- the only remaining gaps
(`pulsaros-spotlight-launcher`, `pulsar-circle-to-search`) are blocked
on Inled's licensing answer, not a packaging question.

## What's next

See `docs/gnome-phase0-findings.md`'s own still-deferred items (deeper
Calamares macOS-esque skinning, a real Plymouth boot-splash theme,
Sayri's licensing question, the KDE-cruft cleanup) — none of those
changed status tonight. New from this session:

- Get a real person to run through the "still needs a human" checklist
  above and report back; fold any real bugs found into a phase 2 doc.
- Consider whether `packages.sh` and `packages.list` being two
  separately-synced files (this session's actual root cause for the
  six-package gap) is worth hardening against — e.g. a single
  `rsync_push.py` wrapper that always pushes the whole
  `profiles/pulsaros/` directory instead of individual files, so a
  future session can't repeat the same "pushed one, forgot the other"
  mistake.
