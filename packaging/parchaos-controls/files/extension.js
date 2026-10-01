// SPDX-License-Identifier: GPL-3.0-or-later
// Parcha Controls -- ParchaOS's control center for GNOME Shell.
//
// A tiled panel that opens from the top bar's status icons (and Super+S),
// in place of GNOME's Quick Settings menu. The tiles don't reimplement
// Wi-Fi, Bluetooth and the rest: they mirror and drive the Quick Settings
// toggles GNOME Shell is already running, so behavior (and any backend
// quirks) stays identical to stock GNOME. Brightness comes from
// Main.brightnessManager and Now Playing from GNOME's own MPRIS source.
//
// Original code for ParchaOS, GPL-3.0-or-later.

import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import Shell from 'gi://Shell';
import St from 'gi://St';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import * as Mpris from 'resource:///org/gnome/shell/ui/mpris.js';
import {Slider} from 'resource:///org/gnome/shell/ui/slider.js';
import {Extension, InjectionManager} from 'resource:///org/gnome/shell/extensions/extension.js';

const CELL = 72;
const GAP = 10;
const PAD = 12;

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

function spawn(argv) {
    try {
        Gio.Subprocess.new(argv, Gio.SubprocessFlags.NONE);
    } catch (e) {
        logError(e, `parchaos-controls: could not run ${argv.join(' ')}`);
    }
}

function openSettings(panel) {
    spawn(panel ? ['gnome-control-center', panel] : ['gnome-control-center']);
}

// Clicking a Quick Settings toggle the way a pointer click would: toggle-
// mode buttons (Do Not Disturb, Night Light) flip their own checked state
// on a real click, the rest act in their 'clicked' handler.
function clickToggle(toggle) {
    if (toggle.toggle_mode)
        toggle.checked = !toggle.checked;
    toggle.emit('clicked', Clutter.BUTTON_PRIMARY);
}

function tile(cols, rows, extraClass = '') {
    return new St.Widget({
        style_class: `parchaos-controls-tile ${extraClass}`,
        width: cols * CELL + (cols - 1) * GAP,
        height: rows * CELL + (rows - 1) * GAP,
        layout_manager: new Clutter.BinLayout(),
    });
}

// A round icon button whose "on" state follows a Quick Settings toggle.
// With a string instead of a toggle, it's a plain action button.
function circleFor(source, size, onActivate) {
    const circle = new St.Button({
        style_class: 'parchaos-controls-circle',
        width: size,
        height: size,
        can_focus: true,
        child: new St.Icon({style_class: 'parchaos-controls-circle-icon'}),
    });
    if (typeof source === 'string') {
        circle.child.icon_name = source;
    } else {
        const sync = () => {
            circle.child.icon_name = source.icon_name || source.iconName || 'emblem-system-symbolic';
            if (source.checked)
                circle.add_style_pseudo_class('checked');
            else
                circle.remove_style_pseudo_class('checked');
        };
        source.connectObject('notify::checked', sync, 'notify::icon-name', sync, circle);
        sync();
    }
    circle.connect('clicked', () => (onActivate ?? (() => clickToggle(source)))());
    return circle;
}

function labels(title, subtitle) {
    const box = new St.BoxLayout({
        orientation: Clutter.Orientation.VERTICAL,
        y_align: Clutter.ActorAlign.CENTER,
        x_expand: true,
    });
    const t = new St.Label({style_class: 'parchaos-controls-title', text: title ?? ''});
    const s = new St.Label({style_class: 'parchaos-controls-subtitle', text: subtitle ?? ''});
    t.clutter_text.ellipsize = s.clutter_text.ellipsize = 3;
    box.add_child(t);
    box.add_child(s);
    return {box, t, s};
}

// One row of the connectivity tile: circle toggle + title/subtitle. The
// text opens the matching Settings panel.
function connectivityRow(source, settingsPanel, close) {
    const row = new St.BoxLayout({style_class: 'parchaos-controls-row', x_expand: true});
    row.add_child(circleFor(source, 32));
    const {box, t, s} = labels();
    const text = new St.Button({child: box, x_expand: true, style_class: 'parchaos-controls-row-text'});
    const sync = () => {
        t.text = source.title ?? '';
        s.text = source.subtitle || (source.checked ? 'On' : 'Off');
    };
    source.connectObject('notify::title', sync, 'notify::subtitle', sync,
        'notify::checked', sync, row);
    sync();
    text.connect('clicked', () => {
        close();
        openSettings(settingsPanel);
    });
    row.add_child(text);
    return row;
}

function smallToggle(source, label, onActivate) {
    const t = tile(1, 1, 'parchaos-controls-small');
    const box = new St.BoxLayout({
        orientation: Clutter.Orientation.VERTICAL,
        x_align: Clutter.ActorAlign.CENTER,
        y_align: Clutter.ActorAlign.CENTER,
    });
    const circle = circleFor(source, 36, onActivate);
    circle.x_align = Clutter.ActorAlign.CENTER;
    box.add_child(circle);
    const l = new St.Label({style_class: 'parchaos-controls-small-label', text: label});
    l.clutter_text.ellipsize = 3;
    l.x_align = Clutter.ActorAlign.CENTER;
    box.add_child(l);
    t.add_child(box);
    return t;
}

