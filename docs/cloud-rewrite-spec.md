# parchaos-cloud — clean-room rewrite spec

**Why**: the previous `parchaos-cloud` script was a near-verbatim copy of
Inled's real `pulsar-cloud` script (confirmed via a direct line-by-line
diff: 400 vs 399 lines, differences limited to `pulsar-cloud` ->
`parchaos-cloud` renames). That script's own PKGBUILD does carry an
explicit `license=(GPL-3.0-or-later)` SPDX tag — a real, specific,
deliberate declaration that's legally meaningful on its own terms — but
relying on a bare PKGBUILD field with no actual LICENSE file backing it up
is weaker ground than having ParchaOS's own independent code, and doesn't
fully rule out Inled's general MIT-INLED default being asserted against
it later. Given how small and mechanical this script's actual job is,
rewriting it clean is cheap insurance, matching the standard already set
for the global menu.

This is the only document the rewrite should be written from — not
Inled's script. The functional pattern (rclone remotes mounted via a
systemd user template unit under `~/Cloud/<name>`) is rclone's own public,
documented usage convention (see rclone's real docs for `rclone mount`
under systemd), not anyone's original creative expression.

## What it needs to do

A single CLI, `parchaos-cloud <command> [name]`:

- `choose` — ask (via `zenity` if available, else a terminal prompt)
  whether the user wants the graphical `rclone config` web UI or a
  terminal-based setup wizard, then launch it. This is the `.desktop`
  launcher's entry point.
- `add` / `setup` — walk through `rclone config` interactively to create
  a new remote, then enable+start `parchaos-cloud@<name>.service`.
- `mount <name>` / `unmount <name>` — start/stop the systemd template
  unit for a specific remote.
- `list` — show configured remotes (`rclone listremotes`) and whether
  each is currently mounted (check `~/Cloud/<name>` is a real mountpoint,
  e.g. via `mountpoint -q` or checking `/proc/mounts`).
- `reconnect <name>` — re-run `rclone config reconnect <name>:` for
  remotes whose auth token expired, then restart the mount unit.
- `open <name>` — open `~/Cloud/<name>` in the file manager.

Keep the real, existing external interface unchanged (these are neutral,
functional identifiers, not creative expression, and changing them would
break existing installs for no reason): the `parchaos-cloud@.service`
systemd template unit, `~/Cloud/<name>` mount location, and the
`parchaos-cloud choose` desktop-launcher entry point.

## Explicitly not required

No need to replicate Inled's exact wording for prompts/help text/error
messages — write fresh, clear messages. No need to match their exact
function names or script structure.
