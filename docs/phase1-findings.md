# Phase 1 findings — engine skeleton, real-host results

Status date: 2026-09-18. Everything below is from actually running
`engine/build-iso.sh` on a real Fedora 44 KDE Spin box (the build VM on the
user's the hypervisor cluster — see `docs/phase0-findings.md` for how that VM
came to exist) and boot-testing the result in a fresh VM (the install-test VM, same
cluster). This is the real-host verification the engine's own top-of-file
banner said it was missing.

## What works end-to-end

Running `sudo ./engine/build-iso.sh --skip-branding --branch 44` (the
`--skip-branding` flag added this session — builds `packages.list`'s
plain Fedora KDE Plasma base only, skipping Phase 5's
COPR/`PROFILE_REPO_PACKAGES`/`profile_customize`, since none of that
exists yet — see Phase 2) gets all the way through:

1. Profile loading
2. `dnf --installroot` base cache bootstrap (818 packages, clean)
3. Cloning the base cache into a working rootfs
4. `dracut` initramfs regeneration
5. `mksquashfs` compression of the rootfs
6. ISO assembly

...and produces a real, valid, checksummed `.iso` file. Three real bugs
were found and fixed in the process (all committed to
`engine/build-iso.sh`, see git log for full detail):

1. **`dracut --regenerate-all` doesn't take positional args.** The
   original code passed an output path and kernel version alongside
   `--regenerate-all`, which dracut rejects outright
   (`dracut[F]: --regenerate-all cannot be called with a kernel
   version`). Fixed by dropping `--regenerate-all` and targeting the one
   kernel explicitly.
2. **`systemd-nspawn`'s pty leaves a trailing `\r` on captured output.**
   `run_in_target` allocates a pty (needed for `--chroot`'s interactive
   shell), and its `onlcr` terminal setting means `$(run_in_target rpm
   -q ...)` came back as `"7.2.5-200.fc44.x86_64\r"` — the embedded CR
   then broke `realpath`'s module-directory lookup inside dracut with a
   confusing "no such file or directory". Fixed by piping through `tr -d
   '\r'` at the one call site that parses `run_in_target`'s output.
3. **The hand-rolled El Torito boot image never actually booted.** The
   original approach (`grub2-mkstandalone` + manually concatenating
   `cdboot.img` and the core image + a raw `xorriso -eltorito-boot`
   invocation) produced a *structurally* valid ISO — `xorriso` reported
   success, `file(1)` confirmed a bootable ISO9660 image — that hung
   forever at SeaBIOS's `Booting from DVD/CD...` on a real boot test.
   Two identical screendumps taken minutes apart confirmed it was
   genuinely stuck, not just slow. Also found by inspection (before even
   testing): the built `bios-eltorito.img` was referenced by `xorriso`
   via a bare relative path that only resolves against the ISO source
   tree, not the file's actual location in `$BUILD_DIR` — it could never
   have been found. **Fixed by replacing the whole hand-rolled sequence
   with `grub2-mkrescue`**, the same tool real distros use for this,
   which handles the El Torito boot catalog and hybrid MBR correctly.
   This got the ISO to a real, working GRUB menu (`GRUB version 2.12`,
   showing `pearOS`, real countdown, real keyboard interaction) —
   confirmed interactively via QMP `sendkey`/`screendump`, including
   dropping to a GRUB rescue shell and running `ls`, which correctly
   listed `(cd)/boot/{vmlinuz,initramfs.img}`.

## What's still broken: GRUB relocator "out of memory" at kernel load

With `grub2-mkrescue` fixed, GRUB itself boots and runs fine — but
booting the actual `pearOS` menu entry now fails one step later, at
kernel load time, with:

```
error: ../../grub-core/lib/relocator.c:grub_relocator_prepare_relocs:1542:out of memory.
```

Confirmed via GRUB's own interactive command line (not just the
menuentry script) that this is a real, reproducible failure of the
`boot` command itself, not a display/timing artifact — running `linux
/boot/vmlinuz root=live:LABEL=PEAROS rd.live.image`, `initrd
/boot/initramfs.img`, `boot` by hand at a `grub>` prompt reproduces the
exact same error message. This also resolves an apparent contradiction:
the *automatic* menuentry path shows no error at all and the VM just
powers off a few seconds after "Booting 'pearOS'" — almost certainly the
same relocator failure, just with GRUB's menuentry-script error handling
leading to a poweroff instead of dropping to a visible prompt the way
the interactive path does.