// A plain action button in a small tile (not bound to a toggle).
function smallAction(iconName, label, onActivate) {
    return smallToggle(iconName, label, onActivate);
}

function sliderTile(title, iconName) {
    const t = tile(4, 1, 'parchaos-controls-slider-tile');
    const box = new St.BoxLayout({
        orientation: Clutter.Orientation.VERTICAL,
        x_expand: true,
        y_align: Clutter.ActorAlign.CENTER,
    });
    box.add_child(new St.Label({style_class: 'parchaos-controls-title', text: title}));
    const row = new St.BoxLayout({style_class: 'parchaos-controls-slider-row', x_expand: true});
    const icon = new St.Button({
        style_class: 'parchaos-controls-slider-icon',
        child: new St.Icon({icon_name: iconName}),
    });
    const slider = new Slider(0);
    slider.x_expand = true;
    slider.add_style_class_name('parchaos-controls-slider');
    row.add_child(icon);
    row.add_child(slider);
    box.add_child(row);
    t.add_child(box);
    return {tile: t, slider, icon};
}

// MprisSource has no destroy(): each instance keeps its D-Bus proxy and
// name-owner subscription for good. Keep a single one for the whole shell
// process (this module is only evaluated once, so it survives the
// disable/enable cycle around the lock screen) instead of one per open.
let _mediaSource = null;
function mediaSource() {
    _mediaSource ??= new Mpris.MprisSource();
    return _mediaSource;
}

// Where each control shows up in the picker beside the panel in edit mode.
const ITEM_META = {
    'connectivity': {category: 'Connectivity', icon: 'network-wireless-symbolic'},
    'media': {category: 'Sound and Media', icon: 'audio-x-generic-symbolic'},
    'focus': {category: 'Focus', icon: 'notifications-disabled-symbolic'},
    'dark-mode': {category: 'Display', icon: 'weather-clear-night-symbolic'},
    'night-light': {category: 'Display', icon: 'night-light-symbolic'},
    'display': {category: 'Display', icon: 'display-brightness-symbolic'},
    'sound': {category: 'Sound and Media', icon: 'audio-volume-high-symbolic'},
    'power': {category: 'System', icon: 'power-profile-balanced-symbolic'},
    'screenshot': {category: 'Shortcuts', icon: 'applets-screenshooter-symbolic'},
    'settings': {category: 'Shortcuts', icon: 'emblem-system-symbolic'},
    'lock': {category: 'Shortcuts', icon: 'system-lock-screen-symbolic'},
    'external': {category: 'Other', icon: 'application-x-addon-symbolic'},
};

