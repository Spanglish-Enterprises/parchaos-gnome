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

import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import St from 'gi://St';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as BoxPointer from 'resource:///org/gnome/shell/ui/boxpointer.js';
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

// A package update replaces the shell extensions and theme under a running
// shell, which keeps the old code and can leave the menu bar or wallpaper
// half-drawn until the next login. parchaos-desktop touches this file when
// the extensions or themes change; once it is newer than this shell, say so.
// Motion (ticket #135): menus, popovers and windows come in with a short fade
// and leave with a slightly longer one, with no sliding or zooming. The
// Quick Settings panel (Control Center) keeps its own animation.
const FADE_IN = 120;
const FADE_OUT = 200;

// Tests point this at a scratch file.
const UPDATE_MARKER = GLib.getenv('PARCHAOS_UPDATE_MARKER') ?? '/var/lib/parchaos/session-updated';
const SHELL_STARTED_US = GLib.get_real_time();
let noticeShownFor = 0;

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
        this._hookUpdateNotice();
        this._hookMotion();

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
        this._motion?.clear();
        this._motion = null;
        this._updateMonitor?.cancel();
        this._updateMonitor = null;
        if (this._logindId)
            Gio.DBus.system.signal_unsubscribe(this._logindId);
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
            // PrepareForShutdown is a signal of the login1 Manager (not a
            // property change), sent on the system bus before the session's
            // apps are told to quit.
            this._logindId = Gio.DBus.system.signal_subscribe(
                LOGIND, `${LOGIND}.Manager`, 'PrepareForShutdown', '/org/freedesktop/login1',
                null, Gio.DBusSignalFlags.NONE,
                (_conn, _sender, _path, _iface, _signal, params) => {
                    const [starting] = params.deep_unpack();
                    if (starting)
                        this._save();
                });
        } catch (e) {
            logError(e, 'parchaos-session: could not watch logind');
        }
    }

    // Glass menus (ticket #135): in the Glass style every menu and popover is a
    // smoked, blurred pane with rounded corners and a hairline edge, like the
    // reference; Classic keeps the plain theme menus.
    _dressMenu(pointer) {
        // With the refractive glass extension on, it draws the menu material
        // itself; the row sizing below still applies.
        const refracted = this._settings?.get_boolean('glass-effects') ?? false;
        const glass = this._settings?.get_string('style') !== 'classic';
        const dark = new Gio.Settings({schema_id: 'org.gnome.desktop.interface'})
            .get_string('color-scheme') === 'prefer-dark';
        for (const name of ['parchaos-glass-menu', 'parchaos-glass-menu-light', 'parchaos-menu-metrics',
            'parchaos-menu-dark', 'parchaos-menu-light'])
            pointer.remove_style_class_name(name);
        const content = this._menuContent(pointer);
        const effect = pointer._parchaosBlur;
        if (!glass || !content) {
            if (effect) {
                pointer._parchaosBlurHost?.remove_effect(effect);
                pointer._parchaosBlur = null;
            }
            return;
        }
        pointer.add_style_class_name('parchaos-menu-metrics');
        pointer.add_style_class_name(dark ? 'parchaos-menu-dark' : 'parchaos-menu-light');
        if (refracted) {
            if (effect) {
                pointer._parchaosBlurHost?.remove_effect(effect);
                pointer._parchaosBlur = null;
            }
            return;
        }
        pointer.add_style_class_name('parchaos-glass-menu');
        if (!dark)
            pointer.add_style_class_name('parchaos-glass-menu-light');
        if (!effect) {
            pointer._parchaosBlur = new Shell.BlurEffect({
                radius: 40,
                brightness: dark ? 0.8 : 1.0,
                mode: Shell.BlurMode.BACKGROUND,
            });
            pointer._parchaosBlurHost = content;
            content.add_effect(pointer._parchaosBlur);
        }
    }

    _menuContent(actor) {
        if (actor.has_style_class_name?.('popup-menu-content'))
            return actor;
        for (const child of actor.get_children?.() ?? []) {
            const found = this._menuContent(child);
            if (found)
                return found;
        }
        return null;
    }

    _hookMotion() {
        const self = this;
        this._motion = new InjectionManager();
        const fade = Clutter.AnimationMode.EASE_OUT_QUAD;

        const keepsOwn = pointer =>
            pointer === Main.panel.statusArea?.quickSettings?.menu?._boxPointer;

        this._motion.overrideMethod(BoxPointer.BoxPointer.prototype, 'open', original =>
            function (animate, onComplete) {
                if (!keepsOwn(this))
                    self._dressMenu(this);
                if (!(animate & BoxPointer.PopupAnimation.FULL) || keepsOwn(this))
                    return original.call(this, animate, onComplete);
                this.remove_all_transitions();
                this.scale_x = this.scale_y = 1;
                this.translation_x = this.translation_y = 0;
                this.opacity = 0;
                this._muteKeys = false;
                this.show();
                this.ease({
                    opacity: 255,
                    duration: FADE_IN,
                    mode: fade,
                    onComplete: () => {
                        this._muteInput = false;
                        onComplete?.();
                    },
                });
                return undefined;
            });

        this._motion.overrideMethod(BoxPointer.BoxPointer.prototype, 'close', original =>
            function (animate, onComplete) {
                if (!(animate & BoxPointer.PopupAnimation.FULL) || keepsOwn(this))
                    return original.call(this, animate, onComplete);
                if (!this.visible)
                    return undefined;
                this._muteInput = true;
                this._muteKeys = true;
                this.remove_all_transitions();
                this.ease({
                    opacity: 0,
                    duration: FADE_OUT,
                    mode: fade,
                    onComplete: () => {
                        this.hide();
                        this.opacity = 0;
                        this.translation_x = 0;
                        this.translation_y = 0;
                        this.scale_x = this.scale_y = 1;
                        onComplete?.();
                    },
                });
                return undefined;
            });

        // Windows: the stock animation grows a window out of its bottom edge
        // (opening) and shrinks it (closing). Both become plain fades by
        // rewriting the one ease() call each makes; minimizing is left to
        // the genie effect.
        const wmProto = Object.getPrototypeOf(Main.wm);
        const fadeOnly = (actor, duration, opacity) => {
            actor.ease = props => {
                delete actor.ease;
                return actor.ease({
                    opacity,
                    duration,
                    mode: fade,
                    onStopped: props.onStopped,
                    onComplete: props.onComplete,
                });
            };
        };
        this._motion.overrideMethod(wmProto, '_mapWindow', original =>
            function (shellwm, actor) {
                fadeOnly(actor, FADE_IN, 255);
                const result = original.call(this, shellwm, actor);
                // The stock code has already shrunk the actor to a sliver.
                actor.scale_x = actor.scale_y = 1;
                const cleanup = () => { delete actor.ease; };
                if (result?.finally)
                    result.finally(cleanup);
                else
                    cleanup();
                return result;
            });
        this._motion.overrideMethod(wmProto, '_destroyWindow', original =>
            function (shellwm, actor) {
                fadeOnly(actor, FADE_OUT, 0);
                try {
                    return original.call(this, shellwm, actor);
                } finally {
                    delete actor.ease;
                }
            });
    }

    _backgroundState() {
        const lm = Main.layoutManager;
        const managers = lm._bgManagers ?? [];
        return JSON.stringify({
            managers: managers.length,
            group: lm._backgroundGroup?.get_n_children?.(),
            actors: managers.map(m => ({
                visible: m.backgroundActor?.visible,
                opacity: m.backgroundActor?.opacity,
                size: m.backgroundActor ? [m.backgroundActor.width, m.backgroundActor.height] : null,
            })),
            uri: new Gio.Settings({schema_id: 'org.gnome.desktop.background'}).get_string('picture-uri'),
        });
    }

    _refreshAfterUpdate() {
        try {
            log(`parchaos-session: after update, wallpaper state ${this._backgroundState()}`);
            Main.layoutManager._updateBackgrounds();
            log(`parchaos-session: wallpaper rebuilt ${this._backgroundState()}`);
        } catch (e) {
            logError(e, 'parchaos-session: could not rebuild the wallpaper');
        }
    }

    _hookUpdateNotice() {
        const marker = Gio.File.new_for_path(UPDATE_MARKER);
        const check = () => {
            try {
                const info = marker.query_info('time::modified,time::modified-usec',
                    Gio.FileQueryInfoFlags.NONE, null);
                const modified = info.get_attribute_uint64('time::modified') * 1000000 +
                    info.get_attribute_uint32('time::modified-usec');
                if (modified <= SHELL_STARTED_US || modified === noticeShownFor)
                    return;
                noticeShownFor = modified;
                // Twice in a row an upgrade left the wallpaper gone (plain
                // blue) in the running session. Rebuild the wallpaper layer
                // a moment after the update settles, and log what it looked
                // like so the cause can be found.
                this._later(3000, () => this._refreshAfterUpdate());
                Main.notify('ParchaOS was updated',
                    'Log out and back in to finish the update. Until then the menu bar, dock or wallpaper may look wrong.');
            } catch (e) {
                // No marker yet: nothing has been updated since install.
            }
        };
        try {
            this._updateMonitor = marker.get_parent().monitor_directory(
                Gio.FileMonitorFlags.NONE, null);
            this._updateMonitor.connect('changed', (_m, file) => {
                if (file.get_path() === UPDATE_MARKER)
                    check();
            });
        } catch (e) {
            logError(e, 'parchaos-session: could not watch for updates');
        }
        check();
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
