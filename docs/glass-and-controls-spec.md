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
- **Notifications at the top right** (like the reference). Done in `parchaos-session` `_placeBanners()`; the `notification-banner-reloaded` extension (no GNOME 50/51 release) can be dropped from the enabled list later.
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
| Switch rules | `packaging/parchaos-desktop/files/parchaos-theme-sync` (`GlassEffects`) | Classic turns refraction off; Blur My Shell's dock blur is turned off while refraction is on. |

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
5. **Dock**: DONE (`parchaos-session` `_hookDockGlass`: one `GlassPane` under `dashtodockContainer`, follows `dash-background` per frame; third-party dock glass off in the preset). **Notifications and OSD**: DONE (`parchaos-session` `_follow()`: a `GlassPane` under the notification banner and the OSD window; the OSD window itself still shows its dark theme background, clear it if the owner wants it lighter). **`parchaos-glass-effects` RETIRED (2026-10-01)**: package directory removed, `parchaos-glass` obsoletes it, `parchaos-theme-sync` keeps only the Classic-turns-refraction-off rule and the dock-blur toggle. (Original note: retire `parchaos-glass-effects`: nothing it draws is used any more with the preset (all surfaces are ours), so remove the package, its Requires in `parchaos-desktop`, the preset code in `parchaos-theme-sync` and the `liquid-glass` uuid references; keep its MIT credit in `parchaos-glass/NOTICE`.
6. **GNOME 51 / Fedora 45**: re-check `Clutter.ShaderEffect`, `global.stage.context`, clone sources; extensions already declare 51.
7. **GPU cost**: measure (nested shell with `GALLIUM_HUD` or `intel_gpu_top` equivalent); add a switch in Settings if heavy. Refraction stays opt-in (Settings asks when Glass is turned on).

### 4.2 Edit Controls (ticket #148)
Done: edit mode, separate movable picker, drag from picker, placeholders, corner resize handle (drag, snaps to allowed sizes), per-connection tiles, icon-only at 1x1.
To do: (a) DROPPED: the owner never asked for menu-bar placement; controls go into Control Center only; (b) richer gallery: DONE 1.0.0-36 What's New card + Suggestions row (wrapped rows via `ControlsPicker._flow`; FlowLayout mis-measured inside the scroll view, do not use it); Edit mode is glass too, measured against the owner's Mac screenshot (`edit controls.png`, 1.0.0-38): NO panel pane behind Control Center (every tile is its own glass via `panel.useGlass`; empty slots are faint dark discs, alpha .16); ONE big light glass pane behind the picker (params disp 10, blur 1.6, tint .2, z 30 (1.0.0-40; blur 3 was judged too blurry by the owner against the reference, 0.6 too sharp), Control Center is stacked above the picker), picker ~52% x 84% of the screen CENTRED on screen (owner: the reference screenshot was a crop, so its left offset means nothing; 1.0.0-39), section headings with divider lines. Reference gaps still open: per-category app-style icons in the sidebar, glass look on gallery tiles, a preview picture in the What's New card, larger Suggestions (Wi-Fi 'on' is a white tile); Battery control (1.0.0-37, `_batteryTile`) exists only when UPower reports a battery (absent on a desktop PC, so it never shows in the panel or picker); still to do: live previews, more categories (battery, clock, ...); (c) DONE 1.0.0-35: connection tiles (Wi-Fi, Bluetooth, Wired, VPN, Airplane) can also be 2x2 (icon on top, name and state below; `_smallLayout` handles tall); (d) drop onto a specific empty slot; (e) resize handle shape: match the reference stroke exactly (thick, hugging the corner); (f) Control Center in Classic style keeps the old flat look; confirm.


### 4.2a Pixel measurements of the owner's edit-mode reference (2026-10-01)

Reference files ([private-dropbox]): `edit controls.png` and the later `Screenshot 2026-09-30 at 9.33...PM.png` (light, green meadow wallpaper; better for glass measurements). Both are 2684 px wide Retina captures (1342 logical px); the owner says the images are crops, so absolute positions of the windows mean nothing (the picker is centred on screen).

Method (repeat it, do not eyeball): Pillow/numpy/scipy in a scratch venv (`python3 -m venv imgv && imgv/bin/pip install pillow numpy scipy`), compare the nested-shell screenshot (`scripts/devshot/run.sh`, plan: open Control Center, click Edit Controls) against the reference with `ffmpeg ... hstack`, and measure patches either side of the picker's edge.

Measured on the picker (ParchaOS values in brackets):
- Frost: the hill and tree texture seen sharp outside the picker is completely gone inside it; a Laplacian-energy test gives an equivalent gaussian of at least ~4 device px and a boundary-continuity fit keeps improving up to sigma >= 40 device px, i.e. a heavy blur of roughly 20-24 logical px. [`bgblur: 24`, a real `Shell.BlurEffect` on the clones; the shader's 12-tap blur cannot do this cleanly. Use `pad: 90` so the blur does not darken the pane's edge.]
- No lens distortion in the middle of the picker, only at the rim [`disp: 8`, `z: 30`].
- Darkening: a bright sky (~190) becomes ~125 inside the picker, ratio 0.63-0.72 (mean 0.65), neutral grey; colours of green areas stay saturated. [ours measured 0.69 at `tint .3, dim .5`, then `dim .44`]; re-measure after any glass change (patch pairs either side of the edge).
- Sidebar half of the picker looks slightly darker/greyer than the content half, separated by a 1 px divider at x~543/2000 (not done yet).
- Control Center tiles: each tile is its own glass; small tiles are clear with a bright rim; empty slots are dark translucent discs; the "on" tiles (Wi-Fi, Bluetooth, Dark Mode) are solid white discs with a dark glyph; Sound/Display tiles are clear and show the blurred scenery behind the slider.
- Picker rows: sidebar rows use coloured app-style icons ~38 px with 17 px labels; selected row is a light rounded highlight; gallery tiles are glass (blurred scenery visible through them, bright rim), labels under them; headings are small bold grey with a divider line above; "Done" is a blue pill bottom right.

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
- **Publishing `parchaos-glass` as its own public repo: deferred by the owner (2026-10-01).** Risks and prerequisites if revisited: scrub reference-desktop names from docs, comments and package text; neutral name (e.g. `parcha-glass`); keep the MIT credit/NOTICE for the liquid-glass extension; pick one licence (MIT) for our own code; never include the owner's reference screenshots; lawyer skim if commercial.
- Remote control of the real desktop (clicks) is blocked by the harness permission check; read-only screenshots work.
- Real-desktop confirmation of everything above is still pending: all work was checked in nested or headless shells.
- Figma access: tool-call limit on the Starter plan; ask for frame links when more kit numbers are needed.
