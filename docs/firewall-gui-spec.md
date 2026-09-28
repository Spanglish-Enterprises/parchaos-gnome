# ParchaOS Firewall UI Specification

This document outlines the behavior and architecture for a friendly, per-app network/privacy firewall in ParchaOS (Ticket #126). 

**Legal Note**: This is a pure original GUI built over the official, Red Hat-maintained `firewalld` D-Bus API (`org.fedoraproject.FirewallD1`). It has zero exposure to Inled's stack.

## 1. Core Behavior
Provide users with an intuitive, macOS-like (e.g., Little Snitch) or Windows-like network permission toggle system without exposing raw port/protocol jargon.
- **Per-App Control**: Users can toggle network access ON or OFF for specific applications.
- **Target Audience**: Everyday users prioritizing privacy (e.g., blocking an offline game from calling home) rather than sysadmins writing complex routing rules.

## 2. Integration & Architecture
Instead of building a standalone application, this feature will be integrated directly into the existing `parchaos-controls` (Control Center) panel, matching the established pattern of consolidating system settings.

- **Backend (`firewalld`)**: 
  - The UI will communicate with `firewalld` using its D-Bus interface.
  - No reinventing `netfilter`/`nftables` rule management.
- **Process Matching**:
  - The system will map running processes to `firewalld` zones/rules using cgroups or `systemd` units.
  - **Flatpak Apps**: The UI will leverage Flatpak's native sandboxing portal permissions (`--share=network` vs. `--unshare=network`), which provides robust per-app network isolation out-of-the-box. Flatpak overrides (`flatpak override --user --unshare=network <app-id>`) will be used as the primary mechanism for Flatpak apps, while `firewalld` will handle traditional RPMs/binaries.

## 3. UI Design Principles
- **Simple View**: A clean list of installed/running apps with a simple ON/OFF toggle switch for "Network Access".
- **Advanced View**: A collapsible section for power users exposing the underlying `firewalld` zones, specific ports, and protocols if they wish to audit the raw rules.
