# Feature roadmap from the reference desktop's 2025-2026 releases

Status: 2026-10-01. Owner asked: "think about and document what other features [from the reference
desktop's two latest releases] we can do, and make tickets with specs", then: "make sure that the
specs don't violate any copyright or anything of the sort". Sources (read for ideas only): the
release notes of those two releases (9to5Mac's full list for the 2026 release, Cult of Mac's for
the 2025 one) and the owner's private reference screenshots in the dropbox.

Each section below is the spec its ticket carries: tickets **#172-#186**, filed 2026-10-01.

Left out on purpose: features that need the reference vendor's phone, cloud or chips (calls
through a phone, cloud photo albums, large on-device models), game overlays, music/podcast app
features, and anything an open ticket already covers (listed at the end).

## Originality and licences (applies to every item)

- **Ideas and behaviour only.** Features are inspired by what the reference desktop does. Nothing
  is copied from it: no code, artwork, icons or symbol fonts, sounds, colour values, wallpapers,
  screenshots or text.
- **Our own names and wording.** None of the reference's feature names, app names or exact menu
  labels in the UI, package names or user docs. Examples used here: "file piles", "ongoing
  activity", "Ambient Sounds", "Reader", "Automations", "Screen Lookup", "Cast Screen", "New Note",
  "High Contrast", "Voice Recorder". Use GNOME's own terms where they exist (Power Saver, GNOME's
  accent colours).
- **Look.** A general style (glass, rounded shapes, a top menu bar) is fine; specific trade dress is
  not. Window buttons, icons and layout pictures are drawn by us with our own colour values, and
  pass the Apple-lookalike audit before the repo goes public (owner rule, 2026-09-25).
- **Reference screenshots and recordings** stay private (dropbox) and are used only to measure;
  never shipped, never in the public repo or the website.
- **Third-party pieces** carry an open licence recorded in their package: Tesseract and its
  language data (Apache-2.0), GWeather with MET Norway data (attribution shown in the UI, as the
  weather menu does now), CC0 or self-made sounds, Adwaita icons (CC BY-SA / LGPL), Desktop Icons
  NG (GPL, our fork), Piper/espeak-ng voices (already licence-checked for Speak Selection).
- **Sources** above are cited for traceability, not quoted in the product.

---

## 1. More controls for Edit Controls (#172)
Spec: `docs/controls-catalog.md` (full table). 21 controls whose backing is already installed
(Calculator, Timer, Alarm, Stopwatch, New Note, Weather, Keyboard Brightness, Screen Recording,
Keep Awake, Camera Off, Microphone Off, Location, Text Size, Zoom, High Contrast, Show Desktop,
Back Up Now, Clipboard History, Dictation, Speak Selection, Snapshots); 5 more after the owner
approves one package each (Voice Recorder, Cast Screen, Camera, Characters, Screen Reader). All
hidden by default, listed by category, shown only when they apply, fed to the usage learner.
Done when: each appears in its category in Edit Controls, works from the panel, and a smoke check
covers add/tap/remove for each.

## 2. Weather popover with forecast (#173)
Layout reference: owner's 12.31.45 screenshot. Today the menu-bar weather item shows only the
temperature and "Open Weather". Spec: one glass popover (menu material), about 380 px wide: place
name with a location arrow, large temperature, condition and high/low on the right; a warning row
when GWeather reports an alert; five hourly columns (hour, symbol, rain chance when > 20%,
temperature); up to two other places from GNOME Weather's saved locations, one row each; "Open
Weather" and the data credit line at the bottom (MET Norway's terms require attribution). Symbols:
Adwaita/ParchaOS icons. Refresh every 15 minutes and when opened. Done when: side by side with the
reference shows the same rows, and a headless test fills it from a fixed GWeather fixture.

## 3. Battery menu for laptops (#174)
Layout reference: 12.31.02. A popover from the menu-bar battery item: "Battery" and percentage;
power source; Power mode with a Power Saver switch (GNOME's `power-saver` profile); "No apps are
using much power" or the top two apps by CPU over the last minute (read locally from `/proc`,
nothing stored); "Power Settings..." opens Settings > Power. Only on machines with a battery.
Done when: on a laptop VM with a fake UPower battery the rows show and the switch changes the
power profile.

## 4. Desktop right-click menu and file piles (#175)
Behaviour reference: owner's 09-29 screen recording. Desktop menu (our wording): New Folder;
Properties; Change Wallpaper...; Edit Widgets... (once #165 lands); a divider; Group Files into
Piles (check); Sort Piles By > Type / Last Opened / Date Added / Date Modified / Date Created /
Tags; Icon Options. Piles: desktop files of one group are drawn as one pile (top three thumbnails
fanned), labelled by group ("Pictures", "Screenshots", "Recordings", "Documents"...); click fans
it open in place, click again closes it; new files join their pile. Built in parchaos-desktop-icons
(our Desktop Icons NG fork) as patches. Types from MIME types; dates from file info. Done when: the
recording's sequence can be repeated on ParchaOS (turn on, group by type, open a pile, open a file
from it).

## 5. Menu bar: clear background and overflow (#176)
Idea: the 2025 release's clear menu bar with an optional background; the 2026 release's expanding
of status items that would be hidden. Spec: Settings > Appearance > Menu bar background: Clear
(default with Glass), Tinted, Solid; text colour keeps following the wallpaper. Overflow: when
status icons would collide with the app menus, the left-most ones fold into a "..." item that opens
them in a small glass strip. Done when: at 1280 px with ten tray icons nothing overlaps, and each
background mode reads well over a light and a dark wallpaper.

