# Control Center: controls catalogue

Status: 2026-10-01. Tickets #172 (this catalogue), #148 (Edit Controls), #135 (glass). Owner decisions: every control
below is **listed in Edit Controls but not in the panel by default**; Suggestions learn from use and
surface them (see "Learning" below).

## Shipped controls (in the panel by default)

Wi-Fi, Bluetooth, Wired, VPN, Airplane mode, Now Playing, Focus (Do Not Disturb), Dark Mode,
Night Light, Display (only with a built-in backlight), Sound, Power mode, Battery (only with a
battery), Screenshot, Settings, Lock, plus other extensions' Quick Settings toggles ("Other").

## To add: backing already on the system (no new packages)

| Control | Category | Size(s) | What it does | Backed by |
|---|---|---|---|---|
| Calculator | Utilities | 1x1 | Opens Calculator | `org.gnome.Calculator` (installed) |
| Timer | Clock | 1x1, 2x1 | Opens Clocks on Timer; 2x1 shows time left of a running timer | `org.gnome.clocks` (installed) |
| Alarm | Clock | 1x1, 2x1 | Opens Alarms; 2x1 shows the next alarm | `org.gnome.clocks` |
| Stopwatch | Clock | 1x1 | Opens Stopwatch | `org.gnome.clocks` |
| New Note | Notes | 1x1 | New note in Text Editor (`~/Documents/Notes/<date>.md`) | `org.gnome.TextEditor` (installed) |
| Weather | Weather | 2x1, 2x2 | Current conditions; opens Weather | GWeather, as the menu-bar weather item |
| Keyboard Brightness | Display | 4x1, 2x1 | Slider; only with a backlit keyboard | UPower `KbdBacklight` |
| Screen Recording | Shortcuts | 1x1 | Starts the shell's recorder (screen or area) | `Main.screenshotUI` (video mode) |
| Keep Awake | System | 1x1 | Inhibits idle and sleep until turned off | `Shell` inhibitor / `org.gnome.SessionManager.Inhibit` |
| Camera Off | Privacy | 1x1 | Blocks the camera for every app | `org.gnome.desktop.privacy disable-camera` |
| Microphone Off | Privacy | 1x1 | Blocks the microphone for every app | `org.gnome.desktop.privacy disable-microphone` |
| Location Services | Privacy | 1x1 | On/off | `org.gnome.system.location enabled` |
| Text Size | Accessibility | 1x1, 4x1 | Larger text toggle (1x1) or slider (4x1) | `org.gnome.desktop.interface text-scaling-factor` |
| Zoom | Accessibility | 1x1 | Screen magnifier on/off | `org.gnome.desktop.a11y.applications screen-magnifier-enabled` |
| High Contrast | Accessibility | 1x1 | High contrast / greyscale | `org.gnome.desktop.a11y.interface high-contrast` |
| Show Desktop | Desktop | 1x1 | Hides all windows, again brings them back | window actors (as Edit Controls) |
| Back Up Now | Utilities | 1x1, 2x1 | Starts Parcha Backup; 2x1 shows the last backup | `deja-dup --backup` |
| Clipboard History | Utilities | 1x1 | Opens the clipboard list | parchaos-clipboard |
| Dictation | Accessibility | 1x1 | Starts dictation | parchaos-dictation |
| Speak Selection | Accessibility | 1x1 | Reads the selected text aloud | parchaos-speak |
| Snapshots | Utilities | 1x1 | Opens Wisp (system snapshots) | parchaos-snapshots |

## To add: needs one package in the ISO (owner approval for size)

| Control | Category | Package |
|---|---|---|
| Voice Recorder | Notes | `gnome-sound-recorder` |
| Cast Screen | Display | `gnome-network-displays` |
| Camera | Utilities | `gnome-snapshot` |
| Characters | Utilities | `gnome-characters` |
| Screen Reader | Accessibility | `orca` |

## Later (needs the feature first)

Nearby Share (#149), Phone Link (#156), Focus modes (#154), window tiling left/right (Window menu
already works; a control is small once wanted).

## Rules for every new control

- Original names and wording; no reference-desktop names (see `feature-roadmap-2026.md`,
  "Originality and licences"). Icons: Adwaita symbolic or our own, never the reference's symbols.
- Hidden by default (`controls-hidden`), listed in its category in the picker.
- Only shown when it applies (no Keyboard Brightness without a backlit keyboard, no Battery on a
  desktop). Same rule as Display and Battery today.
- Sizes follow the owner's tile rules: plain switches 1x1 only; shortcuts 1x1 or 2x1; sliders 4x1
  or 2x1; connections 1x1/2x1/2x2.
- Feeds the learner: a tap counts, and so does using the thing it stands for by a route that is
  clearly the user's (opening the app it opens). Map the app id in `USAGE_APPS`.

## Learning (Suggestions)

Private by design (owner: "learn, while maintaining privacy"). `UsageLearner` in
`parchaos-controls` keeps control id -> {score with a 14-day half-life, last use} in
`~/.local/share/parchaos/controls-usage.json`, created 0600, nothing else. It counts taps and slides
on a control, screenshots, and opening Settings. Automatic switches (sunset dark mode, scheduled Do
Not Disturb, idle lock) are not counted. Suggestions: used controls not in the panel first, then
the other missing ones; a fixed handful only before there is any history. Settings > Privacy >
Suggestions has the switch (`learn-usage`) and "Forget what was learned"; turning it off or Forget
deletes the file, and the extension drops its copy (file monitor).
