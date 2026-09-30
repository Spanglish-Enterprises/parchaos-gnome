// SPDX-License-Identifier: GPL-3.0-or-later
// ParchaOS Launcher -- a full-screen app launcher for GNOME Shell.
//
// Replaces the overview's app grid: whatever would open it (the dock's
// Show Apps button, Super+A) opens this instead. Blurred desktop
// background, a search field at the top, a paged grid of apps with page
// dots, and folders (GNOME's own org.gnome.desktop.app-folders, so the
// folder setup is shared with the rest of the system) that open in place.
//
// Original code for ParchaOS, GPL-3.0-or-later.

import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import Shell from 'gi://Shell';
import St from 'gi://St';

import * as Background from 'resource:///org/gnome/shell/ui/background.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as OverviewControls from 'resource:///org/gnome/shell/ui/overviewControls.js';
import {Extension, InjectionManager} from 'resource:///org/gnome/shell/extensions/extension.js';

const COLUMNS = 7;
const ROWS = 5;
// Opening is a short fade, closing a little slower (ticket #135: no zooming).
const FADE_IN = 120;
const FADE_OUT = 200;
const PAGE_TIME = 320;
const DOCK_UUID = 'parcha-dock@parchaos.org';

function folderName(settings) {
    const name = settings.get_string('name');
    if (settings.get_boolean('translate')) {
        const translated = Shell.util_get_translated_folder_name(name);
        if (translated !== null)
            return translated;
    }
    return name;
}

function appCategories(appInfo) {
    return (appInfo.get_categories() ?? '').split(';').filter(c => c);
}

// Apps and folders to show, as items {type: 'app', app} or
// {type: 'folder', id, name, apps}. Folder membership follows the same
// rules as GNOME's own app grid: listed apps plus apps matching the
// folder's categories, minus excluded-apps. Empty folders are skipped.
function loadItems() {
    const appSys = Shell.AppSystem.get_default();
    const apps = appSys.get_installed()
        .filter(info => info.should_show())
        .map(info => appSys.lookup_app(info.get_id()))
        .filter(app => app);
    const byId = new Map(apps.map(app => [app.get_id(), app]));

    const foldersSettings = new Gio.Settings({schema_id: 'org.gnome.desktop.app-folders'});
    const inFolder = new Set();
    const folders = [];
    for (const id of foldersSettings.get_strv('folder-children')) {
        const settings = new Gio.Settings({
            schema_id: 'org.gnome.desktop.app-folders.folder',
            path: `/org/gnome/desktop/app-folders/folders/${id}/`,
        });
        const excluded = settings.get_strv('excluded-apps');
        const categories = settings.get_strv('categories');
        const members = [];
        const add = appId => {
            const app = byId.get(appId);
            if (app && !excluded.includes(appId) && !members.includes(app))
                members.push(app);
        };
        settings.get_strv('apps').forEach(add);
        if (categories.length > 0) {
            for (const app of apps) {
                if (appCategories(app.get_app_info()).some(c => categories.includes(c)))
                    add(app.get_id());
            }
        }
        if (members.length === 0)
            continue;
        members.sort((a, b) => a.get_name().localeCompare(b.get_name()));
        members.forEach(app => inFolder.add(app));
        folders.push({type: 'folder', id, name: folderName(settings), apps: members});
    }

    const loose = apps.filter(app => !inFolder.has(app))
        .sort((a, b) => a.get_name().localeCompare(b.get_name()))
        .map(app => ({type: 'app', app}));
    return applyOrder([...loose, ...folders]);
}

// --- Arrangement ---
//
// The order the user arranged items in is kept in org.parchaos.desktop
// launcher-order, as app IDs and "folder:<id>". Items it doesn't list
// (newly installed apps, new folders) follow, in the default order.

function itemKey(item) {
    return item.type === 'app' ? item.app.get_id() : `folder:${item.id}`;
}

function orderSettings() {
    const settings = styleSettings();
    return settings?.settings_schema.has_key('launcher-order') ? settings : null;
}

function applyOrder(items) {
    const order = orderSettings()?.get_strv('launcher-order') ?? [];
    if (order.length === 0)
        return items;
    const byKey = new Map(items.map(item => [itemKey(item), item]));
    const placed = order.filter(key => byKey.has(key)).map(key => byKey.get(key));
    const rest = items.filter(item => !placed.includes(item));
    return [...placed, ...rest];
}

function saveOrder(items) {
    orderSettings()?.set_strv('launcher-order', items.map(itemKey));
}

function folderSettings(id) {
    return new Gio.Settings({
        schema_id: 'org.gnome.desktop.app-folders.folder',
        path: `/org/gnome/desktop/app-folders/folders/${id}/`,
    });
}

// A name for a new folder from what its two apps have in common.
const FOLDER_NAMES = [
    ['Game', 'Games'], ['Development', 'Developer'], ['Graphics', 'Creativity'],
    ['AudioVideo', 'Entertainment'], ['Office', 'Productivity'], ['Education', 'Education'],
    ['Network', 'Internet'], ['Science', 'Science'], ['System', 'System'],
    ['Settings', 'System'], ['Utility', 'Utilities'],
];

function newFolderName(apps) {
    const shared = apps.map(app => appCategories(app.get_app_info()))
        .reduce((a, b) => a.filter(c => b.includes(c)));
    return FOLDER_NAMES.find(([category]) => shared.includes(category))?.[1] ?? 'Folder';
}

function createFolder(apps) {
    const parent = new Gio.Settings({schema_id: 'org.gnome.desktop.app-folders'});
    const id = `parchaos-${GLib.uuid_string_random().slice(0, 8)}`;
    const settings = folderSettings(id);
    settings.set_string('name', newFolderName(apps));
    settings.set_boolean('translate', false);
    settings.set_strv('apps', apps.map(app => app.get_id()));
    parent.set_strv('folder-children', [...parent.get_strv('folder-children'), id]);
    return id;
}

function addToFolder(id, app) {
    const settings = folderSettings(id);
    const appId = app.get_id();
    settings.set_strv('excluded-apps', settings.get_strv('excluded-apps').filter(a => a !== appId));
    if (!settings.get_strv('apps').includes(appId))
        settings.set_strv('apps', [...settings.get_strv('apps'), appId]);
}

