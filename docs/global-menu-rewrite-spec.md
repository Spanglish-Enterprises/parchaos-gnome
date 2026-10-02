# Global menu bar — clean-room rewrite spec

**Why this exists**: `parcha-global-menu` was a direct fork of Inled's own
`pulsaros-global-menu` (fetched and `sed`-patched at build time from
`Inled-Pulsar-OS/PKG`). Inled's own PKG monorepo README explicitly lists it
under "Original Inled / Pulsar OS work — no third-party upstream," and their
actual license text (read directly at `license.inled.es`, not assumed from the
"MIT-INLED" name) adds real restrictions beyond standard MIT: a non-compete
clause, a mandatory-relicensing-back-to-MIT-INLED clause, and a rights-
retention clause requiring derivative works to grant "all rights and benefits
exclusively to the original authors." ParchaOS is a directly competing
Linux desktop product, so this is real exposure, not a theoretical one.

This document is the *only* thing the rewrite should be written from. No part
of the implementation should be written by reading, referencing, or adapting
Inled's actual `extension.js` — only this feature description, the reference desktop's
publicly-known menu bar conventions, and GNOME Shell's own public,
documented extension APIs (`PanelMenu`, `PopupMenu`, `St`, `Clutter`,
`GObject`, etc. — the same APIs any independent GNOME Shell extension uses).

## What it needs to do

### Logo menu (leftmost)
A small button showing the ParchaOS passion-fruit logo. Opens a menu with:
an "About ParchaOS" item (shows a real system-info panel: OS name/version,
kernel, memory — sourced from `/etc/os-release`, `uname`, `/proc/meminfo`,
not copied from any other project's about-panel code), and real system
actions (Settings, Lock Screen, Log Out, Restart, Shut Down). Restart/Shut
Down should confirm before acting (a simple confirmation dialog is enough —
no specific countdown-timer behavior needs to be replicated from anything).

### App menu (next to the logo)
Shows the name of the currently focused application, bold. When no real
user window has focus (desktop focused, or a background/overlay window like
Desktop Icons NG's own rendering surface — exclude any window whose
GApplication id or WM_CLASS matches known desktop-shell helper apps, not
just DING specifically, so this generalizes), shows "Parcher" as the
default idle-state label, following the common convention of showing the file manager's name when
nothing else is focused. Clicking it opens a small menu: "About
{app}," "Hide {app}," "Quit {app}" — Hide should minimize the focused
window, Quit should close it via the window's own close/delete request.

### Standard menus: File, Edit, View, Go, Window, Help
Populated with real, standard actions a desktop user would expect, using
real public keyboard shortcuts (GNOME/GTK/Nautilus conventions, not
anything Inled invented):
- **File**: New Window (`Ctrl+N`), Close Window (`Ctrl+W`)
- **Edit**: Undo (`Ctrl+Z`), Redo (`Ctrl+Y`), Cut (`Ctrl+X`), Copy
  (`Ctrl+C`), Paste (`Ctrl+V`)
- **View**: Icon View (`Ctrl+1`), List View (`Ctrl+2`), Show Hidden Files
  (`Ctrl+H`) — real, long-standing Nautilus/GTK shortcuts
- **Go**: Back (`Alt+Left`), Home, Documents, Downloads, Pictures (open the
  real special-dirs via `GLib.get_user_special_dir`)
- **Window**: Minimize (`Super+H`... or send a minimize request directly),
  Zoom/maximize toggle
- **Help**: a generic "ParchaOS Help" item pointing at this project's own
  real docs/support channel (not Inled's Debian-support link or any
  Inled-branded destination)

Implementation mechanism: simulate the real keyboard shortcut via a virtual
keyboard device (`Clutter.VirtualInputDevice`/`notify_keyval`), the same
general technique any GNOME accessibility or automation tool uses — not a
mechanism unique to or copied from Inled.

### Weather indicator (right side, already built independently)
Already implemented this session as new, original code — verified against
real GNOME `gnome-weather`'s own public source for correct `GWeather`/
`Geoclue` API usage (a different, real, independent GNOME project, not
Inled's). Carry it over as-is into the rewrite; it was never derived from
Inled's file in the first place.

### Explicitly NOT in scope for this pass
- The custom full-screen lock screen with video-wallpaper playback (a
  large, separate subsystem in the original). Ship the OS's real, stock
  GNOME lock screen for now; revisit as its own clean-room project later if
  wanted.
- The 60-second countdown power-off/restart dialog specifically — a plain
  confirm/cancel dialog satisfies the same real user need without
  replicating that specific behavior.

## Naming

New UUID: keep `parchaos-global-menu@parchaos.org` (ParchaOS's own product
identity, not Inled's `pulsaros-global-menu@inled.es`) — this was already
the case after the earlier rebrand, no change needed there. GObject type
names, CSS classes, and internal structure should all be freshly named,
not mirrored from Inled's file.
