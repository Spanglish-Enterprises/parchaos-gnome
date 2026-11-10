// SPDX-License-Identifier: GPL-3.0-or-later
// Window tiling (ticket #182): halves, quarters, thirds and fill, from three places that share
// this one code path: dragging a window to a screen edge or corner (a preview shows where it will
// go), Ctrl+Super+arrow keys, and the Window menu (Move & Resize, Arrange Windows).
//
// Dragging: left or right edge = half, a corner = quarter, the top edge = fill. GNOME's own edge
// tiling is turned off while this runs (it only knows halves) and back on afterwards.
// Keys: Ctrl+Super+Left/Right = halves; Up/Down from a half go to its quarters; Up otherwise
// fills; Down from fill or a half's quarter steps back; Down otherwise returns the window to the
// size it had before it was first tiled.
//
// Original code for ParchaOS, GPL-3.0-or-later.

import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import St from 'gi://St';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';

// Layout -> [x, y, width, height] as fractions of the monitor's work area.
export const LAYOUTS = {
    'left': [0, 0, 1 / 2, 1],
    'right': [1 / 2, 0, 1 / 2, 1],
    'top-left': [0, 0, 1 / 2, 1 / 2],
    'top-right': [1 / 2, 0, 1 / 2, 1 / 2],
    'bottom-left': [0, 1 / 2, 1 / 2, 1 / 2],
    'bottom-right': [1 / 2, 1 / 2, 1 / 2, 1 / 2],
    'left-third': [0, 0, 1 / 3, 1],
    'center-third': [1 / 3, 0, 1 / 3, 1],
    'right-third': [2 / 3, 0, 1 / 3, 1],
    'left-two-thirds': [0, 0, 2 / 3, 1],
    'right-two-thirds': [1 / 3, 0, 2 / 3, 1],
    'fill': [0, 0, 1, 1],
};

/** The rectangle of a layout inside a work area; neighbours share edges exactly. */
export function rectFor(layout, area) {
    const [fx, fy, fw, fh] = LAYOUTS[layout];
    const x1 = area.x + Math.round(area.width * fx), x2 = area.x + Math.round(area.width * (fx + fw));
    const y1 = area.y + Math.round(area.height * fy), y2 = area.y + Math.round(area.height * (fy + fh));
    return {x: x1, y: y1, width: x2 - x1, height: y2 - y1};
}

const KEY_STEPS = {
    left: {'top-right': 'top-left', 'bottom-right': 'bottom-left'},
    right: {'top-left': 'top-right', 'bottom-left': 'bottom-right'},
    up: {'left': 'top-left', 'right': 'top-right', 'bottom-left': 'left', 'bottom-right': 'right'},
    down: {'left': 'bottom-left', 'right': 'bottom-right', 'top-left': 'left', 'top-right': 'right', 'fill': 'restore'},
};
const KEY_DEFAULT = {left: 'left', right: 'right', up: 'fill', down: 'restore'};

/** Where a Ctrl+Super+arrow press takes a window that is in `current` (a layout or null). */
export function nextLayout(current, direction) {
    return KEY_STEPS[direction][current] ?? KEY_DEFAULT[direction];
}

/** Layouts for arranging n windows side by side (2: halves, 3: a half and two quarters, 4: quarters). */
export function arrangement(n) {
    return {
        2: ['left', 'right'],
        3: ['left', 'top-right', 'bottom-right'],
        4: ['top-left', 'top-right', 'bottom-left', 'bottom-right'],
    }[n] ?? [];
}

const EDGE = 8;      // px from a screen edge that counts as touching it
const CORNER = 60;   // px along an edge, from a corner, that count as the corner

/** The drag zone for a pointer at (x, y) on a monitor with geometry m, or null. */
export function zoneAt(x, y, m) {
    const left = x - m.x < EDGE, right = m.x + m.width - 1 - x < EDGE;
    const top = y - m.y < EDGE, bottom = m.y + m.height - 1 - y < EDGE;
    const nearTop = y - m.y < CORNER, nearBottom = m.y + m.height - y < CORNER;
    const nearLeft = x - m.x < CORNER, nearRight = m.x + m.width - x < CORNER;
    if (left)
        return nearTop ? 'top-left' : nearBottom ? 'bottom-left' : 'left';
    if (right)
        return nearTop ? 'top-right' : nearBottom ? 'bottom-right' : 'right';
    if (top)
        return nearLeft ? 'top-left' : nearRight ? 'top-right' : 'fill';
    if (bottom && (nearLeft || nearRight))
        return nearLeft ? 'bottom-left' : 'bottom-right';
    return null;
}

function isMaximized(win) {
    return typeof win.is_maximized === 'function' ? win.is_maximized()
        : win.get_maximized?.() === Meta.MaximizeFlags.BOTH;
}

function setMaximized(win, on) {
    const modern = typeof win.is_maximized === 'function';
    if (on)
        modern ? win.maximize() : win.maximize(Meta.MaximizeFlags.BOTH);
    else
        modern ? win.unmaximize() : win.unmaximize(Meta.MaximizeFlags.BOTH);
}

function sameRect(a, b) {
    return a && b && Math.abs(a.x - b.x) < 3 && Math.abs(a.y - b.y) < 3 &&
        Math.abs(a.width - b.width) < 3 && Math.abs(a.height - b.height) < 3;
}

/** The layout a window is in now, if it still sits where it was tiled. */
export function currentLayout(win) {
    const t = win._parchaosTile;
    if (!t)
        return null;
    if (t.layout === 'fill')
        return isMaximized(win) ? 'fill' : null;
    return sameRect(win.get_frame_rect(), t.rect) ? t.layout : null;
}