// Takes an app out of a folder; a folder left empty is deleted.
// Returns true when the folder was deleted.
function removeFromFolder(folder, app) {
    const settings = folderSettings(folder.id);
    const appId = app.get_id();
    const listed = settings.get_strv('apps');
    if (listed.includes(appId))
        settings.set_strv('apps', listed.filter(a => a !== appId));
    // Also a member through its categories: exclude it explicitly.
    const categories = settings.get_strv('categories');
    if (appCategories(app.get_app_info()).some(c => categories.includes(c)))
        settings.set_strv('excluded-apps', [...settings.get_strv('excluded-apps'), appId]);
    if (folder.apps.length <= 1) {
        const parent = new Gio.Settings({schema_id: 'org.gnome.desktop.app-folders'});
        parent.set_strv('folder-children',
            parent.get_strv('folder-children').filter(f => f !== folder.id));
        for (const key of settings.settings_schema.list_keys())
            settings.reset(key);
        return true;
    }
    return false;
}

// ParchaOS visual style ("glass" or "classic") from the org.parchaos.desktop
// schema shipped by parchaos-desktop; null when the schema isn't installed.
function styleSettings() {
    const schema = Gio.SettingsSchemaSource.get_default()?.lookup('org.parchaos.desktop', true);
    return schema ? new Gio.Settings({settings_schema: schema}) : null;
}

function applyStyleClass(actor, settings) {
    const style = settings?.get_string('style') ?? 'glass';
    for (const s of ['glass', 'classic'])
        actor.remove_style_class_name(`parchaos-style-${s}`);
    actor.add_style_class_name(`parchaos-style-${style}`);
}

const LONG_PRESS_MS = 550;

// Runs argv, resolving to {ok, stdout, stderr}.
function runAsync(argv) {
    return new Promise(resolve => {
        let proc;
        try {
            proc = Gio.Subprocess.new(argv,
                Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE);
        } catch (e) {
            resolve({ok: false, stdout: '', stderr: e.message});
            return;
        }
        proc.communicate_utf8_async(null, null, (p, res) => {
            try {
                const [, stdout, stderr] = p.communicate_utf8_finish(res);
                resolve({ok: p.get_successful(), stdout: stdout ?? '', stderr: stderr ?? ''});
            } catch (e) {
                resolve({ok: false, stdout: '', stderr: e.message});
            }
        });
    });
}

const AppTile = GObject.registerClass({
    Signals: {'activate': {}, 'long-press': {}, 'remove': {}},
}, class AppTile extends St.Button {
    _init(item, iconSize, width) {
        super._init({
            style_class: 'parchaos-launcher-tile',
            reactive: true,
            can_focus: true,
            track_hover: true,
            x_align: Clutter.ActorAlign.CENTER,
            y_align: Clutter.ActorAlign.START,
        });
        this.item = item;
        const box = new St.BoxLayout({orientation: Clutter.Orientation.VERTICAL, width});
        this.set_child(box);

        let icon;
        if (item.type === 'app') {
            icon = item.app.create_icon_texture(iconSize);
        } else {
            icon = new St.Widget({
                style_class: 'parchaos-launcher-folder-icon',
                width: iconSize,
                height: iconSize,
                style: `border-radius: ${Math.round(iconSize * 0.23)}px;`,
            });
            // A 3x3 grid of mini icons filling the tile, laid out from the
            // top-left like a full folder even when it holds fewer apps.
            const pad = Math.round(iconSize * 0.1);
            const cell = (iconSize - 2 * pad) / 3;
            const sub = Math.floor(cell * 0.9);
            item.apps.slice(0, 9).forEach((app, i) => {
                const mini = app.create_icon_texture(sub);
                mini.set_size(sub, sub);
                mini.x = Math.round(pad + (i % 3) * cell + (cell - sub) / 2);
                mini.y = Math.round(pad + Math.floor(i / 3) * cell + (cell - sub) / 2);
                icon.add_child(mini);
            });
        }
        // The icon sits in a holder so edit mode can put a remove badge on
        // its corner.
        this._iconSize = iconSize;
        this._holder = new St.Widget({width: iconSize, height: iconSize});
        this._holder.x_align = Clutter.ActorAlign.CENTER;
        this._holder.add_child(icon);
        this._icon = icon;
        box.add_child(this._holder);

        this._label = new St.Label({
            text: item.type === 'app' ? item.app.get_name() : item.name,
            style_class: 'parchaos-launcher-label',
            x_align: Clutter.ActorAlign.CENTER,
        });
        this._label.clutter_text.ellipsize = 3; // Pango.EllipsizeMode.END
        box.add_child(this._label);

        this._icon.set_pivot_point(0.5, 0.5);
        this.connect('notify::pressed', () => {
            this._icon.ease({
                opacity: this.pressed ? 160 : 255,
                duration: 80,
            });
        });
        // Long press (or right-click) enters edit mode; the click that
        // ends a long press doesn't also open the app.
        this.connect('button-press-event', (_a, event) => {
            const button = event.get_button();
            if (button === Clutter.BUTTON_SECONDARY) {
                this.emit('long-press');
                return Clutter.EVENT_STOP;
            }
            if (button === Clutter.BUTTON_PRIMARY) {
                this._longPressed = false;
                this._clearLongPress();
                this._longPressId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, LONG_PRESS_MS, () => {
                    this._longPressId = 0;
                    this._longPressed = true;
                    this.emit('long-press');
                    return GLib.SOURCE_REMOVE;
                });
            }
            return Clutter.EVENT_PROPAGATE;
        });
        this.connect('button-release-event', () => {
            this._clearLongPress();
            return Clutter.EVENT_PROPAGATE;
        });
        this.connect('leave-event', () => {
            this._clearLongPress();
            return Clutter.EVENT_PROPAGATE;
        });
        this.connect('destroy', () => this._clearLongPress());
        this.connect('clicked', () => {
            if (this._longPressed) {
                this._longPressed = false;
                return;
            }
            this.emit('activate');
        });
    }

    _clearLongPress() {
        if (this._longPressId) {
            GLib.source_remove(this._longPressId);
            this._longPressId = 0;
        }
    }

    // Edit mode: the icon breathes gently (a slow scale pulse, offset per
    // tile so they don't move in lockstep) and removable apps get a badge.
    setEditing(editing, removable = false) {
        this._icon.remove_transition('scale-x');
        this._icon.remove_transition('scale-y');
        this._icon.scale_x = this._icon.scale_y = 1;
        if (editing) {
            const delay = Math.floor(Math.random() * 700);
            this._icon.ease({
                scale_x: 0.94,
                scale_y: 0.94,
                duration: 900,
                delay,
                mode: Clutter.AnimationMode.EASE_IN_OUT_SINE,
                repeatCount: -1,
                autoReverse: true,
            });
        }
        const wantBadge = editing && removable;
        if (wantBadge && !this._badge) {
            this._badge = new St.Button({
                style_class: 'parchaos-launcher-remove',
                child: new St.Icon({icon_name: 'window-close-symbolic'}),
                can_focus: true,
            });
            this._badge.set_position(-6, -6);
            this._badge.connect('clicked', () => this.emit('remove'));
            this._holder.add_child(this._badge);
        } else if (!wantBadge && this._badge) {
            this._badge.destroy();
            this._badge = null;
        }
    }
});

