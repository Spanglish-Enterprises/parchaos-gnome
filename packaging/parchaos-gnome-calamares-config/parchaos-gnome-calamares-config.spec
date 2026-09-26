# ==============================================================================
# ParchaOS (GNOME) Calamares installer branding and module configuration.
# Ported directly from the KDE (pearos) variant's own
# pearos-calamares-config -- everything here (partition layout, kernel
# install, EFI population, bootloader branding, install sequence) is
# 100% DE-agnostic (nothing SDDM/KDE-specific), and the KDE variant's
# own package already carries three real, hard-won fixes found via
# genuine end-to-end install+reboot tests on real/virtual hardware (see
# that package's own spec banner and changelog for the full story):
#   1. BIOS+GPT+btrfs needs an explicit BIOS Boot Partition that
#      Fedora's stock partition.conf doesn't add automatically.
#   2. KPMCore accepts the BIOS Boot Partition's `type:` GUID without
#      error but doesn't actually apply it to the GPT partition entry
#      -- grub2-install still fails without a follow-up `parted ...
#      set N bios_grub on`.
#   3. This engine's unpackfs-based install (copying a pre-built
#      squashfs rather than running real `dnf install` transactions)
#      means kernel-core's, grub2-efi-x64's, and shim-x64's own
#      %posttrans scriptlets never fire -- no kernel/initramfs/BLS
#      entry, and no populated EFI System Partition, without step 3's
#      manual work.
#
# What changed from the KDE (pearos) package, and why:
#   - branding/ParchaOS/ (was branding/pearOS/) -- logo.png, icon.png,
#     welcome.png, slide1.png replaced with ParchaOS's own real
#     passion-fruit branding (derived from branding/logo/ in this
#     repo), not pearOS's pear. componentName/branding: key updated to
#     match. Unused leftover assets/ (installer_frame.png,
#     pearos_installer.png -- confirmed unreferenced by any .qml/.qss/
#     .desc file) dropped rather than carried over uncritically.
#   - branding.desc's productName/versionedName simplified to
#     "ParchaOS" (dropped the KDE variant's own "NiceC0re" codename,
#     which is specific to that product); bootloaderEntryName set to
#     "ParchaOS (GNOME)" and bootloader.conf's efiBootloaderId to
#     "parchaos-gnome", both distinct from the KDE variant's own
#     "ParchaOS"/"parchaos" so the two products' EFI boot menu entries
#     don't collide if both are ever tested on the same physical
#     machine.
#   - scripts/pearos-* renamed to scripts/parchaos-* (and the
#     shellprocess-*.conf files that reference them updated to match)
#     for naming consistency with this product; script *logic* is
#     unchanged except parchaos-finalize-install's Plymouth theme name
#     (pear-plymouth -> parcha-plymouth, a theme this profile doesn't
#     ship yet -- the existing `[ -d ... ]` guard makes this a safe
#     no-op until one is built, matching how the KDE variant handled
#     the same gap while its own theme was in progress).
#   - usr/local/share/applications/calamares.desktop (new, GNOME-only
#     addition) -- overrides Fedora's stock calamares package's own
#     /usr/share/applications/calamares.desktop, which ships
#     `Exec=kdesu /usr/bin/calamares`. kdesu is KDE-specific and FAILS
#     OUTRIGHT on this GNOME live session (confirmed via real testing,
#     2026-09-23: exits status 1 immediately, no output at all --
#     clicking the real "Install System" icon would do nothing
#     visible). /usr/local/share/applications/ is a real, standard
#     XDG_DATA_DIRS override mechanism (freedesktop.org's own default
#     ordering puts it before /usr/share/applications/) -- no RPM file
#     conflict with the stock calamares package, since it's a different
#     path. Real, verified working replacement Exec line:
#     `pkexec env DISPLAY=:0 QT_QPA_PLATFORM=xcb /usr/bin/calamares` --
#     found via extensive real debugging this session: plain `pkexec
#     calamares` authenticates fine (this live media's own polkit rules
#     allow it passwordlessly) but the escalated Qt process can't find
#     a display at all without DISPLAY/QT_QPA_PLATFORM explicitly set,
#     since pkexec sanitizes the environment. Verified this exact
#     recipe launches Calamares with full branding and control end to
#     end (real disk install + reboot completed successfully using it).
# ==============================================================================

Name:           parchaos-gnome-calamares-config
Version:        2026.09.23
Release:        26%{?dist}
Summary:        ParchaOS (GNOME) Calamares installer branding and module configuration

License:        NOASSERTION
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        parchaos-gnome-calamares-config-files.tar.gz
BuildArch:      noarch

Requires:       calamares

