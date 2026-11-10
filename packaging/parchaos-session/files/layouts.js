// SPDX-License-Identifier: GPL-3.0-or-later
// Window positions for each monitor setup (ticket #181).
//
// For every set of connected monitors (each monitor known by its vendor, product and serial
// from its EDID, or its connector when it has no serial) this remembers which monitor each window
// was on and where. When that same set comes back (re-plugging, waking up, docking) the windows
// go back there; a set never seen before keeps GNOME's own placement. Saved in
// ~/.local/state/parchaos/window-layouts.json so a set seen in an earlier session is known too;
// windows from an earlier session are matched by app, in order.
//
// Original code for ParchaOS, GPL-3.0-or-later.

import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';

const STATE_DIR = GLib.build_filenamev([GLib.get_user_state_dir(), 'parchaos']);
export const LAYOUTS_FILE = GLib.getenv('PARCHAOS_LAYOUTS_FILE') ??
    GLib.build_filenamev([STATE_DIR, 'window-layouts.json']);
const MAX_SETS = 8;             // monitor setups remembered; the least recently used is dropped
const RECORD_DELAY_MS = 1000;   // wait for a move or resize to finish before recording it
const SETTLE_MS = 2500;         // after monitors change, ignore GNOME's own shuffling this long
const RESTORE_DELAY_MS = 400;   // let GNOME finish moving windows off a removed monitor first

// One id per shell process: windows recorded under it can be matched exactly by their sequence.
const LOGIN = GLib.uuid_string_random();

/** A stable id for one physical monitor. */
export function monitorId(vendor, product, serial, connector) {
    const s = (serial ?? '').trim();
    const unknown = !s || /^0x0*$/i.test(s) || s === '0';
    return `${vendor ?? ''}:${product ?? ''}:${unknown ? `@${connector ?? ''}` : s}`;
}

/** The id of a whole setup: its monitors' ids in a fixed order. */
export function setKey(ids) {
    return [...ids].sort().join('+');
}

/**
 * Pairs recorded entries with current windows. Exact sequence numbers win (the same window in this
 * session); otherwise, entries from another session go to windows of the same app, in order.
 * windows: [{seq, app}], entries: [{seq, app, login}]; returns Map(window index -> entry).
 */
export function matchWindows(windows, entries, login = LOGIN) {
    const result = new Map();
    const used = new Set();
    windows.forEach((w, i) => {
        const e = entries.find(x => x.login === login && x.seq === w.seq);
        if (e) {
            result.set(i, e);
            used.add(e);
        }
    });
    windows.forEach((w, i) => {
        if (result.has(i) || !w.app)
            return;
        const e = entries.find(x => !used.has(x) && x.login !== login && x.app === w.app);
        if (e) {
            result.set(i, e);
            used.add(e);
        }
    });
    return result;
}

function monitors() {
    const manager = global.backend.get_monitor_manager();
    const result = [];
    for (const logical of manager.get_logical_monitors()) {
        for (const m of logical.get_monitors()) {
            result.push({
                id: monitorId(m.get_vendor(), m.get_product(), m.get_serial(), m.get_connector()),
                index: logical.get_number(),
            });
        }
    }
    return result;
}

export function isMaximized(win) {
    if (typeof win.is_maximized === 'function')
        return win.is_maximized();
    return win.get_maximized?.() === Meta.MaximizeFlags.BOTH;
}

// Mutter 18 (GNOME 50) dropped the MaximizeFlags argument along with
// get_maximized(); passing it only logs "too many arguments".
export function maximize(win) {
    if (typeof win.is_maximized === 'function')
        win.maximize();
    else
        win.maximize(Meta.MaximizeFlags.BOTH);
}

export function unmaximize(win) {
    if (typeof win.is_maximized === 'function')
        win.unmaximize();
    else
        win.unmaximize(Meta.MaximizeFlags.BOTH);
}


function trackedWindows() {
    return global.display.list_all_windows()
        .filter(w => w.get_window_type() === Meta.WindowType.NORMAL && !w.skip_taskbar)
        .sort((a, b) => a.get_stable_sequence() - b.get_stable_sequence());
}

function appIdOf(win) {
    const app = Shell.WindowTracker.get_default().get_window_app(win);
    return app && !app.is_window_backed() ? app.get_id() : null;
}

export class WindowLayouts {
    constructor() {
        this._sets = this._load();
        this._sources = new Set();
        this._settleUntil = 0;
        this._key = this._currentKey();
        Main.layoutManager.connectObject('monitors-changed', () => this._onMonitorsChanged(), this);
        global.display.connectObject(
            'window-created', (_d, win) => this._watch(win),
            'grab-op-end', () => this._queueRecord(), this);
        for (const win of trackedWindows())
            this._watch(win);
        this._queueRecord();
    }

    _currentKey() {
        return setKey(monitors().map(m => m.id));
    }

    _watch(win) {
        win.connectObject(
            'position-changed', () => this._queueRecord(),
            'size-changed', () => this._queueRecord(),
            'workspace-changed', () => this._queueRecord(), this);
    }

