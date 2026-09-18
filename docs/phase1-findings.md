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

## Where things stand

- The engine correctly performs Phases 1–6 (profile loading through
  initramfs regeneration) with no known issues.
- Phase 7 (ISO assembly) now produces a structurally correct, genuinely
  further-along-booting ISO than before this session (real GRUB menu,
  real kernel/initrd files present and locatable) but does not yet reach
  a working desktop — the relocator OOM blocks kernel load.
- This is the concrete blocker on Phase 1's "get a plain, unbranded
  Fedora KDE Plasma live ISO building end-to-end" checkpoint. Everything
  up to and including a bootable GRUB menu is proven working; booting
  the actual OS is not yet achieved.