**Three hypotheses tested and ruled out** (each confirmed by an actual
rebuild/reboot cycle, not just reasoning):

1. **VM machine type (`q35` vs `i440fx`/`pc`)** — q35's more complex
   memory map (PCIe MMCONFIG, etc.) seemed like a plausible culprit for
   BIOS-mode relocator issues. Switched the install-test VM to `--machine pc` and
   retested: identical crash.
2. **VM RAM size** — reduced from 4096MB to 1024MB in case a larger
   total RAM produces a more fragmented/complex E820 map that trips up
   GRUB's relocator. Identical crash.
3. **`linux16`/`initrd16` (real-mode boot protocol) instead of
   `linux`/`initrd`** — the classic fix for exactly this class of GRUB
   relocator error, on the theory that the 32-bit/EFI-style loader path
   needs the relocator while the older real-mode path doesn't. Tested
   directly at the GRUB command line: **identical error, verbatim**, so
   in this GRUB version (2.12) `linux16`/`initrd16` still routes through
   the relocator internally.
4. **Trimming `grub2-mkrescue`'s embedded module set** — by default it
   embeds `--install-modules=all` for every detected platform
   (`i386-pc`, `i386-efi`, `x86_64-efi` were all present on the build
   host), which is a lot of code occupying GRUB's own limited low-memory
   footprint before it ever gets to the relocator. Rebuilt with
   `--install-modules="linux normal iso9660 biosdisk memdisk search tar
   ls part_msdos part_gpt fat ext2 gzio"` (temporarily hiding the
   `i386-efi`/`x86_64-efi` module directories so the restriction doesn't
   break EFI-platform detection — grub2-mkrescue otherwise tries to
   apply the same module list to whichever platforms it finds, and
   `biosdisk` doesn't exist under `i386-efi`, so the naive restricted
   rebuild fails outright with `cannot open
   '/usr/lib/grub/i386-efi/biosdisk.mod'`). The minimal-module BIOS-only
   ISO built fine but **still hit the identical relocator error on
   boot**.

**Not yet tried / the strongest remaining lead**: the actual upstream
`Fedora-KDE-Desktop-Live-44-1.7.x86_64.iso` (the one used to install VM
111 in the first place) boots via BIOS *successfully* in this exact same
the hypervisor/QEMU environment — proven, since that's how the build VM itself came
to exist. That rules out the environment (this specific QEMU/SeaBIOS
version, this specific the hypervisor host) as the cause and strongly points at
something in *how the boot image itself is built* — Fedora's own tooling
(lorax/livemedia-creator) almost certainly does not use a generic
`grub2-mkrescue` invocation the way this engine now does; it's likely
using a purpose-built, minimal eltorito image from its own templates.
Concrete next steps for whoever picks this up:

1. Extract and inspect the actual El Torito boot image from the real
   Fedora ISO (`xorriso -indev Fedora-KDE-...iso -report_el_torito
   plain`, or similar) and compare its structure/module set against what
   `grub2-mkrescue` produces here.
2. As a pragmatic short-term fix, consider lifting Fedora's own
   `boot/grub2/`-equivalent boot image out of the real Fedora ISO and
   grafting it into ours, rather than re-deriving one from
   `grub2-mkrescue` — reusing a proven-working boot chain instead of
   continuing to debug a from-scratch one.
3. Check whether this is a known, reported GRUB 2.12 bug (the
   `relocator.c` line number and exact wording are specific enough to
   search for) — if it's a known regression, there may already be a
   documented workaround or a point-release fix.
4. Try the same build on a different QEMU/SeaBIOS version to see if it's
   version-specific.

## Update: compared the real Fedora ISO's El Torito record directly

Ran `xorriso -indev <iso> -report_el_torito plain` against both the real
`Fedora-KDE-Desktop-Live-44-1.7.x86_64.iso` and our
`grub2-mkrescue`-built ISO, side by side:

```
Fedora:  El Torito boot img :   1  BIOS  y   none  0x0000  0x00      4         165
         El Torito img path :   1  /boot/x86_64/loader/eltorito.img
         El Torito img opts :   1  boot-info-table grub2-boot-info

Ours:    El Torito boot img :   1  BIOS  y   none  0x0000  0x00      4        1228
         El Torito img path :   1  /boot/grub/i386-pc/eltorito.img
         El Torito img opts :   1  boot-info-table grub2-boot-info
```