const Launcher = GObject.registerClass({
    Signals: {'closed': {}},
}, class Launcher extends St.Widget {
    _init(helper) {
        const monitor = Main.layoutManager.primaryMonitor;
        super._init({
            style_class: 'parchaos-launcher',
            reactive: true,
            x: monitor.x,
            y: monitor.y,
            width: monitor.width,
            height: monitor.height,
            opacity: 0,
        });
        this._monitor = monitor;
        applyStyleClass(this, styleSettings());
        this._page = 0;
        this._scrollAccum = 0;
        this._folderView = null;
        this._helper = helper;
        this._editing = false;
        this._removable = new Set();
        this._press = null;
        this._drag = null;
        this.connect('captured-event', (_a, event) => this._onCapturedEvent(event));

        // Blur the wallpaper alone (a clone of the background group), not
        // whatever windows are open on top of it.
        this._backdrop = new St.Widget({
            width: monitor.width,
            height: monitor.height,
            clip_to_allocation: true,
        });
        // Solid base: the blurred clone isn't fully opaque, and windows
        // behind the launcher must never show through it.
        this._backdrop.add_child(new St.Widget({
            style: 'background-color: #101014;',
            width: monitor.width,
            height: monitor.height,
        }));
        // Our own wallpaper actor (like the overview's): a clone of the
        // desktop's would copy the holes mutter leaves under windows.
        const wallpaper = new St.Widget({
            width: monitor.width,
            height: monitor.height,
        });
        this._bgManager = new Background.BackgroundManager({
            container: wallpaper,
            monitorIndex: monitor.index,
            vignette: false,
            // Place it at 0,0 in our container, not at the monitor's
            // global position (off-screen for any monitor not at 0,0).
            controlPosition: false,
        });
        wallpaper.add_effect(new Shell.BlurEffect({
            radius: 100,
            brightness: 0.78,
            mode: Shell.BlurMode.ACTOR,
        }));
        this._backdrop.add_child(wallpaper);
        this._dotsIdleId = 0;
        this._scrollLockId = 0;
        this.connect('destroy', () => {
            this._bgManager?.destroy();
            this._bgManager = null;
            if (this._dotsIdleId)
                GLib.source_remove(this._dotsIdleId);
            if (this._scrollLockId)
                GLib.source_remove(this._scrollLockId);
            this._dotsIdleId = this._scrollLockId = 0;
            this._cancelDrag();
            // Helper replies can arrive after the launcher is gone.
            this._destroyed = true;
            this._confirm = null;
        });
        this._backdrop.add_child(new St.Widget({
            style_class: 'parchaos-launcher-backdrop',
            width: monitor.width,
            height: monitor.height,
        }));
        this.add_child(this._backdrop);

        const scale = St.ThemeContext.get_for_stage(global.stage).scale_factor;
        this._scale = scale;

        // Search field, horizontally centered near the top.
        this._entry = new St.Entry({
            style_class: 'parchaos-launcher-search',
            hint_text: 'Search Applications',
            can_focus: true,
            width: 330 * scale,
        });
        this._entry.set_primary_icon(new St.Icon({
            icon_name: 'edit-find-symbolic',
            style_class: 'parchaos-launcher-search-icon',
        }));
        this._entry.x = Math.round((monitor.width - this._entry.width) / 2);
        this._entry.y = Math.round(monitor.height * 0.05);
        this.add_child(this._entry);
        this._entry.clutter_text.connect('text-changed', () => this._onSearchChanged());
        this._entry.clutter_text.connect('activate', () => this._activateFirst());
        this._entry.clutter_text.connect('key-press-event', (_a, event) => this._onKeyPress(event));

        // Grid area: below the search field, above the page dots and dock.
        const top = this._entry.y + 80 * scale;
        const bottom = monitor.height - 150 * scale;
        this._gridArea = {
            x: Math.round(monitor.width * 0.08),
            y: Math.round(top),
            width: Math.round(monitor.width * 0.84),
            height: Math.round(bottom - top),
        };
        this._cellW = Math.floor(this._gridArea.width / COLUMNS);
        this._cellH = Math.floor(this._gridArea.height / ROWS);
        this._iconSize = Math.round(Math.min(this._cellH - 44 * scale, this._cellW * 0.55, 112 * scale));

        this._clip = new St.Widget({
            x: 0,
            y: this._gridArea.y,
            width: monitor.width,
            height: this._gridArea.height,
            clip_to_allocation: true,
        });
        this.add_child(this._clip);
        this._pages = new St.Widget({width: monitor.width, height: this._gridArea.height});
        this._clip.add_child(this._pages);

        this._dots = new St.BoxLayout({style_class: 'parchaos-launcher-dots'});
        this.add_child(this._dots);

        this._items = loadItems();
        this._buildPages(this._items);

        this.connect('button-release-event', (_a, event) => {
            if (event.get_button() !== Clutter.BUTTON_PRIMARY)
                return Clutter.EVENT_STOP;
            if (this._editing)
                this._setEditing(false);
            else
                this.close();
            return Clutter.EVENT_STOP;
        });
        this.connect('scroll-event', (_a, event) => this._onScroll(event));
        // Two-finger touchpad swipes arrive as smooth scroll events.
        this.connect('key-press-event', (_a, event) => this._onKeyPress(event));
    }

    // --- Drag and drop ---
    //
    // Dragging a tile moves it: the others make room as it passes, and
    // holding it at a page edge turns the page. Held over another app it
    // makes a folder of the two; over a folder it goes in. Dragged out of
    // an open folder, an app leaves it. Dragging starts edit mode. The
    // arrangement is saved (see saveOrder / app-folders).

    _tileFromActor(actor) {
        for (let a = actor; a && a !== this; a = a.get_parent()) {
            if (a instanceof AppTile)
                return a;
            if (a.has_style_class_name?.('parchaos-launcher-remove'))
                return null;
        }
        return null;
    }

    _onCapturedEvent(event) {
        const type = event.type();
        if (type === Clutter.EventType.BUTTON_PRESS && event.get_button() === Clutter.BUTTON_PRIMARY) {
            this._press = null;
            if (this._confirm || this._entry.get_text().trim() !== '')
                return Clutter.EVENT_PROPAGATE;
            // (During capture the event actor is the launcher itself, so
            // pick what's under the pointer.)
            const [x, y] = event.get_coords();
            const tile = this._tileFromActor(
                global.stage.get_actor_at_pos(Clutter.PickMode.REACTIVE, x, y));
            if (tile) {
                this._press = {tile, x, y, inFolder: !!this._folderView};
            }
            return Clutter.EVENT_PROPAGATE;
        }
        if (type === Clutter.EventType.MOTION) {
            const [x, y] = event.get_coords();
            if (this._press && !this._drag &&
                Math.hypot(x - this._press.x, y - this._press.y) > 12 * this._scale)
                this._startDrag(this._press, x, y);
            if (this._drag) {
                this._updateDrag(x, y);
                return Clutter.EVENT_STOP;
            }
            return Clutter.EVENT_PROPAGATE;
        }
        if (type === Clutter.EventType.BUTTON_RELEASE) {
            this._press = null;
            if (this._drag) {
                const [x, y] = event.get_coords();
                this._endDrag(x, y);
                return Clutter.EVENT_STOP;
            }
        }
        return Clutter.EVENT_PROPAGATE;
    }

    _startDrag(press, x, y) {
        const {tile} = press;
        tile.fake_release?.();
        tile._clearLongPress();
        tile._longPressed = true;   // its click, if any, isn't an open
        if (!this._editing)
            this._setEditing(true);
        const [ix, iy] = tile._icon.get_transformed_position();
        const size = this._iconSize;
        // An app gets its own icon (a tile inside a folder goes away with
        // the folder); a folder is drawn from its tile.
        const clone = tile.item.type === 'app'
            ? tile.item.app.create_icon_texture(size)
            : new Clutter.Clone({source: tile._icon, width: size, height: size});
        clone.set_size(size, size);
        clone.set_pivot_point(0.5, 0.5);
        this.add_child(clone);
        clone.set_position(ix - this.x, iy - this.y);
        clone.ease({scale_x: 1.1, scale_y: 1.1, duration: 120});
        tile.opacity = 0;
        this._drag = {
            tile, item: tile.item, clone,
            offX: press.x - ix, offY: press.y - iy,
            fromFolder: press.inFolder ? this._folderView._folder : null,
            list: this._items.filter(it => it !== tile.item),
            insert: -1, target: null, hoverTile: null, hoverId: 0, edgeId: 0,
        };
        this._drag.insert = press.inFolder ? this._drag.list.length : this._items.indexOf(tile.item);
    }

    _updateDrag(x, y) {
        const drag = this._drag;
        drag.clone.set_position(x - drag.offX - this.x, y - drag.offY - this.y);

        // Inside an open folder: leaving its panel takes the app out.
        const view = this._folderView;
        if (view) {
            const [px, py] = view._panel.get_transformed_position();
            const [pw, ph] = view._panel.get_transformed_size();
            if (x < px || x > px + pw || y < py || y > py + ph)
                this._closeFolder();
            return;
        }

        this._updateEdgeFlip(x);
        const hovered = this._tileAtIcon(x, y);
        if (hovered)
            this._clearGapTimer();
        if (hovered && hovered !== drag.hoverTile) {
            this._clearHover();
            drag.hoverTile = hovered;
            // A moment's pause over an app or folder means "put it in".
            if (drag.item.type === 'app') {
                drag.hoverId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 350, () => {
                    drag.hoverId = 0;
                    drag.target = hovered;
                    hovered._holder.add_style_class_name('parchaos-launcher-drop-target');
                    return GLib.SOURCE_REMOVE;
                });
            }
            return;
        }
        if (hovered)
            return;
        this._clearHover();
        // Make room only once the pointer rests: passing over other cells
        // on the way to an icon mustn't push that icon away.
        const index = this._indexAt(x, y);
        if (index !== drag.pendingInsert) {
            this._clearGapTimer();
            drag.pendingInsert = index;
            drag.gapId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 180, () => {
                drag.gapId = 0;
                this._moveGap(index);
                return GLib.SOURCE_REMOVE;
            });
        }
    }

    _clearGapTimer() {
        const drag = this._drag;
        if (drag?.gapId)
            GLib.source_remove(drag.gapId);
        if (drag) {
            drag.gapId = 0;
            drag.pendingInsert = undefined;
        }
    }

    _clearHover() {
        const drag = this._drag;
        if (!drag)
            return;
        if (drag.hoverId)
            GLib.source_remove(drag.hoverId);
        drag.hoverId = 0;
        drag.target?._holder.remove_style_class_name('parchaos-launcher-drop-target');
        drag.target = null;
        drag.hoverTile = null;
    }

    // Holding the dragged icon at the left or right edge turns the page.
    _updateEdgeFlip(x) {
        const drag = this._drag;
        const margin = 40 * this._scale;
        const dir = x - this.x < this._gridArea.x - margin / 2 ? -1
            : x - this.x > this._gridArea.x + this._gridArea.width + margin / 2 ? 1 : 0;
        if (dir === 0 || drag.edgeDir !== dir) {
            if (drag.edgeId)
                GLib.source_remove(drag.edgeId);
            drag.edgeId = 0;
            drag.edgeDir = dir;
        }
        if (dir !== 0 && !drag.edgeId) {
            drag.edgeId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 600, () => {
                const page = this._page + dir;
                if (page >= 0 && page < this._nPages)
                    this._setPage(page);
                return GLib.SOURCE_CONTINUE;
            });
        }
    }

    // The tile whose icon (inner part) is under the pointer, if any.
    _tileAtIcon(x, y) {
        const inset = this._iconSize * 0.2;
        return this._tiles.find(t => {
            if (t === this._drag.tile || !t.mapped)
                return false;
            const [ix, iy] = t._icon.get_transformed_position();
            return x > ix + inset && x < ix + this._iconSize - inset &&
                y > iy + inset && y < iy + this._iconSize - inset;
        }) ?? null;
    }

    // Grid slot under the pointer on the current page.
    _indexAt(x, y) {
        const perPage = COLUMNS * ROWS;
        const lx = x - this.x - this._gridArea.x;
        const ly = y - this.y - this._gridArea.y;
        const col = Math.max(0, Math.min(COLUMNS - 1, Math.floor(lx / this._cellW)));
        const row = Math.max(0, Math.min(ROWS - 1, Math.floor(ly / this._cellH)));
        const index = this._page * perPage + row * COLUMNS + col;
        return Math.min(index, this._drag.list.length);
    }

    _slotPosition(index) {
        const perPage = COLUMNS * ROWS;
        const i = index % perPage;
        return {
            page: Math.floor(index / perPage),
            x: this._gridArea.x + (i % COLUMNS) * this._cellW + 6 * this._scale,
            y: Math.floor(i / COLUMNS) * this._cellH +
                Math.round((this._cellH - this._iconSize - 34 * this._scale) / 2),
        };
    }

    // Leave a gap at `insert`: every other tile slides to its new slot.
    _moveGap(insert) {
        const drag = this._drag;
        if (insert === drag.insert)
            return;
        drag.insert = insert;
        const pages = this._pages.get_children();
        drag.list.forEach((item, j) => {
            const tile = this._tiles.find(t => t.item === item);
            if (!tile)
                return;
            const pos = this._slotPosition(j >= insert ? j + 1 : j);
            const page = pages[pos.page];
            if (!page)
                return;
            if (tile.get_parent() !== page) {
                tile.get_parent()?.remove_child(tile);
                page.add_child(tile);
                tile.set_position(pos.x, pos.y);
            } else {
                tile.ease({x: pos.x, y: pos.y, duration: 180, mode: Clutter.AnimationMode.EASE_OUT_QUAD});
            }
        });
    }

    _endDrag(x, y) {
        const drag = this._drag;
        // A drop before the pause still goes where the pointer is.
        if (drag.gapId && drag.pendingInsert !== undefined)
            drag.insert = drag.pendingInsert;
        this._clearGapTimer();
        this._drag = null;
        if (drag.edgeId)
            GLib.source_remove(drag.edgeId);
        if (drag.hoverId)
            GLib.source_remove(drag.hoverId);
        drag.clone.destroy();

        const target = drag.target?.item;
        const onOwnFolder = drag.fromFolder && target?.type === 'folder' &&
            target.id === drag.fromFolder.id;
        if (drag.fromFolder && (this._folderView || onOwnFolder)) {
            // Dropped back inside or onto the folder it came from: nothing changes.
            if (this._folderView)
                drag.tile.opacity = 255;
            else
                this._reload();
            return;
        }
        // Taking the last app out deletes its folder; drop it from the order
        // too, and shift a later insert position up by one.
        const takeOut = () => {
            if (!drag.fromFolder || !removeFromFolder(drag.fromFolder, drag.item.app))
                return;
            const at = drag.list.findIndex(it => it.type === 'folder' && it.id === drag.fromFolder.id);
            if (at < 0)
                return;
            drag.list = drag.list.filter((_, i) => i !== at);
            if (drag.insert > at)
                drag.insert--;
        };
        if (target && drag.item.type === 'app') {
            takeOut();
            let order = drag.list;
            if (target.type === 'folder') {
                addToFolder(target.id, drag.item.app);
            } else {
                const id = createFolder([target.app, drag.item.app]);
                order = order.map(it => it === target ? {type: 'folder', id} : it);
            }
            saveOrder(order);
        } else {
            takeOut();
            const order = drag.list.slice();
            const insert = drag.insert < 0 ? order.length : Math.min(drag.insert, order.length);
            order.splice(insert, 0, drag.fromFolder ? {type: 'app', app: drag.item.app} : drag.item);
            saveOrder(order);
        }
        this._reload();
    }

    _cancelDrag() {
        const drag = this._drag;
        if (!drag)
            return;
        this._clearGapTimer();
        this._drag = null;
        if (drag.edgeId)
            GLib.source_remove(drag.edgeId);
        if (drag.hoverId)
            GLib.source_remove(drag.hoverId);
    }

    // Rebuild from the saved arrangement, keeping the page and edit mode.
    _reload() {
        this._items = loadItems();
        this._buildPages(this._items);
        if (this._editing)
            this._allTiles().forEach(t => t.setEditing(true, this._removable.has(t.item.app.get_id())));
    }

    _buildPages(items) {
        this._pages.destroy_all_children();
        this._tiles = [];
        const perPage = COLUMNS * ROWS;
        this._nPages = Math.max(1, Math.ceil(items.length / perPage));
        const pageW = this._monitor.width;

        for (let p = 0; p < this._nPages; p++) {
            const page = new St.Widget({
                x: p * pageW,
                width: pageW,
                height: this._gridArea.height,
            });
            items.slice(p * perPage, (p + 1) * perPage).forEach((item, i) => {
                const tile = new AppTile(item, this._iconSize, this._cellW - 12 * this._scale);
                tile.x = this._gridArea.x + (i % COLUMNS) * this._cellW + 6 * this._scale;
                tile.y = Math.floor(i / COLUMNS) * this._cellH +
                    Math.round((this._cellH - this._iconSize - 34 * this._scale) / 2);
                this._wireTile(tile, item);
                page.add_child(tile);
                this._tiles.push(tile);
            });
            this._pages.add_child(page);
        }

        this._dots.destroy_all_children();
        for (let p = 0; p < this._nPages; p++) {
            const dot = new St.Button({style_class: 'parchaos-launcher-dot', can_focus: false});
            dot.connect('clicked', () => this._setPage(p));
            this._dots.add_child(dot);
        }
        this._dots.visible = this._nPages > 1;
        this._page = Math.min(this._page, this._nPages - 1);
        this._setPage(this._page, false);
        this._select(-1);
    }

    // Keyboard selection: a highlighted tile that arrows move and Enter
    // opens. Moving past the last or first tile of a page flips the page.
    _select(index) {
        this._tiles[this._selected]?.remove_style_pseudo_class('selected');
        this._selected = index;
        const tile = this._tiles[index];
        if (!tile)
            return;
        tile.add_style_pseudo_class('selected');
        const page = Math.floor(index / (COLUMNS * ROWS));
        if (page !== this._page)
            this._setPage(page);
    }

    _moveSelection(sym) {
        const n = this._tiles.length;
        if (n === 0)
            return;
        const perPage = COLUMNS * ROWS;
        let i = this._selected;
        if (i === undefined || i < 0 || !this._tiles[i]) {
            this._select(Math.min(this._page * perPage, n - 1));
            return;
        }
        const pos = i % perPage;
        if (sym === Clutter.KEY_Right)
            i += 1;
        else if (sym === Clutter.KEY_Left)
            i -= 1;
        else if (sym === Clutter.KEY_Down)
            i = pos + COLUMNS < perPage ? i + COLUMNS : i;
        else if (sym === Clutter.KEY_Up)
            i = pos - COLUMNS >= 0 ? i - COLUMNS : i;
        this._select(Math.max(0, Math.min(n - 1, i)));
    }

    _setPage(page, animate = true) {
        page = Math.max(0, Math.min(this._nPages - 1, page));
        this._page = page;
        const x = -page * this._monitor.width;
        this._pages.remove_all_transitions();
        if (animate) {
            this._pages.ease({
                translation_x: x,
                duration: PAGE_TIME,
                mode: Clutter.AnimationMode.EASE_OUT_CUBIC,
            });
        } else {
            this._pages.translation_x = x;
        }
        this._dots.get_children().forEach((dot, i) => {
            if (i === page)
                dot.add_style_pseudo_class('checked');
            else
                dot.remove_style_pseudo_class('checked');
        });
        // Center the dots under the grid (their width is known once styled).
        if (this._dotsIdleId)
            return;
        this._dotsIdleId = GLib.idle_add(GLib.PRIORITY_DEFAULT, () => {
            this._dotsIdleId = 0;
            const [, natW] = this._dots.get_preferred_width(-1);
            this._dots.x = Math.round((this._monitor.width - natW) / 2);
            this._dots.y = this._gridArea.y + this._gridArea.height + 12 * this._scale;
            return GLib.SOURCE_REMOVE;
        });
    }

    _onScroll(event) {
        if (this._folderView)
            return Clutter.EVENT_STOP;
        const dir = event.get_scroll_direction();
        if (dir === Clutter.ScrollDirection.SMOOTH) {
            const [dx, dy] = event.get_scroll_delta();
            this._scrollAccum += Math.abs(dx) > Math.abs(dy) ? dx : dy;
            if (Math.abs(this._scrollAccum) >= 1.5 && !this._scrollLock) {
                this._setPage(this._page + (this._scrollAccum > 0 ? 1 : -1));
                this._scrollAccum = 0;
                // Ignore the tail of the same fling.
                this._scrollLock = true;
                this._scrollLockId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, PAGE_TIME + 80, () => {
                    this._scrollLockId = 0;
                    this._scrollLock = false;
                    this._scrollAccum = 0;
                    return GLib.SOURCE_REMOVE;
                });
            }
        } else if (dir === Clutter.ScrollDirection.DOWN || dir === Clutter.ScrollDirection.RIGHT) {
            this._setPage(this._page + 1);
        } else if (dir === Clutter.ScrollDirection.UP || dir === Clutter.ScrollDirection.LEFT) {
            this._setPage(this._page - 1);
        }
        return Clutter.EVENT_STOP;
    }

    _onKeyPress(event) {
        const sym = event.get_key_symbol();
        if (sym === Clutter.KEY_Escape) {
            if (this._confirm)
                this._closeConfirm();
            else if (this._folderView)
                this._closeFolder();
            else if (this._editing)
                this._setEditing(false);
            else if (this._entry.get_text() !== '')
                this._entry.set_text('');
            else
                this.close();
            return Clutter.EVENT_STOP;
        }
        const arrows = [Clutter.KEY_Left, Clutter.KEY_Right, Clutter.KEY_Up, Clutter.KEY_Down];
        if (this._folderView) {
            if (arrows.includes(sym)) {
                this._moveFolderSelection(sym);
                return Clutter.EVENT_STOP;
            }
            return Clutter.EVENT_PROPAGATE;
        }
        if (sym === Clutter.KEY_Page_Down) {
            this._setPage(this._page + 1);
            return Clutter.EVENT_STOP;
        }
        if (sym === Clutter.KEY_Page_Up) {
            this._setPage(this._page - 1);
            return Clutter.EVENT_STOP;
        }
        if (arrows.includes(sym)) {
            this._moveSelection(sym);
            return Clutter.EVENT_STOP;
        }
        return Clutter.EVENT_PROPAGATE;
    }

    _onSearchChanged() {
        const text = this._entry.get_text().trim();
        if (this._folderView)
            this._closeFolder();
        if (text === '') {
            this._buildPages(this._items);
            return;
        }
        const appSys = Shell.AppSystem.get_default();
        const seen = new Set();
        const results = [];
        for (const group of Shell.AppSystem.search(text)) {
            for (const id of group) {
                const app = appSys.lookup_app(id);
                if (!app || seen.has(id) || !app.get_app_info().should_show())
                    continue;
                seen.add(id);
                results.push({type: 'app', app});
            }
        }
        this._page = 0;
        this._buildPages(results);
        if (results.length > 0)
            this._select(0);
    }

    // Arrow keys inside an open folder move a selection of its own.
    _moveFolderSelection(sym) {
        const view = this._folderView;
        const tiles = view._tiles;
        const n = tiles.length;
        if (n === 0)
            return;
        let i = view._selected ?? -1;
        if (i < 0) {
            i = 0;
        } else if (sym === Clutter.KEY_Right) {
            i = Math.min(n - 1, i + 1);
        } else if (sym === Clutter.KEY_Left) {
            i = Math.max(0, i - 1);
        } else if (sym === Clutter.KEY_Down) {
            i = i + COLUMNS < n ? i + COLUMNS : i;
        } else if (sym === Clutter.KEY_Up) {
            i = i - COLUMNS >= 0 ? i - COLUMNS : i;
        }
        tiles[view._selected]?.remove_style_pseudo_class('selected');
        view._selected = i;
        tiles[i].add_style_pseudo_class('selected');
    }

    _activateFirst() {
        // With a folder open, Enter opens the folder's selected app, never
        // the (hidden) main grid's.
        const view = this._folderView;
        if (view) {
            const tile = view._tiles[view._selected];
            if (tile)
                this._activateItem(tile.item, tile);
            return;
        }
        const selected = this._tiles[this._selected];
        if (selected) {
            this._activateItem(selected.item, selected);
            return;
        }
        const first = this._tiles.find(t => t.item.type === 'app');
        if (this._entry.get_text().trim() !== '' && first)
            this._activateItem(first.item, first);
    }

    _wireTile(tile, item) {
        tile.connect('activate', () => this._activateItem(item, tile));
        if (item.type !== 'app')
            return;
        tile.connect('long-press', () => this._setEditing(true));
        tile.connect('remove', () => this._confirmRemove(item.app));
        if (this._editing)
            tile.setEditing(true, this._removable.has(item.app.get_id()));
    }

    _allTiles() {
        const tiles = [...this._tiles];
        this._folderView?._tiles?.forEach(t => tiles.push(t));
        return tiles.filter(t => t.item.type === 'app' && t.get_parent() !== null);
    }

    // Edit mode: icons pulse, removable apps show a badge. Which apps are
    // removable is asked of the helper once per edit session.
    _setEditing(editing) {
        if (editing === this._editing)
            return;
        this._editing = editing;
        const tiles = this._allTiles();
        tiles.forEach(t => t.setEditing(editing, this._removable.has(t.item.app.get_id())));
        if (!editing || !this._helper)
            return;
        const ids = new Set();
        for (const it of this._items) {
            if (it.type === 'app')
                ids.add(it.app.get_id());
            else
                it.apps.forEach(a => ids.add(a.get_id()));
        }
        runAsync([this._helper, 'removable', ...ids]).then(({ok, stdout}) => {
            if (!ok || this._destroyed || !this._editing)
                return;
            try {
                this._removable = new Set(JSON.parse(stdout));
            } catch (e) {
                return;
            }
            this._allTiles().forEach(t =>
                t.setEditing(true, this._removable.has(t.item.app.get_id())));
        });
    }

    _confirmRemove(app) {
        this._closeConfirm();
        const m = this._monitor;
        const shade = new St.Widget({
            style_class: 'parchaos-launcher-confirm-shade',
            reactive: true,
            width: m.width,
            height: m.height,
        });
        shade.connect('button-release-event', () => {
            this._closeConfirm();
            return Clutter.EVENT_STOP;
        });
        const box = new St.BoxLayout({
            style_class: 'parchaos-launcher-confirm',
            orientation: Clutter.Orientation.VERTICAL,
            reactive: true,
        });
        box.connect('button-release-event', () => Clutter.EVENT_STOP);
        const icon = app.create_icon_texture(64);
        icon.x_align = Clutter.ActorAlign.CENTER;
        box.add_child(icon);
        box.add_child(new St.Label({
            style_class: 'parchaos-launcher-confirm-title',
            text: `Uninstall "${app.get_name()}"?`,
            x_align: Clutter.ActorAlign.CENTER,
        }));
        const baseText = 'The app will be removed from this computer. Your own files stay where they are.';
        const body = new St.Label({
            style_class: 'parchaos-launcher-confirm-body',
            text: `${baseText}\n\nChecking what will be removed…`,
            x_align: Clutter.ActorAlign.CENTER,
        });
        body.clutter_text.line_wrap = true;
        box.add_child(body);
        const buttons = new St.BoxLayout({style_class: 'parchaos-launcher-confirm-buttons', x_expand: true});
        const cancel = new St.Button({label: 'Cancel', style_class: 'parchaos-launcher-confirm-button', x_expand: true, can_focus: true});
        const remove = new St.Button({label: 'Uninstall', style_class: 'parchaos-launcher-confirm-button destructive', x_expand: true, can_focus: true});
        cancel.connect('clicked', () => this._closeConfirm());
        // Uninstall stays off until the helper has worked out everything
        // the removal takes with it, which the dialog then lists.
        remove.reactive = false;
        remove.opacity = 128;
        let confirmed = null;
        remove.connect('clicked', () => {
            this._closeConfirm();
            if (confirmed)
                this._uninstall(app, confirmed);
        });
        runAsync([this._helper, 'plan', app.get_id()]).then(({stdout}) => {
            if (this._destroyed || this._confirm !== shade)
                return;
            let result = {};
            try {
                result = JSON.parse(stdout);
            } catch (e) {
                result = {error: 'Couldn\'t check what would be removed.'};
            }
            const packages = result.packages ?? [];
            if (result.error || packages.length === 0) {
                body.text = result.error || 'Couldn\'t check what would be removed.';
                return;
            }
            body.text = packages.length > 1
                ? `${baseText}\n\nThis also removes: ${packages.join(', ')}.`
                : baseText;
            confirmed = packages;
            remove.reactive = true;
            remove.opacity = 255;
            this._placeConfirmBox(box);
        });
        buttons.add_child(cancel);
        buttons.add_child(remove);
        box.add_child(buttons);
        shade.add_child(box);
        this.add_child(shade);
        this._confirm = shade;
        this._placeConfirmBox(box);
        cancel.grab_key_focus();
    }

    _placeConfirmBox(box) {
        const m = this._monitor;
        const [, natW] = box.get_preferred_width(-1);
        const [, natH] = box.get_preferred_height(natW);
        box.set_position(Math.round((m.width - natW) / 2), Math.round((m.height - natH) / 2));
    }

    _closeConfirm() {
        this._confirm?.destroy();
        this._confirm = null;
    }

    // The password prompt for system packages is a shell dialog that would
    // sit under the launcher, so close first and report by notification.
    // The helper removes nothing unless the plan still matches the list
    // the user confirmed.
    _uninstall(app, packages) {
        const name = app.get_name();
        const id = app.get_id();
        const helper = this._helper;
        this.close();
        runAsync([helper, 'uninstall', id, ...packages]).then(({ok, stderr}) => {
            if (ok) {
                Main.notify(`${name} was uninstalled`, '');
            } else {
                const reason = stderr.trim().split('\n').pop() || 'The removal was cancelled or failed.';
                Main.notify(`Couldn't uninstall ${name}`, reason);
            }
        });
    }

    _activateItem(item, tile) {
        if (item.type === 'folder') {
            this._openFolder(item, tile);
            return;
        }
        if (this._editing)
            return;
        item.app.activate();
        this.close();
    }

    _openFolder(folder, _tile) {
        const m = this._monitor;
        const s = this._scale;
        const view = new St.Widget({
            reactive: true,
            width: m.width,
            height: m.height,
            opacity: 0,
        });
        view.connect('button-release-event', () => {
            this._closeFolder();
            return Clutter.EVENT_STOP;
        });

        const cols = COLUMNS;
        const rows = Math.max(1, Math.ceil(folder.apps.length / cols));
        const panelW = Math.round(m.width * 0.88);
        const cellW = Math.floor((panelW - 48 * s) / cols);
        const cellH = this._cellH;
        const maxRows = Math.max(1, Math.floor((m.height * 0.62) / cellH));
        const visibleRows = Math.min(rows, maxRows);

        const grid = new St.Widget({width: cols * cellW, height: rows * cellH});
        const folderTiles = [];
        folder.apps.forEach((app, i) => {
            const item = {type: 'app', app};
            const tile = new AppTile(item, this._iconSize, cellW - 12 * s);
            tile.x = (i % cols) * cellW + 6 * s;
            tile.y = Math.floor(i / cols) * cellH +
                Math.round((cellH - this._iconSize - 34 * s) / 2);
            this._wireTile(tile, item);
            folderTiles.push(tile);
            grid.add_child(tile);
        });

        const scroll = new St.ScrollView({
            style_class: 'parchaos-launcher-folder-scroll',
            hscrollbar_policy: St.PolicyType.NEVER,
            vscrollbar_policy: rows > maxRows ? St.PolicyType.AUTOMATIC : St.PolicyType.NEVER,
            width: cols * cellW,
            height: visibleRows * cellH,
        });
        const content = new St.BoxLayout({orientation: Clutter.Orientation.VERTICAL});
        content.add_child(grid);
        scroll.set_child(content);

        const panel = new St.Bin({
            style_class: 'parchaos-launcher-folder-panel',
            reactive: true,
            child: scroll,
        });
        // Clicks inside the panel (but not on an app) keep the folder open.
        panel.connect('button-release-event', () => Clutter.EVENT_STOP);
        const [, panelNatW] = panel.get_preferred_width(-1);
        const [, panelNatH] = panel.get_preferred_height(panelNatW);
        panel.x = Math.round((m.width - panelNatW) / 2);
        panel.y = Math.round((m.height - panelNatH) / 2 - 20 * s);

        // The name is editable in place: click it, type, press Enter.
        const titleW = Math.round(420 * s);
        const title = new St.Entry({
            text: folder.name,
            style_class: 'parchaos-launcher-folder-title',
            width: titleW,
            can_focus: true,
        });
        title.clutter_text.x_align = Clutter.ActorAlign.CENTER;
        title.x = Math.round((m.width - titleW) / 2);
        title.y = panel.y - 64 * s;
        title.connect('button-release-event', () => Clutter.EVENT_STOP);
        const rename = () => {
            const name = title.get_text().trim();
            if (name && name !== folder.name) {
                const settings = folderSettings(folder.id);
                settings.set_string('name', name);
                settings.set_boolean('translate', false);
                folder.name = name;
                view._changed = true;
            }
        };
        title.clutter_text.connect('activate', () => {
            rename();
            this._entry.grab_key_focus();
        });
        title.clutter_text.connect('key-focus-out', rename);

        view.add_child(title);
        view.add_child(panel);
        this.add_child(view);
        this._folderView = view;
        view._tiles = folderTiles;
        view._panel = panel;
        view._folder = folder;

        view.ease({opacity: 255, duration: FADE_IN, mode: Clutter.AnimationMode.EASE_OUT_QUAD});
        for (const actor of [this._clip, this._dots, this._entry])
            actor.ease({opacity: 0, duration: FADE_IN, mode: Clutter.AnimationMode.EASE_OUT_QUAD});
    }

    _closeFolder() {
        const view = this._folderView;
        if (!view)
            return;
        this._folderView = null;
        if (global.stage.key_focus && view.contains(global.stage.key_focus))
            this._entry.grab_key_focus();
        view.ease({
            opacity: 0,
            duration: FADE_OUT,
            mode: Clutter.AnimationMode.EASE_OUT_QUAD,
            onStopped: () => view.destroy(),
        });
        // A renamed folder shows its new name on the grid.
        if (view._changed && !this._drag)
            this._reload();
        for (const actor of [this._clip, this._dots, this._entry])
            actor.ease({opacity: 255, duration: FADE_IN, mode: Clutter.AnimationMode.EASE_OUT_QUAD});
    }

    open() {
        Main.uiGroup.add_child(this);
        Main.uiGroup.set_child_above_sibling(this, null);
        this._grab = Main.pushModal(this, {actionMode: Shell.ActionMode.POPUP});
        this._entry.grab_key_focus();

        this.ease({opacity: 255, duration: FADE_IN, mode: Clutter.AnimationMode.EASE_OUT_QUAD});
        return true;
    }

    close() {
        if (this._closing)
            return;
        this._closing = true;
        if (this._grab) {
            Main.popModal(this._grab);
            this._grab = null;
        }
        this.ease({
            opacity: 0,
            duration: FADE_OUT,
            mode: Clutter.AnimationMode.EASE_OUT_QUAD,
            onStopped: () => {
                this.emit('closed');
                this.destroy();
            },
        });
    }
});