    _later(ms, callback) {
        const id = GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, () => {
            this._sources.delete(id);
            callback();
            return GLib.SOURCE_REMOVE;
        });
        this._sources.add(id);
        return id;
    }

    _queueRecord() {
        if (this._recordId)
            return;
        this._recordId = this._later(RECORD_DELAY_MS, () => {
            this._recordId = 0;
            this.record();
        });
    }

    /** Remember where every window is, under the current monitor setup. */
    record() {
        if (Main.sessionMode.isLocked || GLib.get_monotonic_time() / 1000 < this._settleUntil)
            return;
        const byIndex = new Map(monitors().map(m => [m.index, m.id]));
        const windows = [];
        for (const win of trackedWindows()) {
            const index = win.get_monitor();
            const id = byIndex.get(index);
            if (!id)
                continue;
            const area = global.display.get_monitor_geometry(index);
            const r = win.get_frame_rect();
            windows.push({
                login: LOGIN,
                seq: win.get_stable_sequence(),
                app: appIdOf(win),
                monitor: id,
                x: r.x - area.x, y: r.y - area.y, width: r.width, height: r.height,
                maximized: isMaximized(win),
                fullscreen: win.is_fullscreen(),
            });
        }
        if (!windows.length)
            return;
        this._key = this._currentKey();
        // An entry for a window that is closed now stays for the next session only if no window of
        // this session replaced it, so apps opened again later still find their place.
        const earlier = (this._sets[this._key]?.windows ?? []).filter(e => e.login !== LOGIN &&
            !windows.some(w => w.app && w.app === e.app));
        this._sets[this._key] = {saved: Date.now(), windows: [...windows, ...earlier]};
        this._save();
    }

    _onMonitorsChanged() {
        const key = this._currentKey();
        if (key === this._key)
            return;
        this._key = key;
        this._settleUntil = GLib.get_monotonic_time() / 1000 + SETTLE_MS;
        if (this._sets[key])
            this._later(RESTORE_DELAY_MS, () => this.restore());
    }

    /** Put windows back where they were the last time this monitor setup was connected. */
    restore() {
        const entries = this._sets[this._key]?.windows ?? [];
        if (!entries.length)
            return;
        const byId = new Map(monitors().map(m => [m.id, m.index]));
        const windows = trackedWindows();
        const pairs = matchWindows(windows.map(w => ({seq: w.get_stable_sequence(), app: appIdOf(w)})), entries);
        for (const [i, entry] of pairs)
            this.place(windows[i], entry, byId);
        this._settleUntil = GLib.get_monotonic_time() / 1000 + RECORD_DELAY_MS;
    }

    /** The saved place of a window of `appId` under the current setup that no other window took, or null. */
    claimFor(appId) {
        this._claimed ??= new Set();
        const e = (this._sets[this._currentKey()]?.windows ?? [])
            .find(x => x.app === appId && !this._claimed.has(x));
        if (e)
            this._claimed.add(e);
        return e ?? null;
    }

    place(win, entry, byId = new Map(monitors().map(m => [m.id, m.index]))) {
        const index = byId.get(entry.monitor);
        if (index === undefined)
            return false;
        try {
            if (entry.fullscreen) {
                win.move_to_monitor(index);
                return true;
            }
            if (isMaximized(win))
                unmaximize(win);
            if (win.get_monitor() !== index)
                win.move_to_monitor(index);
            const area = global.display.get_monitor_geometry(index);
            win.move_resize_frame(true, area.x + entry.x, area.y + entry.y, entry.width, entry.height);
            if (entry.maximized)
                maximize(win);
            return true;
        } catch (e) {
            logError(e, 'parchaos-session: could not put a window back');
            return false;
        }
    }

    currentKey() {
        return this._currentKey();
    }

    _load() {
        try {
            const [, contents] = GLib.file_get_contents(LAYOUTS_FILE);
            const data = JSON.parse(new TextDecoder().decode(contents));
            return data?.version === 1 && data.sets ? data.sets : {};
        } catch (e) {
            return {};
        }
    }

    _save() {
        const keys = Object.keys(this._sets).sort((a, b) => this._sets[b].saved - this._sets[a].saved);
        for (const key of keys.slice(MAX_SETS))
            delete this._sets[key];
        try {
            GLib.mkdir_with_parents(GLib.path_get_dirname(LAYOUTS_FILE), 0o700);
            GLib.file_set_contents(LAYOUTS_FILE, JSON.stringify({version: 1, sets: this._sets}));
        } catch (e) {
            logError(e, 'parchaos-session: could not save window layouts');
        }
    }

    destroy() {
        this.record();
        Main.layoutManager.disconnectObject(this);
        global.display.disconnectObject(this);
        for (const win of global.display.list_all_windows())
            win.disconnectObject(this);
        for (const id of this._sources)
            GLib.source_remove(id);
        this._sources.clear();
    }
}