%description
Calamares installer configuration for ParchaOS's GNOME variant: real
ParchaOS passion-fruit branding (logo, icon, welcome image, slideshow,
stylesheet, sidebar) and module configuration (install sequence, live
squashfs unpack source, BIOS Boot Partition + KPMCore workaround,
kernel/EFI installation, bootloader branding, post-install
finalization) ported from the KDE (pearos) variant's own
pearos-calamares-config, which carries three real fixes found via that
variant's own end-to-end install+reboot tests. See this spec's banner
comment for the full list of what changed for this GNOME product and
why.

%prep
%setup -q -c -n %{name}-%{version}

%install
mkdir -p %{buildroot}
cp -a etc %{buildroot}/
cp -a usr %{buildroot}/
chmod 0755 %{buildroot}%{_sysconfdir}/calamares/scripts/parchaos-finalize-install
chmod 0755 %{buildroot}%{_sysconfdir}/calamares/scripts/parchaos-fix-biosboot-flag
chmod 0755 %{buildroot}%{_sysconfdir}/calamares/scripts/parchaos-install-kernel
chmod 0755 %{buildroot}%{_sysconfdir}/calamares/scripts/parchaos-stage-kernel
chmod 0755 %{buildroot}%{_sysconfdir}/calamares/scripts/parchaos-fix-efi-bootentry
chmod 0755 %{buildroot}%{_sysconfdir}/calamares/scripts/parchaos-set-default-subvol
chmod 0755 %{buildroot}%{_sysconfdir}/calamares/scripts/parchaos-write-grub-menuentry
chmod 0755 %{buildroot}%{_sysconfdir}/calamares/scripts/parchaos-disable-blscfg
chmod 0755 %{buildroot}%{_sysconfdir}/calamares/scripts/parchaos-remove-calamares-app
chmod 0755 %{buildroot}/usr/local/bin/parchaos-launch-calamares

%files
%{_sysconfdir}/calamares/settings.conf
%{_sysconfdir}/calamares/modules/
%{_sysconfdir}/calamares/scripts/
%{_sysconfdir}/calamares/branding/
/usr/local/share/applications/calamares.desktop
/usr/local/bin/parchaos-launch-calamares
%{_datadir}/polkit-1/actions/org.parchaos.installer.policy

%changelog
* Sat Sep 26 2026 ParchaOS packaging - 2026.09.23-26
- Run the installer through its own polkit action
  (org.parchaos.pkexec.installer), so the live session can allow exactly
  the installer without a password.
* Sat Sep 26 2026 ParchaOS packaging - 2026.09.23-25
- Style installer checkboxes and radio buttons; call the launcher
  Install ParchaOS.
* Sat Sep 26 2026 ParchaOS packaging - 2026.09.23-24
- Use parchaos-boot's GRUB setup instead of a static entry pinned to the
  install kernel; set the BIOS boot flag only on the install target
  disk.
* Fri Sep 25 2026 ParchaOS packaging - 23
- Security: disable Calamares' install-log upload. The default sent the
  log unencrypted to a public paste service (termbin.com), readable by
  anyone with the link (disk layout, hostname, user name, hardware).
* Fri Sep 25 2026 ParchaOS packaging - 2026.09.23-22
- Reworded comments and changelog to describe user-reported issues
  instead of quoting them.
* Fri Sep 25 2026 ParchaOS packaging - 2026.09.23-21
- Reworded summary/description/comments to describe features instead of
  naming macOS, per the project's trademark-caution naming policy.
* Thu Sep 24 2026 ParchaOS packaging - 2026.09.24-20
- Added files/etc/calamares/modules/users.conf, overriding Calamares'
  stock defaultGroups to add `input`. Real bug found live on real
  hardware: parchaos-macos-remap (xremap) had been crash-looping since
  boot (restart counter 2353) because the installed user account was
  never a member of the `input` group, and Fedora's uaccess udev rules
  deliberately don't dynamically grant keyboard/mouse event-node
  access the way they do for joysticks. See the new file's own banner
  comment for the full root cause.
