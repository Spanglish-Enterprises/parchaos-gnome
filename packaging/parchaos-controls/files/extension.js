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
import Graphene from 'gi://Graphene';
import Shell from 'gi://Shell';
import St from 'gi://St';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import * as Mpris from 'resource:///org/gnome/shell/ui/mpris.js';
import {Slider} from 'resource:///org/gnome/shell/ui/slider.js';
import * as Location from 'resource:///org/gnome/shell/ui/status/location.js';
import {Extension, InjectionManager} from 'resource:///org/gnome/shell/extensions/extension.js';

// ParchaOS glass (parchaos-glass): our own refractive glass for the tiles. Optional: without it
// the panel keeps its plain look.
const GLASS_JS = GLib.getenv('PARCHAOS_GLASS_JS') ?? '/usr/share/parchaos-glass/glass.js';
let GlassPane = null;
try {
    ({GlassPane} = await import(`file://${GLASS_JS}`));
} catch (e) {
    console.log(`parchaos-controls: glass library not available (${e.message})`);
}

const CELL = 72;
const GAP = 10;
// Opening and closing Control Center, measured frame by frame on the owner's 60 fps recording
// (10.25 PM, 2026-10-01): the whole panel fades in place (no slide, no zoom, no stagger) while a
// slight blur clears; closing is a shorter fade that blurs a little on the way out. Curves are
// cubic-bezier fits of the measured fade (0.008 and 0.005 RMS); blur is the fitted gaussian
// sigma at the start (open) or end (close), in logical px.
const OPEN_MOTION = {duration: 287, c1: [0.35, 0.27], c2: [0.21, 1.0], sigma: 2};
const CLOSE_MOTION = {duration: 219, c1: [0.27, 0.66], c2: [0.32, 1.0], sigma: 1.5};

// Runs one transition on the popup: opacity follows the curve, and the blur is strongest where
// the panel is faintest (sigma x (1 - progress) opening, sigma x progress closing).
function runMotion(actor, opening, onDone) {
    const m = opening ? OPEN_MOTION : CLOSE_MOTION;
    actor._parchaosMotion?.stop();
    actor._parchaosMotion = null;
    const settings = St.Settings.get();
    if (!settings.enable_animations) {
        actor.opacity = opening ? 255 : 0;
        onDone();
        return;
    }
    let blur = actor.get_effect('parchaos-motion-blur');
    if (!blur) {
        blur = new Shell.BlurEffect({mode: Shell.BlurMode.ACTOR, brightness: 1.0});
        actor.add_effect_with_name('parchaos-motion-blur', blur);
    }
    const timeline = new Clutter.Timeline({
        actor,
        duration: Math.round(m.duration * settings.slow_down_factor),
    });
    timeline.set_progress_mode(Clutter.AnimationMode.CUBIC_BEZIER);
    timeline.set_cubic_bezier_progress(
        new Graphene.Point({x: m.c1[0], y: m.c1[1]}), new Graphene.Point({x: m.c2[0], y: m.c2[1]}));
    const apply = p => {
        const shown = opening ? p : 1 - p;
        actor.opacity = Math.round(255 * shown);
        // Shell.BlurEffect's radius is twice the gaussian sigma.
        const radius = 2 * m.sigma * (1 - shown);
        blur.radius = Math.round(radius);
        blur.enabled = radius >= 0.5;
    };
    apply(0);
    timeline.connect('new-frame', () => apply(timeline.get_progress()));
    timeline.connect('completed', () => {
        apply(1);
        blur.enabled = false;
        actor._parchaosMotion = null;
        onDone();
    });
    actor._parchaosMotion = timeline;
    timeline.start();
}

// The "recently" pill above the tiles (owner's reference): the app that last asked for the
// location ("Weather recently", opens the app) or the last screenshot ("Screenshot taken",
// shows it in the file browser). An entry stays this long.
const RECENT_SECONDS = 15 * 60;

class RecentActivity {
    constructor() {
        this._latest = null;
        // Geoclue asks the shell's agent to authorize every app that wants the location; the
        // agent object is called by method name, so wrapping the instance method is enough.
        this._agent = Location.getGeoclueAgent();
        const agent = this._agent;
        const original = agent.AuthorizeAppAsync;
        agent.AuthorizeAppAsync = (params, invocation) => {
            // Count the app only when the shell grants it the location: the reply carries the
            // decision, so the invocation is wrapped to read it on the way out.
            const [desktopId] = params;
            const reply = new Proxy(invocation, {
                get: (target, key) => {
                    if (key === 'return_value') {
                        return value => {
                            try {
                                const [granted] = value.deepUnpack();
                                const app = Shell.AppSystem.get_default().lookup_app(`${desktopId}.desktop`);
                                if (granted && app)
                                    this._latest = {kind: 'location', app, time: GLib.get_monotonic_time()};
                            } catch (e) {
                                logError(e, 'parchaos-controls: recent location');
                            }
                            target.return_value(value);
                        };
                    }
                    const v = target[key];
                    return typeof v === 'function' ? v.bind(target) : v;
                },
            });
            return original.call(agent, params, reply);
        };
        this._shotId = Main.screenshotUI.connect('screenshot-taken', (_ui, file) => {
            this._latest = {kind: 'screenshot', file, time: GLib.get_monotonic_time()};
        });
    }

    latest() {
        const l = this._latest;
        if (!l || GLib.get_monotonic_time() - l.time > RECENT_SECONDS * 1e6)
            return null;
        if (l.kind === 'screenshot' && !l.file?.query_exists(null))
            return null;
        return l;
    }

    destroy() {
        // The wrapper is an own property over the class method; removing it restores the shell's.
        delete this._agent.AuthorizeAppAsync;
        Main.screenshotUI.disconnect(this._shotId);
        this._latest = null;
    }
}

let recentActivity = null;

function showInFiles(file) {
    Gio.DBus.session.call('org.freedesktop.FileManager1', '/org/freedesktop/FileManager1',
        'org.freedesktop.FileManager1', 'ShowItems', new GLib.Variant('(ass)', [[file.get_uri()], '']),
        null, Gio.DBusCallFlags.NONE, -1, null, (conn, res) => {
            try {
                conn.call_finish(res);
            } catch (e) {
                // No file manager on the bus: open the folder instead.
                Gio.AppInfo.launch_default_for_uri(file.get_parent().get_uri(), null);
            }
        });
}

// Tile corners, traced on the owner's reference (9.33 PM screenshot, hairline fitted per pixel):
// they are superellipse quadrants (|x|^n + |y|^n = r^n), not circular arcs on flat edges. The
// Display slider (4x1) curves over its whole half-height with n = 2.5 (fit 1.0 device px RMS);
// the 2x2 tile's corner reaches 50 px with n = 3.1 (0.82 px RMS). 1x1 and 2x1 tiles are
// circles and capsules (n = 2).
const CORNER_MAX = 50;
// How far the resize handle's box reaches past the tile's corner.
const HANDLE_OUT = 5;

function isBlockTile(item) {
    return item.rows > 1 || item.cols > 2;
}

function tileShape(item) {
    const short = Math.min(item.cols, item.rows) * CELL + (Math.min(item.cols, item.rows) - 1) * GAP;
    if (!isBlockTile(item))
        return {r: short / 2, n: 2};
    const r = Math.min(short / 2, CORNER_MAX);
    return {r, n: r >= CORNER_MAX ? 3.1 : 2.5};
}

