# plumOS — pearOS on Fedora

A true pearOS variant on a **Fedora** base: same look, feel, and app set as
the existing Arch and Debian pearOS builds (dock, top bar, SDDM login theme,
icon pack, GTK/Kvantum theming, KWin blur/glass compositor effect) — only
the base distro's package manager, installer, and bootloader plumbing
change. The desktop-environment layer is **KDE Plasma**, non-negotiably:
pearOS's signature effects are built on KDE-specific APIs, and porting them
to GNOME would mean rebuilding the flagship blur/glass effect from scratch.

This repo is the build engine + profile for that variant, structured the
same way `Pear-Project/iso` (the Debian build) is: a generic, profile-driven
engine plus a `profiles/<name>/` directory holding everything specific to
one distro flavor (package list, repo definitions, branding, boot menu
text). The Fedora engine underneath is a full rewrite (`dnf`/`rpm`/
`livemedia-creator` instead of `debootstrap`/`apt`/`dpkg`), but the
engine/profile separation and the branding/app layer on top are the same
pattern.

## Status

Phase 0 (de-risking) is done as far as it can be done without a real Fedora
KDE Spin machine — see [`docs/phase0-findings.md`](docs/phase0-findings.md)
for what was verified against the actual upstream source, and what's still
open. Phase 1 (engine skeleton) is in progress. See the checklist below.

## Reference repos

| Repo | Role | Porting need |
|---|---|---|
| [`pearOS-archlinux/iso`](https://github.com/pearOS-archlinux/iso) | Arch ISO builder (archiso/pacstrap) | Reference for package list only; build tooling is Arch-specific |
| [`Pear-Project/iso`](https://github.com/Pear-Project/iso) | Debian ISO builder | **Template for this engine's structure** (engine/profile split); implementation doesn't port (debootstrap/apt/dpkg) |
| [`pearOS-archlinux/liquid-gel`](https://github.com/pearOS-archlinux/liquid-gel) | KWin blur/glass effect (compiled, fork of `kwin-effects-forceblur`) | Needs an RPM spec + a real Fedora build attempt — see Phase 0 findings, biggest fidelity risk |
| [`pearOS-archlinux/pkgbuilds` → `pearos-dock`](https://github.com/pearOS-archlinux/pkgbuilds) | The actual dock (native Plasma 6 applet, **not** the Android/Trebuchet fork) | Needs an RPM spec + Wayland behavior test |
| [`pearOS-archlinux/pafari`](https://github.com/pearOS-archlinux/pafari) | Default browser (Epiphany/GNOME Web fork) | Meson/Ninja build already; needs an RPM spec |
| [`pearOS-archlinux/pearos-settings`](https://github.com/pearOS-archlinux/pearos-settings) | Config files/scripts/skel | Static files; simple noarch RPM |
| [`pearOS-archlinux/pearos-bootloader`](https://github.com/pearOS-archlinux/pearos-bootloader) (Ploader, rEFInd fork) | UEFI bootloader | Distro-agnostic (GNU-EFI/EDK2) — reusable as-is |
| `syslinux` (Arch/Debian) | BIOS/non-EFI fallback | **Swapped for GRUB2** — Fedora convention, not ported |
| [`Pear-Project/pearOS-Default-*`](https://github.com/Pear-Project) (Kvantum, GTK, Icons, SDDM, Wallpapers) | Branding assets | Plain files (CSS/QML/icons); repackage as RPM with minimal changes |
| `pear-calamares-config` | Installer branding | Not found at the expected location as of this writing — needs a maintainer pointer (see Phase 0 findings) |

## Layout

```
engine/            The generic Fedora build engine (build-iso.sh)
profiles/pearos/   Everything specific to the pearOS flavor: profile.conf,
                    packages.list, repo.sh (COPR/RPM Fusion setup),
                    customize.sh (branding/session defaults)
packaging/         RPM .spec files for the pieces that don't exist upstream
                    as Fedora packages yet
docs/              Phase 0 findings, working notes
.github/workflows/ CI: automated ISO builds + checksums
```

## Roadmap

- [x] **Phase 0 — De-risk.** `liquid-gel` build-compatibility research and
      dock identification done at the source level; a real build/Wayland
      test on Fedora KDE Spin hardware is still the next concrete step.
      See [`docs/phase0-findings.md`](docs/phase0-findings.md).
- [ ] **Phase 1 — Engine skeleton.** Profile-driven Fedora live-ISO engine
      (`engine/build-iso.sh`, `livemedia-creator`-based). Get a plain,
      unbranded Fedora KDE Plasma live ISO building end-to-end before any
      pearOS branding.
- [ ] **Phase 2 — Package repo.** COPR repo for anything not in Fedora's
      official repos; `.spec` files for `liquid-gel`, `pafari`,
      `pearos-settings`, `pearos-dock` (drafted in `packaging/`, untested
      against a real Fedora build root — see the banner in each spec).
- [ ] **Phase 3 — Branding layer.** Icons, GTK theme, Kvantum, SDDM theme,
      wallpapers repackaged as RPMs and wired into the profile as live-
      session defaults.
- [ ] **Phase 4 — Installer & boot.** Port `pear-calamares-config` (or
      theme Anaconda instead); confirm Ploader boots under Fedora's EFI
      setup with GRUB2 as the BIOS fallback.
- [ ] **Phase 5 — Infra & release.** GitHub Actions for automated ISO
      builds + checksums; profile README with the Fedora-specific pitch
      (release cadence, SELinux, hardware/driver support).

Priority order matters: Phases 2–5 assume Phase 0's two risks are resolved,
since either one could change assumptions baked into later phases (session
default, effect availability). Update `docs/phase0-findings.md` as real
hands-on results come in.
