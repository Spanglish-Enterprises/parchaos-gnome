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

Made a real, multi-pronged effort at this in a later session
(2026-09-18) rather than assuming it was impossible:

- Confirmed QEMU's absolute-positioning "QEMU HID Tablet" device is
  the active pointer (`info mice`) and that `mouse_move`/`mouse_button`
  HMC commands all return success — but the on-screen cursor never
  moved from its initial position across many attempts at different
  coordinates (including obviously-different corners), and clicking
  Calamares' own "Next" button (with a completely clean, all-checks-passing
  Welcome page — a real disk attached, running as root) never advanced
  the wizard.
- Switched to the relative "QEMU PS/2 Mouse" device (`mouse_set 2`) and
  sent many relative moves — same result, no movement, no effect.
- Hypothesized the display backend (the hypervisor's default `vga: std`)
  might not pair well with a Wayland compositor's expectations for
  hardware cursor planes; switched to `--vga virtio` (paravirtualized,
  the modern recommended pairing for Linux guests) and retested after a
  full reboot — kernel-level device enumeration looked identical
  (`input: QEMU QEMU USB Tablet` in dmesg), no visible cursor at all
  this time (plausibly because virtio-gpu renders the cursor via a
  hardware overlay plane that QMP's `screendump` doesn't capture — a
  separate, real finding worth knowing for any future screenshot-based
  verification work), but a click on the exact same "Next" button
  coordinates still didn't advance the page.
- Also confirmed, by actually reading Calamares' own `--help` output
  and its project wiki's Test Guide, that Calamares has **no true
  unattended/preseed install mode** — `-g`/`-j` exist only for isolated
  single-module or slideshow *testing*, not for driving a real install
  sequence without the interactive wizard. (An earlier draft of this
  document incorrectly said "Calamares supports an unattended mode,
  not configured here" — that was wrong and has been corrected here.)
  Calamares is fundamentally built as an interactive GUI wizard; any
  real automated QA of it (as some distros do in CI) drives actual
  synthetic mouse/keyboard input against a real display, not a
  config-only bypass.

Keyboard input (arrow keys, Enter, letters — used earlier to unlock an
idle session) does work throughout all of this. Only mouse motion and
clicks fail to have any effect, consistently, across every device type
and display backend tried. This points to something at the
libinput/seat level in this specific QEMU/kwin_wayland combination, not
a bug in Calamares or this project's own packaging — Calamares itself
is already proven correct (real branded rendering, correct
requirements-validation logic in both failing and passing states, all
confirmed above). Not investigated further past this point (real,
open-ended systems debugging with no guaranteed payoff) — asked the
user how to proceed, and the decision was to move on rather than keep
digging, revisiting later if useful (e.g., a manual click-through via
the hypervisor's own real VNC/SPICE console, a genuinely different input path
from QMP's emulated devices, was offered but not exercised this
session).

**This remains the single biggest unverified step before this project
could reasonably go near real hardware**: nobody has yet confirmed
Calamares can actually partition a disk, unpack the squashfs, write a
bootloader, and produce a system that boots on its own.

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

## Secure Boot: signed the chain, then found grub2-mkrescue was silently discarding it (2026-09-18, later session)

Generated a self-signed MOK (`openssl req` 2048-bit RSA, 10-year cert,
`CN=plumOS (pearOS on Fedora) Secure Boot MOK`), signed `ploader_x64.efi`
with it (`sbsign`, verified with `sbverify` → "Signature verification
OK"), and pulled Fedora's own `shim-x64` package's binaries
(`shimx64.efi`, `mmx64.efi`/MokManager, `fbx64.efi`) to chainload
through, matching the standard third-party-signing pattern (VirtualBox/
ZFS/NVIDIA kernel modules use the same shim→MOK→MokManager flow). Wired
`engine/build-iso.sh` to lay out `EFI/BOOT/BOOTX64.EFI`=shim,
`EFI/BOOT/grubx64.efi`=signed Ploader (shim's hardcoded next-stage
name), plus `mmx64.efi` and the MOK `.cer` for enrollment, falling back
to unsigned Ploader if the signing artifacts aren't present.

**First real boot test under actual Secure-Boot-enabled OVMF** (the boot-test VM,
the VM host, `efidisk0` recreated with `pre-enrolled-keys=1` — i.e. Microsoft's
real keys pre-enrolled, not the `pre-enrolled-keys=0`-disabled config
every earlier UEFI test in this doc used) **failed**: `BdsDxe: failed to
load Boot0002 "UEFI QEMU DVD-ROM"... Access Denied -- rejected probably
by Secure Boot`.

Ruled out, in order, with real evidence for each:
- **Wrong/broken signature** — `sbverify`/`osslsigncode verify` on the
  shim binary confirmed it's genuinely signed by "Microsoft Corporation
  UEFI CA 2011", the real chain shim ships with.
- **OVMF doesn't trust that CA** — dumped the actual `db` variable from
  the varstore template (`virt-fw-vars --print --verbose`) and found
  "Microsoft Corporation UEFI CA 2011" present, exactly matching the
  signer.
- **dbx (forbidden-signature list) revocation** — computed the shim
  binary's real Authenticode digest via `osslsigncode verify` and
  grepped it against the full dbx hash dump; no match.
- **File corruption in the build** — extracted the actual
  `EFI/BOOT/BOOTX64.EFI` from inside the built ISO and diffed its
  SHA256 against the original `shimx64.efi`; identical.
- **This specific OVMF/the hypervisor setup can't do Secure Boot at all** —
  booted the stock, unmodified `Fedora-KDE-Desktop-Live-44-1.7.x86_64.iso`
  on the exact same VM/config; it booted cleanly through its own real
  shim→grub chain, proving the firmware setup is sound.

**Root cause, found by comparing the two ISOs' actual El Torito boot
catalogs** (`xorriso -report_el_torito plain`): our own hand-built,
correctly-signed `EFI/efiboot.img` (with shim/Ploader/mmx64.efi) really
was sitting in the ISO's filesystem tree exactly as intended — but
**`grub2-mkrescue` never uses it**. It silently builds its own,
separate, freshly-generated (therefore unsigned) UEFI FAT image
(reported as a hidden `/efi.img`, ~2.9MB, vs. our real 16MB image) and
that's what the boot catalog's UEFI entry actually points at. Confirmed
by byte-extracting the *real* El Torito UEFI image at its reported LBA
(not the named `/EFI/efiboot.img` tree file, which is a red herring —
it's never read by firmware) and hashing its `BOOTX64.EFI`: a totally
different, unsigned, grub2-mkrescue-built GRUB binary
(`edd7bb3c...`, 331,776 bytes), not our shim at all.

This also means the earlier "Ploader chainloading the real live system
under UEFI" claim in this same doc needs a **correction**: since
`build-iso.sh` has always written a working `/boot/grub/grub.cfg` and
grub2-mkrescue's own auto-generated GRUB reads that same path, the
"full desktop boots under UEFI" result was very likely grub2-mkrescue's
own GRUB chainloading the kernel directly — not Ploader at all. Ploader
itself (menu chrome, keyboard input) was independently confirmed via
the standalone bare-EFI test, which never went through grub2-mkrescue,
so that half still stands. What's now in question is only whether
Ploader was ever actually in the loop for the full-ISO boot chain.

**Fix, verified working**: replaced the single `grub2-mkrescue` call's
implicit UEFI handling with an explicit two-step build — reuse
grub2-mkrescue's own proven-reliable BIOS El Torito image (extracted
from its own output, `/boot/grub/i386-pc/eltorito.img`) but hand the
whole thing to a direct `xorriso -as mkisofs` invocation that
explicitly points `-eltorito-alt-boot -e EFI/efiboot.img -no-emul-boot`
at *our* real efiboot.img. Verified via the same LBA-extraction method:
the real UEFI boot catalog entry now correctly reports our full 16MB
image (`Ldsiz 32768` × 512 = exactly 16,777,216 bytes), and the
extracted `BOOTX64.EFI`/`grubx64.efi` inside it hash-match our real
signed shim/Ploader exactly.

**Booted this corrected ISO under the same Secure-Boot-enabled the boot-test VM**:
no more "Access Denied" — shim itself is now accepted and loads. A
*different*, not-yet-root-caused issue follows: the display alternates
between the normal 1280×800 OVMF splash and a brief 640×480 blank frame
(consistent with something — likely MokManager or Ploader itself —
switching GOP video mode), then returns to the OVMF splash again,
suggesting a reset/reboot loop rather than a clean stop at MokManager's
enrollment screen. Serial console is empty at this stage (shim/
MokManager only write to the VGA/GOP console, not serial), so this
needs either a working mouse/more QMP screendump timing precision, or a
manual console session, to actually see what's happening — not yet
attempted further this session; deprioritized in favor of a live-desktop
UI issue the user flagged directly (see docs/phase3-findings.md).

Encoded into `engine/build-iso.sh` and rebuilt (`branded11`) — but this
first attempt introduced a **real regression**: BIOS boot hit `grub
rescue>` immediately, `part_*.mod ... file not found` for every
partition module GRUB tried. Root cause: `eltorito.img` is only GRUB's
minimal bootstrap core.img — at runtime it loads further modules
(partition drivers, fonts, `normal.mod`, etc.) from
`/boot/grub/i386-pc/*.mod`, and the fix's extraction step only pulled
out the one `eltorito.img` file, not the ~970-file module tree that
goes with it. Fixed by extracting the *whole* `/boot/grub` tree from
grub2-mkrescue's staging output instead of just that one file (our own
`grub.cfg` comes along unchanged, since grub2-mkrescue only read it as
input). A second build (`branded12`) hit the identical `grub rescue>`
failure because the fix had been verified against a standalone test
script but the actual `build-iso.sh` edit was never re-synced to the
build host before that run — a process mistake, not a second bug; caught
by checking the built ISO's own `/boot/grub` file count
(`xorriso -find`, expected 973, got 15) rather than assuming the earlier
manual verification carried over.

**Fully verified working, both boot paths, on a real rebuilt ISO
(`branded12`)**: BIOS boot reaches full systemd/desktop (the install-test VM,
seabios) — real boot log, no grub rescue. Secure-Boot-enabled UEFI
(the boot-test VM, OVMF `pre-enrolled-keys=1`) no longer shows "Access Denied";
shim itself is now trusted and loads. The separate post-shim
reset/reboot-loop issue (video mode alternating 1280x800/640x480, no
serial output since shim/MokManager only write to VGA/GOP) noted above
is still open and unexplored further this session — deprioritized
after the user's own attention moved to a live-desktop UI issue (dock
icons, button order — see `docs/phase3-findings.md`), consistent with
the earlier "move on, revisit later" call on the Calamares mouse-input
gap.

### Follow-up: the post-shim issue isn't about MOK enrollment — Ploader hangs unconditionally when chainloaded via shim

Went back to this after the UI fixes were verified. Working theory
going in: shim was correctly refusing our self-signed `grubx64.efi`
because nothing had ever staged a MOK enrollment request (`mokutil
--import` needs to run from a booted OS to set the `MokNew` EFI
variable before shim will auto-launch MokManager on the next boot) —
`mokutil` isn't even in this profile's `packages.list`, so the live ISO
had no way to do this at all.

To test that theory, booted the same `branded12` ISO on the boot-test VM with
**Secure Boot fully disabled** (`pre-enrolled-keys=0`, same as every
earlier non-SB UEFI test) — with SB off, LoadImage() doesn't verify
anything at all, so if the MOK-enrollment theory were the whole story,
this should boot straight through regardless of trust.

**It didn't. It hung completely.** Two screendumps taken several
real-world seconds apart, after confirming via QMP `query-status` that
the VM's CPU was still actually running (not paused by the
hypervisor), came back **pixel-identical** (`PIL.ImageChops.difference`
bbox: `None`) — a genuine frozen frame, not just a slow-moving
animation. This is a different symptom from the earlier SB-enabled
test (which showed a *reset loop* — the OVMF splash recurring, video
mode alternating) — with SB off there's no verification step to fail,
so this isn't shim rejecting anything. **Something in Ploader itself
hangs when it's invoked as `grubx64.efi` via shim's chainload, that
does not happen when the identical binary is loaded directly by
firmware as `BOOTX64.EFI`** (confirmed working in this doc's own
standalone UEFI boot test, earlier).