// A point on the corner curve at angle a (0 = along the right edge, pi/2 = along the bottom),
// at distance r from the corner's centre in the curve's own norm.
function cornerPoint(r, n, a) {
    const c = Math.cos(a), sn = Math.sin(a);
    return [r * Math.sign(c) * Math.abs(c) ** (2 / n), r * Math.sign(sn) * Math.abs(sn) ** (2 / n)];
}

// True when a stage point is on (or near) the resize stroke, not just in its box: the box covers
// a big part of a round button, where a press should move the tile instead.
function onResizeStroke(item, x, y) {
    const handle = item.resizeHandle;
    if (!handle?.visible || !handle.mapped)
        return false;
    const [ok, lx, ly] = handle.transform_stage_point(x, y);
    if (!ok || lx < 0 || ly < 0)
        return false;
    const {r, n} = tileShape(item);
    const dx = Math.abs(lx - HANDLE_OUT), dy = Math.abs(ly - HANDLE_OUT);
    const dist = (dx ** n + dy ** n) ** (1 / n);
    return Math.abs(dist - (r + 1)) <= 10;
}
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
    // Like the reference: the smallest size shows just the icon; a wider tile adds the name beside it.
    t._smallLayout = (cols, rows) => {
        const iconOnly = cols === 1 && rows === 1;
        l.visible = !iconOnly;
        t.set_style_class_name(`parchaos-controls-tile parchaos-controls-small${iconOnly ? ' parchaos-controls-small-icononly' : ''}`);
        if (cols >= 2 && rows === 1) {
            box.orientation = Clutter.Orientation.HORIZONTAL;
            box.set_style('spacing: 10px; padding: 0 12px;');
            l.x_align = Clutter.ActorAlign.START;
            l.y_align = Clutter.ActorAlign.CENTER;
            circle.x_align = Clutter.ActorAlign.START;
            circle.y_align = Clutter.ActorAlign.CENTER;
        } else {
            box.orientation = Clutter.Orientation.VERTICAL;
            box.set_style(null);
            l.x_align = Clutter.ActorAlign.CENTER;
            circle.x_align = Clutter.ActorAlign.CENTER;
        }
    };
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
const CATEGORY_ICONS = {
    'All Controls': ['view-grid-symbolic', '#8e8e93'],
    'Connectivity': ['network-wireless-symbolic', '#0a84ff'],
    'Sound and Media': ['audio-volume-high-symbolic', '#ff453a'],
    'Focus': ['weather-clear-night-symbolic', '#5e5ce6'],
    'Display': ['display-brightness-symbolic', '#0a84ff'],
    'System': ['preferences-system-symbolic', '#8e8e93'],
    'Shortcuts': ['emblem-system-symbolic', '#ff9f0a'],
    'Other': ['application-x-addon-symbolic', '#30d158'],
};

// Sizes a control can take, in grid cells (columns x rows); the first is the
// default. Edit Controls cycles through them with the corner handle.
// Plain on/off switches (Dark Mode, Night Light, Power Mode) have one size; shortcut buttons
// (Screenshot, Settings, Lock) can be icon-only or wide.
const SWITCH_SIZES = [[1, 1]];
const SMALL_SIZES = [[1, 1], [2, 1]];
const ITEM_SIZES = {
    'wifi': [[2, 1], [1, 1], [2, 2]],
    'bluetooth': [[2, 1], [1, 1], [2, 2]],
    'wired': [[2, 1], [1, 1], [2, 2]],
    'vpn': [[2, 1], [1, 1], [2, 2]],
    'airplane': [[2, 1], [1, 1], [2, 2]],
    'media': [[2, 2], [2, 1]],
    'focus': [[2, 1], [1, 1]],
    'dark-mode': SWITCH_SIZES,
    'night-light': SWITCH_SIZES,
    'display': [[4, 1], [2, 1]],
    'sound': [[4, 1], [2, 1]],
    'power': SWITCH_SIZES,
    'battery': [[2, 1]],
    'screenshot': SMALL_SIZES,
    'settings': SMALL_SIZES,
    'lock': SMALL_SIZES,
};

