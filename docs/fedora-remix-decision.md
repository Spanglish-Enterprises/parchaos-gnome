# Fedora Remix Trademark & Release Strings Decision

**Date**: 2026-09-28  
**Scope**: Ticket #106 (Legal sweep task T28)  
**Target Files**: `/etc/system-release`, `/etc/os-release`, `/usr/lib/os-release`, `CPE_NAME`

---

## 1. Background & Legal Analysis

Under the official **Fedora Project Trademark Guidelines** and **Fedora Remix Guidance**:
* Fedora software combined with third-party software, customized desktop environments, or modified system repositories (such as ParchaOS with its custom COPR, Flathub defaults, and customized desktop shell) constitutes a **Fedora Remix**.
* A Fedora Remix **must not** use official Fedora trademarks or represent itself as an official Fedora release.
* Retaining `/etc/system-release` with `"Fedora release <ver>"`, `/usr/lib/os-release` as `"Fedora Linux"`, and `CPE_NAME="cpe:/o:fedoraproject:fedora:<ver>"` on a distributed operating system image breaches the trademark guidelines by falsely indicating official Fedora provenance.

---

## 2. Decision

**The ParchaOS Project formally adopts the standard Fedora Remix compliant release model:**
1. **Transition to Generic Upstream Packages**: Replace `fedora-release` with `generic-release` and `generic-logos` in the base ISO package manifest (`profiles/parchaos/packages.list`).
2. **Explicit Distribution Identity**:
   * `/etc/os-release`: Branded as `ParchaOS` with `ID=parchaos` and `ID_LIKE=fedora`.
   * `CPE_NAME`: Set to `cpe:/o:parchaos:parchaos:<version_id>` to fully dissociate from `cpe:/o:fedoraproject:fedora`.
   * `/etc/system-release`: Written as `ParchaOS release <version_id>` (overriding both Fedora and generic release strings for login banners, motd, and CLI identity tools).
3. **Compatibility Safeguards**:
   * `VERSION_ID` is preserved unmodified from upstream (e.g., `44`), ensuring `dnf` variables (such as `$releasever`), repository metalinks, and package manager compatibility remain 100% functional.
   * `ID_LIKE=fedora` ensures systemd, flatpak portals, and app stores recognize the underlying OS family.

---

## 3. Technical Implementation

* **Base Packages (`profiles/parchaos/packages.list`)**:
  * Removed `fedora-release`.
  * Added `generic-release` and `generic-logos`.
* **OS Release Script (`packaging/parchaos-release/files/parchaos-os-release`)**:
  * Emits `CPE_NAME="cpe:/o:parchaos:parchaos:${version_id}"`.
  * Filters out stock `CPE_NAME`.
  * Explicitly writes `ParchaOS release ${version_id}` into `/etc/system-release`.
* **Package Spec (`packaging/parchaos-release/parchaos-release.spec`)**:
  * Bumped release to `1.0.0-7`.
  * Requires and hooks triggers on `generic-release-common`.
  * Provides symlink cleanup for both `/etc/os-release` and `/etc/system-release` in `%postun`.

---

## 4. Compliance Verification

* **Fedora Trademark Guidelines**: Compliant (no unauthorized Fedora marks on the distributed live or installed image).
* **Package Management**: Compliant (`$releasever` evaluates to matching numeric Fedora branch).
* **Identity Audit**: `/etc/system-release` and `/etc/os-release` report unified `ParchaOS` branding.
