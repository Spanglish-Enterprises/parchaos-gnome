# Glass, Control Center and menus: plan and hand-over spec

Status: 2026-10-01 (updated after menus moved to our glass). Tickets #135 (Glass), #148 (Edit Controls), #131 (dock), #169 (upgrade breakage).
Written so another agent can continue. Read `docs/DEVELOPMENT.md` first (test rigs must never touch the real desktop).

## 1. Owner requirements (settled, do not re-ask)

- **Glass must be exactly how macOS 27's liquid glass works. No less.** Build ParchaOS's *own* glass (not the third-party
  extension), judged side by side against the owner's references.
- **Every UI task is checked side by side** with the owner's references before it is called done: the Figma UI kit
  (file key `[design-kit-key-removed]`: Menus 207:14481, Menu Bar and Dock 207:14475, Materials 483:8848) and the macOS
  screenshots in `[private-dropbox]` (SMB share `[private-network-share]`, path `ParchaOS/dropbox`; read with
  smbprotocol, credentials in `[credentials-file-removed]`, never print them). Crop, scale to one height, `hstack`, measure, list
  every difference, fix, send the image. Figma's Starter plan has a tool-call limit: save numbers and screenshots locally.
- **Motion:** menus, popovers, windows: short fade in (120 ms), slightly slower fade out (200 ms), no sliding/zooming.
  Control Center keeps its own animation.
- **Edit Controls is always available**, in every style, and has no wiggle: resize handle on every tile at once.
- **Controls live in Control Center only.** Dragging a control onto the top bar was tried (2026-10-01) and removed: the owner never asked for it (it came from a line in the macOS reference's hint text). Do not re-add without being asked.
- **Naming:** original ParchaOS names and wording; no reference-desktop names in the UI or docs.
- Don't use the word "liquid" in package names or UI.

## 2. Architecture

| Piece | Where | Notes |
|---|---|---|
| Own glass library | `packaging/parchaos-glass/glass.js` | `GlassPane` actor: a `Clutter.Clone` of the background group and the window group through a `Clutter.ShaderEffect`. Signed-distance rounded rect, superellipse bezel, Snell refraction through the bezel normal, edge lens that builds to the rim, rim light along the light direction, inner shadow away from the light, cool drop shadow. Model follows the MIT liquid-glass extension (credit in `NOTICE`). |
| Control Center | `packaging/parchaos-controls/files/extension.js` | `ControlsPanel` (tiles, edit mode), `ControlsPicker` (separate window), `ControlsButton` (top-bar button). With refraction on, one `GlassPane` per tile. |
| Menus | `packaging/parchaos-session/files` (`_dressMenu`, `_glassBehind`, `_hookMotion`), `parchaos-global-menu` | Style classes, fades, and our own `GlassPane` behind each menu when refraction is on. |
| Preset | `packaging/parchaos-desktop/files/parchaos-theme-sync` (`GLASS_PRESET`) | Writes the third-party extension's settings. Retire as our glass takes over. |
| Third-party glass | `packaging/parchaos-glass-effects` (MIT, liquid-glass by Ryosuke Watanabe) | Still draws dock and notifications (menus and Control Center are ours). Settings schema path is `/org/gnome/shell/extensions/liquid-glass/` (not the uuid path). |

Settings keys: `org.parchaos.desktop` `style` (glass|classic), `glass-effects` (refraction), `controls-order`, `controls-hidden`,
`controls-sizes` (`id=COLSxROWS`).

## 3. Test rig (use this, not guesses)

- **Real GPU preview:** `sudo dnf install mutter-devkit`, then
  `DEVKIT=1 EXTS="parchaos-controls@parchaos.org" SETTINGS="/org/parchaos/desktop/style 'glass';..." OUT=/tmp/x scripts/devshot/run.sh plan.json 60`
  opens a nested GNOME Shell window on the real GPU with a private HOME and bus, runs the JSON plan (clicks, drags, keys, screenshots)
  and writes PNGs. Headless mode (no `DEVKIT`) uses software rendering and cannot judge glass.
- Plan steps: `wait`, `shot`, `move`, `press`, `release`, `drag`, `type`, `combo`, `log`, `states`.
- Wallpaper for tests: copy `~/.config/background`; use a grid test image to judge refraction.
- Clutter 50 notes: `new Clutter.ShaderEffect()` (no `shader_type`); uniforms need `GObject.Value` (float/int); vec3 uniforms are not
  supported from GJS, pass three floats; `St.BoxLayout` has no `vertical`/`spacing`/`children` properties (use `orientation`, style `spacing`, `add_child`).
- `scripts/smoke-test.sh` must pass; `scripts/lint.sh` must pass; add a spec changelog entry and bump Release for every package change.
- Shadows: keep the drop shadow (`shi`) and inner shadow (`ao`) low; the owner flagged stronger-than-reference shadows once.
- **Real-desktop checks** are read-only screenshots through the portal
  (`gdbus call --session -d org.freedesktop.portal.Desktop -o /org/freedesktop/portal/desktop -m org.freedesktop.portal.Screenshot.Screenshot "" "{'interactive': <false>}"` writes `~/Pictures/Screenshot-N.png`). No remote control is available (see section 6).

## 4. Work remaining, in priority order

### 4.1 Glass: match the reference (ticket #135)
Done: working shader, Control Center tiles. To do:
1. **Tune to the macOS reference** (Control Center photo in the ticket and `dropbox`): stronger edge lens and the visible warped ring ~15% in; rim hot-spots at top and bottom; dark smoky body; verify with a grid test image and with the real wallpaper.
2. **Backdrop-adaptive tint**: DONE (smoky on dark, warm grey veil on bright, text stays white). Still to do: per-pane text colour sampling for very bright wallpapers; warm refraction tint like the light reference.
3. **Slider look**: thin track and thin fill DONE; still to do: Display slider (no tile yet), end icons, and the AirDrop-style round button on the Sound tile.
4. **Menus**: DONE for refraction mode: `parchaos-session` `_glassBehind()` puts a `GlassPane` under each menu's content (follows it per frame, fades with it, 14 px corners); the third-party menu glass is switched off in the preset. To do: left-align menus to their button like the reference, per-item hover pill on glass, popovers (weather, calendar) check, Classic style unchanged.
5. **Dock and notifications** with `GlassPane`; then remove `parchaos-glass-effects` and the preset in `parchaos-theme-sync`.
6. **GNOME 51 / Fedora 45**: re-check `Clutter.ShaderEffect`, `global.stage.context`, clone sources; extensions already declare 51.
7. **GPU cost**: measure (nested shell with `GALLIUM_HUD` or `intel_gpu_top` equivalent); add a switch in Settings if heavy. Refraction stays opt-in (Settings asks when Glass is turned on).

### 4.2 Edit Controls (ticket #148)
Done: edit mode, separate movable picker, drag from picker, placeholders, corner resize handle (drag, snaps to allowed sizes), per-connection tiles, icon-only at 1x1.
To do: (a) **Menu Bar option**: drag a control from the picker onto the top bar; it shows as an icon in the bar (`controls-menubar` key, a `PanelMenu.Button` per control, drag off to remove); (b) richer gallery: What's New card, Suggestions, live previews, more categories (battery, clock, ...); (c) Wi-Fi/Network tiles can also go taller (2x2); (d) drop onto a specific empty slot; (e) resize handle shape: match the reference stroke exactly (thick, hugging the corner); (f) Control Center in Classic style keeps the old flat look; confirm.

### 4.3 Menu bar menus (ticket #135)
Done: logo, app, File/Edit/View/Go/Window/Help with shortcuts, Recent Items, Force Quit. To do: apps' own menus (D-Bus menu export, like the reference's Bookmarks/Mail/Tools), Sort By / Open With submenus, Services; open-item capsule polish; shortcut symbols for all items; Quick Look wiring.