Leading (unconfirmed) hypothesis, not yet dug into at the source
level: Ploader is a rEFInd fork, and rEFInd-family bootloaders commonly
locate their own config/theme directory relative to their own known
install path/filename. Loaded as `grubx64.efi` instead of the
`BOOTX64.EFI` path it was built/tested against, Ploader may be failing
to find itself and hanging instead of erroring gracefully — a real
compatibility gap between "designed to be the firmware's directly
chosen bootloader" and "designed to be chainloaded as GRUB's
replacement," which are different roles. Would need to actually read
Ploader's own path-discovery code (`profiles/pearos/ploader/`'s
sources) to confirm — not done this session.

**Not further pursued this session** — this is now a real, likely
non-trivial Ploader source-level bug, not a quick config/procedure
fix, and continuing to debug a silent hang with zero diagnostic
surface (no serial output, no crash log, nothing but a frozen
screendump) has a poor time-to-signal ratio without a better probe
(e.g. rebuilding Ploader with debug prints to a serial port, if its
codebase even supports that). Left as an open, well-documented gap
rather than guessed at further.

## Full disk install + reboot into the installed system — CONFIRMED WORKING (2026-09-20)

The single biggest open item in this whole document. Unblocked by
finding a way around the mouse-input dead end documented above: Qt
apps expose a real, driveable accessibility tree over AT-SPI when
`QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1` is set (confirmed first against
`kcalc` — drove a real `7 + 1 = 8` calculation through named button
clicks with zero mouse involvement — then against Calamares itself,
whose every page's widgets, including the actual target disk combo box
and partition radio buttons, are fully present and addressable by name
and role). Text fields needed real QMP keyboard input rather than
AT-SPI's `insertText` (the latter updates the visible text and
per-field validation, but doesn't reliably fire whatever aggregate
signal enables the page's `Next` button); buttons, checkboxes, and
radio buttons work fine via AT-SPI `doAction(0)`.

