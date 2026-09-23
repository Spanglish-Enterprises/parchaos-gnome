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
Release:        7%{?dist}
Summary:        ParchaOS (GNOME) Calamares installer branding and module configuration

License:        NOASSERTION
URL:            https://github.com/alexgalicea/parchaos-gnome
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
chmod 0755 %{buildroot}/usr/local/bin/parchaos-launch-calamares

%files
%{_sysconfdir}/calamares/settings.conf
%{_sysconfdir}/calamares/modules/
%{_sysconfdir}/calamares/scripts/
%{_sysconfdir}/calamares/branding/
/usr/local/share/applications/calamares.desktop
/usr/local/bin/parchaos-launch-calamares

%changelog
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
- Real user feedback ("logo seems a bit weird and off center"): fixed
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