export default class ParchaOSLauncherExtension extends Extension {
    enable() {
        this._launcher = null;
        this._suppress = false;
        this._dockModule = null;
        this._loadDockModule();
        this._extChangedId = Main.extensionManager.connect('extension-state-changed',
            (_m, ext) => {
                if (ext.uuid === DOCK_UUID)
                    this._loadDockModule();
            });

        this._injections = new InjectionManager();
        const self = this;
        this._injections.overrideMethod(Main.overview, 'show', original => function (state, ...args) {
            if (state === OverviewControls.ControlsState.APP_GRID) {
                if (!self._suppress)
                    self.toggle();
                return;
            }
            original.call(this, state, ...args);
        });
        // With the overview already open, Show Apps (ours or the dock's)
        // switches it to the app grid in place instead of calling show();
        // leave the overview and open the launcher instead.
        const controls = Main.overview._overview?.controls;
        if (controls) {
            this._injections.overrideMethod(controls, '_onShowAppsButtonToggled', original => function (...args) {
                if (!self._suppress && self._showAppsButtons().some(b => b.checked)) {
                    Main.overview.hide();
                    self.toggle();
                    return;
                }
                original.call(this, ...args);
            });
        }
    }

    disable() {
        if (this._extChangedId) {
            Main.extensionManager.disconnect(this._extChangedId);
            this._extChangedId = 0;
        }
        this._injections?.clear();
        this._injections = null;
        this._launcher?.close();
        this._launcher = null;
        this._dockModule = null;
    }

