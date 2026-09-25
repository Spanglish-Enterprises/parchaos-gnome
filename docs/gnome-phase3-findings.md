# Phase 3 findings — scoping Pulsar OS's remaining bigger features

Date: 2026-09-24. Follows the extension-polish pass in
`gnome-phase1-findings.md` and the licensing audit in
`gnome-phase2-findings.md`. Real user request: scope seven bigger
Pulsar OS features this profile doesn't have yet (Control Center
replica, Dynamic Island-style notification UI, app store, driver
manager, live wallpaper, GUI update tool, hosts-file ad-blocker),
prioritizing whichever have a real path that doesn't depend on Inled's
licensing answer.

## Licensing check, done first (same habit as everything else)

All seven were checked against real repos before anything else, the
same diligence that found Sayri/pulsaros-timemachine/etc. blocked:

| Feature | Real location | License |
|---|---|---|
| Control Center replica | `Inled-Pulsar-OS/PKG`, `pulsaros-control-center/` + `pulsaros-control-center-button/` | Inside PKG monorepo — `license: null` |
| Dynamic Island-style UI | `Inled-Pulsar-OS/PKG`, `pulsaros-island/` | Inside PKG monorepo — `license: null` |
| App store | `Inled-Pulsar-OS/store` (separate repo, JavaScript) | `license: null` (checked its own repo directly, not assumed from the PKG pattern) |
| Driver manager | `Inled-Pulsar-OS/PKG`, `driverman/` | Inside PKG monorepo — `license: null` |
| Live wallpaper | `Inled-Pulsar-OS/PKG`, `pulsaros-live-wallpaper/` | Inside PKG monorepo — `license: null` |
| GUI update tool | `Inled-Pulsar-OS/PKG`, `pulsaros-update/` | Inside PKG monorepo — `license: null` |
| Hosts-file ad-blocker | `Inled-Pulsar-OS/PKG`, `pulsaros-hblock/` | Inside PKG monorepo — `license: null` |

**All seven of Pulsar's own real implementations are blocked**, same
as every other Inled-original component found this session. None of
them can be adapted or ported without Inled's answer to the
already-recommended single outreach email.

## The three with a real path that doesn't touch any of that

Three of these features have the underlying *need* solved by something
that isn't Pulsar's code at all — either a real Fedora package, or a
separately-licensed third-party project. Checked each one directly:

**GUI update tool → `gnome-software` is a real, official Fedora
package** (50.4-1.fc44, confirmed via `dnf list --available`). GNOME
Software already does exactly this job on Fedora Workstation: a GUI
front-end for `dnf` updates plus Flatpak app browsing/installation. No
packaging work needed at all beyond adding it to `packages.list` — this
is the single lowest-effort item of all seven.

**Hosts-file ad-blocker → real upstream is `hectorm/hblock`**, not
Pulsar's fork (`pulsaros-hblock` is presumably built on the same real
upstream, but its own copy inherits PKG's blocked license — checked the
actual root project instead). Confirmed real MIT `LICENSE.md` via
GitHub API. It's a single POSIX shell script (`hblock`) plus a man
page — genuinely simple to package: fetch/merge public blocklists into
`/etc/hosts`, refreshed on a timer. No Fedora package exists yet
(confirmed via `dnf list --available hblock` — no matches), so this
needs packaging from source, but it's the same low-complexity shape as
`parchaos-notification-position` etc. from the extension-polish pass,
not a big lift.

**Live/animated wallpaper → real, actively-maintained alternative
exists**: `Si11-ibrahim/gnome-video-wallpaper-screensaver`, real MIT
license, pushed as recently as 2026-09-05 (independent of Pulsar OS
entirely). Not yet inspected in depth (build system, GNOME Shell
version compatibility, whether it needs a native video-decode
dependency) -- that's the next real step if this gets picked up, same
diligence pattern as the other extensions this session.

## The four genuinely blocked, no shortcut available

Control Center replica, Dynamic Island-style notification UI, app
store, and driver manager all stay in the "blocked on Inled" bucket
alongside Sayri/pulsaros-timemachine/pulsaros-welcome/
gnome-macos-remap-wayland/plymouth-macoslike/calamares-themes/
pulsar-pear-sound-theme/pulsaros-spotlight-launcher/
pulsar-circle-to-search -- the running list is now 13 items gated on
one outreach email to Inled (`info@inled.es`), still not sent as of
this writing (the user's call to make, not something to draft or send
unprompted).

