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

import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as OverviewControls from 'resource:///org/gnome/shell/ui/overviewControls.js';
import {Extension, InjectionManager} from 'resource:///org/gnome/shell/extensions/extension.js';

const COLUMNS = 7;
const ROWS = 5;
const ANIM_TIME = 220;
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
    return [...loose, ...folders];
}

const AppTile = GObject.registerClass({
    Signals: {'activate': {}},
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
                layout_manager: new Clutter.GridLayout({
                    row_homogeneous: true,
                    column_homogeneous: true,
                }),
            });
            const pad = Math.floor(iconSize * 0.1);
            const sub = Math.floor((iconSize - 2 * pad) / 3 * 0.9);
            icon.set_style(`${icon.get_style()} padding: ${pad}px;`);
            // Always a full 3x3 grid, so a folder with few apps still
            // lays its icons out from the top-left like a full one.
            for (let i = 0; i < 9; i++) {
                const app = item.apps[i];
                const bin = new St.Bin({
                    child: app ? app.create_icon_texture(sub) : null,
                    width: sub,
                    height: sub,
                    x_expand: true,
                    y_expand: true,
                });
                icon.layout_manager.attach(bin, i % 3, Math.floor(i / 3), 1, 1);
            }
        }
        icon.x_align = Clutter.ActorAlign.CENTER;
        this._icon = icon;
        box.add_child(icon);

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
        this.connect('clicked', () => this.emit('activate'));
    }
});

const Launcher = GObject.registerClass({
    Signals: {'closed': {}},
}, class Launcher extends St.Widget {
    _init() {
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
        this._page = 0;
        this._scrollAccum = 0;
        this._folderView = null;

        this._backdrop = new St.Widget({
            style_class: 'parchaos-launcher-backdrop',
            width: monitor.width,
            height: monitor.height,
        });
        this._backdrop.add_effect(new Shell.BlurEffect({
            radius: 90,
            brightness: 0.62,
            mode: Shell.BlurMode.BACKGROUND,
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
            if (event.get_button() === Clutter.BUTTON_PRIMARY)
                this.close();
            return Clutter.EVENT_STOP;
        });
        this.connect('scroll-event', (_a, event) => this._onScroll(event));
        // Two-finger touchpad swipes arrive as smooth scroll events.
        this.connect('key-press-event', (_a, event) => this._onKeyPress(event));
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
                tile.connect('activate', () => this._activateItem(item, tile));
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
        GLib.idle_add(GLib.PRIORITY_DEFAULT, () => {
            if (!this._dots)
                return GLib.SOURCE_REMOVE;
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
                GLib.timeout_add(GLib.PRIORITY_DEFAULT, PAGE_TIME + 80, () => {
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
            if (this._folderView)
                this._closeFolder();
            else if (this._entry.get_text() !== '')
                this._entry.set_text('');
            else
                this.close();
            return Clutter.EVENT_STOP;
        }
        if (this._entry.get_text() === '' && !this._folderView) {
            if (sym === Clutter.KEY_Right || sym === Clutter.KEY_Page_Down) {
                this._setPage(this._page + 1);
                return Clutter.EVENT_STOP;
            }
            if (sym === Clutter.KEY_Left || sym === Clutter.KEY_Page_Up) {
                this._setPage(this._page - 1);
                return Clutter.EVENT_STOP;
            }
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
    }

    _activateFirst() {
        const first = this._tiles.find(t => t.item.type === 'app');
        if (this._entry.get_text().trim() !== '' && first)
            this._activateItem(first.item, first);
    }

    _activateItem(item, tile) {
        if (item.type === 'folder') {
            this._openFolder(item, tile);
            return;
        }
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
        folder.apps.forEach((app, i) => {
            const item = {type: 'app', app};
            const tile = new AppTile(item, this._iconSize, cellW - 12 * s);
            tile.x = (i % cols) * cellW + 6 * s;
            tile.y = Math.floor(i / cols) * cellH +
                Math.round((cellH - this._iconSize - 34 * s) / 2);
            tile.connect('activate', () => this._activateItem(item, tile));
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

        const title = new St.Label({
            text: folder.name,
            style_class: 'parchaos-launcher-folder-title',
            width: m.width,
        });
        title.clutter_text.x_align = Clutter.ActorAlign.CENTER;
        title.y = panel.y - 64 * s;

        view.add_child(title);
        view.add_child(panel);
        this.add_child(view);
        this._folderView = view;

        panel.set_pivot_point(0.5, 0.5);
        panel.scale_x = panel.scale_y = 0.92;
        panel.ease({scale_x: 1, scale_y: 1, duration: ANIM_TIME, mode: Clutter.AnimationMode.EASE_OUT_QUAD});
        view.ease({opacity: 255, duration: ANIM_TIME, mode: Clutter.AnimationMode.EASE_OUT_QUAD});
        for (const actor of [this._clip, this._dots, this._entry])
            actor.ease({opacity: 0, duration: ANIM_TIME, mode: Clutter.AnimationMode.EASE_OUT_QUAD});
    }

    _closeFolder() {
        const view = this._folderView;
        if (!view)
            return;
        this._folderView = null;
        view.ease({
            opacity: 0,
            duration: ANIM_TIME,
            mode: Clutter.AnimationMode.EASE_OUT_QUAD,
            onStopped: () => view.destroy(),
        });
        for (const actor of [this._clip, this._dots, this._entry])
            actor.ease({opacity: 255, duration: ANIM_TIME, mode: Clutter.AnimationMode.EASE_OUT_QUAD});
    }

    open() {
        Main.uiGroup.add_child(this);
        Main.uiGroup.set_child_above_sibling(this, null);
        this._grab = Main.pushModal(this, {actionMode: Shell.ActionMode.POPUP});
        this._entry.grab_key_focus();

        this._clip.set_pivot_point(0.5, 0.5);
        this._clip.scale_x = this._clip.scale_y = 1.06;
        this._clip.ease({scale_x: 1, scale_y: 1, duration: ANIM_TIME, mode: Clutter.AnimationMode.EASE_OUT_QUAD});
        this.ease({opacity: 255, duration: ANIM_TIME, mode: Clutter.AnimationMode.EASE_OUT_QUAD});
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
        this._clip.ease({scale_x: 1.06, scale_y: 1.06, duration: ANIM_TIME, mode: Clutter.AnimationMode.EASE_IN_QUAD});
        this.ease({
            opacity: 0,
            duration: ANIM_TIME,
            mode: Clutter.AnimationMode.EASE_IN_QUAD,
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
            const launcher = new Launcher();
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
