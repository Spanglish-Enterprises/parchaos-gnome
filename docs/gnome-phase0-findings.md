# GNOME variant phase 0 findings — from fork to a real, verified install

Status date: 2026-09-23. This repo's README still describes the *original*
fork-day plan (2026-09-22) in detail; this doc records what actually
happened since, following this project's own convention (see the KDE
repo's `docs/phase0-findings.md` through `phase4-findings.md`) of writing
down real, verified results rather than letting a stale plan stand in for
history. Read this alongside the README, not instead of it — the README's
"What carries over" and "Full Pulsar OS package reference" sections are
still accurate background; only its "Status" line and parts of "Next
steps" are out of date.

## Summary: what's real and working right now

A GNOME live ISO for this profile (`profiles/pulsaros/`) builds
successfully via `engine/build-iso.sh`, boots to a real branded GNOME
Shell desktop, and has had a **complete, real, end-to-end Calamares
install + reboot + login test pass on a disposable VM disk** — partition,
user creation, erase-disk install, reboot, and a real authenticated
desktop session showing this project's own branding. This is the same
rigor bar the KDE (pearos) variant's own `phase4-findings.md` established,
now met for this profile too.

## Packages built and wired in (`packaging/`, referenced from
`profiles/pulsaros/packages.sh` and `customize.sh`)

- **`parchaos-gtk-theme`** / **`parchaos-icon-theme`** — real upstream
  vinceliuice MacTahoe GTK/icon themes (MIT / GPL-3.0), set as the
  default via `customize.sh`'s dconf db. Five real, independently
  root-caused packaging bugs found and fixed across this package's own
  `Release` history (a `[[ false ]]` bash truthiness bug, a missing
  `BuildRequires: sudo`, a missing `mkdir -p` before an `install.sh -d`
  call, a missing `glib2-devel`/`libxml2` BuildRequires that only
  surfaced because COPR's mock chroot is network-isolated, and a
  nonexistent `Requires: gnome-themes-extra`) — see that spec's own
  changelog for the full root-cause writeup of each.
- **`parchaos-dock`** — Pulsar OS's real Dash-to-Dock fork ("Pulsar
  Dock"), rebranded "Parcha Dock" (GPL-2.0).
