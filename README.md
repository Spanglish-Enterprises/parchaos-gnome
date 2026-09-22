# plumOS — pearOS on Fedora

A true pearOS variant on a **Fedora** base: same look, feel, and app set as
the existing Arch and Debian pearOS builds (dock, top bar, SDDM login theme,
icon pack, GTK/Kvantum theming, KWin blur/glass "liquid gel" compositor
effect) — only the base distro's package manager, installer, and bootloader
plumbing change. The desktop environment is **KDE Plasma**, non-negotiably:
pearOS's signature effects are built on KDE-specific APIs, and porting them
to GNOME would mean rebuilding the flagship blur/glass effect from scratch.

This repo is the build engine + profile for that variant, structured the
same way `Pear-Project/iso` (the Debian build) is: a generic, profile-driven
engine plus a `profiles/<name>/` directory holding everything specific to
one distro flavor (package list, repo definitions, branding, boot menu
text). The Fedora engine underneath is a full rewrite (`dnf`/`rpm` instead
of `debootstrap`/`apt`/`dpkg`), but the engine/profile separation and the
branding/app layer on top are the same pattern.

## Status

**A real, working, installable plumOS exists today** — both as a live ISO
you can boot and try, and as something you can install to a real disk.

- **Live boot**: confirmed working fully automatically under both BIOS and
  real UEFI firmware, reaching the complete branded desktop (dock, top bar,
  liquid-gel wallpaper, live widgets) with zero manual intervention. UEFI
  support was the last major gap and was root-caused and fixed — see
  [`docs/phase4-findings.md`](docs/phase4-findings.md) for the full story
  (a firmware-specific FAT image-size boundary, plus adopting Fedora's own
  real `grub2-efi-x64-cdboot` package instead of hand-building a UEFI
  bootloader).
- **Disk install**: BIOS+GPT+btrfs is fully verified end-to-end, twice,
  independently (install → reboot → real desktop, confirmed non-cosmetically
  by checking the booted system is genuinely running from the installed
  disk, not a live-media fallback). UEFI install mechanics (partitioning,
  kernel install, EFI System Partition population, real `efibootmgr` boot
  entry) are all individually verified correct; final reboot-to-desktop
  confirmation on this specific test setup is blocked by an apparent
  OVMF/virtio-scsi quirk unrelated to plumOS's own logic — see
  `docs/phase4-findings.md`.
