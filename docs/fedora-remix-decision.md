# Fedora Remix Trademark Decision

Per Ticket #106 and the Fedora Trademark Guidelines, ParchaOS modifies the underlying Fedora platform (via COPR, alternate default repositories like Flathub, and deep shell integrations). Therefore, it technically operates as a **Fedora Remix**.

### Decision
**We have chosen to switch to `generic-release` and `generic-logos`.** 

### Rationale
Fedora's trademark guidelines mandate that derivatives altering the core configuration must not use the official "Fedora" branding, logos, or release strings, to prevent confusing users into believing the derivative is an official Fedora Spin. 
By replacing `fedora-release` with `generic-release`, we ensure `/etc/system-release` and `/usr/lib/os-release` are scrubbed of Fedora's protected trademarks, while safely keeping `VERSION_ID` intact so that `dnf` and system version checks continue working perfectly. 

### Implementation
1. `profiles/parchaos/packages.list` now installs `generic-release` and `generic-logos` instead of `fedora-release`.
2. `packaging/parchaos-release/parchaos-release.spec` was updated to hook into `generic-release-common` rather than `fedora-release-common`.

This brings the OS into full compliance with Fedora's Remix trademark policy.
