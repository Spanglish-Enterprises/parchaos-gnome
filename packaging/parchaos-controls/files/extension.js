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

const KEYBOARD_STYLE = 'parchaos-keyboard-style';

// "Super as Ctrl": on = the Super key works like Cmd (keyboard remap on,
// ParchaOS shortcuts); off = standard Super and Ctrl roles. Switching runs
// parchaos-keyboard-style, which applies immediately.
function keyboardStyleTile() {
    const t = tile(1, 1, 'parchaos-controls-small');
    const box = new St.BoxLayout({
        orientation: Clutter.Orientation.VERTICAL,
        x_align: Clutter.ActorAlign.CENTER,
        y_align: Clutter.ActorAlign.CENTER,
    });
    const circle = circleFor('input-keyboard-symbolic', 36, () => {
        const next = circle.has_style_pseudo_class('checked') ? 'windows' : 'mac';
        setChecked(next === 'mac');
        runStyle([next]).catch(e => logError(e, 'parchaos-controls: keyboard style'));
    });
    circle.x_align = Clutter.ActorAlign.CENTER;
    const setChecked = on => {
        if (on)
            circle.add_style_pseudo_class('checked');
        else
            circle.remove_style_pseudo_class('checked');
    };
    const runStyle = async args => {
        const proc = Gio.Subprocess.new([KEYBOARD_STYLE, ...args],
            Gio.SubprocessFlags.STDOUT_PIPE);
        const [out] = await new Promise((resolve, reject) =>
            proc.communicate_utf8_async(null, null, (p, res) => {
                try {
                    resolve(p.communicate_utf8_finish(res).slice(1));
                } catch (e) {
                    reject(e);
                }
            }));
        return (out ?? '').trim();
    };
    runStyle(['status'])
        .then(style => setChecked(style !== 'windows'))
        .catch(e => logError(e, 'parchaos-controls: keyboard style'));
    box.add_child(circle);
    const l = new St.Label({style_class: 'parchaos-controls-small-label', text: 'Super as Ctrl'});
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

const ControlsPanel = GObject.registerClass({
    Signals: {'request-close': {}},
}, class ControlsPanel extends St.BoxLayout {
    _init(qs) {
        super._init({
            style_class: 'parchaos-controls-panel',
            orientation: Clutter.Orientation.VERTICAL,
        });
        this._qs = qs;
        this.add_effect(new Shell.BlurEffect({
            radius: 60,
            brightness: 0.9,
            mode: Shell.BlurMode.BACKGROUND,
        }));

        const grid = new St.Widget({layout_manager: new Clutter.GridLayout({
            row_spacing: GAP,
            column_spacing: GAP,
        })});
        this.add_child(grid);
        const lm = grid.layout_manager;

        lm.attach(this._connectivityTile(), 0, 0, 2, 2);
        lm.attach(this._nowPlayingTile(), 2, 0, 2, 2);

        const dnd = this._firstItem(qs._doNotDisturb);
        let col = 0;
        if (dnd) {
            lm.attach(this._focusTile(dnd), 0, 2, 2, 1);
            col = 2;
        }
        // GNOME's own dark style toggle writes 'default' (no preference)
        // for light, which Electron/Chromium apps treat as "keep guessing"
        // and can stay dark or light. Write an explicit preference both
        // ways; the toggle still mirrors the state.
        const dark = this._firstItem(qs._darkMode);
        if (dark) {
            lm.attach(smallToggle(dark, 'Dark Mode', () => {
                Main.layoutManager.screenTransition.run();
                const iface = new Gio.Settings({schema_id: 'org.gnome.desktop.interface'});
                iface.set_string('color-scheme', dark.checked ? 'prefer-light' : 'prefer-dark');
            }), col++, 2, 1, 1);
        }
        const night = this._firstItem(qs._nightLight);
        if (night && col < 4)
            lm.attach(smallToggle(night, 'Night Light'), col++, 2, 1, 1);

        let row = 3;
        const display = this._displayTile();
        if (display)
            lm.attach(display, 0, row++, 4, 1);
        const sound = this._soundTile();
        if (sound)
            lm.attach(sound, 0, row++, 4, 1);

        // Toggles other extensions add to Quick Settings (e.g. GSConnect's
        // Mobile Devices), two per row.
        const external = this._externalItems();
        external.forEach((item, i) => {
            lm.attach(this._externalTile(item), (i % 2) * 2, row, 2, 1);
            if (i % 2 === 1 || i === external.length - 1)
                row++;
        });

        // Small tiles, four per row: power mode (when the machine has
        // profiles), the Super-as-Ctrl keyboard style, then screenshot,
        // settings and lock.
        const small = [];
        const power = this._firstItem(qs._powerProfiles);
        if (power?.visible) {
            small.push(smallToggle(power, 'Power Mode', () => {
                this.emit('request-close');
                openSettings('power');
            }));
        }
        if (GLib.find_program_in_path(KEYBOARD_STYLE))
            small.push(keyboardStyleTile());
        small.push(smallAction('applets-screenshooter-symbolic', 'Screenshot', () => {
            this.emit('request-close');
            // Let the menu close before the screenshot UI grabs input.
            GLib.timeout_add(GLib.PRIORITY_DEFAULT, 250, () => {
                Main.screenshotUI.open().catch(logError);
                return GLib.SOURCE_REMOVE;
            });
        }));
        small.push(smallAction('emblem-system-symbolic', 'Settings', () => {
            this.emit('request-close');
            openSettings();
        }));
        small.push(smallAction('system-lock-screen-symbolic', 'Lock', () => {
            this.emit('request-close');
            Main.screenShield?.lock(true);
        }));
        small.forEach((t, i) => lm.attach(t, i % 4, row + Math.floor(i / 4), 1, 1));
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

        const source = new Mpris.MprisSource();
        let player = null;
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
                art.child = new St.Icon({icon_name: 'audio-x-generic-symbolic', icon_size: 24});
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
                art.child = new St.Icon({gicon: new Gio.FileIcon({file: Gio.File.new_for_uri(url)}), icon_size: 44});
            } else {
                const appIcon = player.app?.create_icon_texture(44);
                art.child = appIcon ?? new St.Icon({icon_name: 'audio-x-generic-symbolic', icon_size: 24});
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
        GLib.timeout_add(GLib.PRIORITY_DEFAULT, 150, () => {
            if (t.get_stage())
                sync();
            return GLib.SOURCE_REMOVE;
        });
        sync();
        t.connect('destroy', () => {
            player?.disconnectObject(t);
            source.disconnectObject(t);
        });
        return t;
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
        this._holder.set_child(this._panel);
    }

    _destroyPanel() {
        this._panel?.destroy();
        this._panel = null;
    }

    destroy() {
        this.releaseIndicators();
        this._destroyPanel();
        super.destroy();
    }
});

export default class ParchaControlsExtension extends Extension {
    enable() {
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
