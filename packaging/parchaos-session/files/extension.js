// SPDX-License-Identifier: GPL-3.0-or-later
// ParchaOS Session Restore -- reopens the apps that were open at the end of
// the last session and puts their windows back where they were.
//
// While the session runs, the open apps and their windows (workspace,
// monitor, position, size, maximized/fullscreen/minimized) are saved every
// SAVE_INTERVAL seconds and whenever the extension is disabled, so a crash
// or power loss is covered too. At the next login the saved apps that
// aren't already running are launched, and their windows are placed as
// they appear. Apps that restore their own documents (browsers, editors,
// note apps) come back with them.
//
// Logging out closes apps one by one, so the session is also saved when
// the log out / restart / power off dialog opens, and saving stops once
// the user confirms (it resumes if they cancel).
//
// Original code for ParchaOS, GPL-3.0-or-later.

import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as EndSessionDialog from 'resource:///org/gnome/shell/ui/endSessionDialog.js';
import {Extension, InjectionManager} from 'resource:///org/gnome/shell/extensions/extension.js';

const LOGIND = 'org.freedesktop.login1';

const SAVE_INTERVAL = 30;          // seconds
const PLACE_WINDOW_S = 90;         // how long to wait for restored windows
const STATE_DIR = GLib.build_filenamev([GLib.get_user_state_dir(), 'parchaos']);
const STATE_FILE = GLib.build_filenamev([STATE_DIR, 'session.json']);
// Once per login. Extensions are disabled and re-enabled around the lock
// screen, but this module is only evaluated once per shell process, and
// every login starts a new shell. (A marker file in the runtime dir
// survived logout whenever the user manager lingered.)
let restoredThisLogin = false;

function desktopSettings() {
    const schema = Gio.SettingsSchemaSource.get_default()?.lookup('org.parchaos.desktop', true);
    return schema ? new Gio.Settings({settings_schema: schema}) : null;
}

function isMaximized(win) {
    if (typeof win.is_maximized === 'function')
        return win.is_maximized();
    return win.get_maximized?.() === Meta.MaximizeFlags.BOTH;
}

function maximize(win) {
    try {
        win.maximize(Meta.MaximizeFlags.BOTH);
    } catch (e) {
        win.maximize();
    }
}

function unmaximize(win) {
    try {
        win.unmaximize(Meta.MaximizeFlags.BOTH);
    } catch (e) {
        win.unmaximize();
    }
}

export default class ParchaSessionExtension extends Extension {
    enable() {
        this._settings = desktopSettings();
        this._pending = new Map();   // appId -> [saved window, ...]
        this._handlers = [];
        this._sources = new Set();
        this._windowHandlers = new Map();  // window -> shown handler id
        this._ending = false;
        this._hookEndSession();
        this._hookLogind();

        if (!restoredThisLogin) {
            restoredThisLogin = true;
            if (this._settings?.get_boolean('restore-session') ?? true) {
                const saved = this._load();
                if (saved.length > 0)
                    this._whenStarted(() => this._restore(saved));
            }
        }

        this._saveId = GLib.timeout_add_seconds(GLib.PRIORITY_LOW, SAVE_INTERVAL, () => {
            this._save();
            return GLib.SOURCE_CONTINUE;
        });
    }

    disable() {
        this._save();
        if (this._saveId)
            GLib.source_remove(this._saveId);
        this._saveId = 0;
        this._injections?.clear();
        this._injections = null;
        this._stopPlacing();
        for (const id of this._sources)
            GLib.source_remove(id);
        this._sources.clear();
        for (const [win, handlerId] of this._windowHandlers)
            win.disconnect(handlerId);
        this._windowHandlers.clear();
        if (this._logindId)
            Gio.bus_unown_name(this._logindId);
        this._logindId = 0;
        if (this._startupId)
            Main.layoutManager.disconnect(this._startupId);
        this._startupId = 0;
        this._settings = null;
    }