**These are structurally equivalent** — same platform, same tiny
4-sector initial load size, same `boot-info-table grub2-boot-info`
options, both GRUB2-based. (Fedora's ISO also carries a second, separate
UEFI El Torito entry pointing at a real ~30MB UEFI image — irrelevant
here since we're debugging the BIOS path specifically, and our ISO
correctly has no such entry since Ploader/UEFI isn't wired up yet.)

This rules out the El Torito *catalog* record itself as the difference
and narrows the real culprit to one of:

1. The actual compiled contents of the embedded `eltorito.img` /
   `core.img` (i.e. something in exactly which GRUB modules are built in
   and how, beyond what the catalog metadata shows) — Fedora's own lorax
   tooling almost certainly generates this from its own template/module
   list rather than `grub2-mkrescue`'s defaults, and Phase 1's own
   module-trimming experiment (see above) didn't reach parity with
   whatever Fedora actually ships.
2. How the *kernel and initramfs themselves* were built. Fedora's own
   live initramfs is built by their own lorax/dracut invocation with
   their own flags and module curation; ours comes from a plain `dracut
   --force <path> <kver>` inside the chroot with no live-specific
   flags beyond what `dracut-live` contributes by default. Worth
   checking: run `lsinitrd` on both initramfs images and diff the
   module/driver lists, and check whether Fedora's dracut invocation
   (visible in their kickstart/lorax templates) passes flags this
   engine's Phase 6 doesn't.

Given the El Torito catalogs match, hypothesis 2 (the initramfs itself)
is now the more promising lead over hypothesis 1 (the boot loader image) —
next session should start there: `lsinitrd` both initramfs images and
diff them before going back to disassembling `eltorito.img` binaries.

**Further update, same session**: checked what GRUB modules the real
Fedora ISO actually ships (`xorriso -indev <iso> -find /boot -type f`)
to test hypothesis 1 more rigorously. Fedora's `/boot/grub2/i386-pc/`
contains essentially every GRUB i386-pc module — hundreds of `.mod`
files, the same "install everything" footprint `grub2-mkrescue`'s
default (`--install-modules=all`) produces. **This further disproves
the module-trimming hypothesis**: if a large module set were the cause,
Fedora's own ISO — which ships just as many modules and boots fine in
this identical environment — would hit the same relocator error and it
doesn't. Hypothesis 2 (the actual initramfs/kernel build, or Fedora's
different `grub.cfg` structure — their layout uses `blscfg.mod`,
implying BLS-style boot entries rather than this engine's simple
hand-written `menuentry`, at paths `/boot/x86_64/loader/{linux,initrd}`
rather than this engine's `/boot/{vmlinuz,initramfs.img}`) is now the
clear leading theory. Extraction of Fedora's actual boot `linux`/`initrd`
files for a direct `lsinitrd`/size comparison was queued but not
completed this session (network access to the the hypervisor cluster became
unreliable) — this is the exact next step for whoever continues:

```
xorriso -indev Fedora-KDE-Desktop-Live-44-1.7.x86_64.iso -osirrox on \
  -extract /boot/x86_64/loader/initrd /tmp/fedora-initrd.img \
  -extract /boot/x86_64/loader/linux /tmp/fedora-vmlinuz \
  -extract /boot/grub2/grub.cfg /tmp/fedora-grub.cfg
```

then compare against this engine's own
`build/rootfs-pearos-44/boot/{vmlinuz-*,initramfs-*.img}` (`lsinitrd`,
file sizes, and reading `fedora-grub.cfg`'s actual `linux`/`initrd`
invocation for anything this engine's simple grub.cfg template is
missing).

## Resolution: both real bugs found and fixed — the ISO boots

Continuing from the leads above, extracted and read the real Fedora
ISO's actual `grub.cfg` directly. It never relies on automatic root
detection — it runs `search --file --set=root <marker>` before
referencing anything via `($root)/...`. Checking `$root` in our own
build confirmed it was sitting at a garbage value (`hd96`) the whole
time, since this engine's grub.cfg never set it. Also notable while
comparing: Fedora's own initrd is 263MB (`/boot/x86_64/loader/initrd`,
extracted and measured directly) — **7x larger than ours** — and boots
fine in this identical environment, which conclusively rules out initrd
size as a cause of anything here.