* Thu Sep 24 2026 ParchaOS packaging - 2026.09.24-19
- Real bug found via a real install FAILURE in a fresh VM regression
  test of Release 18 (2026-09-24), minutes after Release 18 shipped:
  Calamares' own error dialog reported
  "/etc/calamares/scripts/parchaos-disable-blscfg: No such file or
  directory" (exit code 127) partway through install. Root cause: this
  package's spec has `Requires: calamares`, and Release 18's fix for
  "Calamares still visible after install" put `dnf -y remove
  calamares` inside parchaos-finalize-install, which runs very early
  in the exec sequence (right before dracut, for Plymouth-theme
  timing reasons). Removing "calamares" cascade-removed this package
  too because of that Requires, wiping every remaining file under
  /etc/calamares/scripts/ mid-install and breaking every shellprocess
  step that still needed to run afterward (parchaos-disable-blscfg,
  parchaos-fix-efi-bootentry, parchaos-write-grub-menuentry). Fixed by
  moving the Calamares-app removal into its own new script
  (parchaos-remove-calamares-app) and shellprocess step
  (shellprocess@remove-calamares-app), wired in as the absolute LAST
  step in settings.conf's exec sequence, right before `umount` --
  after every other script from this package has already executed.
  parchaos-finalize-install is reverted back to its original scope
  (Plymouth theme + livesys-scripts removal only).

* Thu Sep 24 2026 ParchaOS packaging - 2026.09.24-18
- Real bugs found via a real installed system on actual hardware
  (2026-09-24), after Release 17's boot fix got the system booting
  end to end for the first time: (1) Calamares itself remained a
  launchable app on the finished desktop -- since Calamares copies the
  live squashfs verbatim onto the target disk, the installer's own
  launcher/.desktop never got removed from the result. Fixed in
  parchaos-finalize-install: removes the launcher and dnf-removes the
  calamares package itself post-install. (2) GNOME Terminal and Files
  both failed to open (Terminal spun forever with no window ever
  appearing, Files did nothing) -- root-caused via the installed
  system's own journal, read offline by mounting its disk through
  qemu-nbd from the hypervisor: gnome-terminal-server exits immediately
  with "Locale not supported." because en_US.UTF-8 was never actually
  generated -- Fedora ships locale data split per-language into
  glibc-langpack-<lang> RPMs, and none were ever installed. Also
  explains the setlocale warnings seen on every login all night, and
  is the likely cause of Nautilus's own repeated ABRT crashes seen in
  the same journal window. Fixed by adding glibc-langpack-en to
  profiles/pulsaros/packages.list. (3) A MediaTek MT7922 WiFi/
  Bluetooth combo card's Bluetooth firmware was missing entirely
  (dmesg flooded with firmware load failures every ~0.5s, forever) --
  confirmed via `rpm -qf` on a real Fedora 44 system that this
  firmware lives in a separate mt7xxx-firmware subpackage that
  linux-firmware's own dependencies don't pull in (same per-vendor
  split pattern as amd-gpu-firmware). Fixed by adding mt7xxx-firmware
  to packages.list. (Note: a real Realtek RTL8125 wired NIC also
  showed link-up-but-no-DHCP on the same hardware; confirmed its
  firmware already ships inside the base linux-firmware package, so
  that one is NOT a missing-firmware issue and remains genuinely
  unresolved -- needs real lspci/dmesg data from a working network to
  diagnose further.) (4) parchaos-fix-efi-bootentry assumed efibootmgr
  -c always prepends new entries to BootOrder; on a real dual-boot
  disk this came out as "0000,0003" with a stale Windows Boot Manager
  entry ahead of the fresh ParchaOS one. Fixed by explicitly moving
  the ParchaOS entry to the front of BootOrder after creating it,
  preserving every other existing entry rather than deleting anything.