    // One-shot timeout that's removed if the extension is disabled first.
    _later(ms, callback) {
        const id = GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, () => {
            this._sources.delete(id);
            callback();
            return GLib.SOURCE_REMOVE;
        });
        this._sources.add(id);
    }

    _hookEndSession() {
        const self = this;
        const proto = EndSessionDialog.EndSessionDialog.prototype;
        this._injections = new InjectionManager();
        // Save while every app is still open, then stop saving so the
        // closing-down desktop doesn't replace it.
        this._injections.overrideMethod(proto, 'OpenAsync', original => function (...args) {
            self._save();
            return original.apply(this, args);
        });
        this._injections.overrideMethod(proto, '_confirm', original => function (...args) {
            self._ending = true;
            return original.apply(this, args);
        });
        this._injections.overrideMethod(proto, 'cancel', original => function (...args) {
            self._ending = false;
            return original.apply(this, args);
        });
    }

    // A reboot that skips the end-session dialog (systemctl reboot, offline
    // update) doesn't go through EndSessionDialog, so also save when logind
    // signals PrepareForShutdown.
    _hookLogind() {
        try {
            this._logindId = Gio.bus_own_name(
                Gio.BusType.SYSTEM, LOGIND,
                Gio.BusNameOwnerFlags.NONE,
                (bus, name) => {
                    bus.signal_subscribe(
                        LOGIND, 'org.freedesktop.DBus.Properties',
                        'PropertiesChanged', '/org/freedesktop/login1',
                        null, Gio.DBusSignalFlags.NONE,
                        (_conn, _sender, _path, _iface, signal, params) => {
                            if (signal !== 'PropertiesChanged')
                                return;
                            const [iface, changed] = params.deep_unpack();
                            if (iface === LOGIND && 'PrepareForShutdown' in changed) {
                                if (changed['PrepareForShutdown'].deep_unpack())
                                    this._save();
                            }
                        });
                },
                null, null);
        } catch (e) {
            logError(e, 'parchaos-session: could not watch logind');
        }
    }

    _whenStarted(callback) {
        if (!Main.layoutManager._startingUp) {
            this._later(2000, callback);
            return;
        }
        this._startupId = Main.layoutManager.connect('startup-complete', () => {
            Main.layoutManager.disconnect(this._startupId);
            this._startupId = 0;
            callback();
        });
    }

    // --- Saving ---

    _snapshot() {
        const tracker = Shell.WindowTracker.get_default();
        const windows = global.display.list_all_windows()
            .filter(w => w.get_window_type() === Meta.WindowType.NORMAL && !w.skip_taskbar)
            .sort((a, b) => a.get_stable_sequence() - b.get_stable_sequence());
        const entries = [];
        for (const w of windows) {
            const app = tracker.get_window_app(w);
            if (!app || app.is_window_backed())
                continue;
            const r = w.get_frame_rect();
            entries.push({
                app: app.get_id(),
                workspace: w.get_workspace()?.index() ?? 0,
                monitor: w.get_monitor(),
                x: r.x, y: r.y, width: r.width, height: r.height,
                maximized: isMaximized(w),
                fullscreen: w.is_fullscreen(),
                minimized: w.minimized,
            });
        }
        return entries;
    }

    _save() {
        if (Main.sessionMode.isLocked || this._ending)
            return;
        // While logging out, apps close one by one within a few seconds;
        // don't let that emptied-out state replace the real session. An
        // empty desktop is only saved once it has lasted two save
        // intervals (the user really closed everything).
        if (this._snapshot().length === 0) {
            this._emptyTicks = (this._emptyTicks ?? 0) + 1;
            if (this._emptyTicks < 2)
                return;
        } else {
            this._emptyTicks = 0;
        }
        try {
            GLib.mkdir_with_parents(STATE_DIR, 0o700);
            GLib.file_set_contents(STATE_FILE, JSON.stringify({
                version: 1,
                saved: Date.now(),
                windows: this._snapshot(),
            }));
        } catch (e) {
            logError(e, 'parchaos-session: could not save the session');
        }
    }

    _load() {
        try {
            const [ok, contents] = GLib.file_get_contents(STATE_FILE);
            if (!ok)
                return [];
            const data = JSON.parse(new TextDecoder().decode(contents));
            return Array.isArray(data?.windows) ? data.windows : [];
        } catch (e) {
            return [];
        }
    }

    // --- Restoring ---

    _restore(saved) {
        const appSys = Shell.AppSystem.get_default();
        for (const entry of saved) {
            if (!this._pending.has(entry.app))
                this._pending.set(entry.app, []);
            this._pending.get(entry.app).push(entry);
        }
        for (const appId of [...this._pending.keys()]) {
            const app = appSys.lookup_app(appId);
            // Gone (uninstalled) or already open (autostart, the user):
            // don't launch it, and leave its windows alone.
            if (!app || app.get_state() !== Shell.AppState.STOPPED) {
                this._pending.delete(appId);
                continue;
            }
            try {
                app.activate();
            } catch (e) {
                logError(e, `parchaos-session: could not reopen ${appId}`);
                this._pending.delete(appId);
            }
        }
        if (this._pending.size === 0)
            return;

        this._handlers.push([global.display,
            global.display.connect('window-created', (_d, win) => this._onWindowCreated(win))]);
        this._placeTimeoutId = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, PLACE_WINDOW_S, () => {
            this._placeTimeoutId = 0;
            this._stopPlacing();
            return GLib.SOURCE_REMOVE;
        });
    }

    _onWindowCreated(win) {
        if (win.get_window_type() !== Meta.WindowType.NORMAL)
            return;
        // On Wayland a new window has no app ID yet (the client sends it
        // right after), so match it to its app once it's shown.
        const id = win.connect('shown', () => {
            win.disconnect(id);
            this._windowHandlers.delete(win);
            GLib.idle_add(GLib.PRIORITY_DEFAULT, () => {
                this._matchAndPlace(win);
                return GLib.SOURCE_REMOVE;
            });
        });
        this._windowHandlers.set(win, id);
    }

    _matchAndPlace(win) {
        const app = Shell.WindowTracker.get_default().get_window_app(win);
        const queue = app ? this._pending.get(app.get_id()) : null;
        if (!queue?.length)
            return;
        const entry = queue.shift();
        if (queue.length === 0)
            this._pending.delete(app.get_id());
        // Some apps resize themselves right after mapping; place again a
        // moment later.
        this._place(win, entry);
        this._later(400, () => {
            if (win.get_display())
                this._place(win, entry);
        });
        if (this._pending.size === 0)
            this._stopPlacing();
    }

    _place(win, entry) {
        try {
            const nWorkspaces = global.workspace_manager.get_n_workspaces();
            if (entry.workspace < nWorkspaces)
                win.change_workspace_by_index(entry.workspace, false);
            if (isMaximized(win))
                unmaximize(win);
            win.move_resize_frame(true, entry.x, entry.y, entry.width, entry.height);
            if (entry.maximized)
                maximize(win);
            if (entry.fullscreen)
                win.make_fullscreen();
            if (entry.minimized)
                win.minimize();
        } catch (e) {
            logError(e, 'parchaos-session: could not place a window');
        }
    }

    _stopPlacing() {
        for (const [obj, id] of this._handlers)
            obj.disconnect(id);
        this._handlers = [];
        if (this._placeTimeoutId) {
            GLib.source_remove(this._placeTimeoutId);
            this._placeTimeoutId = 0;
        }
    }
}
