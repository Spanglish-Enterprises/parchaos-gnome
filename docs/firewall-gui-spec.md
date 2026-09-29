# ParchaOS Firewall UI Specification

This document outlines the behavior and architecture for a friendly, per-app network/privacy firewall in ParchaOS (Ticket #126). 

**Legal Note**: This is a pure original GUI built over the official, Red Hat-maintained `firewalld` D-Bus API (`org.fedoraproject.FirewallD1`). It has zero exposure to Inled's stack.

## 1. Core Behavior
Provide users with an intuitive per-app network permission toggle system without exposing raw port/protocol jargon.
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

## 4. As built (parchaos-settings 1.0.0-15): the design changed

The first draft (section 2) used `firewalld` for apps that are not Flatpaks. That cannot work: `firewalld` filters by zone, port and service and has no way to tell which app a connection came from. It is also not installed on the ISO. What shipped instead:

- **Where:** a Privacy page in ParchaOS Settings (not Parcha Controls; a list of dozens of apps with switches suits a window better than the top-bar panel). Each app has a switch, "Network access", and a search box filters the list.
- **Flatpak apps:** Flatpak's own permission. Blocking adds `!network` to the app's user override (`~/.local/share/flatpak/overrides/<app-id>`), which Flatpak reads the next time the app starts. Other overrides in that file are kept.
- **Other apps:** a per-user copy of the app's launcher that starts it with bubblewrap in a network namespace with no interfaces (`bwrap --dev-bind / / --unshare-net`), so it can reach nothing, not even the local network. The copy turns off D-Bus activation (otherwise GNOME ignores `Exec`) and carries `X-ParchaOS-NetworkBlocked=true`. Allowing removes the copy; a launcher the user made themselves is never replaced or removed.
- **Timing:** a change applies the next time the app starts. An app that is already running keeps its network, and an app that hands off to an already-running copy of itself stays as that copy was. The page says so.
- **Helper:** `/usr/libexec/parchaos-app-network` (`list`, `set ID allow|block`, `refresh`), tested by `packaging/parchaos-settings/tests/test_app_network.py`, which includes a check that a blocked command sees only the loopback interface. A user service runs `refresh` at login so blocked launchers follow app updates.
- **Not covered:** apps started some other way than their launcher (a terminal, a script, autostart entries that do not use the launcher); blocking only some destinations or ports; the Advanced view of raw firewalld rules from section 3 (firewalld is not part of the image).