const ControlsPanel = GObject.registerClass({
    Signals: {'request-close': {}, 'edit-changed': {}, 'items-changed': {}},
}, class ControlsPanel extends St.BoxLayout {
    _init(qs) {
        super._init({
            style_class: 'parchaos-controls-panel',
            orientation: Clutter.Orientation.VERTICAL,
        });
        applyStyleClass(this, styleSettings());
        // Light or dark panel, following the system appearance (and the
        // Dark Mode tile in this panel, live).
        this._interface = new Gio.Settings({schema_id: 'org.gnome.desktop.interface'});
        const syncScheme = () => {
            if (this._interface.get_string('color-scheme') === 'prefer-dark')
                this.remove_style_class_name('parchaos-light');
            else
                this.add_style_class_name('parchaos-light');
        };
        const schemeId = this._interface.connect('changed::color-scheme', syncScheme);
        this.connect('destroy', () => {
            this._interface.disconnect(schemeId);
            this._endDrag();
        });
        syncScheme();
        this._qs = qs;
        this.add_effect(new Shell.BlurEffect({
            radius: 60,
            brightness: 0.9,
            mode: Shell.BlurMode.BACKGROUND,
        }));

        this._desktop = styleSettings();
        this._grid = new St.Widget({layout_manager: new Clutter.GridLayout({
            row_spacing: GAP,
            column_spacing: GAP,
        })});
        this.add_child(this._grid);

        // Every tile is an item with a stable id, so the order and the hidden
        // ones can be saved (Edit Controls).
        this._items = [];
        const add = (id, name, cols, rows, widget) => {
            if (widget) {
                const meta = ITEM_META[id] ?? ITEM_META.external;
                this._items.push({id, name, cols, rows, widget, hidden: false,
                    category: meta.category, icon: meta.icon});
            }
        };

        add('connectivity', 'Network', 2, 2, this._connectivityTile());
        add('media', 'Now playing', 2, 2, this._nowPlayingTile());

        const dnd = this._firstItem(qs._doNotDisturb);
        if (dnd)
            add('focus', 'Focus', 2, 1, this._focusTile(dnd));
        // GNOME's own dark style toggle writes 'default' (no preference)
        // for light, which Electron/Chromium apps treat as "keep guessing"
        // and can stay dark or light. Write an explicit preference both
        // ways; the toggle still mirrors the state.
        const dark = this._firstItem(qs._darkMode);
        if (dark) {
            add('dark-mode', 'Dark Mode', 1, 1, smallToggle(dark, 'Dark Mode', () => {
                Main.layoutManager.screenTransition.run();
                const iface = new Gio.Settings({schema_id: 'org.gnome.desktop.interface'});
                iface.set_string('color-scheme', dark.checked ? 'prefer-light' : 'prefer-dark');
            }));
        }
        const night = this._firstItem(qs._nightLight);
        if (night)
            add('night-light', 'Night Light', 1, 1, smallToggle(night, 'Night Light'));

        add('display', 'Display', 4, 1, this._displayTile());
        add('sound', 'Sound', 4, 1, this._soundTile());

        // Toggles other extensions add to Quick Settings (e.g. GSConnect's
        // Mobile Devices).
        this._externalItems().forEach((item, i) =>
            add(`external:${item.title ?? i}`, item.title ?? 'Extra', 2, 1, this._externalTile(item)));

        // Small tiles: power mode (when the machine has profiles), then
        // screenshot, settings and lock.
        const power = this._firstItem(qs._powerProfiles);
        if (power?.visible) {
            add('power', 'Power Mode', 1, 1, smallToggle(power, 'Power Mode', () => {
                this.emit('request-close');
                openSettings('power');
            }));
        }
        add('screenshot', 'Screenshot', 1, 1, smallAction('applets-screenshooter-symbolic', 'Screenshot', () => {
            this.emit('request-close');
            // Let the menu close before the screenshot UI grabs input.
            GLib.timeout_add(GLib.PRIORITY_DEFAULT, 250, () => {
                Main.screenshotUI.open().catch(logError);
                return GLib.SOURCE_REMOVE;
            });
        }));
        add('settings', 'Settings', 1, 1, smallAction('emblem-system-symbolic', 'Settings', () => {
            this.emit('request-close');
            openSettings();
        }));
        add('lock', 'Lock', 1, 1, smallAction('system-lock-screen-symbolic', 'Lock', () => {
            this.emit('request-close');
            Main.screenShield?.lock(true);
        }));

        // Edit Controls: hide tiles and put them in another order.
        this._editing = false;
        this._canEdit = !!this._desktop?.settings_schema.has_key('controls-order') &&
            !!this._desktop?.settings_schema.has_key('controls-hidden');
        for (const item of this._items)
            this._addEditButtons(item);
        this._editButton = new St.Button({
            style_class: 'parchaos-controls-edit',
            label: 'Edit Controls',
            x_align: Clutter.ActorAlign.CENTER,
            can_focus: true,
            visible: this._canEdit,
        });
        this._editButton.connect('clicked', () => this._setEditing(!this._editing));
        this.add_child(this._editButton);
        this._layout();
    }

    // Edit mode (like rearranging apps on a phone): each tile gets a round
    // badge on its corner, - to hide it or + to bring a hidden one back, and
    // tiles are dragged to a new place.
    _addEditButtons(item) {
        const badge = new St.Button({
            style_class: 'parchaos-controls-edit-badge',
            label: '\u2212',
            x_align: Clutter.ActorAlign.START,
            y_align: Clutter.ActorAlign.START,
            x_expand: true,
            y_expand: true,
            can_focus: true,
            visible: false,
        });
        badge.set_translation(-7, -7, 0);
        badge.connect('clicked', () => this._toggleHidden(item));
        item.badge = badge;
        item.widget.add_child(badge);
        item.widget.set_pivot_point(0.5, 0.5);
        this._attachDrag(item);
    }

    // The tile under a point, for dragging and dropping.
    _itemAt(x, y) {
        return this._items.find(item => {
            if (!item.widget.mapped)
                return false;
            const [ex, ey] = item.widget.get_transformed_position();
            const [w, h] = item.widget.get_transformed_size();
            return x >= ex && x < ex + w && y >= ey && y < ey + h;
        });
    }

    // While editing, a clear layer over each tile takes the pointer, so a
    // tile's own button does not fire and the tile can be dragged. The badge
    // sits above it and keeps its own click.
    _attachDrag(item) {
        const overlay = new St.Widget({
            reactive: false,
            visible: false,
            x_expand: true,
            y_expand: true,
        });
        item.overlay = overlay;
        item.widget.insert_child_below(overlay, item.badge);
        overlay.connect('button-press-event', (_o, event) => {
            if (event.get_button() !== 1)
                return Clutter.EVENT_PROPAGATE;
            const [x, y] = event.get_coords();
            this._drag = {item, x, y, moved: false, target: null, grab: global.stage.grab(overlay)};
            return Clutter.EVENT_STOP;
        });
        overlay.connect('motion-event', (_o, event) => {
            const drag = this._drag;
            if (!drag || drag.item !== item)
                return Clutter.EVENT_PROPAGATE;
            const [x, y] = event.get_coords();
            if (!drag.moved && Math.hypot(x - drag.x, y - drag.y) < 8)
                return Clutter.EVENT_STOP;
            if (!drag.moved) {
                drag.moved = true;
                item.widget.get_parent()?.set_child_above_sibling(item.widget, null);
                item.widget.remove_all_transitions();
                item.widget.rotation_angle_z = 0;
                item.widget.add_style_pseudo_class('drag');
            }
            item.widget.set_translation(x - drag.x, y - drag.y, 0);
            const over = this._itemAt(x, y);
            const target = over && over !== item ? over : null;
            if (target !== drag.target) {
                drag.target?.widget.remove_style_pseudo_class('drop');
                target?.widget.add_style_pseudo_class('drop');
                drag.target = target;
            }
            return Clutter.EVENT_STOP;
        });
        overlay.connect('button-release-event', () => {
            const drag = this._drag;
            if (!drag || drag.item !== item)
                return Clutter.EVENT_PROPAGATE;
            this._endDrag();
            return Clutter.EVENT_STOP;
        });
    }

    _endDrag() {
        const drag = this._drag;
        this._drag = null;
        if (!drag)
            return;
        drag.grab?.dismiss();
        drag.item.widget.remove_style_pseudo_class('drag');
        drag.target?.widget.remove_style_pseudo_class('drop');
        drag.item.widget.set_translation(0, 0, 0);
        if (drag.moved && drag.target)
            this._moveTo(drag.item, drag.target);
        else
            this._wiggle(drag.item);
    }

    // Put `item` where `target` is, the others shifting along. A hidden tile
    // dropped among the shown ones is shown again; dropped on a hidden one it
    // stays hidden.
    _moveTo(item, target) {
        const ordered = this._ordered();
        ordered.splice(ordered.indexOf(item), 1);
        ordered.splice(ordered.indexOf(target), 0, item);
        item.hidden = target.hidden;
        this._save(ordered);
        this._layout();
    }

    // A slight, endless tilt on every tile while editing.
    _wiggle(item) {
        const widget = item.widget;
        widget.remove_all_transitions();
        widget.rotation_angle_z = 0;
        if (!this._editing || item.hidden)
            return;
        const swing = (angle) => {
            if (!this._editing || widget.is_finalized?.())
                return;
            widget.ease({
                rotation_angle_z: angle,
                duration: 110 + Math.floor(Math.random() * 40),
                mode: Clutter.AnimationMode.EASE_IN_OUT_SINE,
                onComplete: () => swing(-angle),
            });
        };
        swing(Math.random() < 0.5 ? 0.9 : -0.9);
    }

    // Items in the saved order; ones the saved order does not know keep their
    // default place after it.
    _ordered() {
        const saved = this._canEdit ? this._desktop.get_strv('controls-order') : [];
        const hidden = new Set(this._canEdit ? this._desktop.get_strv('controls-hidden') : []);
        const byId = new Map(this._items.map(i => [i.id, i]));
        const ordered = saved.filter(id => byId.has(id)).map(id => byId.get(id));
        for (const item of this._items) {
            if (!ordered.includes(item))
                ordered.push(item);
        }
        for (const item of ordered)
            item.hidden = hidden.has(item.id);
        return ordered;
    }

    _layout() {
        const grid = this._grid;
        const lm = grid.layout_manager;
        for (const child of grid.get_children())
            grid.remove_child(child);
        const taken = [];
        const isFree = (c, r, w, h) => {
            if (c + w > 4)
                return false;
            for (let y = r; y < r + h; y++) {
                for (let x = c; x < c + w; x++) {
                    if (taken[y]?.[x])
                        return false;
                }
            }
            return true;
        };
        const ordered = this._ordered();
        // Hidden tiles wait at the end while editing, dimmed, with a +.
        const sequence = [...ordered.filter(i => !i.hidden), ...ordered.filter(i => i.hidden)];
        for (const item of sequence) {
            if (item.hidden && !this._editing)
                continue;
            let placed = false;
            for (let r = 0; !placed; r++) {
                for (let c = 0; c < 4 && !placed; c++) {
                    if (!isFree(c, r, item.cols, item.rows))
                        continue;
                    for (let y = r; y < r + item.rows; y++) {
                        taken[y] ??= [];
                        for (let x = c; x < c + item.cols; x++)
                            taken[y][x] = true;
                    }
                    lm.attach(item.widget, c, r, item.cols, item.rows);
                    placed = true;
                }
            }
            item.badge.visible = this._editing;
            item.overlay.visible = this._editing;
            item.overlay.reactive = this._editing;
            item.badge.label = item.hidden ? '+' : '\u2212';
            item.widget.opacity = item.hidden ? 110 : 255;
            item.widget.set_translation(0, 0, 0);
            this._wiggle(item);
        }
    }

    _setEditing(editing) {
        this._editing = editing;
        this._endDrag();
        this._editButton.label = editing ? 'Done' : 'Edit Controls';
        // The picker has its own Done.
        this._editButton.visible = this._canEdit && !editing;
        this._layout();
        this.emit('edit-changed');
    }

    get editing() {
        return this._editing;
    }

    finishEditing() {
        this._setEditing(false);
    }

    // The controls not shown in the panel, for the picker.
    availableItems() {
        this._ordered();
        return this._items.filter(i => i.hidden);
    }

    // Put a control from the picker back into the panel.
    addItem(item) {
        const ordered = this._ordered();
        item.hidden = false;
        this._save(ordered);
        this._layout();
        this.emit('items-changed');
    }

    _save(ordered) {
        this._desktop.set_strv('controls-order', ordered.map(i => i.id));
        this._desktop.set_strv('controls-hidden', ordered.filter(i => i.hidden).map(i => i.id));
    }

    _toggleHidden(item) {
        const ordered = this._ordered();
        item.hidden = !item.hidden;
        this._save(ordered);
        this._layout();
        this.emit('items-changed');
    }

    // Quick Settings keeps no list of extension-added items; they're the
    // grid's toggles that don't belong to one of its own indicators.
    _externalItems() {
        const qs = this._qs;
        const grid = qs.menu?._grid;
        if (!grid)
            return [];
        const known = new Set();
        for (const [key, value] of Object.entries(qs)) {
            if (key.startsWith('_') && Array.isArray(value?.quickSettingsItems))
                value.quickSettingsItems.forEach(item => known.add(item));
        }
        return grid.get_children().filter(c =>
            !known.has(c) && c.visible && typeof c.checked === 'boolean' && 'title' in c);
    }

    // The extension that added a Quick Settings item, so its name can open
    // that extension's settings.
    _ownerOf(item) {
        // GJS names an extension's GObject classes after its UUID, e.g.
        // Gjs_gsconnect_andyholmes_github_io_extension_ServiceToggle.
        const typeName = item.constructor?.$gtype?.name ?? '';
        for (const ext of Main.extensionManager._extensions?.values() ?? []) {
            if (typeName.startsWith(`Gjs_${ext.uuid.replace(/[@.]/g, '_')}_`))
                return ext.uuid;
        }
        // Extensions that set their own GTypeName usually prefix it with
        // their name (GSConnectServiceIndicator for gsconnect@...).
        const lower = typeName.toLowerCase();
        for (const ext of Main.extensionManager._extensions?.values() ?? []) {
            const name = ext.uuid.split('@')[0].toLowerCase().replace(/[^a-z0-9]/g, '');
            if (name.length >= 4 && lower.startsWith(name))
                return ext.uuid;
        }
        for (const ext of Main.extensionManager._extensions?.values() ?? []) {
            const obj = ext.stateObj;
            if (!obj)
                continue;
            for (const value of Object.values(obj)) {
                if (value?.quickSettingsItems?.includes?.(item))
                    return ext.uuid;
            }
        }
        return null;
    }

    _externalTile(item) {
        const t = tile(2, 1, 'parchaos-controls-focus');
        const row = new St.BoxLayout({x_expand: true, y_align: Clutter.ActorAlign.CENTER});
        row.add_child(circleFor(item, 32));
        const {box, t: title, s} = labels();
        const sync = () => {
            title.text = item.title ?? '';
            s.text = item.subtitle || (item.checked ? 'On' : 'Off');
        };
        item.connectObject('notify::title', sync, 'notify::subtitle', sync,
            'notify::checked', sync, row);
        sync();
        const text = new St.Button({child: box, x_expand: true, style_class: 'parchaos-controls-row-text'});
        text.connect('clicked', () => {
            const uuid = this._ownerOf(item);
            if (uuid) {
                this.emit('request-close');
                Main.extensionManager.openExtensionPrefs(uuid, '', {});
            } else {
                clickToggle(item);
            }
        });
        row.add_child(text);
        t.add_child(row);
        return t;
    }

    _firstItem(indicator) {
        return indicator?.quickSettingsItems?.[0] ?? null;
    }

    _connectivityTile() {
        const t = tile(2, 2, 'parchaos-controls-connectivity');
        const box = new St.BoxLayout({
            orientation: Clutter.Orientation.VERTICAL,
            style_class: 'parchaos-controls-connectivity-box',
            x_expand: true,
            y_align: Clutter.ActorAlign.CENTER,
        });
        const net = this._qs._network;
        const rows = [];
        const wifi = net?._wirelessToggle;
        const wired = net?._wiredToggle;
        if (wifi?.visible)
            rows.push([wifi, 'wifi']);
        else if (wired?.visible)
            rows.push([wired, 'network']);
        const bt = this._firstItem(this._qs._bluetooth);
        if (bt?.visible)
            rows.push([bt, 'bluetooth']);
        if (wifi?.visible && wired?.visible)
            rows.push([wired, 'network']);
        const vpn = net?._vpnToggle;
        if (vpn?.visible && rows.length < 3)
            rows.push([vpn, 'network']);
        const airplane = this._firstItem(this._qs._rfkill);
        if (airplane?.visible && rows.length < 3)
            rows.push([airplane, 'wifi']);
        for (const [source, panel] of rows.slice(0, 3)) {
            box.add_child(connectivityRow(source, panel, () => this.emit('request-close')));
        }
        if (rows.length === 0)
            box.add_child(new St.Label({style_class: 'parchaos-controls-subtitle', text: 'No network devices'}));
        t.add_child(box);
        return t;
    }

    _focusTile(dnd) {
        const t = tile(2, 1, 'parchaos-controls-focus');
        const row = new St.BoxLayout({x_expand: true, y_align: Clutter.ActorAlign.CENTER});
        row.add_child(circleFor(dnd, 32));
        const {box, t: title, s} = labels('Focus', '');
        const sync = () => (s.text = dnd.checked ? 'Do Not Disturb' : 'Off');
        dnd.connectObject('notify::checked', sync, row);
        sync();
        const text = new St.Button({child: box, x_expand: true, style_class: 'parchaos-controls-row-text'});
        text.connect('clicked', () => clickToggle(dnd));
        row.add_child(text);
        t.add_child(row);
        void title;
        return t;
    }

    _displayTile() {
        const scale = Main.brightnessManager?.globalScale;
        if (!scale)
            return null;
        const {tile: t, slider} = sliderTile('Display', 'display-brightness-symbolic');
        let block = false;
        const fromScale = () => {
            block = true;
            slider.value = scale.value;
            block = false;
        };
        scale.connectObject('notify::value', fromScale, t);
        fromScale();
        slider.connect('notify::value', () => {
            if (!block)
                scale.value = slider.value;
        });
        return t;
    }

    _soundTile() {
        const source = this._qs._volumeOutput?._output;
        if (!source?.slider)
            return null;
        const {tile: t, slider, icon} = sliderTile('Sound', 'audio-volume-high-symbolic');
        let block = false;
        const fromSource = () => {
            block = true;
            slider.maximum_value = source.slider.maximum_value;
            slider.value = source.slider.value;
            icon.child.icon_name = source.icon_name || source.iconName || 'audio-volume-high-symbolic';
            block = false;
        };
        source.slider.connectObject('notify::value', fromSource, t);
        source.connectObject('notify::icon-name', fromSource, t);
        fromSource();
        slider.connect('notify::value', () => {
            if (!block)
                source.slider.value = slider.value;
        });
        // Icon click mutes/unmutes, same as Quick Settings.
        icon.connect('clicked', () => source.emit('icon-clicked'));
        return t;
    }

    _nowPlayingTile() {
        const t = tile(2, 2, 'parchaos-controls-media');
        const box = new St.BoxLayout({
            orientation: Clutter.Orientation.VERTICAL,
            style_class: 'parchaos-controls-media-box',
            x_expand: true,
            y_expand: true,
        });
        const art = new St.Bin({style_class: 'parchaos-controls-media-art', width: 44, height: 44});
        const {box: text, t: title, s: artist} = labels();
        const top = new St.BoxLayout({style_class: 'parchaos-controls-media-top'});
        top.add_child(art);
        top.add_child(text);
        const controls = new St.BoxLayout({
            style_class: 'parchaos-controls-media-controls',
            x_align: Clutter.ActorAlign.CENTER,
            y_expand: true,
            y_align: Clutter.ActorAlign.END,
        });
        const mk = name => {
            const b = new St.Button({
                style_class: 'parchaos-controls-media-button',
                child: new St.Icon({icon_name: name}),
                can_focus: true,
            });
            controls.add_child(b);
            return b;
        };
        const prev = mk('media-skip-backward-symbolic');
        const play = mk('media-playback-start-symbolic');
        const next = mk('media-skip-forward-symbolic');
        box.add_child(top);
        box.add_child(controls);
        t.add_child(box);

        const source = mediaSource();
        let player = null;
        // Replacing a St.Bin's child only unparents the old one; destroy it
        // so icons with destroy handlers aren't left to the GC sweep.
        const setArt = actor => {
            art.child?.destroy();
            art.child = actor;
        };
        const sync = () => {
            const players = source.players;
            const newPlayer = players.find(p => p.status === 'Playing') ?? players[0] ?? null;
            if (newPlayer !== player) {
                player?.disconnectObject(t);
                player = newPlayer;
                player?.connectObject('changed', sync, t);
            }
            if (!player) {
                title.text = 'Not Playing';
                artist.text = '';
                setArt(new St.Icon({icon_name: 'audio-x-generic-symbolic', icon_size: 24}));
                controls.opacity = 90;
                controls.reactive = false;
                return;
            }
            controls.opacity = 255;
            controls.reactive = true;
            title.text = player.trackTitle || player.app?.get_name() || 'Unknown';
            artist.text = (player.trackArtists ?? []).join(', ');
            const url = player.trackCoverUrl;
            if (url) {
                setArt(new St.Icon({gicon: new Gio.FileIcon({file: Gio.File.new_for_uri(url)}), icon_size: 44}));
            } else {
                const appIcon = player.app?.create_icon_texture(44);
                setArt(appIcon ?? new St.Icon({icon_name: 'audio-x-generic-symbolic', icon_size: 24}));
            }
            play.child.icon_name = player.status === 'Playing'
                ? 'media-playback-pause-symbolic' : 'media-playback-start-symbolic';
            prev.reactive = player.canGoPrevious !== false;
            next.reactive = player.canGoNext !== false;
        };
        source.connectObject('player-added', sync, 'player-removed', sync, t);
        prev.connect('clicked', () => player?.previous());
        play.connect('clicked', () => player?.playPause());
        next.connect('clicked', () => player?.next());
        art.reactive = true;
        art.connect('button-release-event', () => {
            if (player) {
                player.raise();
                this.emit('request-close');
            }
            return Clutter.EVENT_STOP;
        });
        // MprisSource finds players asynchronously; sync once it has.
        let syncId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 150, () => {
            syncId = 0;
            sync();
            return GLib.SOURCE_REMOVE;
        });
        sync();
        t.connect('destroy', () => {
            if (syncId)
                GLib.source_remove(syncId);
            player?.disconnectObject(t);
            source.disconnectObject(t);
        });
        return t;
    }
});