If ParchaOS ever needs to build these four from scratch instead of
waiting on Inled: a Control Center replica and a Dynamic Island-style
notification UI are both real, substantial GNOME Shell extension
projects (custom quick-settings panel, custom always-on-top overlay
widget) on the order of the `parcha-dock`/`parchaos-global-menu` effort
already done for this profile — not simple config-value fixes. An app
store is a much bigger undertaking (a real application with its own
backend/catalog, not just a themed frontend over `dnf`/Flatpak — GNOME
Software, once added per the recommendation above, already covers the
"browse and install software" need reasonably well without one). A
driver manager's value depends heavily on what hardware gaps it's
meant to paper over; Fedora's own `dnf` already resolves most driver
needs automatically (as this project's own firmware-package additions
throughout `gnome-phase1-findings.md` demonstrate) except for a real
GUI to expose that, which is a smaller, more scoped project than
Pulsar's own real `driverman` (which has a full CMake-built native GUI
per its repo listing) if ParchaOS ever wants one.

## Update, 2026-09-24: all three shipped -- `gnome-software` turned into a real, multi-round pafari saga

`gnome-software` and `parchaos-hblock` are both installed and confirmed
working on real hardware. `gnome-software` was expected to be a
zero-effort add (a stock Fedora package) but surfaced a real, genuine
chain of bugs in `pafari` (this profile's existing Epiphany-fork
browser, unrelated to anything in this phase's own scope) that had
simply never been exercised before:

1. **File conflicts on first install**: `pafari` never declared itself
   a replacement for the real `epiphany-runtime` package the way
   `parchaos-finder` already does for `nautilus` -- adding
   `gnome-software` was the first thing in this project's history to
   transitively depend on `epiphany-runtime`, exposing the gap. Fixed
   with the standard `Provides`/`Conflicts`/`Obsoletes` triple.
2. **Still failed after that fix**: real `epiphany-runtime` has
   `Epoch: 1` (confirmed via `dnf info` on real hardware); `pafari` had
   no epoch at all. RPM's solver compares Epoch before Version/Release,
   so the un-epoched Provides/Obsoletes couldn't actually out-rank the
   real package. Added `Epoch: 1` to `pafari` and epoch-qualified both
   lines.
3. **Still failed, differently**: an old, pre-fix `pafari-26.8-3` build
   was still sitting in this project's own COPR repo, giving dnf's
   solver an escape-hatch path (downgrade pafari to the version with no
   conflict declarations, then install real `epiphany-runtime`
   alongside it) instead of just accepting the already-installed,
   properly-declared pafari. Deleted the stale builds
   (`copr-cli delete-build`) -- a real, generally-applicable lesson:
   old COPR builds of a package that later gains
   Provides/Obsoletes/Conflicts should be pruned, not left around as
   silent alternate resolutions.
4. **Still failed, once more**: with the stale build gone, dnf's error
   became fully explicit for the first time -- `gnome-software` has a
   genuine hard `Requires: epiphany-runtime(x86-64)` (an earlier
   `dnf repoquery --requires` check had grabbed a different installed
   `gnome-software` build and misread this as a soft `Recommends`).
   `pafari`'s manually-declared `Provides: epiphany-runtime = ...` line
   never got an ISA-suffixed `(x86-64)` variant auto-generated the way
   the package's own self-Provides does, so it never matched
   `gnome-software`'s exact capability string. Added the ISA-suffixed
   Provides explicitly.
5. **hblock's own real bug, found after all of that**: its `%post`
   used `systemctl preset`, which only enables a unit if a `.preset`
   policy file says to -- this project ships none, so Fedora's default
   policy left the ad-blocker timer installed but inert. Switched to
   `systemctl enable --now`.

Five real, independent bugs, four of them on a completely unrelated
existing package, all found and fixed by trying to add one trivial
Fedora package. `pafari` is now at `1:26.8-6`, confirmed installed
alongside `gnome-software` and `parchaos-hblock` with zero file
conflicts and the ad-blocker timer active on real hardware.

## What's next

Recommended order, per user direction to prioritize the three
unblocked items: `gnome-software` (add to `packages.list`, effectively
free), then `hblock` (real, small packaging job, same shape as
`parchaos-notification-position`), then a deeper look at the live
wallpaper extension's build requirements before packaging it. The four
blocked items wait on the Inled email like everything else in that
bucket.