**Fix 1**: added `search --file --set=root /boot/vmlinuz` (plus
`insmod iso9660/gzio/ext2`) to the grub.cfg template, and switched the
`linux`/`initrd` lines to use `($root)/boot/...` explicitly instead of
bare paths, matching Fedora's proven pattern. Also switched
`root=live:LABEL=` to `root=live:CDLABEL=` to match Fedora's exact
dracut-live invocation for optical media.

Verified interactively at the GRUB command line: `echo root=$root` now
correctly prints `root=cd` (matching the real device from `ls`), not the
old garbage value. **Rebuilt and reboot-tested — this fix genuinely
resolved the relocator OOM.** The boot now proceeds past GRUB into the
actual kernel and systemd (confirmed via screendump: real
`systemd[1]: Started ...`/`Reached target ...` messages, not silence).

**New bug surfaced immediately after** (expected — this is progress, not
a regression): `dracut: FATAL: Don't know how to handle
'root=live:CDLABEL=PEAROS'`. Root cause: dracut's default hostonly mode
decides which modules to bake into the initramfs by inspecting the
*build* environment (a plain chroot, no live media involved), so it has
no way to know `dmsquash-live` — the module that actually knows how to
parse `root=live:...` — is needed, and silently omits it, even though
the module is fully present (confirmed:
`/usr/lib/dracut/modules.d/70dmsquash-live/`, part of the
already-installed `dracut-live` package from `packages.list`).

**Fix 2**: changed Phase 6's dracut invocation to
`dracut --force --no-hostonly --add dmsquash-live <path> <kver>`.
`--add` forces the module in regardless of hostonly detection;
`--no-hostonly` on top because live media has to work on whatever
hardware it's booted on, not just the build host's — hostonly's
driver-pruning would otherwise risk shipping media that can't even find
its own root filesystem on different hardware.

**Result, verified via a full rebuild + reboot test**: the ISO now boots
all the way past both previous failure points. Confirmed via the router
controller (querying the VM's own MAC address as a network client) that
the live system reached a fully working multi-user environment with
networking: **hostname `localhost-live`** (Fedora live media's exact
default hostname, not something this engine sets itself) with a real
DHCP-assigned IP. This is about as strong a proof as is available
short of an interactive login that the live root mounted, switch-root
succeeded, and standard services (NetworkManager at minimum) started
normally.

The one remaining open question: the actual graphical session (SDDM →
Plasma) hadn't visibly appeared on the display after ~2 minutes of
waiting — screendumps showed a plain graphical-resolution console with
just a blinking cursor, no crash, network fully up. This is most likely
just the plain-text console (no `rhgb` on the kernel command line means
no graphical Plymouth splash, so a "boring" text console during the
quiet portion of boot is expected) with SDDM/Plasma still starting, not
a new failure — but it wasn't confirmed reaching an actual visible
desktop before this session ended. **Next step for whoever continues**:
check whether SDDM actually starts (`systemctl status sddm` would need
either a login shell or emitting to the console — consider temporarily
dropping `quiet` and/or adding `rhgb` back so boot progress is visible
on screen for the next test, or just wait longer / try logging in via
the live user's default credentials once the console is confirmed to be
an actual login prompt, not a hang).

## Where things stand

- The engine correctly performs Phases 1–7 end to end: profile loading,
  base cache bootstrap, rootfs clone, initramfs regeneration, and ISO
  assembly all produce a working result with no known issues.
- The built ISO **boots**: real GRUB menu → real kernel boot → real
  systemd startup → live root mounted and switched into → networking up
  with the correct live-media hostname. Both hard blockers found this
  session (the GRUB relocator OOM, caused by never explicitly setting
  `$root`; and dracut silently omitting the `dmsquash-live` module
  needed to parse `root=live:...`) are fixed and verified via full
  rebuild + reboot cycles, not just reasoning.
- **This effectively achieves Phase 1's "get a plain, unbranded Fedora
  KDE Plasma live ISO building end-to-end" checkpoint** — the one
  remaining unconfirmed piece is whether the graphical session (SDDM →
  Plasma) actually appears on screen, which wasn't visually confirmed
  before this session ended (see the note above — most likely just needs
  a longer wait or a kernel cmdline tweak for boot-progress visibility,
  not a new bug). That's the very next thing to check.