// ---------------------------------------------------------------------
// The picker beside the panel in edit mode (ticket #148): a search box, the
// categories of controls, a gallery of the controls that are not in the
// panel, and Done. Clicking a control puts it back in the panel.
// ---------------------------------------------------------------------
const ControlsPicker = GObject.registerClass(
class ControlsPicker extends St.BoxLayout {
    _init(panel) {
        super._init({
            style_class: 'parchaos-controls-panel parchaos-controls-picker',
            orientation: Clutter.Orientation.VERTICAL,
        });
        this._panel = panel;
        this._category = null;
        this._query = '';
        applyStyleClass(this, styleSettings());
        if (panel.has_style_class_name('parchaos-light'))
            this.add_style_class_name('parchaos-light');
        this.add_effect(new Shell.BlurEffect({radius: 60, brightness: 0.9, mode: Shell.BlurMode.BACKGROUND}));

        this._search = new St.Entry({
            style_class: 'parchaos-controls-search',
            hint_text: 'Search Controls',
            can_focus: true,
        });
        this._search.clutter_text.connect('text-changed', () => {
            this._query = this._search.get_text().trim().toLowerCase();
            this._refresh();
        });
        this.add_child(this._search);

        const body = new St.BoxLayout({style_class: 'parchaos-controls-picker-body', x_expand: true, y_expand: true});
        this._categories = new St.BoxLayout({
            style_class: 'parchaos-controls-categories',
            orientation: Clutter.Orientation.VERTICAL,
        });
        this._gallery = new St.BoxLayout({
            style_class: 'parchaos-controls-gallery',
            orientation: Clutter.Orientation.VERTICAL,
            x_expand: true,
        });
        body.add_child(this._categories);
        body.add_child(new St.ScrollView({
            child: this._gallery,
            x_expand: true,
            y_expand: true,
            overlay_scrollbars: true,
            style_class: 'parchaos-controls-gallery-scroll',
        }));
        this.add_child(body);

        const footer = new St.BoxLayout({style_class: 'parchaos-controls-picker-footer'});
        footer.add_child(new St.Label({
            text: 'Click a control to put it in Control Center.',
            style_class: 'parchaos-controls-picker-hint',
            x_expand: true,
            y_align: Clutter.ActorAlign.CENTER,
        }));
        const done = new St.Button({style_class: 'parchaos-controls-done', label: 'Done', can_focus: true});
        done.connect('clicked', () => this._panel.finishEditing());
        footer.add_child(done);
        this.add_child(footer);

        panel.connect('items-changed', () => this._refresh());
    }

    open() {
        this._query = '';
        this._search.set_text('');
        this._category = null;
        this._refresh();
        this.show();
    }

    _refresh() {
        const available = this._panel.availableItems();
        const names = [...new Set(available.map(i => i.category))];
        this._categories.destroy_all_children();
        const addCategory = (label, value) => {
            const b = new St.Button({
                style_class: 'parchaos-controls-category',
                label,
                x_align: Clutter.ActorAlign.FILL,
                can_focus: true,
                toggle_mode: false,
            });
            if (this._category === value)
                b.add_style_pseudo_class('active');
            b.connect('clicked', () => {
                this._category = value;
                this._refresh();
            });
            this._categories.add_child(b);
        };
        addCategory('All Controls', null);
        for (const name of names)
            addCategory(name, name);

        this._gallery.destroy_all_children();
        const shown = available.filter(i =>
            (!this._category || i.category === this._category) &&
            (!this._query || i.name.toLowerCase().includes(this._query) ||
                i.category.toLowerCase().includes(this._query)));
        if (available.length === 0) {
            this._gallery.add_child(new St.Label({
                text: 'Everything is already in Control Center.',
                style_class: 'parchaos-controls-picker-hint',
            }));
            return;
        }
        if (shown.length === 0) {
            this._gallery.add_child(new St.Label({
                text: 'No controls match.',
                style_class: 'parchaos-controls-picker-hint',
            }));
            return;
        }
        for (const category of [...new Set(shown.map(i => i.category))]) {
            this._gallery.add_child(new St.Label({text: category, style_class: 'parchaos-controls-gallery-heading'}));
            const row = new St.BoxLayout({style_class: 'parchaos-controls-gallery-row'});
            for (const item of shown.filter(i => i.category === category)) {
                const cell = new St.Button({
                    style_class: 'parchaos-controls-gallery-item',
                    can_focus: true,
                    child: new St.BoxLayout({orientation: Clutter.Orientation.VERTICAL}),
                });
                const inner = cell.child;
                inner.add_child(new St.Icon({icon_name: item.icon, style_class: 'parchaos-controls-gallery-icon'}));
                inner.add_child(new St.Label({text: item.name, style_class: 'parchaos-controls-gallery-label'}));
                cell.connect('clicked', () => this._panel.addItem(item));
                row.add_child(cell);
            }
            this._gallery.add_child(row);
        }
    }
});