    // The dock's module is already loaded by the extension manager, so
    // importing it again returns the same instance (and its dockManager).
    _loadDockModule() {
        const dock = Main.extensionManager.lookup(DOCK_UUID);
        if (!dock || dock.state !== 1 /* ACTIVE */) {
            this._dockModule = null;
            return;
        }
        import(`${dock.dir.get_uri()}/extension.js`)
            .then(mod => {
                this._dockModule = mod;
            })
            .catch(e => logError(e, 'parchaos-launcher: could not reach the dock'));
    }

    _showAppsButtons() {
        const buttons = [Main.overview.dash?.showAppsButton];
        for (const d of this._dockModule?.dockManager?._allDocks ?? [])
            buttons.push(d.dash?.showAppsButton);
        return buttons.filter(b => b);
    }

    toggle() {
        // One click can reach us more than once in the same event (the
        // dock and the overview both react to the Show Apps toggle).
        const now = GLib.get_monotonic_time();
        if (now - (this._lastToggle ?? 0) < 250000)
            return;
        this._lastToggle = now;

        if (this._launcher) {
            this._launcher.close();
        } else {
            const launcher = new Launcher(`${this.path}/parchaos-launcher-apps`);
            launcher.connect('closed', () => {
                if (this._launcher === launcher)
                    this._launcher = null;
            });
            launcher.open();
            this._launcher = launcher;
        }
        this._uncheckShowAppsButtons();
    }

    // Show Apps buttons are toggles that stay pressed after the click that
    // opened us. Release them without re-triggering the grid.
    _uncheckShowAppsButtons() {
        this._suppress = true;
        try {
            for (const b of this._showAppsButtons()) {
                if (b.checked)
                    b.checked = false;
            }
        } finally {
            this._suppress = false;
        }
    }
}