/** Puts a window in a layout on monitor `monitor` (default: its own), or back to its old size. */
export function tile(win, layout, monitor = win.get_monitor()) {
    if (!win)
        return;
    const before = win._parchaosTile;
    if (layout === 'restore') {
        if (isMaximized(win))
            setMaximized(win, false);
        if (before?.restore)
            win.move_resize_frame(true, before.restore.x, before.restore.y, before.restore.width, before.restore.height);
        win._parchaosTile = null;
        return;
    }
    // The size to go back to is the one from before the first tiling.
    const restore = currentLayout(win) || isMaximized(win) ? before?.restore ?? null : win.get_frame_rect();
    if (win.get_monitor() !== monitor)
        win.move_to_monitor(monitor);
    if (layout === 'fill') {
        setMaximized(win, true);
        win._parchaosTile = {layout, restore};
        return;
    }
    if (isMaximized(win))
        setMaximized(win, false);
    const rect = rectFor(layout, Main.layoutManager.getWorkAreaForMonitor(monitor));
    win.move_resize_frame(true, rect.x, rect.y, rect.width, rect.height);
    win._parchaosTile = {layout, rect, restore};
}

/** Arranges the most recently used windows on the focused window's monitor and workspace. */
export function arrange(n, focused = global.display.focus_window) {
    const monitor = focused?.get_monitor() ?? global.display.get_current_monitor();
    const workspace = global.workspace_manager.get_active_workspace();
    const windows = global.display.get_tab_list(Meta.TabList.NORMAL, workspace)
        .filter(w => w.get_monitor() === monitor && !w.minimized && w.can_move?.() !== false)
        .slice(0, n);
    const layouts = arrangement(windows.length >= n ? n : windows.length);
    windows.forEach((w, i) => tile(w, layouts[i], monitor));
}

/** Drag snapping, keyboard shortcuts and GNOME's edge tiling switched off while it runs. */
export class Tiling {
    constructor(keySettings) {
        this._mutter = new Gio.Settings({schema_id: 'org.gnome.mutter'});
        this._mutter.set_boolean('edge-tiling', false);

        global.display.connectObject(
            'grab-op-begin', (_d, win, op) => this._dragBegin(win, op),
            'grab-op-end', () => this._dragEnd(), this);

        this._keys = [];
        if (keySettings) {
            for (const direction of ['left', 'right', 'up', 'down']) {
                const name = `tile-${direction}`;
                if (!keySettings.settings_schema.has_key(name))
                    continue;
                Main.wm.addKeybinding(name, keySettings, Meta.KeyBindingFlags.NONE, Shell.ActionMode.NORMAL,
                    () => this.key(direction));
                this._keys.push(name);
            }
        }
    }

    key(direction, win = global.display.focus_window) {
        if (!win || win.get_window_type() !== Meta.WindowType.NORMAL)
            return;
        tile(win, nextLayout(currentLayout(win), direction));
    }

    _dragBegin(win, op) {
        const moving = op === Meta.GrabOp.MOVING || op === Meta.GrabOp.MOVING_UNCONSTRAINED;
        if (!moving || !win || win.get_window_type() !== Meta.WindowType.NORMAL)
            return;
        this._dragWindow = win;
        this._zone = null;
        this._pollId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 30, () => {
            this._track();
            return GLib.SOURCE_CONTINUE;
        });
    }

    _track() {
        const [x, y] = global.get_pointer();
        const monitor = Main.layoutManager.monitors.findIndex(m =>
            x >= m.x && x < m.x + m.width && y >= m.y && y < m.y + m.height);
        if (monitor < 0)
            return;
        const zone = zoneAt(x, y, Main.layoutManager.monitors[monitor]);
        if (zone === this._zone && monitor === this._monitor)
            return;
        this._zone = zone;
        this._monitor = monitor;
        this._showPreview(zone ? rectFor(zone, Main.layoutManager.getWorkAreaForMonitor(monitor)) : null);
    }

    _showPreview(rect) {
        if (!rect) {
            const preview = this._preview;
            this._preview = null;
            preview?.ease({opacity: 0, duration: 120, onStopped: () => preview.destroy()});
            return;
        }
        if (!this._preview) {
            const [x, y] = global.get_pointer();
            this._preview = new St.Widget({style_class: 'parchaos-tile-preview', opacity: 0, x, y, width: 1, height: 1});
            global.window_group.add_child(this._preview);
            const actor = this._dragWindow?.get_compositor_private();
            if (actor && actor.get_parent() === global.window_group)
                global.window_group.set_child_below_sibling(this._preview, actor);
        }
        this._preview.ease({
            opacity: 255, x: rect.x, y: rect.y, width: rect.width, height: rect.height,
            duration: 160, mode: Clutter.AnimationMode.EASE_OUT_QUAD,
        });
    }

    _dragEnd() {
        if (this._pollId)
            GLib.source_remove(this._pollId);
        this._pollId = 0;
        const win = this._dragWindow, zone = this._zone, monitor = this._monitor;
        this._dragWindow = null;
        this._zone = null;
        this._showPreview(null);
        if (win && zone)
            tile(win, zone, monitor);
    }

    destroy() {
        this._dragEnd();
        global.display.disconnectObject(this);
        for (const name of this._keys)
            Main.wm.removeKeybinding(name);
        this._keys = [];
        // Back to GNOME's default (on), so a crash in between cannot leave it off for good.
        this._mutter.reset('edge-tiling');
    }
}