const ControlsButton = GObject.registerClass(
class ControlsButton extends PanelMenu.Button {
    _init(ext) {
        super._init(0.5, 'Parcha Controls', false);
        this.add_style_class_name('parchaos-controls-button');
        this._box = new St.BoxLayout({style_class: 'panel-status-indicators-box'});
        this.add_child(this._box);
        this._glyph = new St.Icon({
            gicon: Gio.icon_new_for_string(`${ext.path}/icons/parchaos-controls-symbolic.svg`),
            style_class: 'system-status-icon',
        });

        this.menu.actor.add_style_class_name('parchaos-controls-popup');
        // PopupMenu won't open an empty menu, so keep a holder in it and
        // fill it each time it opens.
        this._holder = new St.Bin();
        this.menu.box.add_child(this._holder);
        this.menu.connect('open-state-changed', (_m, open) => {
            if (open)
                this._build();
        });
        this.menu.connect('menu-closed', () => this._destroyPanel());
    }

    // GNOME's status icons (network, volume, battery...) stay in the top
    // bar; they move into this button, followed by our glyph.
    adoptIndicators(qs) {
        this._qs = qs;
        this._indicators = qs._indicators;
        this._indicators.get_parent()?.remove_child(this._indicators);
        this._box.add_child(this._indicators);
        this._box.add_child(this._glyph);
    }

    releaseIndicators() {
        if (!this._indicators)
            return;
        this._box.remove_child(this._indicators);
        this._qs.add_child(this._indicators);
        this._indicators = null;
    }

    _build() {
        this._destroyPanel();
        this._panel = new ControlsPanel(this._qs);
        this._panel.connect('request-close', () => this.menu.close());
        // In edit mode a picker sits to the left of the panel.
        this._row = new St.BoxLayout({style_class: 'parchaos-controls-row-holder'});
        this._picker = new ControlsPicker(this._panel);
        this._picker.hide();
        this._row.add_child(this._picker);
        this._row.add_child(this._panel);
        this._panel.connect('edit-changed', () => {
            if (this._panel.editing)
                this._picker.open();
            else
                this._picker.hide();
        });
        this._holder.set_child(this._row);
    }

    _destroyPanel() {
        this._row?.destroy();
        this._row = null;
        this._picker = null;
        this._panel = null;
    }

    destroy() {
        this.releaseIndicators();
        this._destroyPanel();
        super.destroy();
    }
});