const ITEM_META = {
    'wifi': {category: 'Connectivity', icon: 'network-wireless-symbolic'},
    'bluetooth': {category: 'Connectivity', icon: 'bluetooth-active-symbolic'},
    'wired': {category: 'Connectivity', icon: 'network-wired-symbolic'},
    'vpn': {category: 'Connectivity', icon: 'network-vpn-symbolic'},
    'airplane': {category: 'Connectivity', icon: 'airplane-mode-symbolic'},
    'media': {category: 'Sound and Media', icon: 'audio-x-generic-symbolic'},
    'focus': {category: 'Focus', icon: 'notifications-disabled-symbolic'},
    'dark-mode': {category: 'Display', icon: 'weather-clear-night-symbolic'},
    'night-light': {category: 'Display', icon: 'night-light-symbolic'},
    'display': {category: 'Display', icon: 'display-brightness-symbolic'},
    'sound': {category: 'Sound and Media', icon: 'audio-volume-high-symbolic'},
    'power': {category: 'System', icon: 'power-profile-balanced-symbolic'},
    'battery': {category: 'System', icon: 'battery-level-80-symbolic'},
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
            if (this._glassSyncId)
                GLib.source_remove(this._glassSyncId);
            this._glassSyncId = 0;
            if (this._frameId)
                global.stage.disconnect(this._frameId);
            this._frameId = 0;
        });
        syncScheme();
        this._qs = qs;
        // No background blur: Shell.BlurEffect cannot follow rounded corners and
        // showed square halos around the panel, so the panel is more opaque instead.


        this._desktop = styleSettings();
        this._grid = new St.Widget({layout_manager: new Clutter.GridLayout({
            row_spacing: GAP,
            column_spacing: GAP,
        })});
        this._addRecentPill();
        this.add_child(this._grid);

        // Every tile is an item with a stable id, so the order and the hidden
        // ones can be saved (Edit Controls).
        this._items = [];
        const add = (id, name, cols, rows, widget) => {
            if (widget) {
                const meta = ITEM_META[id] ?? ITEM_META.external;
                const sizes = ITEM_SIZES[id] ?? [[cols, rows]];
                this._items.push({id, name, cols, rows, widget, hidden: false,
                    category: meta.category, icon: meta.icon, sizes, defaultSize: [cols, rows]});
            }
        };

        const net = this._qs._network;
        const connections = [
            ['wifi', 'Wi-Fi', net?._wirelessToggle, 'wifi', 'Off'],
            ['bluetooth', 'Bluetooth', this._firstItem(this._qs._bluetooth), 'bluetooth', 'Off'],
            ['wired', 'Wired', net?._wiredToggle, 'network', 'Off'],
            ['vpn', 'VPN', net?._vpnToggle, 'network', 'Off'],
            ['airplane', 'Airplane Mode', this._firstItem(this._qs._rfkill), 'wifi', 'Off'],
        ];
        for (const [id, name, source, panel, sub] of connections) {
            if (source?.visible)
                add(id, name, 2, 1, this._connectionTile(source, panel, sub));
        }
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
        // Only on machines that have a battery (a desktop PC shows none).
        add('battery', 'Battery', 2, 1, this._batteryTile());
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
        this._canSize = this._canEdit && !!this._desktop?.settings_schema.has_key('controls-sizes');
        this._placeholders = [];
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

    _addRecentPill() {
        const recent = recentActivity?.latest();
        if (!recent)
            return;
        const box = new St.BoxLayout({style_class: 'parchaos-controls-recent-box'});
        const icon = new St.Icon({
            icon_name: recent.kind === 'location' ? 'find-location-symbolic' : 'camera-photo-symbolic',
            style_class: 'parchaos-controls-recent-icon',
            y_align: Clutter.ActorAlign.CENTER,
        });
        const text = recent.kind === 'location' ? `${recent.app.get_name()} recently` : 'Screenshot taken';
        box.add_child(icon);
        box.add_child(new St.Label({text, y_align: Clutter.ActorAlign.CENTER}));
        this._recentPill = new St.Button({
            style_class: 'parchaos-controls-recent',
            child: box,
            x_align: Clutter.ActorAlign.CENTER,
            can_focus: true,
            accessible_name: text,
        });
        this._recentPill.connect('clicked', () => {
            this.emit('request-close');
            if (recent.kind === 'location')
                recent.app.activate();
            else
                showInFiles(recent.file);
        });
        this.add_child(this._recentPill);
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
        // The resize handle of the reference: a curved white stroke on the
        // tile's bottom-right corner, dragged to the size wanted.
        const handle = new St.DrawingArea({
            style_class: 'parchaos-controls-resize-handle',
            x_align: Clutter.ActorAlign.END,
            y_align: Clutter.ActorAlign.END,
            x_expand: true,
            y_expand: true,
            reactive: true,
            visible: false,
        });
        // The stroke sits on the tile's own corner curve (concentric with it), so the box is
        // the corner square plus a little room for the stroke outside the tile.
        handle.set_translation(HANDLE_OUT, HANDLE_OUT, 0);
        handle.connect('repaint', area => {
            const cr = area.get_context();
            const {r, n} = tileShape(item);
            cr.setLineCap(1);
            cr.setLineJoin(1);
            cr.setLineWidth(6.5);
            cr.setSourceRGBA(1, 1, 1, 0.95);
            // Follows the tile's own corner curve, just outside the outline.
            for (let i = 0; i <= 24; i++) {
                const [px, py] = cornerPoint(r + 1, n, Math.PI * (0.09 + 0.32 * i / 24));
                if (i === 0)
                    cr.moveTo(HANDLE_OUT + px, HANDLE_OUT + py);
                else
                    cr.lineTo(HANDLE_OUT + px, HANDLE_OUT + py);
            }
            cr.stroke();
            cr.$dispose();
        });
        item.resizeHandle = handle;
        item.badge = badge;
        item.widget.add_child(badge);
        item.widget.add_child(handle);
        item.widget.set_pivot_point(0.5, 0.5);
        this._attachDrag(item);
    }

    // The tile under a point, for dragging and dropping.
    _itemAt(x, y) {
        return this._items.find(item => {
            if (item.hidden || !item.widget.mapped)
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

    // No wiggle: while editing, everything is editable right away (resize handle on
    // every tile, drag to move), so tiles stay still.
    _wiggle(item) {
        item.widget.remove_all_transitions();
        item.widget.rotation_angle_z = 0;
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
        const sizes = new Map((this._canSize ? this._desktop.get_strv('controls-sizes') : [])
            .map(e => e.split('=')).filter(e => e.length === 2));
        for (const item of ordered) {
            item.hidden = hidden.has(item.id);
            const [c, r] = (sizes.get(item.id) ?? '').split('x').map(Number);
            const ok = item.sizes.some(([sc, sr]) => sc === c && sr === r);
            [item.cols, item.rows] = ok ? [c, r] : item.defaultSize;
        }
        return ordered;
    }

    _layout() {
        const grid = this._grid;
        const lm = grid.layout_manager;
        for (const child of grid.get_children())
            grid.remove_child(child);
        for (const ph of this._placeholders)
            ph.destroy();
        this._placeholders = [];
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
        let lastRow = 0;
        for (const item of this._ordered()) {
            // Controls that are not in the panel wait in the picker.
            item.badge.visible = false;
            item.resizeHandle.visible = false;
            item.overlay.visible = false;
            item.overlay.reactive = false;
            if (item.hidden)
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
                    lastRow = Math.max(lastRow, r + item.rows - 1);
                    placed = true;
                }
            }
            // The tile's own size follows the chosen size.
            item.widget.set_size(item.cols * CELL + (item.cols - 1) * GAP, item.rows * CELL + (item.rows - 1) * GAP);
            item.widget._smallLayout?.(item.cols, item.rows);
            if (isBlockTile(item))
                item.widget.add_style_class_name('parchaos-controls-block');
            else
                item.widget.remove_style_class_name('parchaos-controls-block');
            const hs = tileShape(item).r + 2 * HANDLE_OUT;
            item.resizeHandle?.set_size(hs, hs);
            item.resizeHandle?.queue_repaint();
            item.badge.visible = this._editing;
            item.resizeHandle.visible = this._editing && item.sizes.length > 1;
            item.overlay.visible = this._editing;
            item.overlay.reactive = this._editing;
            item.badge.label = '\u2212';
            item.widget.opacity = 255;
            item.widget.set_translation(0, 0, 0);
            this._wiggle(item);
        }
        // Empty round slots show where more controls can go.
        if (this._editing) {
            // Two spare rows, as in the reference.
            for (let r = 0; r <= lastRow + 2; r++) {
                for (let c = 0; c < 4; c++) {
                    if (!isFree(c, r, 1, 1))
                        continue;
                    const ph = new St.Widget({style_class: 'parchaos-controls-placeholder', width: CELL, height: CELL});
                    lm.attach(ph, c, r, 1, 1);
                    this._placeholders.push(ph);
                }
            }
        }
    }

    // Resizing by dragging the corner handle: the pointer position picks the
    // nearest size the control allows.
    beginResize(item) {
        const [ox, oy] = item.widget.get_transformed_position();
        return {item, ox, oy, ordered: this._ordered()};
    }

    dragResize(state, x, y) {
        const item = state.item;
        const step = CELL + GAP;
        const wantC = (x - state.ox + GAP) / step;
        const wantR = (y - state.oy + GAP) / step;
        let best = null;
        for (const [c, r] of item.sizes) {
            const d = Math.abs(c - wantC) + Math.abs(r - wantR);
            if (!best || d < best.d)
                best = {c, r, d};
        }
        if (best.c !== item.cols || best.r !== item.rows) {
            item.cols = best.c;
            item.rows = best.r;
            // Saved as it goes: the layout reads the saved sizes.
            this._saveSizes(state.ordered);
            this._layout();
        }
    }

    endResize(state) {
        this._saveSizes(state.ordered);
        this.emit('items-changed');
    }

    // ---- ParchaOS glass behind the tiles (refractive glass on) ----
    useGlass(layer) {
        this._glassLayer = layer;
        this._glassPanes = new Map();
        this.add_style_class_name('parchaos-glass-on');
        for (const item of this._items) {
            item.widget.connect('notify::allocation', () => this._queueGlassSync());
            item.widget.connect('notify::visible', () => this._queueGlassSync());
        }
        this.connect('notify::allocation', () => this._queueGlassSync());
        // The menu can still be sliding or scaling as it opens: keep the panes on their tiles.
        this._frameId = global.stage.connect('before-update', () => {
            if (!this.mapped || !this._glassLayer)
                return;
            const [x, y] = this._glassLayer.get_transformed_position();
            const [sx] = this._glassLayer.get_transformed_size();
            if (x !== this._gx || y !== this._gy || sx !== this._gw) {
                this._gx = x;
                this._gy = y;
                this._gw = sx;
                this._syncGlass();
            }
        });
        this._queueGlassSync();
    }

    dropGlass() {
        if (!this._glassLayer)
            return;
        if (this._frameId)
            global.stage.disconnect(this._frameId);
        this._frameId = 0;
        for (const pane of this._glassPanes.values())
            pane.destroy();
        this._glassPanes.clear();
        this._glassLayer = null;
        this.remove_style_class_name('parchaos-glass-on');
    }

    _queueGlassSync() {
        if (this._glassSyncId || !this._glassLayer)
            return;
        this._glassSyncId = GLib.idle_add(GLib.PRIORITY_DEFAULT_IDLE, () => {
            this._glassSyncId = 0;
            this._syncGlass();
            return GLib.SOURCE_REMOVE;
        });
    }

    _syncGlass() {
        const layer = this._glassLayer;
        if (!layer || !GlassPane)
            return;
        const [lx, ly] = layer.get_transformed_position();
        if (!Number.isFinite(lx) || !Number.isFinite(ly))
            return;
        for (const item of this._items) {
            const w = item.widget;
            let pane = this._glassPanes.get(item.id);
            const show = !item.hidden && w.visible && w.mapped;
            if (!show) {
                pane?.hide();
                continue;
            }
            if (!pane) {
                pane = new GlassPane({});
                pane.hide();
                layer.add_child(pane);
                this._glassPanes.set(item.id, pane);
            }
            const [x, y] = w.get_transformed_position();
            const [pw, ph] = w.get_transformed_size();
            if (!Number.isFinite(x) || pw <= 0 || ph <= 0)
                continue;
            pane.set_position(x - lx, y - ly);
            pane.set_size(pw, ph);
            pane.show();
            // hair: the reference tiles keep a crisp bright outline even over a bright sky
            // band: on a small round button the default 26 px bezel covers almost the whole face and
            // pulls the backdrop across it; the reference's buttons are clear in the middle.
            const shape = tileShape(item);
            pane.set({radius: Math.min(shape.r, Math.min(pw, ph) / 2), cn: shape.n, hair: 0.38, band: Math.min(26, Math.min(pw, ph) * 0.26)});
        }
    }

    _cycleSize(item) {
        const ordered = this._ordered();
        const i = item.sizes.findIndex(([c, r]) => c === item.cols && r === item.rows);
        const [c, r] = item.sizes[(i + 1) % item.sizes.length];
        item.cols = c;
        item.rows = r;
        this._saveSizes(ordered);
        this._layout();
        this.emit('items-changed');
    }

    _saveSizes(ordered) {
        if (!this._canSize)
            return;
        const entries = ordered
            .filter(i => i.cols !== i.defaultSize[0] || i.rows !== i.defaultSize[1])
            .map(i => `${i.id}=${i.cols}x${i.rows}`);
        this._desktop.set_strv('controls-sizes', entries);
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

    // Every control, for the picker (it lists those in the panel too, as the reference does).
    allItems() {
        return this._ordered();
    }

    // Briefly lights up a control's tile, to show where it is.
    flash(item) {
        const w = item.widget;
        w.remove_transition('opacity');
        w.opacity = 90;
        w.ease({opacity: 255, duration: 450, mode: Clutter.AnimationMode.EASE_OUT_QUAD});
    }

    // The controls not shown in the panel, for the picker.
    availableItems() {
        this._ordered();
        return this._items.filter(i => i.hidden);
    }

    // Put a control from the picker back into the panel.
    addItem(item, target = null) {
        const ordered = this._ordered();
        item.hidden = false;
        if (target && target !== item) {
            ordered.splice(ordered.indexOf(item), 1);
            ordered.splice(ordered.indexOf(target), 0, item);
        } else {
            // To the end of the panel.
            ordered.splice(ordered.indexOf(item), 1);
            ordered.push(item);
        }
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

    _batteryTile() {
        let proxy = null;
        try {
            proxy = Gio.DBusProxy.new_for_bus_sync(Gio.BusType.SYSTEM, Gio.DBusProxyFlags.NONE, null,
                'org.freedesktop.UPower', '/org/freedesktop/UPower/devices/DisplayDevice',
                'org.freedesktop.UPower.Device', null);
        } catch (e) {
            return null;
        }
        const get = name => proxy.get_cached_property(name)?.deepUnpack();
        // Type 2 is a battery; IsPresent is false on a desktop.
        if (!get('IsPresent') || get('Type') !== 2)
            return null;
        const t = tile(2, 1, 'parchaos-controls-focus');
        const row = new St.BoxLayout({x_expand: true, y_align: Clutter.ActorAlign.CENTER, style: 'padding: 0 14px 0 12px; spacing: 10px;'});
        const icon = new St.Icon({icon_size: 24, style_class: 'parchaos-controls-circle-icon'});
        row.add_child(icon);
        const {box, t: title, s: sub} = labels('Battery', '');
        row.add_child(box);
        const sync = () => {
            const pct = Math.round(get('Percentage') ?? 0);
            const state = get('State');
            icon.icon_name = get('IconName') ?? 'battery-symbolic';
            title.text = `Battery ${pct}%`;
            sub.text = state === 1 ? 'Charging' : state === 4 ? 'Fully charged' : 'On battery';
        };
        const id = proxy.connect('g-properties-changed', sync);
        t.connect('destroy', () => proxy.disconnect(id));
        sync();
        t.add_child(row);
        return t;
    }

    _firstItem(indicator) {
        return indicator?.quickSettingsItems?.[0] ?? null;
    }

    // One tile per connection (Wi-Fi, Bluetooth, Wired, ...), each resizable like the reference: the
    // wide size shows the name and state beside the icon, the small size is just the icon.
    _connectionTile(source, settingsPanel, defaultSub) {
        const t = tile(2, 1, 'parchaos-controls-connection');
        const row = new St.BoxLayout({x_expand: true, y_align: Clutter.ActorAlign.CENTER, style: 'padding: 0 14px 0 12px; spacing: 10px;'});
        const circle = circleFor(source, 36);
        row.add_child(circle);
        const {box, t: title, s} = labels();
        const text = new St.Button({child: box, x_expand: true, style_class: 'parchaos-controls-row-text'});
        const sync = () => {
            title.text = source.title ?? '';
            s.text = source.subtitle || (source.checked ? 'On' : defaultSub);
        };
        source.connectObject('notify::title', sync, 'notify::subtitle', sync, 'notify::checked', sync, row);
        sync();
        text.connect('clicked', () => {
            this.emit('request-close');
            openSettings(settingsPanel);
        });
        row.add_child(text);
        t.add_child(row);
        t._smallLayout = (cols, rows) => {
            const iconOnly = cols === 1 && rows === 1;
            const tall = rows >= 2;
            text.visible = !iconOnly;
            // Tall: the icon on top, the name and the state under it.
            row.orientation = tall ? Clutter.Orientation.VERTICAL : Clutter.Orientation.HORIZONTAL;
            row.y_align = Clutter.ActorAlign.CENTER;
            circle.x_align = tall ? Clutter.ActorAlign.START : Clutter.ActorAlign.FILL;
            row.x_align = iconOnly ? Clutter.ActorAlign.CENTER : Clutter.ActorAlign.FILL;
            row.set_style(iconOnly ? null : (tall ? 'padding: 14px; spacing: 12px;' : 'padding: 0 14px 0 12px; spacing: 10px;'));
            t.set_style_class_name(`parchaos-controls-tile parchaos-controls-connection${iconOnly ? ' parchaos-controls-small-icononly' : ''}`);
        };
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
// The picker beside the panel in edit mode (ticket #148), laid out after the owner's reference
// (edit controls.png, 9.33 PM), measured in logical px: a 244 px sidebar (search field, then
// categories with app-style icons, 46 px rows), a gallery of every control by category (What's
// New card, Suggestions, one section per category; 65 px cells, 11 px gaps, names under the
// tiles), and a footer with the hint and Done. Controls already in the panel are listed too
// (as in the reference); dragging one moves it, clicking one shows where it is.
// ---------------------------------------------------------------------
const GALLERY_CELL = 65;
// The What's New card is kept for a later release: the first release has nothing to call new
// (owner, 2026-10-01). Set to true to show it above Suggestions again.
const SHOW_WHATS_NEW = false;
const GALLERY_GAP = 11;

const ControlsPicker = GObject.registerClass(
class ControlsPicker extends St.BoxLayout {
    _init(panel) {
        super._init({
            style_class: 'parchaos-controls-panel parchaos-controls-picker',
            orientation: Clutter.Orientation.HORIZONTAL,
            reactive: true,
        });
        this._panel = panel;
        this._category = null;
        this._query = '';
        applyStyleClass(this, styleSettings());
        if (panel.has_style_class_name('parchaos-light'))
            this.add_style_class_name('parchaos-light');

        // Sidebar: search, then the categories.
        this._sidebar = new St.BoxLayout({
            style_class: 'parchaos-controls-picker-sidebar',
            orientation: Clutter.Orientation.VERTICAL,
            reactive: true,
        });
        this._search = new St.Entry({
            style_class: 'parchaos-controls-search',
            hint_text: 'Search Controls',
            can_focus: true,
            primary_icon: new St.Icon({icon_name: 'edit-find-symbolic', style_class: 'parchaos-controls-search-icon'}),
        });
        this._search.clutter_text.connect('text-changed', () => {
            this._query = this._search.get_text().trim().toLowerCase();
            this._refresh();
        });
        this._sidebar.add_child(this._search);
        this._categories = new St.BoxLayout({
            style_class: 'parchaos-controls-categories',
            orientation: Clutter.Orientation.VERTICAL,
            reactive: true,
        });
        this._sidebar.add_child(new St.ScrollView({
            child: this._categories,
            y_expand: true,
            hscrollbar_policy: St.PolicyType.NEVER,
            vscrollbar_policy: St.PolicyType.EXTERNAL,
        }));
        this.add_child(this._sidebar);

        // Gallery and footer.
        const main = new St.BoxLayout({
            style_class: 'parchaos-controls-picker-main',
            orientation: Clutter.Orientation.VERTICAL,
            x_expand: true,
            y_expand: true,
        });
        this._gallery = new St.BoxLayout({
            style_class: 'parchaos-controls-gallery',
            orientation: Clutter.Orientation.VERTICAL,
            x_expand: true,
        });
        main.add_child(new St.ScrollView({
            child: this._gallery,
            x_expand: true,
            y_expand: true,
            // scrolls, but shows no bar (as in the reference)
            hscrollbar_policy: St.PolicyType.NEVER,
            vscrollbar_policy: St.PolicyType.EXTERNAL,
            style_class: 'parchaos-controls-gallery-scroll',
        }));
        const footer = new St.BoxLayout({style_class: 'parchaos-controls-picker-footer', reactive: true});
        footer.add_child(new St.Label({
            text: 'Drag a control to place it in Control Center.',
            style_class: 'parchaos-controls-picker-hint',
            x_expand: true,
            y_align: Clutter.ActorAlign.CENTER,
        }));
        const done = new St.Button({style_class: 'parchaos-controls-done', label: 'Done', can_focus: true});
        done.connect('clicked', () => this._panel.finishEditing());
        footer.add_child(done);
        main.add_child(footer);
        this.add_child(main);
        this._footer = footer;

        // The window moves when its background is dragged (sidebar, footer, the window itself).
        this.grip = this;
        panel.connect('items-changed', () => this._refresh());
    }

    // True for the parts of the window that move it when dragged.
    isMoveArea(actor) {
        return actor === this || actor === this._sidebar || actor === this._categories || actor === this._footer;
    }

    focusSearch() {
        this._search.grab_key_focus();
    }

    open() {
        this._query = '';
        this._search.set_text('');
        this._category = null;
        this._refresh();
        this.show();
    }

    // The control a gallery tile stands for, or null.
    itemOf(actor) {
        for (let a = actor; a && a !== this; a = a.get_parent()) {
            if (a._controlItem)
                return a._controlItem;
        }
        return null;
    }

    _categoryRow(label, value) {
        const [iconName, colour] = CATEGORY_ICONS[label] ?? CATEGORY_ICONS.Other;
        const line = new St.BoxLayout({style_class: 'parchaos-controls-category-line', x_expand: true});
        // App-style icon: a dark rounded square with the category's coloured glyph.
        line.add_child(new St.Bin({
            style_class: 'parchaos-controls-category-chip',
            child: new St.Icon({icon_name: iconName, icon_size: 15, style: `color: ${colour};`}),
            y_align: Clutter.ActorAlign.CENTER,
        }));
        line.add_child(new St.Label({text: label, y_align: Clutter.ActorAlign.CENTER}));
        const b = new St.Button({
            style_class: 'parchaos-controls-category',
            child: line,
            x_align: Clutter.ActorAlign.FILL,
            can_focus: true,
        });
        if (this._category === value)
            b.add_style_pseudo_class('checked');
        b.connect('clicked', () => {
            this._category = value;
            this._refresh();
        });
        return b;
    }

    // What's New: a short note and a small picture of a screen with Control Center on it.
    _whatsNew() {
        const card = new St.BoxLayout({style_class: 'parchaos-controls-whatsnew'});
        const text = new St.BoxLayout({orientation: Clutter.Orientation.VERTICAL, x_expand: true, y_align: Clutter.ActorAlign.CENTER});
        text.add_child(new St.Label({text: "What's New", style_class: 'parchaos-controls-whatsnew-title'}));
        const blurb = new St.Label({
            text: 'Control Center is yours to arrange. Resize and reorder controls so the ones you use most are a click away. Connections can be icon-only, wide or tall.',
            style_class: 'parchaos-controls-whatsnew-text',
        });
        blurb.clutter_text.line_wrap = true;
        blurb.clutter_text.ellipsize = 0;
        text.add_child(blurb);
        card.add_child(text);

        const screen = new St.Widget({style_class: 'parchaos-controls-whatsnew-screen', layout_manager: new Clutter.FixedLayout()});
        // 196 x 124 as in the reference; smaller when the picker is narrow, so the text keeps room.
        const k = (this.layoutWidth || 733) < 640 ? 0.72 : 1;
        screen.set_size(Math.round(196 * k), Math.round(124 * k));
        // menu bar, a column of tiles at the right, and the dock
        const at = (actor, x, y, w, h) => {
            actor.set_position(Math.round(x * k), Math.round(y * k));
            actor.set_size(Math.max(1, Math.round(w * k)), Math.max(1, Math.round(h * k)));
        };
        const bar = new St.Widget({style_class: 'parchaos-controls-whatsnew-bar'});
        at(bar, 6, 5, 60, 3);
        screen.add_child(bar);
        const tiles = [[150, 14, 18, 10], [170, 14, 18, 10], [150, 27, 38, 10], [150, 40, 18, 18], [170, 40, 18, 18], [150, 61, 38, 8], [150, 72, 38, 8]];
        for (const [x, y, w, h] of tiles) {
            const t = new St.Widget({style_class: 'parchaos-controls-whatsnew-tile'});
            at(t, x, y, w, h);
            screen.add_child(t);
        }
        const dock = new St.Widget({style_class: 'parchaos-controls-whatsnew-dock'});
        at(dock, 60, 110, 120, 8);
        screen.add_child(dock);
        card.add_child(screen);
        return card;
    }

    _heading(text, first = false) {
        return new St.Label({text, style_class: 'parchaos-controls-gallery-heading' + (first ? ' first' : '')});
    }

    _refresh() {
        const all = this._panel.allItems();
        const names = [...new Set(all.map(i => i.category))];
        this._categories.destroy_all_children();
        this._categories.add_child(this._categoryRow('All Controls', null));
        for (const name of names)
            this._categories.add_child(this._categoryRow(name, name));

        this._gallery.destroy_all_children();
        const shown = all.filter(i =>
            (!this._category || i.category === this._category) &&
            (!this._query || i.name.toLowerCase().includes(this._query) ||
                i.category.toLowerCase().includes(this._query)));
        if (shown.length === 0) {
            this._gallery.add_child(new St.Label({text: 'No controls match.', style_class: 'parchaos-controls-picker-hint'}));
            return;
        }
        let first = true;
        if (!this._category && !this._query) {
            if (SHOW_WHATS_NEW)
                this._gallery.add_child(this._whatsNew());
            // Suggestions: controls not in the panel yet, else a few handy ones.
            const missing = shown.filter(i => i.hidden);
            const handy = ['screenshot', 'lock', 'night-light', 'focus', 'dark-mode', 'settings']
                .map(id => shown.find(i => i.id === id)).filter(Boolean);
            const picks = [...new Set([...missing, ...handy])].slice(0, 6);
            if (picks.length) {
                this._gallery.add_child(this._heading('Suggestions', true));
                this._flow(this._gallery, picks);
                first = false;
            }
        }
        for (const category of [...new Set(shown.map(i => i.category))]) {
            this._gallery.add_child(this._heading(category, first));
            first = false;
            this._flow(this._gallery, shown.filter(i => i.category === category));
        }
    }

    // Lay tiles out in rows that wrap at the gallery width; each tile takes its cells plus room
    // for its name.
    _flow(parent, items) {
        // layoutWidth is set by the owner before the picker is shown (it may not be on stage yet)
        const budget = Math.max(GALLERY_CELL * 2, (this.layoutWidth || 700) - 244 - 2 * 17);
        let row = null, used = 0;
        for (const item of items) {
            const [cols] = item.defaultSize;
            const w = cols * GALLERY_CELL + (cols - 1) * GALLERY_GAP;
            if (!row || used + w > budget) {
                row = new St.BoxLayout({style_class: 'parchaos-controls-gallery-row', x_align: Clutter.ActorAlign.START});
                parent.add_child(row);
                used = 0;
            }
            row.add_child(this._tile(item));
            used += w + GALLERY_GAP + 12;
        }
    }

    // A control at the size it has in the panel, its name under it (wide tiles also show the
    // name inside, as in the reference).
    _tile(item, forDrag = false) {
        const [cols, rows] = item.defaultSize;
        const w = cols * GALLERY_CELL + (cols - 1) * GALLERY_GAP;
        const h = rows * GALLERY_CELL + (rows - 1) * GALLERY_GAP;
        const holder = new St.BoxLayout({
            style_class: 'parchaos-controls-gallery-cell',
            orientation: Clutter.Orientation.VERTICAL,
            reactive: !forDrag,
        });
        holder._controlItem = item;
        const round = rows === 1;
        const shape = new St.BoxLayout({
            style_class: 'parchaos-controls-gallery-item' + (round ? ' round' : '') + (cols > 1 && rows === 1 ? ' wide' : '') + (rows > 1 ? ' tall' : ''),
            style: `width: ${w}px; height: ${h}px; min-width: ${w}px; min-height: ${h}px;` +
                (round ? '' : ` border-radius: ${Math.min(h / 2, CORNER_MAX) * 0.6}px;`),
            x_align: Clutter.ActorAlign.CENTER,
            reactive: !forDrag,
        });
        if (rows > 1) {
            // tall tiles: the glyph sits in the top-left corner
            shape.orientation = Clutter.Orientation.VERTICAL;
            shape.add_child(new St.Icon({icon_name: item.icon, style_class: 'parchaos-controls-gallery-icon', x_align: Clutter.ActorAlign.START}));
        } else if (cols > 1) {
            const disc = new St.Bin({
                style_class: 'parchaos-controls-gallery-disc',
                child: new St.Icon({icon_name: item.icon, style_class: 'parchaos-controls-gallery-icon'}),
                y_align: Clutter.ActorAlign.CENTER,
            });
            shape.add_child(disc);
            const inline = new St.Label({text: item.name, style_class: 'parchaos-controls-gallery-inline', y_align: Clutter.ActorAlign.CENTER, x_expand: true});
            inline.clutter_text.line_wrap = true;
            shape.add_child(inline);
        } else {
            shape.add_child(new St.Icon({icon_name: item.icon, style_class: 'parchaos-controls-gallery-icon', x_expand: true, y_align: Clutter.ActorAlign.CENTER}));
        }
        if (this.glass && !forDrag) {
            // As in the reference, a gallery tile is glass too (our pane, behind the tile's content).
            const stack = new St.Widget({layout_manager: new Clutter.BinLayout(), x_align: Clutter.ActorAlign.CENTER});
            const pane = new GlassPane({});
            const r = round ? h / 2 : Math.min(h / 2, CORNER_MAX);
            pane.set({radius: r, cn: round ? 2 : 3.1, hair: 0.38, blur: 14, tint: 0.14, dim: 0.62, disp: 20, z: 60,
                band: Math.min(26, Math.min(w, h) * 0.26)});
            pane.set_size(w, h);
            stack.set_size(w, h);
            stack.add_child(pane);
            stack.add_child(shape);
            holder.add_child(stack);
        } else {
            holder.add_child(shape);
        }
        if (!forDrag) {
            const label = new St.Label({
                text: item.name,
                style_class: 'parchaos-controls-gallery-label',
                x_align: Clutter.ActorAlign.CENTER,
                style: `max-width: ${Math.max(w, GALLERY_CELL + 14)}px;`,
            });
            label.clutter_text.line_wrap = true;
            label.clutter_text.ellipsize = 0;
            label.clutter_text.set_line_alignment(1);
            holder.add_child(label);
        }
        return holder;
    }

    // A floating copy that follows the pointer while a control is dragged out.
    dragCopy(item) {
        const copy = this._tile(item, true);
        copy.add_style_class_name('parchaos-controls-drag-copy');
        copy.opacity = 220;
        return copy;
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
        // Control Center has its own transition (runMotion), in place of the stock slide or the
        // short fade other menus get.
        const pointer = this.menu._boxPointer;
        pointer.open = (animate, onComplete) => {
            pointer.remove_all_transitions();
            pointer.translation_x = pointer.translation_y = 0;
            pointer.scale_x = pointer.scale_y = 1;
            pointer._muteKeys = false;
            pointer.show();
            const done = () => {
                pointer._muteInput = false;
                onComplete?.();
            };
            if (!animate) {
                pointer.opacity = 255;
                done();
            } else {
                runMotion(pointer, true, done);
            }
        };
        pointer.close = (animate, onComplete) => {
            if (!pointer.visible)
                return;
            pointer._muteInput = true;
            pointer._muteKeys = true;
            pointer.remove_all_transitions();
            const done = () => {
                pointer.hide();
                pointer.opacity = 0;
                onComplete?.();
            };
            if (!animate)
                done();
            else
                runMotion(pointer, false, done);
        };
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
        this._row = new St.Widget({style_class: 'parchaos-controls-row-holder'});
        if (GlassPane && this._glassWanted?.()) {
            this._glassLayer = new Clutter.Actor();
            this._row.add_child(this._glassLayer);
        }
        this._row.add_child(this._panel);
        if (this._glassLayer)
            this._panel.useGlass(this._glassLayer);
        this._panel.connect('edit-changed', () => {
            if (this._panel.editing)
                this._beginEdit();
        });
        this._holder.set_child(this._row);
    }

    _glassWanted() {
        const settings = styleSettings();
        return !!settings?.settings_schema.has_key('glass-effects') && settings.get_boolean('glass-effects') &&
            settings.get_string('style') !== 'classic';
    }

    _destroyPanel() {
        if (this._editOverlay)
            return;
        this._row?.destroy();
        this._row = null;
        this._panel = null;
    }

    // Edit mode (ticket #148): the picker is its own window, as in the
    // reference, with Control Center beside it. Both live on a transparent
    // full-screen layer that takes over input from the menu; a press outside
    // them, Escape or Done ends editing.
    _beginEdit() {
        const panel = this._panel;
        if (!panel || this._editOverlay)
            return;
        const monitor = Main.layoutManager.currentMonitor;
        const [px, py] = panel.get_transformed_position();
        // On its own layer the panel needs its own background.
        panel.remove_style_class_name('parchaos-hosted');
        const glassOn = !!GlassPane && this._glassWanted();
        panel.dropGlass();
        this._glassLayer?.destroy();
        this._glassLayer = null;
        // As in the reference: no panel behind Control Center, every tile is its own glass.
        const overlay = new St.Widget({
            reactive: true,
            x: monitor.x,
            y: monitor.y,
            width: monitor.width,
            height: monitor.height,
        });
        this._row.remove_child(panel);
        overlay.add_child(panel);
        panel.set_position(px - monitor.x, py - monitor.y);

        const picker = new ControlsPicker(panel);
        picker.glass = glassOn;
        // 55% x 88% of the screen, as measured on the reference.
        const pickerSize = [Math.min(900, Math.round(monitor.width * 0.55)), Math.round(monitor.height * 0.88)];
        picker.layoutWidth = pickerSize[0];
        picker.set_size(...pickerSize);
        overlay.add_child(picker);
        overlay.set_child_above_sibling(panel, picker);
        // Glass behind both windows in edit mode too (as in the reference):
        // one pane each, following them as they move or resize.
        if (glassOn) {
            const layer = new Clutter.Actor();
            overlay.insert_child_below(layer, null);
            panel.useGlass(layer);
            const panes = [[picker, 18]].map(([actor, radius]) => {
                const pane = new GlassPane({});
                pane.set({radius, disp: 8, blur: 0, bgblur: 24, pad: 90, tint: 0.3, dim: 0.44, z: 30});
                layer.add_child(pane);
                actor.add_style_class_name('parchaos-glass-edit');
                return {actor, pane};
            });
            const follow = () => {
                if (!overlay.mapped)
                    return;
                const [ox, oy] = overlay.get_transformed_position();
                for (const {actor, pane} of panes) {
                    const [x, y] = actor.get_transformed_position();
                    const [w, h] = actor.get_transformed_size();
                    if (!Number.isFinite(x) || w <= 0 || h <= 0)
                        continue;
                    pane.set_position(x - ox, y - oy);
                    pane.set_size(w, h);
                }
            };
            const frame = global.stage.connect('before-update', follow);
            overlay.connect('destroy', () => global.stage.disconnect(frame));
            follow();
        }
        // Centred in the room left of Control Center, so the two never overlap (on a narrow
        // screen it shrinks to fit); it can be moved by dragging its background.
        const place = () => {
            const panelLeft = px - monitor.x;
            const room = panelLeft - 24;
            let [pw, ph] = picker.get_size();
            if (pw > room - 32) {
                pw = Math.max(520, room - 32);
                picker.layoutWidth = pw;
                picker.set_size(pw, ph);
            }
            const x = Math.max(16, Math.round((room - pw) / 2));
            picker.set_position(x, Math.round((monitor.height - ph) / 2));
        };
        this._editOverlay = overlay;
        this._picker = picker;
        const finish = () => {
            if (panel.editing)
                panel.finishEditing();
        };
        // Pointer handling on the edit layer: a press outside the two windows
        // ends editing; the grip moves the picker; a control dragged out of
        // the picker can be dropped on Control Center.
        const within = (actor, root) => {
            for (let a = actor; a; a = a.get_parent()) {
                if (a === root)
                    return true;
            }
            return false;
        };
        const inside = (actor, px, py) => {
            const [ax, ay] = actor.get_transformed_position();
            const [aw, ah] = actor.get_transformed_size();
            return px >= ax && px < ax + aw && py >= ay && py < ay + ah;
        };
        let drag = null;
        overlay.connect('captured-event', (_o, event) => {
            const type = event.type();
            const [x, y] = event.get_coords();
            const hit = global.stage.get_actor_at_pos(Clutter.PickMode.REACTIVE, x, y);
            if (type === Clutter.EventType.BUTTON_PRESS && event.get_button() === 1) {
                if (picker.isMoveArea(hit)) {
                    const [px0, py0] = picker.get_position();
                    drag = {kind: 'window', x, y, px0, py0};
                    return Clutter.EVENT_STOP;
                }
                const resizing = panel._items.find(i => !i.hidden && onResizeStroke(i, x, y));
                if (resizing) {
                    drag = {kind: 'resize', state: panel.beginResize(resizing)};
                    return Clutter.EVENT_STOP;
                }
                const item = within(hit, picker) ? picker.itemOf(hit) : null;
                if (item) {
                    drag = {kind: 'item', item, x, y, moved: false, copy: null};
                    return Clutter.EVENT_STOP;
                }
                if (!within(hit, panel) && !within(hit, picker)) {
                    finish();
                    return Clutter.EVENT_STOP;
                }
                return Clutter.EVENT_PROPAGATE;
            }
            if (!drag)
                return Clutter.EVENT_PROPAGATE;
            if (type === Clutter.EventType.MOTION) {
                if (drag.kind === 'window') {
                    picker.set_position(drag.px0 + x - drag.x, drag.py0 + y - drag.y);
                } else if (drag.kind === 'resize') {
                    panel.dragResize(drag.state, x, y);
                } else {
                    if (!drag.moved && Math.hypot(x - drag.x, y - drag.y) < 8)
                        return Clutter.EVENT_STOP;
                    if (!drag.moved) {
                        drag.moved = true;
                        drag.copy = picker.dragCopy(drag.item);
                        overlay.add_child(drag.copy);
                    }
                    const [ox, oy] = overlay.get_transformed_position();
                    drag.copy.set_position(x - ox - 30, y - oy - 30);
                }
                return Clutter.EVENT_STOP;
            }
            if (type === Clutter.EventType.BUTTON_RELEASE) {
                const done = drag;
                drag = null;
                if (done.kind === 'resize')
                    panel.endResize(done.state);
                if (done.kind === 'item') {
                    done.copy?.destroy();
                    if (!done.moved) {
                        if (done.item.hidden)
                            panel.addItem(done.item);
                        else
                            panel.flash(done.item);
                    }
                    else if (inside(panel, x, y))
                        panel.addItem(done.item, panel._itemAt(x, y) ?? null);
                }
                return Clutter.EVENT_STOP;
            }
            return Clutter.EVENT_STOP;
        });
        overlay.connect('key-press-event', (_o, event) => {
            if (event.get_key_symbol() === Clutter.KEY_Escape) {
                finish();
                return Clutter.EVENT_STOP;
            }
            return Clutter.EVENT_PROPAGATE;
        });
        panel.connect('edit-changed', () => {
            if (!panel.editing)
                this._endEdit();
        });

        Main.uiGroup.add_child(overlay);
        Main.uiGroup.set_child_above_sibling(overlay, null);
        // Filled once it is on stage (its gallery tiles carry glass panes that need the stage).
        place();
        picker.open();
        this._grab = Main.pushModal(overlay, {actionMode: Shell.ActionMode.POPUP});
        picker.focusSearch();
        // The menu has done its job; its panel now lives on the overlay.
        this.menu.close(false);
    }

    _endEdit() {
        const overlay = this._editOverlay;
        if (!overlay)
            return;
        this._editOverlay = null;
        if (this._grab) {
            Main.popModal(this._grab);
            this._grab = null;
        }
        overlay.destroy();
        this._picker = null;
        this._row?.destroy();
        this._row = null;
        this._panel = null;
    }

    destroy() {
        this._endEdit();
        this.releaseIndicators();
        this._destroyPanel();
        super.destroy();
    }
});


// With refractive glass on, the glass extension draws the standard Quick
// Settings menu and nothing else, so Control Center lives *in* that menu
// (ticket #148): the standard button and menu stay, the panel replaces the
// menu's own grid while it is open, and the extension's glass shows through
// the transparent panel. Edit Controls works exactly as in the button version.
class HostedControls {
    constructor(qs) {
        this._qs = qs;
        this.menu = qs.menu;
        this._row = null;
        this._panel = null;
        this._picker = null;
        this._editOverlay = null;
        this._grab = null;
        this._openId = this.menu.connect('open-state-changed', (_m, open) => {
            if (open)
                this._build();
            else
                this._closed();
        });
    }

    _build() {
        this._destroyPanel();
        this.menu._grid?.hide();
        // The menu's own pane is the glass extension's job (one capsule per tile).
        this.menu.box.set_style('background-color: transparent; border-color: transparent; box-shadow: none;');
        this._panel = new ControlsPanel(this._qs);
        this._panel.add_style_class_name('parchaos-hosted');
        // The glass extension gives every Quick Settings toggle its own piece
        // of glass; our tiles carry the same classes so they get one each.
        for (const item of this._panel._items) {
            item.widget.add_style_class_name(item.id === 'display' || item.id === 'sound' ? 'quick-slider' : 'quick-toggle');
            // The toggle classes make the theme shorten labels; let them show in full.
            const unclip = a => {
                if (a instanceof St.Label)
                    a.clutter_text.ellipsize = 0;
                for (const c of a.get_children?.() ?? [])
                    unclip(c);
            };
            unclip(item.widget);
        }
        this._panel.connect('request-close', () => this.menu.close());
        this._row = new St.Widget({style_class: 'parchaos-controls-row-holder'});
        if (GlassPane && this._glassWanted?.()) {
            this._glassLayer = new Clutter.Actor();
            this._row.add_child(this._glassLayer);
        }
        this._row.add_child(this._panel);
        if (this._glassLayer)
            this._panel.useGlass(this._glassLayer);
        this._panel.connect('edit-changed', () => {
            if (this._panel?.editing)
                this._beginEdit();
        });
        this.menu.box.add_child(this._row);
    }

    _closed() {
        this._destroyPanel();
        this.menu._grid?.show();
        this.menu.box.set_style(null);
    }

    destroy() {
        this._endEdit();
        if (this._openId)
            this.menu.disconnect(this._openId);
        this._openId = 0;
        this._row?.destroy();
        this._row = null;
        this._panel = null;
        this.menu._grid?.show();
        this.menu.box.set_style(null);
    }
}

// A tiny D-Bus method for the Screenshot app in the app grid (ticket #130):
// GNOME Shell's capture tool can only be opened from inside the Shell, and
// the old standalone screenshot app cannot reach it on Wayland.
const SHELL_BUS_XML = `<node><interface name="org.parchaos.Shell">
  <method name="OpenScreenshotUI"/>
</interface></node>`;

for (const name of ['_destroyPanel', '_beginEdit', '_endEdit', '_glassWanted'])
    HostedControls.prototype[name] = ControlsButton.prototype[name];

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
        recentActivity = new RecentActivity();
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

    _refracted() {
        const settings = styleSettings();
        return !!settings?.settings_schema.has_key('glass-effects') && settings.get_boolean('glass-effects');
    }

    _setup(qs) {
        this._qs = qs;
        this._settings = styleSettings();
        this._modeId = this._settings?.settings_schema.has_key('glass-effects')
            ? this._settings.connect('changed::glass-effects', () => this._remake()) : 0;
        // Our own glass draws the tiles now, so the button form is used in every style (the
        // third-party glass extension no longer has to host the panel).
        this._hosted = false;
        if (this._hosted) {
            this._host = new HostedControls(qs);
            return;
        }
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

    // Switching refractive glass on or off swaps between the two forms.
    _teardown() {
        if (this._modeId)
            this._settings?.disconnect(this._modeId);
        this._modeId = 0;
        this._settings = null;
        this._host?.destroy();
        this._host = null;
        this._injections?.clear();
        this._injections = new InjectionManager();
        this._button?.destroy();
        this._button = null;
        this._qs?.container.disconnectObject(this);
        this._qs?.container.show();
    }

    _remake() {
        const qs = this._qs;
        this._teardown();
        if (qs)
            GLib.idle_add(GLib.PRIORITY_DEFAULT, () => { this._setup(qs); return GLib.SOURCE_REMOVE; });
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
        this._teardown();
        recentActivity?.destroy();
        recentActivity = null;
        this._injections?.clear();
        this._injections = null;
        this._qs = null;
    }
}