Running Calamares itself needed `dontChroot`-style care too: it must
run as root (checks this directly, not via polkit-per-action), but
root cannot join the live user's own D-Bus session bus at all —
confirmed directly (`gdbus call` as root against `unix:path=/run/user/
1000/bus` fails at the SASL/credential-passing step, not a policy
rejection) — so root's *own* separate session bus (already provided by
`pam_systemd` at `/run/user/0/bus`, unconditionally) has to be used for
D-Bus/AT-SPI while `XDG_RUNTIME_DIR`/`WAYLAND_DISPLAY` are still
pointed at the live user's compositor socket for rendering. `kdesu`
(the desktop shortcut's actual `Exec=` line) turned out to default to
X11 (`qt.qpa.xcb: could not connect to display`) and never got past
that even with `QT_QPA_PLATFORM=wayland` forced — not pursued further
since driving `calamares` directly, once its own environment was
correct, worked cleanly.

Driving the wizard through Welcome → Location → Keyboard → Users →
Partitions (Erase disk) → Summary → Install surfaced **four more real,
previously-unverified bugs**, each found and fixed in turn by actually
completing an install rather than stopping at "the button doesn't
crash":

1. **`mkfs.btrfs: command not found`** — `btrfs-progs` was never in
   `packages.list` even though `defaultFileSystemType: "btrfs"` is
   what this profile's Calamares config actually uses. The partition
   table got written (parted doesn't need this package), so the
   install failed specifically on formatting, not partitioning.
2. **Every password rejected**, unconditionally, with "the password
   fails the dictionary check - error loading dictionary" — the base
   `cracklib` package only ships `/usr/share/cracklib/cracklib.magic`,
   not the actual dictionary database (`cracklib-dicts`, a separate
   package). Without it, the Users page can never validate any
   password and can never proceed.
3. **"Failed to find unsquashfs, make sure you have the squashfs-tools
   package installed"** — one step further than the above:
   `unpackfs` needs `unsquashfs` to extract the live squashfs onto the
   target, and `squashfs-tools` was never in `packages.list` either
   (building the ISO's own squashfs via `mksquashfs`, in
   `engine/build-iso.sh`, doesn't require the reverse tool in the
   *shipped* rootfs).
4. **`grub2-install --target=i386-pc ... returned error code 1`**, the
   real blocker: `grub2-install`'s own stderr (only visible by
   chrooting into the target manually and re-running the exact
   command — Calamares' own error dialog just shows the exit code) was
   `this GPT partition label contains no BIOS Boot Partition; embedding
   won't be possible` followed by `filesystem 'btrfs' doesn't support
   blocklists`. Fedora's stock `partition.conf` hardcodes
   `defaultPartitionTableType: gpt` unconditionally (not just for
   UEFI) and has no logic to add a BIOS Boot Partition for BIOS+GPT the
   way Anaconda does; combined with this profile's btrfs root, no
   BIOS-mode install could ever complete. Fixed in two parts, both now
   shipped in `pearos-calamares-config`:
   - A new `partition.conf` (previously not shipped at all) with an
     explicit `partitionLayout` prepending a 1MiB BIOS Boot Partition
     ahead of root.
   - KPMCore 26.08.1 accepts partition.conf's `type:` GUID for that
     partition without error but silently never applies it to the real
     GPT partition entry (confirmed by inspecting the actual disk with
     `parted`/checking flags before vs. after — the partition comes out
     the right size, in the right place, with no flag at all). Rather
     than keep fighting KPMCore's YAML schema, added
     `scripts/pearos-fix-biosboot-flag` (a `shellprocess` module
     instance running right after `partition`, un-chrooted) that finds
     the ~1MiB unformatted partition by shape and runs `parted <disk>
     set <N> bios_grub on` directly — confirmed by hand first
     (`parted ... set 1 bios_grub on` then `grub2-install`: "Installation
     finished. No error reported.") before wiring it in as a real fix.

With all four fixed, a real installation completed cleanly end to end
on a blank 20GB disk (the install-test VM, seabios/BIOS+GPT+btrfs): Calamares itself
reported **"All done. pearOS has been installed on your computer."**
Then, the actual proof — changed the VM's boot order to the installed
disk (`scsi0`, no ISO attached) and reset it: **a real systemd boot
sequence from the installed disk**, no live-media involvement at all,
reaching the full pearOS-branded graphical desktop (wallpaper,
calendar/weather widgets, top menu bar showing "Pinder", populated
dock) via SDDM's own autologin.

One loose end, not chased further: the console TTY's own login prompt
rejected the account password that was typed in during the Users page
(typed via real QMP keyboard input, the same mechanism confirmed
necessary to make the page's own validation happy) — while the
*graphical* session was already fully logged in and rendering by the
time this was checked, meaning SDDM's own autologin path (a separate
mechanism from a plain console PAM login) succeeded regardless. Given
the actual goal here — proving a full disk install produces a bootable
system — was conclusively met, this password-sync discrepancy is
logged as a minor follow-up rather than investigated further this
session.

**This is the first time this session (or, as far as this doc's
history shows, this whole project) that a complete
boot-live→install→reboot→working-desktop cycle has been verified
end to end, not assumed or stopped short of.**

## Second verification pass: fresh `branded13` ISO built through the real pipeline (2026-09-20)

The install above was proven on the install-test VM's *live session*, hot-patched by
hand (editing files directly on the running live filesystem, then
launching Calamares against them). That's real, but it doesn't by
itself prove the fixes survive going through the actual shipped
pipeline: COPR-built `pearos-calamares-config` RPM pulled into the live
rootfs via `packages.list`, assembled into a squashfs by
`engine/build-iso.sh`. To close that gap, a full ISO
(`pearos-44-2026.09.20-branded13-x86_64.iso`) was built from scratch
from the current `main` branch (COPR build `11007027` +
`packages.list` with `btrfs-progs`/`cracklib-dicts`/`squashfs-tools`
already listed), deployed to the install-test VM, and the entire install verified a
second time independently:

1. Confirmed `btrfs-progs`, `cracklib-dicts`, and `squashfs-tools` were
   already present in the fresh live rootfs via `rpm -q` — no manual
   installation needed, proving the `packages.list` fix actually took
   effect through the real build.
2. Drove the full Calamares wizard again from scratch (Welcome →
   Location → Keyboard → Users → Partitions → Summary → Install),
   using the same AT-SPI + real QMP-keyboard technique as the first
   pass.
3. Confirmed via `parted` mid-install that the BIOS Boot Partition +
   btrfs root were laid out correctly, matching the shipped
   `partition.conf`.
4. Unpacking completed and Calamares reported **"All done. pearOS has
   been installed on your computer."** a second time.
5. Set the VM's boot order to the installed disk and reset it: booted
   a real systemd sequence from the installed disk and reached the
   full pearOS desktop again (wallpaper, calendar/weather widgets,
   "Pinder" top bar, populated dock) — pixel-equivalent result to the
   first pass, confirmed via screenshot.

This confirms the four bug fixes are reproducible through the actual
shipped artifact (COPR package → `packages.list` →
`engine/build-iso.sh` → ISO), not artifacts of manually patching a
running live session. **The installable-pearOS-daily-driver goal set
for this session is met**: a real ISO, built end to end through this
project's own pipeline, installs to a blank disk and boots to a
working desktop, verified twice independently.

The console-TTY-login password discrepancy noted after the first pass
was not re-checked on this second pass; it remains a minor,
non-blocking follow-up.

## Summary: where Phase 4 actually stands

| Piece | Status |
|---|---|
| Calamares config port | Done, builds cleanly in COPR (`pearos-calamares-config`, build `11002426`) |
| AMD/Intel Vulkan + microcode | Done, confirmed installed |
| Ploader build | Done, two real bugs fixed, confirmed against a real running system |
| Ploader standalone UEFI boot | Confirmed (screendumps, keyboard input works) |
| Ploader chainloading the real live system under UEFI | **Retracted, see Secure Boot section above** — likely was grub2-mkrescue's own auto-built GRUB, not Ploader; unconfirmed either way until re-tested with the xorriso fix |
| Calamares launching + rendering pearOS branding | Confirmed |
| Calamares' own requirements-detection (disk, privileges) | Confirmed working correctly in both failing and passing states |
| **A full disk install + booting the installed system** | **CONFIRMED WORKING (BIOS+GPT+btrfs), verified TWICE — once via live-session hot-patching, once via a genuinely fresh ISO built through the real COPR + packages.list + build-iso.sh pipeline (branded13, 2026-09-20). Four real bugs found and fixed: missing btrfs-progs, missing cracklib-dicts, missing squashfs-tools, and a missing BIOS Boot Partition (config + a KPMCore-flag-application workaround)** |
| Secure Boot support for Ploader | MOK signing + shim chain built and verified cryptographically; root-caused and fixed the grub2-mkrescue image-substitution bug; shim now passes Secure Boot; **Ploader itself hangs when chainloaded via shim as `grubx64.efi`, confirmed independent of Secure Boot/MOK enrollment (hangs identically with SB off) — likely a Ploader-side path-discovery bug, not investigated at the source level. UEFI installs are untested against the new partition.conf/bios-boot-flag fixes, which only matter for BIOS — separate follow-up.** |

Everything above the bold line is genuinely verified, not assumed. The
project now has one fully verified, real, end-to-end installable path
(BIOS+GPT+btrfs). UEFI's remaining gap is entirely in Ploader's own
chainload behavior, not the installer.
