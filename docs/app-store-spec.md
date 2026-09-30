# ParchaOS App Store Specification

This document defines the branding and configuration of the ParchaOS App Store. 

**Legal Note**: This is a pure theming and configuration layer over the official GNOME Software (`gnome-software`) project. It has zero relation to Inled's Pulsar Store code or branding.

## 1. Branding & Identity
Instead of writing a custom app store from scratch, we leverage the robust `gnome-software` package and rebrand it for a seamless ParchaOS experience.
- **Name**: "Parcha Store"
- **Icon**: An original ParchaOS icon, injected via `parchaos-icon-theme`.
- **Implementation**: The `.desktop` file (Display Name and Icon) will be overridden using the existing RPM `%triggerin` hook pattern already established in `packaging/parchaos-app-renames/`.

## 2. Software Sources Configuration
The store must be fully populated with applications out-of-the-box.
- **Flathub**: We will ship a default `.flatpakrepo` file pointing at Flathub, ensuring a massive library of containerized sandboxed apps is available immediately.
- **ParchaOS COPR**: We will inject an AppStream/software-source entry pointing GNOME Software at the official ParchaOS COPR (`alexgalicea/parchaos-gnome`). 
  - *Goal*: Ensure our custom applications (e.g., `parchaos-cloud`, `parchaos-timemachine`) are fully browsable, searchable, and installable via the GUI, rather than forcing users into the `dnf` CLI.

## 3. Uninstallation Flow (Future Integration)
- Once the "dependency-tracked app uninstall helper" (Ticket #125) is completed, it will be surfaced directly within the Parcha Store.
- Instead of GNOME Software's default bare removal, hitting "Uninstall" will trigger the helper to cleanly remove the app and aggressively scan for orphaned config directories (`~/.var/app/`, `~/.cache/`, `~/.config/`).

## 4. Status and what is still open (2026-09-30)
The ticket was closed with only this specification. What actually exists:
- **Done:** the name and icon (`parchaos-app-renames` turns GNOME Software's launcher into "Parcha Store" and re-applies it after updates); Flathub is set up as a software source when the image is built.
- **Not done, browsing our own packages:** the COPR repository carries no AppStream data, so ParchaOS's packages do not show up in the Store. COPR can generate it (`copr-cli modify --appstream on`, turned on 2026-09-30) but only for packages that ship a `metainfo.xml`; none do yet. Only packages with a launcher are worth listing (ParchaOS Settings, the welcome tour, Install Developer Tools); the rest are extensions and themes that belong to the desktop as a whole and should not be removable one by one.
- **Not done, clean removal:** `parchaos-app-store-uninstall-helper` exists but nothing calls it. GNOME Software has no hook for a custom removal step. Two workable routes: run the leftover-folder cleanup from a dnf5 transaction action and a Flatpak uninstall hook so it works from the Store, the launcher and the terminal alike, or offer it as a follow-up prompt after a removal. The launcher's own uninstall (edit mode) is the place it fits first.
- **Already true:** updating from the Store restarts the computer a few times; the update notification and welcome tour say so (#134).
