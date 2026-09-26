# Phase 4 findings — ParchaOS's own desktop pieces, and the September audits

Date: 2026-09-25 to 2026-09-26. Follows `gnome-phase3-findings.md`. With
Pulsar OS's own implementations of the bigger features blocked on
licensing (phase 2/3), this phase built ParchaOS's own versions from
scratch, then audited the whole project twice (security, then general)
and worked through the findings. Tickets are in spanglish-tickets
(project `parchaos`); numbers below refer to them.

## Built from scratch (all GPL-3.0-or-later, original code)

| Package | What it is | Notes |
|---|---|---|
| `parchaos-launcher` | Full-screen app launcher: pages, folders, search, keyboard navigation, edit mode (long-press, pulsing icons, uninstall badge) | Blurs its own copy of the wallpaper (`BackgroundManager` with `controlPosition: false` — without it, monitors not at 0,0 got a black background). Uninstall goes through `parchaos-launcher-apps` (protects ParchaOS and core packages, `rpm -e --test`). |
| `parchaos-controls` | Parcha Controls, the control center: connectivity, now playing, Focus, Dark Mode, Night Light, display/sound sliders, tiles other extensions add to Quick Settings (GSConnect) | GNOME 50's `MprisSource` has no `destroy()`: one instance per shell process (#26). |
| `parchaos-settings` | ParchaOS Settings (libadwaita): style, session restore, Focus schedule, Super as Ctrl | Hybrid by design: a small app, plus a ParchaOS panel in GNOME Settings (`packaging/gnome-control-center/`, one patch). A panel with category `X-GNOME-SystemSettings` gets redirected to the System page; it uses Personalization. |
| `parchaos-session` | Reopens the last session's apps and puts their windows back | Wayland windows have no app ID at `window-created`; match on `shown`. Saves when the end-session dialog opens and freezes on confirm (#45). |
| `parchaos-live-icons` | Live Clock and Calendar icons | St caches textures per file name, so each state is written under a new name. |
| `parchaos-release` | ParchaOS name, logo and links in `/etc/os-release` | `fedora-release-common` owns the file and restores it on update; a `%triggerin` rewrites it (#24). `ID` stays `parchaos` so the app store doesn't offer Fedora releases ParchaOS doesn't support yet. |
| `parchaos-focus-schedule` 1.1 | Scheduled Do Not Disturb | Two fixed timers couldn't recover from a computer that was off at a boundary; a user service now derives the state from the clock (#42). |

Plus: two visual styles (`org.parchaos.desktop` `style`, Glass and
Classic, followed by the menu bar, launcher, Controls and dock), the
About ParchaOS card, and original ParchaOS artwork for ~30 app and folder
icons and the ParchaOS mark (a halved passion fruit), which replaced the
Apple logo MacTahoe draws for `start-here` and the shell's activities
button (#28).

## Packaging lessons

- **Defaults written only by the ISO build never reach existing
  installs.** The extension list, theme and extension-tuning dconf files
  and the Flathub remote all moved into `parchaos-desktop` (#15, #23).
  A user's own `enabled-extensions` hides new defaults forever, so
  `parchaos-extensions-migrate` (user service) offers each new default
  once.
- **Patched Fedora packages lose to newer Fedora builds.** Instead of an
  `Epoch` (permanent), `parchaos-desktop` ships
  `/usr/share/dnf5/repos.override.d/80-parchaos-copr.repo` giving the
  ParchaOS repository priority 90; CI's `fork-versions` job fails when
  Fedora has a newer version of a forked package (#27).
- **`bash -n` doesn't catch an orphaned heredoc body** (the lines parse
  as commands); `shellcheck -S error` does. That bug broke every ISO
  build after 94ea387; `scripts/lint.sh` now runs in CI on every push
  (#30).
- MacTahoe's fixed-size icon copies are link targets for other icons:
  overwrite them, never delete (deleting left 278 dangling links).
- `sed -i` on `/etc/os-release` replaces Fedora's symlink with a file
  that `rpm -V` flags and the next update reverts.

## Security audit (2026-09)

Two medium findings fixed (installer log upload, website support form).
Open: #22, the keyboard remap gives every user raw keyboard access
(`input` group, uinput); the redesign needs a real-hardware test window.
Later hardening from the general audit: TMOG's downloaded AppImage is
checked against a pinned SHA-256 (#40).

## General audit (2026-09-26)

34 findings, filed as #23–#53 (tag `audit`). Fixed in this pass: the ISO
build break, #15, #23, #24, #25 (menu bar sends app-appropriate keys),
#26, #27, #28, #29 (links pointed at the private repository), #30
(except the CI smoke test), #31, #38, #39 (About card no longer blocks
the compositor), #40, #42, #43 (touchegg), #44, #45. Open items are
tracked in their tickets.