- **`parchaos-global-menu`** — Pulsar OS's real in-house macOS-style
  global menu GNOME Shell extension, rebranded "Parcha Menu"
  (MIT-INLED), deliberately scoped to exclude upstream's setuid-root
  lock-screen helper and GRUB/hibernation postinst mutations (see that
  spec's own banner for the full reasoning).
- **`parchaos-finder`** — Pulsar OS's real patched-Nautilus fork,
  rebranded "Parcher" (GPL-3.0, only the `Name=` display string
  rebranded — the real upstream application ID `org.gnome.Nautilus` is
  kept unchanged, which matters for anything else that needs to target
  it by app ID, e.g. `parchaos-macos-remap`'s config.yml).
- **`parchaos-gnome-calamares-config`** — installer branding + the same
  BIOS-Boot-Partition/KPMCore/kernel-install fixes ported from the KDE
  variant's own `pearos-calamares-config` (100% DE-agnostic). This
  package's own real-bug history is the deepest of this session — see
  "The Calamares GNOME launcher saga" below.
- **`parchaos-gnome-plymouth-theme`** / **`parchaos-gnome-wallpaper`** —
  Fedora's stock Plymouth spinner theme and a from-scratch dark
  wallpaper, both carrying the project's real passion-fruit logo as a
  subtle watermark.
- **`parchaos-macos-remap`** — real macOS-style keyboard remap (Cmd<->Ctrl
  swap + macOS keyboard conventions) via xremap (MIT) + its companion
  GNOME Shell extension (GPLv2+), repackaged from Pulsar OS's
  `gnome-macos-remap-wayland` as a declarative RPM (systemd user-preset,
  udev `uaccess`, dconf db) instead of an interactive per-user install
  script — see that spec's own banner for why the interactive-script
  approach would have silently broken on a real disk install (hardcoded
  to whatever username happened to run it, not the one Calamares
  actually creates). Built and COPR-verified 2026-09-23; **not yet
  baked into a rebuilt ISO** (deliberately — see "A note on pacing ISO
  rebuilds" below).
- **`parchaos-cloud`** — real Pulsar OS original work
  (`pulsaros-cloud`, GPL-3.0-or-later): rclone-backed cloud drives
  (Google Drive, OneDrive, iCloud, or any other rclone backend) mounted
  under `~/Cloud/<name>` via a per-account systemd user template unit,
  rebranded, plus a real `.desktop` launcher upstream doesn't ship
  (`Exec=parchaos-cloud choose`, reachable from Activities search).
  Deliberately dropped the upstream package's `onedrive.svg`/
  `google-drive.svg` — real, literal Microsoft/Google trademarked
  logos (confirmed by inspecting the actual SVG paths/gradients, not
  guessed from the filenames), which the real `pulsar-cloud` script
  never actually references at all (provider names only ever appear
  as plain text menu labels in the terminal wizard) — so nothing
  functional was lost by not shipping them, and it avoids real
  trademark exposure the same way this project already avoids
  Apple's. Built and COPR-verified 2026-09-23; also not yet baked into
  a rebuilt ISO, same reasoning as `parchaos-macos-remap`.

## The logo-centering bug (real user feedback, fixed at the source)

Real feedback ("the logo seems a bit weird and off center") traced to
asymmetric canvas padding in the source PNGs
(`branding/logo/parcha-logo-*.png`, `parcha-silhouette-*.png`): 170px left
margin vs. 62px right margin, found via `PIL.Image.getbbox()`. Fixed by
cropping to actual content and re-padding symmetrically at the source,
then regenerating every derived asset — Calamares branding images, the
Plymouth watermark, the wallpaper watermark, and the global-menu panel
icon (which also picked up a real fix in the same pass: it had been a
non-square 443x570 image, now a true 570x570 silhouette). This is the
kind of bug that propagates silently into every downstream composited
asset unless caught at the true source — worth remembering if a future
branding asset looks subtly off again.

## The Calamares GNOME launcher saga (real, multi-round bug hunt)

The single most involved real-bug chain this session, found only through
repeated genuine end-to-end testing of the actual desktop-icon launch
flow (Activities search → click "Install System" → polkit dialog →
Calamares), not by inspecting the `.desktop`/wrapper script and assuming
it would work:

1. **`kdesu` fails outright on GNOME** (exit 1, no output) — the stock
   `calamares` package's own `/usr/share/applications/calamares.desktop`
   uses `Exec=kdesu /usr/bin/calamares`, a KDE-only helper. Fixed with a
   real XDG override at `/usr/local/share/applications/calamares.desktop`
   (freedesktop.org's own default `XDG_DATA_DIRS` ordering puts this
   ahead of `/usr/share/applications/`, no RPM file-conflict risk since
   it's a distinct path), `Exec=pkexec env DISPLAY=:0
   QT_QPA_PLATFORM=xcb /usr/bin/calamares`.
2. **That alone wasn't enough**: `pkexec` sanitizes the escalated
   process's environment, so the pkexec'd Calamares had no `XAUTHORITY`
   and couldn't connect to the X server at all — died near-instantly,
   no visible error. Root-caused by reproducing the exact failure via a
   root shell (the install-test VM's serial console) and iterating until the same
   command worked: needed `XAUTHORITY` pointed at Mutter's real Xwayland
   auth file (`/run/user/$UID/.mutter-Xwaylandauth.<random>` — no hyphen
   before "auth", easy to mistype) plus an explicit `xhost
   +si:localuser:root` grant (X11's classic cross-uid access-control
   mechanism; Wayland's own same-user model doesn't apply since this is
   an XWayland client). Moved the whole sequence into a real script,
   `/usr/local/bin/parchaos-launch-calamares`, rather than fighting
   Desktop Entry Spec's `Exec=` quoting rules for a multi-step shell
   sequence.
3. **Still not enough**: the wrapper resolved `DISPLAY`/`XAUTHORITY` into
   plain shell variables but never `export`ed them — `xhost` is a
   separate process that reads its target display from the *environment*,
   not from an unexported parent-shell variable, so the ACL grant
   silently failed (swallowed by the wrapper's own `|| true`). Found by
   reproducing again with the fix applied by hand (`export DISPLAY
   XAUTHORITY` before the `xhost` call) — confirmed via `ps aux` showing
   Calamares alive and running as root, not crashed.

**What's independently verified working**: the `pkexec`
command Calamares GNOME actually needs, run directly with the correct
environment, launches and keeps Calamares running as root without
crashing (checked via `ps aux` staying alive across multiple minutes,
not just a one-shot check).

**What's not independently verified from this VM**: an actual human
mouse click landing on the polkit "Authenticate" button and Calamares'
window then rendering on screen. This project's remote VM control setup
(QEMU HMP `mouse_move`/`mouse_button` via `qm monitor`) was confirmed,
via a direct calibration test, to have **zero effect on the guest's
cursor position regardless of the coordinates sent** — a pre-existing,
environment-specific limitation (not a regression from anything in this
session), consistent with this project's established history of mouse
input never working reliably in this control setup. Compounding that,
GNOME Shell's own native polkit authentication dialog was found to
dismiss itself on *any* keyboard-only input (`Return`, `Tab`+`Space`,
`Alt`-mnemonics, and arrow-key navigation all tested, all produced the
identical `polkitd: ... FAILED to authenticate ... Request dismissed`
journal line) — this looks like deliberate hardening against
synthetic-input auto-confirmation of a privilege escalation, not a bug.
Net result: the underlying mechanism is verified correct by direct
reproduction, but the exact "click a real button" step a real user will
perform could not be mechanically exercised end-to-end from this
control setup. Real hardware with a real mouse does not share this
limitation.

## A note on pacing ISO rebuilds

Two full ISO rebuild+reboot-test cycles happened in quick succession this
session chasing the launcher bug (rounds 2 and 3 above), and a real
same-day install deadline meant the *last* one (Release 5 of
`parchaos-gnome-calamares-config`, with the `export DISPLAY XAUTHORITY`
fix) was deliberately treated as the final artifact for that install —
`parchaos-macos-remap` and `parchaos-cloud` (both built and
COPR-verified after that point) were **not** folded into another
rebuild, to avoid re-touching an ISO that had already cleared its
verification bar right before someone was about to use it on real
hardware. Whoever picks this up next should fold both into the next ISO
rebuild along with whatever else has accumulated, and re-run a real boot
test before calling that build done — same "verify, don't assume" rule
as everything else in this project's history.

## What's next (see README's own roadmap for full detail)

- Fold `parchaos-macos-remap` and `parchaos-cloud` into a rebuild;
  real-boot-test the Cmd<->Ctrl swap and the per-app remaps (Parcher,
  GNOME Terminal) on an actual keyboard, and the cloud-mount flow
  (`parchaos-cloud choose` → rclone auth → mount appearing under
  `~/Cloud` in Parcher) end to end — neither has been exercised beyond
  a build/dependency check yet.
- Confirm the Calamares launcher fix's last unverified step (real mouse
  click → Authenticate → Calamares window) on whatever hardware actually
  ran tonight's install, and close the loop here if it needs anything
  further.
- The README's "Real, substantial from-scratch ports" list is now
  partly out of date: **`pulsaros-cloud` is done** (`parchaos-cloud`,
  above) — it turned out much smaller in practice than the README's
  "multi-day effort each" framing suggested, since the real upstream
  source is a single self-contained shell script + systemd template +
  icon checked directly into the monorepo, not a separate application
  needing a real build system. `pulsaros-timemachine` (GPL3, but a
  real GTK4/Libadwaita Python app depending on `btrfs-progs`/`restic`/
  `udisks2` — genuinely substantial) and `pulsaros-welcome` (license
  "custom" — needs the same real license check `pulsaros-cloud` and
  Sayri got before any packaging work starts, plus it's a real Rust
  (Tauri)/npm build, not a vendor-and-go port) remain not started.
  **Real blocker found scoping Sayri (2026-09-23), before writing any
  packaging**: its real source
  Sayri (2026-09-23), before writing any packaging**: its real source
  repo (`Inled-Pulsar-OS/sayri`) has no `LICENSE` file at all, and
  GitHub's own API confirms `license: null` — under default copyright
  that means all rights reserved, not "open source, license just
  unspecified." This project has consistently tracked licenses
  carefully for its other real ports (parchaos-finder, parchaos-dock,
  parchaos-global-menu all document their real upstream license in
  their spec's own banner comment) specifically because a public
  release is planned — packaging unlicensed third-party source would
  be a real legal exposure, not just a technical shortcut. Also worth
  noting for whoever picks this up: Sayri is described by its own
  README as "an AI Agent framework" with API-key-holding LLM access
  and a claimed 5-level sandboxing model — even once licensing is
  resolved (e.g. by asking Inled directly, or finding a license
  elsewhere in the monorepo), this is security-sensitive enough that
  the sandboxing claims need real, hands-on verification before
  shipping it to users, not just a build-and-ship port like the
  cosmetic/GNOME-Shell-extension pieces. Not started past this
  scoping pass.
- This repo still carries a pile of KDE-only cruft inherited from the
  original `git push --mirror`-style fork (`pearos-dock`,
  `pearos-liquidgel`, `pearos-launchpad`, `pearos-settings`,
  `parchaos-whitesur-lookandfeel`, `parchaos-appmenu-gtk-module`,
  `pearos-branding`, `pearos-calamares-config` under `packaging/`, plus
  `profiles/pearos/` itself) that the README's own "needs full
  replacement"/"not applicable" table already calls out. **Checked
  2026-09-23 whether this is safe to just delete — it is not, yet**:
  `profiles/pearos/` is the only thing referencing those `packaging/`
  subdirs, but `engine/build-iso.sh` line 34 hardcodes
  `PROFILE="pearos"` as its default when `--profile` isn't passed on
  the command line — deleting `profiles/pearos/` outright would
  silently break any future build invocation that omits `--profile
  pulsaros`. Real cleanup here means changing that default (and
  probably auditing every place that still assumes it) *before*
  deleting anything, not deleting first. Deliberately not done as part
  of this pass — `engine/build-iso.sh` is the same script that built
  the ISO used for tonight's real install, and this is exactly the
  kind of low-payoff, non-zero-risk change not worth touching on that
  timeline. Real cleanup, still not yet done.