- **Packaging**: all custom pieces (Ploader branding assets, `liquid-gel`,
  `pearos-dock`, `pafari`, `pearos-settings`, `pearos-branding`,
  `pearos-calamares-config`) build and publish successfully via a live COPR
  repo: [`alexgalicea/plumos`](https://copr.fedorainfracloud.org/coprs/alexgalicea/plumos/).
- **Branding**: the shipped OS identifies as **plumOS** end-to-end (boot
  menu, `/etc/os-release`, hostname, Calamares installer UI) while internal
  package/profile names stay `pearos-*`, since those name which upstream
  flavor is being ported, not the product.
- **UI parity reference**: a real, official pearOS NiceC0re install is kept
  running as a standing side-by-side comparison target — see
  [`docs/pearos-ui-reference/`](docs/pearos-ui-reference/) for screenshots
  and concrete findings (real Liquid Gel settings, real default Dock
  values, which parts of pearOS's UI are actually just restyled stock KDE
  components).

See [`docs/phase0-findings.md`](docs/phase0-findings.md) through
[`docs/phase4-findings.md`](docs/phase4-findings.md) for the complete,
detailed history — every real bug hit and how it was fixed, not just the
summary above.

## Reference repos

| Repo | Role | Porting need |
|---|---|---|
| [`pearOS-archlinux/iso`](https://github.com/pearOS-archlinux/iso) | Arch ISO builder (archiso/pacstrap) | Reference for package list only; build tooling is Arch-specific |
| [`Pear-Project/iso`](https://github.com/Pear-Project/iso) | Debian ISO builder | Template for this engine's structure (engine/profile split); implementation doesn't port (debootstrap/apt/dpkg) |
| [`pearOS-archlinux/liquid-gel`](https://github.com/pearOS-archlinux/liquid-gel) | KWin blur/glass effect (fork of `kwin-effects-forceblur`) | **Done** — builds and runs correctly on Fedora, packaged as `pearos-liquidgel` |
| [`pearOS-archlinux/pkgbuilds` → `pearos-dock`](https://github.com/pearOS-archlinux/pkgbuilds) | The actual dock (native Plasma 6 applet) | **Done** — packaged as `pearos-dock`, confirmed rendering under Wayland |
| [`pearOS-archlinux/pafari`](https://github.com/pearOS-archlinux/pafari) | Default browser (Epiphany/GNOME Web fork) | **Done** — packaged as `pafari` |
| [`pearOS-archlinux/pearos-settings`](https://github.com/pearOS-archlinux/pearos-settings) | Config files/scripts/skel | **Done** — packaged as `pearos-settings` |
| [`pearOS-archlinux/pearos-bootloader`](https://github.com/pearOS-archlinux/pearos-bootloader) (Ploader, rEFInd fork) | UEFI bootloader | Built and boots correctly, but not currently wired into the live UEFI chain (Fedora's own `grub2-efi-x64-cdboot` is used for real kernel boot instead — see `docs/phase4-findings.md`); re-integrating Ploader as a branded front-end is open future work |
| `pear-calamares-config` | Installer branding | **Done** — packaged as `pearos-calamares-config`, rewritten for Fedora's dracut/squashfs-live/grub2 stack |
| [`Pear-Project/pearOS-Default-*`](https://github.com/Pear-Project) (Kvantum, GTK, Icons, SDDM, Wallpapers) | Branding assets | **Done** — packaged as `pearos-branding` |

## Layout

```
engine/                     The generic Fedora build engine (build-iso.sh)
profiles/pearos/            Everything specific to the pearOS/plumOS flavor:
                             profile.conf, packages.list, repo.sh (COPR
                             setup), customize.sh (branding/session
                             defaults), ploader/ (vendored bootloader binary)
packaging/                  RPM .spec files + source for the pieces that
                             don't exist upstream as Fedora packages:
                             pafari, pearos-branding, pearos-calamares-config,
                             pearos-dock, pearos-liquidgel, pearos-settings
docs/                       Phase 0-4 findings (the real, detailed build
                             history) and docs/pearos-ui-reference/ (real
                             pearOS screenshots + comparison notes)
.github/workflows/          CI: automated ISO builds + checksums
```

## Roadmap

- [x] **Phase 0 — De-risk.** `liquid-gel` and `pearos-dock` build-compatibility
      confirmed on real Fedora KDE Spin hardware. See
      [`docs/phase0-findings.md`](docs/phase0-findings.md).
- [x] **Phase 1 — Engine skeleton.** Profile-driven Fedora live-ISO engine
      (`engine/build-iso.sh`) building a working, unbranded live ISO
      end-to-end. See [`docs/phase1-findings.md`](docs/phase1-findings.md).
- [x] **Phase 2 — Package repo.** Live COPR repo
      ([`alexgalicea/plumos`](https://copr.fedorainfracloud.org/coprs/alexgalicea/plumos/))
      with all custom packages building successfully. See
      [`docs/phase2-findings.md`](docs/phase2-findings.md).
- [x] **Phase 3 — Branding layer.** Icons, GTK theme, Kvantum, SDDM theme,
      wallpapers, dock, and desktop defaults all wired in and confirmed
      rendering on a real booted desktop. See
      [`docs/phase3-findings.md`](docs/phase3-findings.md).
- [x] **Phase 4 — Installer & boot.** `pearos-calamares-config` ported and
      working; BIOS+GPT+btrfs install verified end-to-end twice
      independently; UEFI live boot fixed and confirmed fully automatic;
      UEFI install mechanics individually verified, final reboot
      confirmation outstanding. See
      [`docs/phase4-findings.md`](docs/phase4-findings.md).
- [ ] **Phase 5 — Infra & release.** GitHub Actions for automated ISO
      builds + checksums; profile README with the Fedora-specific pitch
      (release cadence, SELinux, hardware/driver support); confirm UEFI
      install reboot on real hardware or a different test setup; decide on
      Ploader re-integration as a branded UEFI front-end.

Update the relevant `docs/phaseN-findings.md` as real hands-on results come
in — these are the actual source of truth for what's verified vs. assumed,
not this summary.