// A tiny D-Bus method for the Screenshot app in the app grid (ticket #130):
// GNOME Shell's capture tool can only be opened from inside the Shell, and
// the old standalone screenshot app cannot reach it on Wayland.
const SHELL_BUS_XML = `<node><interface name="org.parchaos.Shell">
  <method name="OpenScreenshotUI"/>
</interface></node>`;

export default class ParchaControlsExtension extends Extension {
    _exportShellBus() {
        this._shellBus = Gio.DBusExportedObject.wrapJSObject(SHELL_BUS_XML, {
            OpenScreenshotUI() {
                // Let the app that asked finish closing before the tool grabs input.
                GLib.timeout_add(GLib.PRIORITY_DEFAULT, 250, () => {
                    Main.screenshotUI.open().catch(logError);
                    return GLib.SOURCE_REMOVE;
                });
            },
        });
        this._shellBus.export(Gio.DBus.session, '/org/parchaos/Shell');
        this._shellBusName = Gio.bus_own_name_on_connection(
            Gio.DBus.session, 'org.parchaos.Shell', Gio.BusNameOwnerFlags.NONE, null, null);
    }

    enable() {
        this._exportShellBus();
        this._injections = new InjectionManager();
        this._waitId = 0;
        // Quick Settings builds its indicators asynchronously at startup.
        const tryInit = () => {
            const qs = Main.panel.statusArea.quickSettings;
            if (!qs?._indicators || !qs._volumeOutput) {
                this._waitId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 200, () => {
                    this._waitId = 0;
                    tryInit();
                    return GLib.SOURCE_REMOVE;
                });
                return;
            }
            this._setup(qs);
        };
        tryInit();
    }

    _setup(qs) {
        this._qs = qs;
        this._button = new ControlsButton(this);
        this._button.adoptIndicators(qs);
        const box = qs.get_parent();
        const index = box.get_children().indexOf(qs);
        const boxName = box === Main.panel._leftBox ? 'left'
            : box === Main.panel._centerBox ? 'center' : 'right';
        Main.panel.addToStatusArea('parchaos-controls', this._button, Math.max(index, 0), boxName);
        qs.container.hide();
        qs.container.connectObject('notify::visible', () => {
            if (qs.container.visible)
                qs.container.hide();
        }, this);

        const button = this._button;
        this._injections.overrideMethod(Main.panel, 'toggleQuickSettings', () => function () {
            button.menu.toggle();
        });
        this._injections.overrideMethod(Main.panel, 'closeQuickSettings', () => function () {
            button.menu.close();
        });
    }

    disable() {
        this._shellBus?.unexport();
        this._shellBus = null;
        if (this._shellBusName) {
            Gio.bus_unown_name(this._shellBusName);
            this._shellBusName = 0;
        }
        if (this._waitId) {
            GLib.source_remove(this._waitId);
            this._waitId = 0;
        }
        this._injections?.clear();
        this._injections = null;
        this._button?.destroy();
        this._button = null;
        this._qs?.container.disconnectObject(this);
        this._qs?.container.show();
        this._qs = null;
    }
}
