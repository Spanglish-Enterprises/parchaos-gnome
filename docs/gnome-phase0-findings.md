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
- **`parchaos-global-menu`** — Pulsar OS's real in-house
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
- **`parchaos-macos-remap`** — real keyboard remap (Cmd<->Ctrl
  swap + Cmd-key conventions) via xremap (MIT) + its companion
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
- **`parchaos-focus-schedule`** / **`parchaos-yin-yang`** (+ its
  `python-suntime` dependency) — both already existed in `packaging/`
  (inherited from the KDE repo fork, built and working there) but were
  never added to `profiles/pulsaros/packages.sh`. Checked both for
  real GNOME-specific blockers before wiring them in rather than
  assuming "carries over unchanged" from the README was still
  accurate: `parchaos-focus-schedule` is genuinely 100% DE-agnostic
  (plain `org.freedesktop.Notifications` Inhibit/UnInhibit D-Bus calls
  via `gdbus`, no toolkit dependency at all); `parchaos-yin-yang` is a
  cross-desktop PySide6/Qt app whose GTK/icon-theme/wallpaper plugins
  are directly relevant to this profile (its Kvantum/Plasma-color-
  scheme/Konsole plugins just become inert no-ops under GNOME, not
  broken). Neither needed any code changes — only rebuilding fresh
  against this project's own COPR (`alexgalicea/parchaos-gnome`),
  since both had only ever been built against the KDE repo's separate
  COPR project before. Verified via a real local `rpmbuild --rebuild`
  test for each plus the real COPR mock build, all three (focus-
  schedule, suntime, yin-yang) succeeded. Also not yet baked into a
  rebuilt ISO.
- **`parchaos-tmog`** — already existed, genuinely DE-agnostic
  (AppImage-fetching wrapper, no KDE dependency), already end-to-end
  verified once under an earlier product name. Rebuilt fresh against
  this project's own COPR (11027251, succeeded), wired in.
- **`pafari`** (real pearOS/Pulsar OS fork of GNOME Web/Epiphany,
  GPL-3.0-or-later) — wired in as this profile's browser, filling a
  real gap: `packages.list` ships no web browser at all otherwise.
  The spec's own top banner said "UNTESTED", but that was stale —
  its `%files` section already carried real, dated fixes from an
  actual COPR clean-chroot build (rst2man missing, the real installed
  binary name, modern metainfo path, several installed-but-unpackaged
  libexec/D-Bus/search-provider paths), just never reflected in the
  changelog. Found two real, separate problems getting a fresh build
  working: (1) `rpmbuild --rebuild` only checks *locally installed*
  packages, not what's available via dnf repos — its "pkgconfig(...)
  is needed" errors looked like missing dependencies but were really
  just "not installed on this build box yet"; fixed with a real `sudo
  dnf builddep` pass (67 packages) rather than assuming the spec was
  broken. (2) The `%changelog` had a wrong weekday (Sep 17 2026 is a
  Thursday, not Wednesday) and, once corrected, a new entry appended
  in the wrong order — rpmbuild enforces strictly descending
  chronological order and errors (non-fatally in this rpm version,
  but worth fixing properly) otherwise. A real local `rpmbuild
  --rebuild` (405 compile steps) and the real COPR mock build
  (11027385) both succeeded after these fixes. Also not yet baked
  into a rebuilt ISO.
- **`parchaos-boot-sound`** — checked, deliberately **not** wired in.
  It depends on `pearos-sounds` (built from the KDE repo's
  `pearos-settings.spec`), whose own `%description` already says
  "Upstream declares no license anywhere for this specific content
  (no LICENSE file, no metadata.json); packaged as-is under this
  spec's overall License pending clarification" — a real, pre-existing,
  unresolved license gap. It was apparently already accepted once for
  the KDE product; extending it to a second product this project also
  plans to publicly release, without anything new resolving the gap,
  isn't something to do quietly. Left out and documented instead.

## The logo-centering bug (real user feedback, fixed at the source)

Real feedback (the logo looked slightly off-center) traced to
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

**Update 2026-09-24, closed**: confirmed on real hardware overnight
(see `docs/gnome-phase1-findings.md`) — a real user, real mouse, real
install. The full launcher chain (Activities search → click → polkit
Authenticate → Calamares window → full install → reboot → real
authenticated desktop) completed successfully, multiple times, on the
actual machine this variant is meant to ship to. No longer an open
question.

## A note on pacing ISO rebuilds

