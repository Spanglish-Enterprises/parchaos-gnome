# Phase 4 findings — installer & boot

Phase 4 (per `README.md`) is: "Port `pear-calamares-config` (or theme
Anaconda instead); confirm Ploader boots under Fedora's EFI setup with
GRUB2 as the BIOS fallback." Going in, this was flagged as the biggest
unknown in the whole roadmap — nobody had looked at either half in any
real depth. Both halves got real, verified progress in a single session
(2026-09-18).

## The premise changed: Phase 0's "not found" note was stale

`docs/phase0-findings.md` recorded `pear-calamares-config` as "not
found at the expected location." Asked to search GitHub for anything
useful, and both of the repos Phase 0 couldn't find actually exist and
are active:

- [`pearOS-archlinux/pear-calamares-config`](https://github.com/pearOS-archlinux/pear-calamares-config) —
  the real branding/module config overlay, ~16MB, last updated August
  2026.
- [`pearOS-archlinux/calamares`](https://github.com/pearOS-archlinux/calamares) —
  pearOS's own Calamares notes/wrapper repo.

More importantly: **Fedora packages Calamares itself**, directly in
its own `fedora` repo — confirmed via `dnf5 info calamares` (3.3.14) on
the build VM, then `sudo dnf5 install -y calamares`, which pulled and
installed cleanly with no COPR, no compiling, nothing custom. This
completely changes Phase 4's shape: instead of "build or port an
installer," it's "install Fedora's own package and layer pearOS's
config on top" — a much smaller, well-bounded task. Decided against
theming Anaconda (the other option the roadmap left open) in favor of
real Calamares, since it matches upstream pearOS's actual install
experience and the porting surface turned out to be small.

## Calamares config port

Ported `pear-calamares-config`'s `/etc/calamares/` tree to Fedora as a
new package, `packaging/pearos-calamares-config/`. Unlike this
project's other specs, there's no upstream release tarball — this is a
hand-edited config overlay, and porting it meant genuinely rewriting
several files, not just repackaging them. The ported result lives as a
real, checked-in directory tree at `packaging/pearos-calamares-config/files/`,
and the spec builds its `Source0` tarball from that tree at package-build
time (`tar czf ... -C files .`) rather than fetching anything — see the
spec's own banner comment for the exact command.

### Ported as-is (no changes needed)

All of `branding/pearOS/` — logo, icon, welcome image, slideshow QML,
stylesheet, sidebar QML, translations. Pure UI assets, zero
distro-specific content, verified by reading them directly.

### Rewritten, and why

- **`settings.conf`** — upstream's module sequence uses Arch/mkinitcpio
  modules (`initcpiocfg`, `initcpio`, `shellprocess-alg-mkinitcpio`)
  and an Arch-only hardware-detection tool (`shellprocess-chwd`, chwd
  isn't packaged for Fedora at all). Dropped both; replaced initramfs
  regeneration with Calamares' own `dracut` module, which ships
  directly in Fedora's `calamares` package (confirmed via `rpm -ql
  calamares`). Also restores the standard `users` module to both the
  `show` and `exec` sequences — see the security note below for why.
- **`unpackfs.conf`** — upstream's source path
  (`/run/archiso/bootmnt/arch/x86_64/airootfs.sfs`) is archiso-specific
  and doesn't exist on this engine's live image at all. Verified via a
  real live boot's own `mount`/`find` output (this session) that this
  engine's actual runtime path is
  `/run/initramfs/live/LiveOS/squashfs.img` (Fedora dracut-live's
  standard convention, matching `engine/build-iso.sh`'s own ISO
  layout). Also dropped upstream's second unpack entry for the kernel:
  confirmed by reading `engine/build-iso.sh` directly that this
  engine's squashfs already contains a real kernel + initramfs under
  `/boot` (Phase 6 regenerates dracut's initramfs, Phase 7 copies both
  into `$ROOTFS_TARGET/boot` before squashfs'ing it), unlike archiso's
  `airootfs.sfs` — so a single unpack entry is enough.
- **`shellprocess-remove-livecd.conf` + `scripts/pearos-finalize-install`** —
  upstream calls a script (`/usr/local/bin/alg-finalisation`) that
  isn't part of the `pear-calamares-config` repo at all and appears to
  be Arch/pacman-specific, so there was nothing to port. Written fresh,
  intentionally minimal: systemd's own
  `ConditionKernelCommandLine=rd.live.image` guard already makes every
  `livesys-scripts` unit inert on a real (non-live) boot (see
  `docs/phase1-findings.md`'s autologin fix), so this engine doesn't
  need most of the "clean up live artifacts" work upstream's script
  presumably does. The one genuinely useful thing it does: sets
  pearOS's own `pear-plymouth` theme (packaged by `pearos-settings.spec`)
  as the installed system's default boot splash — otherwise the live
  image's `plymouth-theme-spinner` would stay default forever on a
  freshly-installed system. Runs *before* the `dracut` module in
  `settings.conf`'s sequence so the new theme actually gets baked into
  the regenerated initramfs, not skipped.
- **`bootloader.conf`** — not functionally changed from Fedora's own
  stock `calamares` package default (verified correct: `grub2-install`,
  `grub2-mkconfig`, real Fedora paths, read directly from
  `/usr/share/calamares/modules/bootloader.conf`) — the only edit is
  `efiBootloaderId: "fedora"` → `"pearos"` for a branded EFI boot menu
  entry name. Calamares doesn't merge an `/etc/calamares` override with
  the packaged default (one file wins, not a merge), so this still had
  to be a full copy of the stock file, not just the one changed line.

### Deliberately NOT ported, and why

**`shellprocess-pear-autouser.conf` — skipped entirely.** Upstream's
config does not use Calamares' own "create your account" step at all.
Instead it hardcodes a `default` user with the literal password
`pearos`, full passwordless sudo (`NOPASSWD:ALL`), and autologin — all
baked directly into the *installed* system, not a live-session-only
convenience. Found this while porting and flagged it directly rather
than silently replicating or silently dropping it: asked whether to
(a) match upstream exactly, (b) use Calamares' standard interactive
account-creation flow instead, or (c) keep a pre-made account but drop
the hardcoded password/NOPASSWD. Chose (b).

Worth noting: upstream's own *standard* `users.conf` (a completely
separate file from the shellprocess hack above) is **also** configured
with `doAutologin: true` and `allowWeakPasswords: true` — so that
file isn't ported either. This package ships no `users.conf` override
at all, deliberately falling back to Fedora's own stock `calamares`
`users.conf` default (`doAutologin: false`, `minLength: 6`,
`allowWeakPasswords: false` — verified by reading it directly on
the build VM).

**`packages.conf` — skipped, falls back to the packaged default.**
Upstream sets `backend: pacman` (meaningless on Fedora) with an
Arch-specific `try_remove` list. Fedora's own `calamares` package
already ships a correct default (`backend: dnf`, `try_remove:
[calamares]`) that's exactly right for this engine — everything else
is already baked into the squashfs, nothing else needs
installing/removing at install time. Verified by reading it directly
rather than assumed.

**`users.conf`, `partition.conf`, `mount.conf`, `welcome.conf`,
`grubcfg.conf`** — all fully generic/distro-agnostic. Where upstream's
own file was checked and found equally generic (`partition.conf`,
`mount.conf`, `welcome.conf`), it just wasn't copied — no reason to
duplicate content that would only drift from the packaged default over
time.

## AMD/Intel compatibility (user request: "we also need to make sure its amd compatible")

Checked what was already covered transitively vs. genuinely missing,
by reading the real installed package list in a built rootfs
(`rpm --root .../rootfs-pearos-44 -qa`) rather than guessing:

- **Already covered**: `mesa-dri-drivers` (AMD's `radeonsi` OpenGL
  driver) is already a transitive dependency of `plasma-desktop`/`kwin`
  — confirmed present without any explicit `packages.list` entry.
  `linux-firmware` (already in `packages.list`) bundles AMD GPU
  firmware blobs directly; Fedora doesn't split these into a separate
  per-vendor package.
- **Real gaps found and fixed**: `vulkan-loader` was present (just the
  dispatch library) but **no actual Vulkan driver** — `mesa-vulkan-drivers`
  (which provides `radeonsi`'s RADV Vulkan implementation, and Intel's
  ANV) was missing entirely. **Zero CPU microcode packages** were
  installed at all — `microcode_ctl` (Fedora's single package covering
  both AMD and Intel microcode, dispatched by vendor at boot) was
  missing. Both added to `packages.list`, both confirmed real Fedora
  package names via `dnf5 info` before adding, both confirmed installed
  in the rebuilt rootfs via `rpm -q`.

## Ploader (UEFI bootloader)

### Building it

Source: [`pearOS-archlinux/pearos-bootloader`](https://github.com/pearOS-archlinux/pearos-bootloader)
— confirmed via its own file layout (`EfiLib/`, `gptsync/`,
`Make.common`, `BUILDING.txt`) to be a straight rebrand of rEFInd
(`refind` → `ploader` renames throughout), not a from-scratch project.

Installed `gnu-efi`/`gnu-efi-devel` 3.0.18-16.fc44 (comfortably above
rEFInd's documented 3.0.4+ minimum) and built with `make` (auto-detects
GNU-EFI over TianoCore/EDK2). Two real problems surfaced, both fixed:

1. **`Make.common`'s own "Fedora x86-64" preset comment is wrong** for
   this exact package version — its suggested `GNUEFILIB=/usr/lib64/gnuefi`
   etc. paths don't exist on this system at all. Confirmed via
   `rpm -ql gnu-efi-devel`: the real files (`crt0-efi-x86_64.o`,
   `elf_x86_64_efi.lds`) are directly under plain `/usr/lib`. The
   tree's own **original, un-Fedora-patched defaults** are what
   actually works here — the Fedora-specific preset in the file is
   stale advice for an older `gnu-efi` packaging layout.
2. **Two real gnu-efi 3.0.18 API-drift compile bugs**, not Fedora
   workarounds — fixed via `0001-fix-gnu-efi-3.0.18-api-drift.patch`
   (checked into `profiles/pearos/ploader/`):
   - `EfiLib/legacy.c` and `ploader/lib.c` both define a
     `PearOSReallocatePool` wrapper that calls the real
     `ReallocatePool` with its arguments in the wrong order
     (`ReallocatePool(OldSize, NewSize, OldPool)` instead of
     `ReallocatePool(OldPool, OldSize, NewSize)` — confirmed against
     the actual signature in `/usr/include/efi/efilib.h`).
   - `EfiLib/legacy.c` calls `AsciiStrLen()`, which doesn't exist in
     this gnu-efi version — the real function is `strlena()` (also
     confirmed against `efilib.h`).
   - The repo's own `PKGBUILD` claims "this fork already carries its
     own fixes (PearOSReallocatePool, AsciiStrLen guard...)" — that
     claim doesn't match the actual `main` branch as of 2026-09-18.
     Not investigated further (regression vs. an older targeted
     gnu-efi version, unknown); the patch here is verified against
     what actually compiles today, which is what matters.

Output: `ploader/ploader_x64.efi` — copied into
`profiles/pearos/ploader/` along with the real theme assets (icons,
background, font — includes an `os_fedora.png` icon already), the
sample config, and license/attribution files. `efifs-drivers/` (rEFInd's
non-FAT filesystem read drivers) and `gptsync_x64.efi` (legacy-BIOS/GPT
helper) were **not** carried over — this engine's plan is for Ploader
to chainload Fedora's own already-installed GRUB2 EFI binary
(`grubx64.efi`), which lives on the FAT32 ESP itself, so neither is
needed. Revisit if that assumption changes. Confirmed the real config
filename Ploader looks for is `ploader.conf` (`#define
CONFIG_FILE_NAME L"ploader.conf"` in `ploader/config.h`) — matches the
`ploader.conf-sample` naming already in the repo.

### A process bug, not a Ploader bug: the binary never reached the build host

First branded ISO rebuild after building Ploader (`branded8`) still
logged `WARNING: ploader_x64.efi not built yet` — because the binary
had only been built and copied locally, never `scp`'d to the build VM (the
actual build host `engine/build-iso.sh` runs on). Pushed
`profiles/pearos/ploader/` (binary + theme + config sample + license
files) to the build VM and rebuilt (`branded9`); the log then showed
`Building UEFI boot image (Ploader)...`, confirming the engine took the
real path this time, not the fallback.

### Standalone UEFI boot test — confirmed working

Before testing the full ISO, tested `ploader_x64.efi` in isolation to
de-risk "does this binary even run" separately from "does the whole
ISO's boot chain work." Built a small FAT-formatted disk image
(`mkfs.vfat` + `mtools`' `mmd`/`mcopy` — same tooling
`engine/build-iso.sh` itself already uses for `efiboot.img`) containing
just `EFI/BOOT/BOOTX64.EFI` (= `ploader_x64.efi`) and the theme, no
`ploader.conf` (defaults only). Created a disposable VM (113)
on the VM host with real OVMF UEFI firmware
(`pve-edk2-firmware-ovmf`, `--bios ovmf --machine q35 --efidisk0 ...,pre-enrolled-keys=0`
— Secure Boot's pre-enrolled keys disabled since this binary is
unsigned) and booted it from the bare FAT image.

**Confirmed via QMP screendump**: Ploader's real menu chrome renders —
navigation arrow, and (since this bare test image has no OS present at
all) the correct fallback functions menu (Reboot/Shutdown/Firmware
Setup) with an auto-reboot countdown. Sent a keypress and confirmed the
countdown stopped, proving keyboard input works too. This is a valid,
working EFI binary under real UEFI firmware, independent of anything
else in this project.

### Full-ISO UEFI boot test — confirmed working, including the deeper unknown

Pushed the real `branded9` ISO (with Ploader now actually built into
its `EFI/BOOT` per the engine's `HAVE_UEFI` path) to the VM host and booted it
on the same OVMF-backed the boot-test VM (swapped its disk for the ISO as a
cdrom, `--boot order=ide2`). This tests the part the standalone test
couldn't: **does Ploader actually detect and chainload a real bootable
OS**, not just render its own menu with nothing to boot.

**Confirmed via a sequence of QMP screendumps**:
1. Real systemd/kernel boot log scrolling on screen (`systemd-sysctl`,
   `systemd-udevd`, etc.) — proof Ploader found and launched the ISO's
   real kernel (via chainloading its GRUB2, since Ploader doesn't parse
   ext4/xfs kernels directly without the filesystem drivers this
   project deliberately didn't carry over).
2. pearOS's actual Plymouth boot splash (the bitten-pear logo, from
   `pear-plymouth`) rendering mid-boot with a progress bar.
3. A fully rendered live desktop (calendar/weather widgets, wallpaper)
   — the exact same live session already confirmed working under BIOS
   boot in Phase 1/3, now confirmed reachable under real UEFI too.

This closes out the single biggest open question from the original
Phase 0/4 framing: Ploader doesn't just build and render a menu, it
successfully boots this engine's actual live system under real UEFI
firmware, chain to chain.

## Calamares launch test — structurally confirmed, full install not attempted

With a real UEFI-booted desktop already up on the boot-test VM, attempted to
verify Calamares itself, not just its packaging.

**First attempt** (launched via `sudo -u liveuser env
XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-0 calamares &`,
same technique used earlier this session to launch Dolphin into a live
Wayland session): the process ran but never produced a visible window
or any log output for 100+ seconds, `State: R (running)` the whole
time. Sampling `/proc/<pid>/stack` repeatedly showed it stuck in
`squashfs_decompress`/`squashfs_read_data` every time — traced this to
the boot-test VM only having 1024MB RAM (set for the earlier bare-EFI-binary
test, never bumped up before reusing the VM for a full desktop +
Calamares). A live Plasma session plus a Qt6/QML app with a large
branding asset set doesn't fit comfortably in 1GB, causing heavy
squashfs re-decompression thrashing rather than a real Calamares bug.
Bumped the VM to 4096MB and rebooted.

**Second attempt, after the memory fix**: Calamares produced real log
output quickly (`Cannot open display "default display"` plus benign
MESA/ZINK software-rendering warnings already seen elsewhere in this
project's logs) and, per a screendump, **rendered a complete, correctly
branded window**: "Welcome to the pearOS installer," the pearOS
dark stylesheet, macOS-style traffic-light window controls, and the
full step sequence in the bottom nav bar (Welcome / Location / Keyboard
/ Users / Partitions / Summary / Install / Finish) — confirming
`settings.conf`'s restored `users` step is correctly wired in. The page
correctly reported its own real requirements failures for this test
environment: no target disk attached, and not running with
administrator rights (launched as `liveuser`, not root) — this is
Calamares' own validation logic working exactly as designed, not a
config bug.

**Third attempt**, to push the confirmation further: attached a real
20GB virtual disk to the boot-test VM and relaunched Calamares directly as root
(bypassing `calamares.desktop`'s `kdesu` wrapper, which needs a
password-entry dialog impractical to drive via QMP; this live image's
root has no password anyway, matching the earlier serial-console access
pattern used throughout this project). Result: **a completely clean
Welcome page, zero errors, "Next" enabled** — both real requirements
resolved by the disk + root fixes, confirming the requirements-checking
logic responds correctly to real environment changes, not just always
red or always green.

**Not attempted, and why**: clicking through the rest of the wizard
(Location → Keyboard → Users → Partitions → Summary → Install →
Finish) to a real disk write and a genuine installed-system boot test.
A single `sendkey ret` attempt (hoping Enter would trigger the
already-focused "Next" button) didn't advance the page — focus was
elsewhere (the language combo box), and blindly guessing at tab-order
or coordinates via QMP keyboard/mouse input risks landing on the wrong
control and producing a misleading result rather than a real one. This
needs either a scriptable/unattended Calamares config (Calamares
supports an unattended mode, not configured here) or real
mouse-driven interaction (VNC/SPICE), neither of which this session
set up. **This remains the single biggest unverified step before this
project could reasonably go near real hardware**: nobody has yet
confirmed Calamares can actually partition a disk, unpack the
squashfs, write a bootloader, and produce a system that boots on its
own.

## Secure Boot — not addressed, flagged for whoever continues

`ploader_x64.efi` is unsigned. Every standalone/full-ISO UEFI test this
session ran with Secure Boot's pre-enrolled keys explicitly disabled
(`pre-enrolled-keys=0`) specifically to allow this. Real PCs ship with
Secure Boot enabled and Microsoft's keys pre-enrolled by default, and
will refuse to execute an unsigned EFI binary outright. Two paths
forward, neither attempted here: get Ploader properly signed
(shim + MOK enrollment, the standard approach most third-party
bootloaders use), or document that users need to disable Secure Boot
before installing. This is a real gap between "boots in every test
this session ran" and "boots on a real PC out of the box."

## Summary: where Phase 4 actually stands

| Piece | Status |
|---|---|
| Calamares config port | Done, builds cleanly in COPR (`pearos-calamares-config`, build `11002426`) |
| AMD/Intel Vulkan + microcode | Done, confirmed installed |
| Ploader build | Done, two real bugs fixed, confirmed against a real running system |
| Ploader standalone UEFI boot | Confirmed (screendumps, keyboard input works) |
| Ploader chainloading the real live system under UEFI | Confirmed (boot log, Plymouth splash, full desktop, all under real OVMF) |
| Calamares launching + rendering pearOS branding | Confirmed |
| Calamares' own requirements-detection (disk, privileges) | Confirmed working correctly in both failing and passing states |
| **A full disk install + booting the installed system** | **Not attempted — needs unattended Calamares config or real mouse-driven (VNC/SPICE) testing** |
| Secure Boot support for Ploader | Not addressed |

Everything above the bold line is genuinely verified, not assumed. The
bold line is the actual remaining unknown before this project could
reasonably be tested on real hardware.