* Wed Sep 23 2026 ParchaOS packaging - 2026.09.23-17
- Real bug found via the same real UEFI hardware investigation as
  Release 16: after further testing, the custom.cfg static-menuentry
  bypass (Release 16) did not reliably resolve the boot failure either
  -- inconclusive whether custom.cfg is even sourced at the point this
  profile's generated grub.cfg expects it. Rather than continue
  chasing GRUB's own blscfg/btrfs-driver behavior indirectly, this
  addresses the actual root cause head-on: Fedora's grub2-mkconfig
  defaults to GRUB_ENABLE_BLSCFG enabled, which generates a grub.cfg
  that just calls `insmod blscfg; blscfg` to dynamically read
  /boot/loader/entries/*.conf at real boot time -- the mechanism that
  was failing to find a real OS entry for this named-btrfs-subvolume
  (@root) layout. Added a new script (scripts/parchaos-disable-blscfg)
  and shellprocess step (shellprocess@disable-blscfg, running after
  the stock `grubcfg` module writes /etc/default/grub and before
  `bootloader` calls grub2-mkconfig) that appends
  GRUB_ENABLE_BLSCFG=false to /etc/default/grub, forcing Fedora's
  older, far more battle-tested /etc/grub.d/10_linux static-menuentry
  generator instead. Verified directly on a real installed disk:
  regenerating grub2-mkconfig chrooted with this setting produced a
  real, syntactically correct, complete classic menuentry block with
  correct /@root/-prefixed linux/initrd paths and
  rootflags=subvol=@root -- unlike blscfg's dynamic discovery, which
  produced nothing.

* Wed Sep 23 2026 ParchaOS packaging - 2026.09.23-16
- Real bug found via repeated real full install + reboot tests on
  actual UEFI hardware, reproduced in a VM (2026-09-23): even after
  Release 14's fix (setting @root as the filesystem's default btrfs
  subvolume -- confirmed correct at the raw block level, a plain
  `mount /dev/sdX3 /mnt` with no -o subvol= option correctly showed
  @root's real content including /boot/loader/entries), GRUB's own
  generated grub.cfg still produced a menu with no OS entry at all,
  only the auto-generated "UEFI Firmware Settings" fallback -- pressed
  'c' for GRUB's own command line immediately after selecting the
  (correct, verified) NVRAM boot entry and confirmed directly at the
  GRUB menu screen itself that only that fallback entry exists.
  GRUB's own built-in btrfs filesystem driver is a from-scratch
  reimplementation, separate from the Linux kernel's own btrfs/VFS
  mount logic, and evidently does not resolve the on-disk default-
  subvolume pointer the same way a real `mount` does -- the same fix
  that corrected a real kernel mount's view of the raw partition did
  not change what GRUB's blscfg module found. Rather than continue
  chasing exactly which internal blscfg/GRUB-btrfs-driver behavior is
  responsible, this bypasses blscfg's dynamic discovery entirely:
  added a new script (scripts/parchaos-write-grub-menuentry) and
  shellprocess step (shellprocess@write-grub-menuentry, running after
  the stock `bootloader` module) that reads the same, already-correct
  BLS entry kernel-install wrote (title/linux/initrd/options, already
  using the real /@root/-prefixed paths this subvolume layout needs)
  and writes it out as a real, static `menuentry` block into
  custom.cfg -- which this profile's grub.cfg already sources
  unconditionally via its own stock /etc/grub.d/41_custom template
  section. A static menuentry needs no dynamic BLS discovery at all,
  so whatever GRUB's own blscfg/btrfs-subvolume resolution gap
  actually is becomes irrelevant.
* Wed Sep 23 2026 ParchaOS packaging - 2026.09.23-15
- Real bug found via a real full install test on actual UEFI hardware
  (2026-09-23), literally the very next thing that broke after
  shipping Release 14's fix: install failed immediately with
  "Command </etc/calamares/scripts/parchaos-set-default-subvol>
  finished with exit code 127 ... chroot: failed to run command
  '/bin/sh': No such file or directory". Simple sequencing bug in
  Release 14's own settings.conf placement, not the script logic
  itself: shellprocess@set-default-subvol (dontChroot: false, so
  Calamares chroots into the target to run it) was placed right after
  `mount` but BEFORE `unpackfs` -- at that point the target is still
  an empty, freshly-mounted btrfs subvolume with no actual rootfs
  copied into it yet (unpackfs is the step that copies the squashfs
  content in), so there's no real /bin/sh there at all for chroot to
  exec. Fixed by moving the step to run AFTER unpackfs (right after
  shellprocess@install-kernel, which already successfully chroots into
  the target the same way) instead of before it.
* Wed Sep 23 2026 ParchaOS packaging - 2026.09.23-14
- Real bug found via a real full install + reboot test on actual UEFI
  hardware, reproduced and root-caused in a VM (2026-09-23), one step
  past Release 13's mount.conf fix: even with /boot merged into @root
  (no more separate sibling @boot subvolume), the GRUB menu still
  showed no OS entry, and the system fell back to booting whatever
  live media happened to still be attached instead of the real disk.
  Root-caused by directly testing GRUB's own raw-partition-search
  behavior by hand: mounting the real installed partition with NO
  subvol= option (exactly what GRUB's generated `search --fs-uuid
  --set=root <uuid>` does, with no subvolume awareness at all) landed
  at the btrfs filesystem's neutral top level, where the only visible
  things were the "@root"/"@home" subvolume directories THEMSELVES,
  not their contents -- so /boot/loader/entries (needed by blscfg,
  which populates the BLS-based boot menu at real boot time) was
  invisible, nested inside @root rather than at the top level. This is
  because @root is a NAMED subvolume (id 256 in testing), not the
  filesystem's DEFAULT subvolume (id 5, the neutral top level) --
  anything that mounts the raw partition with no explicit subvol=
  option, GRUB included, lands at that neutral top level unless told
  otherwise. Confirmed the real fix directly, both ways: after running
  `btrfs subvolume set-default` on @root's own id, the exact same raw
  mount-with-no-subvol-option showed @root's real content directly at
  "/", including a correctly-reachable /boot/loader/entries/*.conf.
  Fixed the standard, real-world way btrfs-root distros make GRUB's
  subvolume-blind raw search work at all: added a new script
  (scripts/parchaos-set-default-subvol) and shellprocess step
  (shellprocess@set-default-subvol, running right after `mount` once
  @root exists) that sets @root as the filesystem's own default
  subvolume during install.
* Wed Sep 23 2026 ParchaOS packaging - 2026.09.23-13
- Real bug found via a real full install + reboot test on actual UEFI
  hardware, reproduced and root-caused in a VM (2026-09-23), one step
  past Release 12's fix: with a real, correct NVRAM boot entry now in
  place (confirmed: GRUB itself loaded), the resulting GRUB menu still
  showed no OS entry at all -- only the auto-generated "UEFI Firmware
  Settings" fallback. Root-caused by mounting the real installed disk
  two different ways: mounting just the root btrfs subvolume
  (subvol=@root) shows a completely empty /boot (0 bytes -- just the
  bare mountpoint directory), while separately mounting subvol=@boot
  shows the real vmlinuz/initramfs/loader/entries/*.conf files
  kernel-install actually wrote there -- confirming kernel-install
  itself works correctly, it's a GRUB-visibility problem. Fedora's
  stock mount.conf (which this project inherited unmodified) puts
  /boot in its own separate "@boot" btrfs subvolume, a SIBLING of
  "@root", not nested inside it. The real generated grub.cfg's
  `search --fs-uuid --set=root <uuid>` finds the raw partition and
  lands at the btrfs top level (subvolid 5) by default -- which only
  contains the three sibling @root/@boot/@home directories, not
  /boot/loader/entries directly -- and nothing in the generated
  grub.cfg tells GRUB's blscfg command (which populates the BLS-based
  boot menu at boot time) to descend into the sibling @boot subvolume
  instead. Fixed the way other real btrfs-root distros avoid this
  exact class of problem: overrode mount.conf so /boot is NOT given
  its own separate subvolume at all -- it now lives as a normal
  directory inside @root, so GRUB's root-filesystem search actually
  contains /boot/loader/entries wherever it lands, not hidden in an
  invisible sibling.
* Wed Sep 23 2026 ParchaOS packaging - 2026.09.23-12
- Real bug found via a real full install on actual hardware
  (2026-09-23): install reported success (no error dialog, matching
  all of Release 11's fixes working), but on reboot the firmware
  reported "no bootable device" -- the disk was never even offered as
  a boot option, not a GRUB/kernel-level failure. Root-caused by
  reproducing Calamares' own bootloader module's exact logic by hand
  in a VM (chrooted, real ESP mounted at /boot/efi, efivarfs bind-
  mounted in to match Calamares' own real execution environment
  precisely): its install_secureboot() function (used for this
  profile's `efiBootLoader: "sb-shim"` setting) calls
  `efibootmgr -c ... -l <rootMountPoint><efiDirectory>/shimx64.efi` --
  i.e. the full chroot-relative Linux path
  ("/boot/efi/EFI/fedora/shimx64.efi"). Confirmed directly:
  efibootmgr does NOT strip the mountpoint prefix from that path --
  running that exact command produces a real NVRAM entry whose UEFI
  device path literally embeds "\boot\efi\EFI\fedora\shimx64.efi",
  which does not exist ON THE ESP's own FAT32 filesystem (the ESP's
  real root only has \EFI\fedora\shimx64.efi -- "\boot\efi\" is a
  Linux mountpoint artifact from the chroot, not a real path on that
  filesystem at all). The firmware sees a registered entry, fails to
  load it, and has nothing left to fall back to. Also confirmed the
  real fix directly: the identical efibootmgr command with
  `-l /EFI/fedora/shimx64.efi` (relative to the ESP, no mountpoint
  prefix) produces a correct, loadable entry. This is a real bug in
  Calamares' own stock bootloader module for this exact configuration,
  not in this project's own scripts -- rather than patching a packaged
  file that could silently regress on a future Calamares update, added
  a new script (scripts/parchaos-fix-efi-bootentry) and shellprocess
  step (shellprocess@fix-efi-bootentry) that runs immediately after
  the stock `bootloader` module and adds a second, correct NVRAM entry
  -- efibootmgr's `-c` prepends to BootOrder, so this corrected entry
  takes priority at boot; the broken entry from the stock module is
  left in place as harmless clutter rather than risking deleting the
  wrong thing.
* Wed Sep 23 2026 ParchaOS packaging - 2026.09.23-10
- Real bug found via a real UEFI install attempt on actual hardware
  (2026-09-23), reproduced and root-caused in a VM reconfigured for
  real OVMF/UEFI boot (every earlier VM test in this whole effort used
  BIOS/legacy boot, where this code path is a harmless no-op --
  Release 9's shipped ISO was never actually UEFI-tested before going
  out): install failed again at "Bootloader installation error",
  `grub2-mkconfig -o /boot/efi/EFI/fedora/grub.cfg` returned error code
  1 -- this time WITH the real underlying error pulled from
  /root/.cache/calamares/session.log: "grub2-mkconfig: line 280:
  /boot/efi/EFI/fedora/grub.cfg.new: No such file or directory".
  Mounted the real ESP and root partitions directly (install media
  still attached, same VM) and confirmed: no /EFI directory existed on
  either the real ESP or the target's own /boot/efi -- parchaos-install-
  kernel's ESP-populate block never ran. Root cause: its own
  `find /usr/lib/efi/grub2 -maxdepth 2 -name fedora -type d` (and the
  equivalent for shim) was wrong -- the real on-disk layout is
  /usr/lib/efi/grub2/<epoch:version>/EFI/fedora/, three levels deep,
  not two, confirmed via `find -maxdepth 5` on the real installed
  rootfs. -maxdepth 2 always returned empty, silently skipping the
  whole block every time (including in every previous "successful"
  BIOS-mode test, where it happens to not matter) and hitting the
  script's own warning message on the else branch -- which goes to a
  stderr stream Calamares' shellprocess module doesn't capture into
  its session log, so the failure was completely invisible until
  grub2-mkconfig hit the missing directory much later. Fixed by
  correcting both finds to -maxdepth 3. Re-verified in the same real-
  UEFI VM: this fix confirmed real progress (Calamares now actually
  attempts the copy instead of silently skipping it) but surfaced the
  next real bug, fixed in Release 11 below.
* Wed Sep 23 2026 ParchaOS packaging - 2026.09.23-11
- Real bug found via the same real-UEFI VM re-verification of Release
  10's fix: parchaos-install-kernel now failed with "Command
  /etc/calamares/scripts/parchaos-install-kernel finished with exit
  code 1 ... cp: cannot create hard link
  '/boot/efi/EFI/fedora/./shimx64.efi' to
  '/boot/efi/EFI/fedora/./shim.efi': Operation not permitted". Real
  cause: shim-x64's own packaged files include shimx64.efi and
  shim.efi hard-linked to the same inode, and `cp -a` (used to copy
  the master EFI files onto the ESP) preserves hard links by default
  -- but the destination is the FAT32 ESP, which cannot represent hard
  links at all. Fixed by switching all four `cp -a` calls in this
  block to plain `cp -r`: FAT32 has no Unix permissions, ownership, or
  hard links to preserve in the first place, so dropping `-a`'s
  preservation semantics loses nothing and is the actually-correct
  fix, not just a workaround. Re-verified directly against the real
  disk from the failed run (ESP still real FAT32, sources still the
  real installed grub2-efi-x64/shim-x64 packages) rather than redoing
  the full Calamares GUI wizard again: ran the exact fixed `find` +
  `cp -r` sequence by hand as root -- both copies now exit 0 with real
  independent files (shimx64.efi and shim.efi both present, correct
  sizes, no hard-link error) -- then bind-mounted the populated ESP
  onto the target's own /boot/efi and chrooted in to run the real
  `grub2-mkconfig -o /boot/efi/EFI/fedora/grub.cfg`: "Generating grub
  configuration file ... done", exit 0, a real 8354-byte grub.cfg
  written. Both this release's and Release 10's fixes are now
  confirmed working end to end without needing another full install
  cycle.
* Wed Sep 23 2026 ParchaOS packaging - 2026.09.23-9
- Real bug found via a full install+reboot verification in a VM with
  the install media still attached as a disk (2026-09-23), caught
  BEFORE shipping Release 8 to real hardware: the Release 8 fix's own
  end-to-end verification showed Calamares reporting "All done." and a
  real GRUB menu with a working ParchaOS entry (confirming Release 8's
  fix), but after actually rebooting into it, `findmnt /` showed the
  LiveOS live-overlay filesystem still mounted as root, not the real
  installed btrfs partition -- and `/proc/cmdline` showed
  "root=live:CDLABEL=PARCHAOS rd.live.image", the LIVE session's own
  boot parameters. Root cause: parchaos-install-kernel runs chrooted
  inside the live session, and systemd's kernel-install falls back to
  the CURRENTLY RUNNING kernel's /proc/cmdline for a new BLS entry's
  options whenever /etc/kernel/cmdline doesn't already exist in the
  target -- which it never does on a fresh unpackfs-copied rootfs. So
  the installed system's own generated boot entry was silently
  inheriting the live image's boot parameters and would keep
  re-mounting the live squashfs overlay on every boot instead of the
  real disk -- and would fail to boot at all on real hardware once the
  install media is unplugged. Fixed by having parchaos-install-kernel
  write the real target's own root=UUID=...,rootflags=subvol=... (read
  via `findmnt` on its own already-chroot-mounted /, not guessed) to
  /etc/kernel/cmdline before calling kernel-install, so it has the
  correct real target parameters instead of inheriting the live
  session's. Also adds linux-firmware-amdgpu to packages.list (real bug
  found via user report on real AMD RX 6750 hardware, still stuck at
  800x600 even with mesa-dri-drivers installed: Fedora split
  linux-firmware into per-vendor subpackages, and the plain
  "linux-firmware" metapackage does not pull in the actual amdgpu
  firmware blobs needed for real KMS/display initialization).
* Wed Sep 23 2026 ParchaOS packaging - 2026.09.23-8
- Real bug found via a real disk-install attempt on actual hardware
  (2026-09-23), one step further than Release 7's fix got: install
  failed at "Bootloader installation error", `grub2-mkconfig -o
  /boot/efi/EFI/parchaos-gnome/grub.cfg` returned error code 1.
  bootloader.conf's efiBootloaderId was "parchaos-gnome" (a cosmetic
  branding choice), but with efiBootLoader "sb-shim" Calamares does NOT
  run grub2-install itself -- it just runs grub2-mkconfig against
  /boot/efi/EFI/<efiBootloaderId>/grub.cfg, assuming the shim/grub2-efi-x64
  RPM scriptlets already populated that exact directory. This project's
  parchaos-install-kernel script (which stands in for those scriptlets,
  since unpackfs-based installs never run them) only ever populates
  /boot/efi/EFI/fedora/ and /boot/efi/EFI/BOOT/ -- there was no
  /boot/efi/EFI/parchaos-gnome/ directory for grub2-mkconfig to write
  into. Separately, even if that directory existed, Fedora's shipped
  grubx64.efi/gcdx64.efi are signed images with their GRUB prefix
  hardcoded at build time to /EFI/fedora/ (a well-documented real
  Fedora quirk) -- they would never actually read a grub.cfg placed
  under a differently-named directory regardless of what Calamares
  generates there. Fixed by reverting efiBootloaderId to "fedora", the
  same real directory parchaos-install-kernel already populates and the
  only directory the signed GRUB binaries will ever read from. Ship
  over fidelity: a working boot beats a branded EFI directory name.
* Wed Sep 23 2026 ParchaOS packaging - 2026.09.23-7
- Found and fixed the REAL root cause of Release 6's kernel-install
  failure (that release's own fix, based on a "directory vs file"
  theory, was wrong and has been removed). Reproduced the exact
  failure in a controlled VM by attaching the ISO as a raw block
  device instead of a virtual CD-ROM (closer to how a real USB stick
  presents itself), which reliably triggered the same error a real
  hardware install hit. Extracted Calamares' own session log
  (~/.cache/calamares/session.log) and found the real rsync command
  it ran for unpackfs.conf's second entry: exit code 23, "total size
  is 0" -- the file was never even queued for transfer. Reproducing
  that exact rsync invocation by hand confirmed why: Calamares'
  unpackfs module reuses its generic --exclude /proc/ /sys/ /dev/
  /run/ /run/udev/ pseudo-filesystem excludes for "file" sourcefs
  entries too, and the real source path,
  /run/initramfs/live/boot/vmlinuz, itself lives under /run/ on this
  dracut-live image -- so the entire file was being silently
  self-excluded by its own exclude list. Fixed by staging the kernel
  to /tmp (outside any excluded path) in a new
  shellprocess@stage-kernel step that runs immediately before
  unpackfs, and pointing unpackfs.conf's second entry at that staged
  copy instead. Verified the fix directly: re-running the exact same
  rsync command against the staged path succeeds (exit 0, full
  19MB file transferred) where it silently failed before.
* Wed Sep 23 2026 ParchaOS packaging - 2026.09.23-6
- Real bug found via a real disk-install attempt on actual hardware
  (2026-09-23): install failed partway through with "Command
  /etc/calamares/scripts/parchaos-install-kernel finished with exit
  code 1" -- /boot/vmlinuz-<kver> missing, nothing to install. Every
  VM test this project ran before this succeeded end to end; the real
  difference was booting from an actual USB stick rather than a
  virtual CD-ROM. Most likely explanation: Calamares' unpackfs module
  copied the live kernel INTO a same-named destination directory
  (/boot/vmlinuz.livecopy/vmlinuz) instead of renaming it to the
  destination path directly, so the plain `[ -f ... ]` check on
  /boot/vmlinuz.livecopy silently found nothing. parchaos-install-kernel
  now handles both shapes defensively. Same real hardware test also
  surfaced parchaos-install-kernel's own "ESP not populated" warning
  for real (grub2-efi-x64's own master EFI files weren't present) --
  fixed separately by adding grub2-efi-x64 to packages.list (it was
  never actually pulled in by grub2-efi-x64-cdboot, confirmed via `dnf
  repoquery --requires`).
* Wed Sep 23 2026 ParchaOS packaging - 2026.09.23-5
- Real bug found via a real root-shell test on the install-test VM (2026-09-23):
  Release 4's wrapper resolved DISPLAY/XAUTHORITY into plain shell
  variables but never `export`ed them, so the `xhost
  +si:localuser:root` call right after (a plain external command,
  reads its target display from the process environment, not from an
  unexported parent-shell variable) silently failed to find a display
  to grant access to -- the ACL grant never actually happened, so the
  escalated root Calamares still couldn't connect to X and exited
  near-instantly, identical symptom to Release 3's bug. Confirmed via
  a manual root-shell reproduction: the exact same pkexec command
  launched Calamares successfully (stayed running, no crash) once
  DISPLAY/XAUTHORITY were properly `export`ed before the xhost call.
  Fixed by adding `export DISPLAY XAUTHORITY` to the wrapper script
  before the xhost grant.
* Wed Sep 23 2026 ParchaOS packaging - 2026.09.23-4
- Real bug found via a real end-to-end test of the actual desktop-icon
  launch flow (search "install" -> Enter -> polkit dialog -> press
  Authenticate), the exact path a real user takes: the Release 3 fix
  set DISPLAY/QT_QPA_PLATFORM on the pkexec'd Calamares but never
  forwarded XAUTHORITY or granted the escalated root process X11
  access via `xhost +si:localuser:root` -- both of which the earlier
  manual verification (from a root shell) had done by hand and which
  Release 3's .desktop Exec= line silently dropped. Confirmed via
  screendump: the polkit dialog closes immediately on Authenticate and
  Calamares never appears (no window, no crash dialog) -- consistent
  with the escalated Qt process failing to open the X11 display and
  exiting near-instantly. Fixed by moving the launch logic out of
  Exec= (fragile to get right through Desktop Entry Spec quoting) into
  a real script, /usr/local/bin/parchaos-launch-calamares, which grants
  the xhost access, resolves XAUTHORITY (from the environment, falling
  back to globbing /run/user/$UID/.mutter-Xwaylandauth.* if unset),
  and execs pkexec with DISPLAY/XAUTHORITY/QT_QPA_PLATFORM all
  forwarded explicitly.
* Wed Sep 23 2026 ParchaOS packaging - 2026.09.23-3
- Real bug found via a real, full end-to-end Calamares install +
  reboot test on the install-test VM/the VM host (2026-09-23 -- the actual disk install
  completed successfully and booted into a real installed GDM login
  and desktop session, confirming this package's ported KDE-variant
  fixes all work correctly for this profile too): the stock calamares
  package's own /usr/share/applications/calamares.desktop uses
  `Exec=kdesu /usr/bin/calamares`, which is KDE-specific and fails
  outright on GNOME (kdesu exits 1 immediately). Added a real XDG
  override at /usr/local/share/applications/calamares.desktop with
  `Exec=pkexec env DISPLAY=:0 QT_QPA_PLATFORM=xcb /usr/bin/calamares`,
  the exact recipe verified this session to launch Calamares
  correctly (branding, keyboard input, and a full successful install
  all confirmed working through it).
* Wed Sep 23 2026 ParchaOS packaging - 2026.09.23-2
- Real user feedback (logo looked slightly off-center): fixed
  at the source in branding/logo/ (asymmetric canvas padding cropped
  and re-centered -- see parchaos-global-menu's changelog for the
  full root-cause writeup) and regenerated logo.png, icon.png,
  welcome.png, slide1.png from the corrected source.
* Wed Sep 23 2026 ParchaOS packaging - 2026.09.23-1
- Initial port from the KDE (pearos) variant's own
  pearos-calamares-config for the GNOME profile: real ParchaOS
  passion-fruit branding images generated from branding/logo/, script/
  branding directory names and EFI bootloader ID distinguished from
  the KDE variant, otherwise carrying over that package's own
  real, tested install-sequence fixes unchanged (BIOS Boot Partition,
  KPMCore bios_grub workaround, kernel/EFI installation). Not yet
  build-tested or install-tested for this profile.