### 4.4 Dock (ticket #131)
Done: notification count follows its icon under magnification (patch 0007, untested with a real notification). To do: verify with a real notification; running dot and badge together; glass dock via `GlassPane`.

### 4.5 Upgrade breakage (tickets #169, #115)
Wallpaper vanished and menu bar emptied during `sudo dnf upgrade` twice (2026-09-30), no shell crash, not reproducible headless.
Shipped: `/var/lib/parchaos/session-updated` marker (`%transfiletriggerin` in `parchaos-desktop`), session extension shows a log-out notice, rebuilds the wallpaper layer and the menu bar, logs `parchaos-session: after update`.
**Next time it happens**: `journalctl --user -b | grep parchaos-session` before logging out. Ideas: stop extensions before the transaction (`%pretrans`/offline update only), restart the shell session after updates, or make updates offline-only through the Store.

### 4.6 Other planned items (see the tracker; specs exist for several)
#149 Nearby share, #150/#34 search overlay (needs a name), #151 recovery boot menu (VM test first), #152 translate selection, #154 focus modes, #155 screenshot markup, #156 phone link, #157 migration assistant, #159 privacy report, #160 Flatpak permissions (background not done), #162 speak selection (Piper opt-in), #163 photo search in Parcher, #165 widgets, #166 time-of-day wallpapers, #167 ARM64, #168 managed devices. Also #116 backup network share login (done, untested on the NAS), #132 keyboard remap on relogin, #63 smoke test gaps, #117/#118/#122 Android, Store, assistant (`docs/*-spec.md`).

## 5. Gotchas that cost time

- Replacing extension files under a running shell leaves it with old code: log out after updates. The shell keeps its own copy; `~/.local/share/gnome-shell/extensions/` overrides the system one.
- Never write `%changelog` with a doubled percent sign (lint checks).
- Edit scripts that `replace()` can silently match nothing: assert, and re-read the result. One script once deleted most of an extension file; restore with `git checkout`.
- Don't run `rm -rf` on variable paths (the safety check blocks it): use `"${VAR:?}/name"`.
- `Shell.BlurEffect` cannot follow rounded corners (square halo); our shader draws its own corners.
- The third-party extension hard-codes the Quick Settings menu; Control Center is therefore its own pane drawn by `GlassPane`.
- The tickets MCP: base URL `https://www.spanglishtickets.dev/api/mcp`; long ticket ids from `list_tickets`; comments need `projectId`, `ticketId`, `body`. Keys are masked via `~/.config/claude-redact/literals`.

## 6. Open decisions / blocked
- Remote control of the real desktop (clicks) is blocked by the harness permission check; read-only screenshots work.
- Real-desktop confirmation of everything above is still pending: all work was checked in nested or headless shells.
- Figma access: tool-call limit on the Starter plan; ask for frame links when more kit numbers are needed.