Two full ISO rebuild+reboot-test cycles happened in quick succession this
session chasing the launcher bug (rounds 2 and 3 above), and a real
same-day install deadline meant the *last* one (Release 5 of
`parchaos-gnome-calamares-config`, with the `export DISPLAY XAUTHORITY`
fix) was deliberately treated as the final artifact for that install —
`parchaos-macos-remap`, `parchaos-cloud`, `parchaos-focus-schedule`,
`parchaos-yin-yang`, `parchaos-tmog`, and `pafari` (all built and
COPR-verified after that point) were **not** folded into another
rebuild, to avoid re-touching an ISO that had already cleared its
verification bar right before someone was about to use it on real
hardware. Whoever picks this up next should fold all six into the next
ISO rebuild along with whatever else has accumulated, and re-run a real
boot test before calling that build done — same "verify, don't assume"
rule as everything else in this project's history.

## What's next (see README's own roadmap for full detail)

- **Deeper Calamares installer skinning** (explicit user ask,
  2026-09-23, deliberately deferred — "to complete much later"): the
  current branding pass (logo/icon/welcome/slideshow images,
  stylesheet, page copy) reads as a reskinned generic Linux installer
  wizard, not a look-alike of the reference installer. Calamares'
  branding.desc + QML view files (`main.qml` and each page's own .qml
  under `/usr/share/calamares/...` or an override under
  `/etc/calamares/branding/ParchaOS/`) are the real place to push this
  further — page transitions, a real sidebar/progress
  layout instead of the stock top-tab bar, window chrome, font choices
  — all overridable there. Not started; this is real QML/UI work, not
  a config-value fix like tonight's bugs, so budget real time for it
  separately rather than folding it into a future crisis-driven
  session.
- **A real Plymouth boot-splash theme with the ParchaOS/passion-fruit
  logo** (explicit user ask, 2026-09-23, deliberately deferred, same
  "later" bucket as the Calamares skinning item above): this is
  already a known, previously-identified gap, not a new one --
  parchaos-finalize-install's own Plymouth theme-switch step already
  has a `[ -d ... ]` existence guard specifically because
  `parcha-plymouth` doesn't exist yet, making it a safe no-op in the
  meantime (see that script's own comment and this project's earlier
  KDE-variant history for the pear-plymouth theme it was modeled on).
  Real work needed: build an actual `parcha-plymouth` Plymouth theme
  package (image assets + a `.plymouth` theme script, most likely
  following the same simple "spinner"/"two-step" theme style Fedora's
  own default theme uses) and package/wire it in the same way the KDE
  variant's theme eventually was. Not started.
- **Update 2026-09-24, mostly done** — see `docs/gnome-phase1-findings.md`
  for the full story: all six packages plus `parchaos-desktop` are now
  wired into `packages.sh` and confirmed present in a real built ISO
  (v19), and were installed and process-level-verified directly on
  real hardware (`pafari`/`yin_yang` launch and stay running, the
  `parchaos-macos-remap.service` xremap daemon and its GNOME Shell
  extension are both active). **Still needs a human**: does Cmd
  actually act as Ctrl on a real keypress, does pafari visually render
  a page correctly, does yin-yang's theme switch actually look right,
  does TMOG's real download complete, does the cloud-mount flow work
  end to end with real OAuth, does the focus-schedule notification
  inhibit actually suppress a real popup at 22:00/08:00. All the
  plumbing is confirmed working; the remaining checks are genuinely
  interactive/visual ones only a person at the keyboard can do.
- ~~Confirm the Calamares launcher fix's last unverified step~~ —
  **closed**, see the update inlined above in "The Calamares GNOME
  launcher saga" section.
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
  pulsaros`.
  **Update 2026-09-24**: the prerequisite is done — `--profile` is now
  a required argument in both `engine/build-iso.sh` and the (untested,
  non-functional-anyway) GitHub Actions workflow, no silent default
  anywhere anymore, verified directly (omitting `--profile` now fails
  loudly with a usage message, before ever reaching the sudo re-exec).
  **Update 2026-09-24, deletion done**: with the `--profile` safety
  net confirmed in place, the user approved deleting the cruft
  (`profiles/pearos/`, `pearos-dock`, `pearos-liquidgel`,
  `pearos-launchpad`, `pearos-settings`,
  `parchaos-whitesur-lookandfeel`, `parchaos-appmenu-gtk-module`,
  `pearos-branding`, `pearos-calamares-config` — 153 files). Removed
  via `git rm -r`, cross-checked beforehand that no functional
  (non-comment) references to any of it existed outside
  `profiles/pearos/` itself. `packaging/parchaos-boot-sound/` was
  explicitly kept — it's a real deferred *feature* blocked on a
  licensing gap in its `pearos-sounds` dependency, not dead KDE-only
  cruft. **Staged but not yet committed** — this project's standing
  rule is to never commit without being explicitly asked, so this is
  sitting in the working tree until that word is given.