## 6. Appearance: accent colour, highlight colour, icon style (#177)
Layout reference: owner's 6.02 PM recording. Spec: GNOME's own nine accent colours (blue, teal,
green, yellow, orange, red, pink, purple, slate) via `accent-color`, carried into our GTK and shell
themes; Highlight colour (follows the accent, or a pick); Icon style: Standard, Dark, Glass, Mono
(variants generated by parchaos-icon-theme's generator from our own icons: dark plates; glass =
translucent plates with white glyphs; mono = one colour in the accent). Live preview card. Done
when: each choice changes GTK 3/4, libadwaita, the shell and the icon theme without a log-out.

## 7. Window chrome refresh (#178)
Idea: the 2026 release's glassier window buttons, consistent corners, clearer active windows,
sidebars to the edge, fewer menu icons. Spec: title buttons drawn as glass discs from our own SVGs
and colour values, hover bounce 120 ms (scale 1.0 -> 1.08 -> 1.0); one radius (12 px) for GTK 3,
GTK 4/libadwaita and server-side decorations; inactive windows: title text and buttons at 50%;
sidebars edge to edge in our apps (Parcher, Settings); menu items show icons only where they carry
meaning. Passes the lookalike audit. Done when: side by side with the reference for an active and
an inactive window in light and dark.

## 8. Ongoing activity in the menu bar (#179)
Idea: the 2025 release shows ongoing things in the menu bar. Spec: a small capsule left of the
status icons for one ongoing thing at a time, newest first: running timer (Clocks), file transfer
or download (app progress), screen recording (elapsed time, stop button), media playing (title,
play/pause), later calls and phone notifications through Phone Link (#156). Click opens a glass
popover with details and actions. Sources: MPRIS, the shell's recorder, Clocks D-Bus, the
LauncherEntry progress API the dock already reads. Done when: timer, recording and a download show
and end correctly; nothing appears when idle.

## 9. Screen Lookup (#180)
Idea: the 2026 release's "select part of the screen and ask about it". Local only: a shortcut
(Super+Shift+Space) dims the screen; drag a box; a popover offers Copy Text (OCR with Tesseract,
on device), Translate (#152), Search the web (opens the browser with the text), Look Up
(dictionary), and Ask the assistant (#122) once it exists. Nothing leaves the machine unless the
user picks Search. Done when: text in an image or a paused video can be copied in two clicks, and
OCR runs offline.

## 10. Window positions per monitor setup (#181)
Idea: the 2026 release's better window placement across external displays (the owner uses three
screens). Spec: parchaos-session records, per set of connected monitors (by EDID serials), each app
window's monitor and rectangle; when the same set comes back (wake, re-plug, log-in), windows
return there; a new set starts from GNOME's own placement. Extends session restore (#76). Done
when: unplugging and re-plugging a monitor, or sleeping and waking with three screens, puts every
window back where it was.

## 11. Window tiling layouts (#182)
Idea: tiling by dragging to edges and corners, layouts offered on the maximize button. Spec: drag to
the left/right edge: half; to a corner: quarter; to the top: fill, with a glass preview. Hovering
the maximize title button shows a glass popover with layouts (halves, quarters, thirds, "arrange
two/three/four windows") drawn with our own pictures; Window menu items and Ctrl+Super+arrows do
the same, sharing one code path. Done when: every layout works on 1, 2 and 3 monitors.

## 12. Ambient sounds (#183)
Idea: the 2025 release's sounds that play in the background with a timer. Spec: rain, ocean,
stream, night, white/pink/brown noise; noise generated in code, recordings CC0 with sources listed
in the package README; plays under other audio at its own volume; stops after 15 min-8 h; simple
tone control (warmer/brighter). A Control Center control "Ambient Sounds" (Sound category, hidden
by default) and a Settings > Sound section. Done when: starts from the control, stops on the timer,
survives switching output devices.

## 13. Reader (#184)
Idea: the 2025 release's system-wide reading view. Spec: a shortcut opens the selected text (or the
whole page via the accessibility tree) in a calm reading window: large text, chosen font, spacing
and colours, with Speak (parchaos-speak, #162) highlighting each word as it is read. Local only.
Done when: works for Parcher, the browser and Text Editor, and reads aloud with the current word
highlighted.

## 14. Smart file name suggestions in Parcher (#185)
Idea: the 2026 release's file-name suggestions. Spec: when renaming (or saving a screenshot),
suggest up to three names from the file's content: document title or first heading, image text
(OCR), photo date and place, audio tags. Local only, rules and metadata first, no model download.
Done when: renaming a screenshot of a receipt suggests the shop name and date.

## 15. Automations (#186)
Idea: the reference's automation app and its 2026 "describe it and it is built". First step: a
small app with triggers (time, connecting to a network or a display, an app opening, a file
appearing in a folder) and actions (open, Focus on/off, change a setting, run a command,
move/rename files), stored as plain files in `~/.config/parchaos/automations/`. Building from a
description comes later with the assistant (#122). Done when: three examples (work Focus at 9:00,
move screenshots weekly, dark mode when a projector connects) run reliably.

---

## Already covered by open tickets (add these specs there when work starts)

- **#150 search overlay**: modes on Ctrl+1..4 (Apps, Files, Actions, Clipboard history for the last
  8 hours from parchaos-clipboard); actions run from the results (open with, reveal, copy path, set
  a timer, toggle a setting).
- **#165 widgets**: Edit Widgets and close buttons at the bottom; mixed materials per widget; widgets
  can sit on the desktop.
- **#122 assistant**: "Ask about this" in context menus for selected text, images and files; Screen
  Lookup (#180) hands its selection to it.
- **#156 phone link**: phone notifications and transfers feed ongoing activity (#179).
- **#171 glass transparency slider**: unchanged.
