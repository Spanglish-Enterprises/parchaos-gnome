// SPDX-License-Identifier: GPL-3.0-or-later
/**
 * ParchaOS Global Menu
 *
 * A global application menu bar for GNOME Shell: an app-name
 * label with About/Hide/Quit, standard File/Edit/View/Go/Window/Help
 * menus, a system logo menu with real power actions, and a weather
 * indicator.
 *
 * An independent implementation written for ParchaOS from
 * docs/global-menu-rewrite-spec.md (a plain feature description) and
 * GNOME Shell's public extension APIs. The menus are described by a data
 * table (MENU_TABLE) and built by one generic loop.
 *
 * Compatible with GNOME Shell 45-50, Wayland.
 */

import { Extension } from 'resource:///org/gnome/shell/extensions/extension.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as ModalDialog from 'resource:///org/gnome/shell/ui/modalDialog.js';

import St from 'gi://St';
import Clutter from 'gi://Clutter';
import Shell from 'gi://Shell';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import GdkPixbuf from 'gi://GdkPixbuf';
import Meta from 'gi://Meta';
import GWeather from 'gi://GWeather';
import Geoclue from 'gi://Geoclue';
import * as Config from 'resource:///org/gnome/shell/misc/config.js';

// The adaptive bar tint awaits these two calls. GJS only lets a Gio async
// method be awaited (called without a callback) after it has been
// promisified, and nothing guarantees some other module already did it: a
// headless shell with just the ParchaOS extensions logged "Gio.File.read_async:
// At least 3 arguments required, but only 2 passed" and the bar never tinted.
Gio._promisify(Gio.File.prototype, 'read_async', 'read_finish');
Gio._promisify(Gio.File.prototype, 'load_contents_async', 'load_contents_finish');

// Clutter.get_default_backend() is gone from GNOME 51; the stage's context
// has the backend on both 50 and 51.
function backendOf() {
    return global.stage.context?.get_backend?.() ?? Clutter.get_default_backend();
}

const DEFAULT_APP_NAME = 'Parcher';
const DEFAULT_APP_ID = 'org.gnome.Nautilus.desktop';

// The public ParchaOS website (help, FAQ, bug reports).
const SITE_URL = 'https://parchaos.org';

// A small set of window identities that represent desktop-shell helper
// surfaces (icon grids, overlays) rather than real user applications --
// these should never be tracked as "the focused app."
const IGNORED_APP_IDS = [
    'com.rastersoft.ding', // Desktop Icons NG's own background surface
];

// ---------------------------------------------------------------------
// Synthetic keyboard input, used to trigger a focused app's own real
// keyboard shortcuts (Ctrl+C, Ctrl+1, etc.) from a menu click. This is a
// standard GNOME Shell technique (Clutter's virtual input device API);
// see e.g. any accessibility or automation extension for the same
// general pattern. One virtual keyboard is shared and dropped on disable.
// ---------------------------------------------------------------------
let _keyboard = null;

function sendKeyCombo(modifierKeyvals, keyval) {
    if (!_keyboard) {
        const seat = backendOf().get_default_seat();
        _keyboard = seat.create_virtual_device(Clutter.InputDeviceType.KEYBOARD_DEVICE);
    }
    const keyboard = _keyboard;

    for (const mod of modifierKeyvals)
        keyboard.notify_keyval(0, mod, Clutter.KeyState.PRESSED);
    keyboard.notify_keyval(0, keyval, Clutter.KeyState.PRESSED);
    keyboard.notify_keyval(0, keyval, Clutter.KeyState.RELEASED);
    for (const mod of [...modifierKeyvals].reverse())
        keyboard.notify_keyval(0, mod, Clutter.KeyState.RELEASED);
}

// Menu actions that are sent to the app as keyboard shortcuts. The same
// action needs different keys in different kinds of app: in a terminal
// Ctrl+C interrupts the running command, so Copy is Ctrl+Shift+C there,
// and the file-view items only mean something in the file manager.
// null = the app has no such command; the item is greyed out.
const CTRL = [Clutter.KEY_Control_L];
const CTRL_SHIFT = [Clutter.KEY_Control_L, Clutter.KEY_Shift_L];

const NONE = [];
const ALT = [Clutter.KEY_Alt_L];

const SHORTCUTS = {
    'new-window': {default: [CTRL, Clutter.KEY_n], terminal: [CTRL_SHIFT, Clutter.KEY_N]},
    'new-tab': {default: [CTRL, Clutter.KEY_t], terminal: [CTRL_SHIFT, Clutter.KEY_T]},
    'new-folder': {default: null, files: [CTRL_SHIFT, Clutter.KEY_N]},
    'open': {default: null, files: [NONE, Clutter.KEY_Return]},
    'get-info': {default: null, files: [CTRL, Clutter.KEY_i]},
    'rename': {default: null, files: [NONE, Clutter.KEY_F2]},
    'quick-look': {default: null, files: [NONE, Clutter.KEY_space]},
    'trash': {default: null, files: [NONE, Clutter.KEY_Delete]},
    'print': {default: [CTRL, Clutter.KEY_p], terminal: null},
    'undo': {default: [CTRL, Clutter.KEY_z], terminal: null},
    // Ctrl+Shift+Z is the redo GTK, Chromium, Electron and LibreOffice
    // all accept; Ctrl+Y isn't bound in most GTK 4 apps.
    'redo': {default: [CTRL_SHIFT, Clutter.KEY_Z], terminal: null},
    'cut': {default: [CTRL, Clutter.KEY_x], terminal: null},
    'copy': {default: [CTRL, Clutter.KEY_c], terminal: [CTRL_SHIFT, Clutter.KEY_C]},
    'paste': {default: [CTRL, Clutter.KEY_v], terminal: [CTRL_SHIFT, Clutter.KEY_V]},
    'select-all': {default: [CTRL, Clutter.KEY_a], terminal: [CTRL_SHIFT, Clutter.KEY_A]},
    'find': {default: [CTRL, Clutter.KEY_f], terminal: [CTRL_SHIFT, Clutter.KEY_F]},
    'settings': {default: [CTRL, Clutter.KEY_comma], terminal: [CTRL_SHIFT, Clutter.KEY_comma]},
    'view-icons': {default: null, files: [CTRL, Clutter.KEY_1]},
    'view-list': {default: null, files: [CTRL, Clutter.KEY_2]},
    'hidden-files': {default: null, files: [CTRL, Clutter.KEY_h]},
    'zoom-in': {default: [CTRL, Clutter.KEY_plus], terminal: [CTRL_SHIFT, Clutter.KEY_plus]},
    'zoom-out': {default: [CTRL, Clutter.KEY_minus], terminal: [CTRL, Clutter.KEY_minus]},
    'zoom-reset': {default: [CTRL, Clutter.KEY_0], terminal: [CTRL, Clutter.KEY_0]},
    'reload': {default: [CTRL, Clutter.KEY_r], terminal: null},
    'back': {default: [ALT, Clutter.KEY_Left], terminal: null},
    'forward': {default: [ALT, Clutter.KEY_Right], terminal: null},
    'enclosing': {default: null, files: [ALT, Clutter.KEY_Up]},
    'go-to-folder': {default: null, files: [CTRL, Clutter.KEY_l]},
};

// What each shortcut is called in a menu, in the modifier-and-key notation
// of the keyboard style in use.
const HINTS = {
    'new-window': 'c N', 'new-tab': 'c T', 'new-folder': 'cs N', 'open': 'c O', 'get-info': 'c I',
    'rename': 'F2', 'quick-look': 'Space', 'trash': 'c \u232B', 'print': 'c P', 'undo': 'c Z', 'redo': 'cs Z',
    'cut': 'c X', 'copy': 'c C', 'paste': 'c V', 'select-all': 'c A', 'find': 'c F', 'settings': 'c ,',
    'view-icons': 'c 1', 'view-list': 'c 2', 'hidden-files': 'cs .', 'zoom-in': 'c +', 'zoom-out': 'c \u2212',
    'zoom-reset': 'c 0', 'reload': 'c R', 'back': 'c [', 'forward': 'c ]', 'enclosing': 'c \u2191',
    'go-to-folder': 'cs G',
};

// "c N" -> the text shown next to a menu item. With the Super-as-Ctrl
// keyboard style the command key is what people press, so symbols; with the
// standard style the keys are named.
function hintText(notation) {
    if (!notation)
        return '';
    const [mods, key] = notation.includes(' ') ? notation.split(' ') : ['', notation];
    if (!mods)
        return key;
    const symbols = keyboardStyle() === 'super-ctrl';
    const parts = [];
    if (symbols) {
        if (mods.includes('k'))
            parts.push('\u2303');
        if (mods.includes('a'))
            parts.push('\u2325');
        if (mods.includes('s'))
            parts.push('\u21E7');
        if (mods.includes('c'))
            parts.push('\u2318');
        return parts.join('\u200A') + '\u200A' + key;
    }
    if (mods.includes('k'))
        parts.push('Super');
    if (mods.includes('c'))
        parts.push('Ctrl');
    if (mods.includes('a'))
        parts.push('Alt');
    if (mods.includes('s'))
        parts.push('Shift');
    return [...parts, key].join('+');
}

let _keyboardStyle = {value: 'super-ctrl', read: 0};
function keyboardStyle() {
    const now = GLib.get_monotonic_time();
    if (now - _keyboardStyle.read > 5_000_000) {
        _keyboardStyle.read = now;
        try {
            const path = GLib.build_filenamev([GLib.get_user_config_dir(), 'parchaos', 'keyboard-style']);
            const [ok, bytes] = GLib.file_get_contents(path);
            if (ok)
                _keyboardStyle.value = new TextDecoder().decode(bytes).trim() || 'super-ctrl';
        } catch (e) {
            // No state file yet: the default style.
        }
    }
    return _keyboardStyle.value === 'standard' ? 'standard' : 'super-ctrl';
}

const TERMINAL_IDS = /^(org\.gnome\.(terminal|ptyxis|console)|kgx|com\.mitchellh\.ghostty|org\.wezfurlong\.wezterm|kitty|alacritty|foot|xterm|org\.kde\.konsole|konsole|com\.gexperts\.tilix|com\.raggesilver\.blackbox)/i;
const FILES_IDS = /^org\.gnome\.nautilus/i;

function appKind(window) {
    if (!window)
        return null;
    const app = Shell.WindowTracker.get_default().get_window_app(window);
    const ids = [
        app?.get_id()?.replace(/\.desktop$/, ''),
        window.get_gtk_application_id?.(),
        window.get_wm_class?.(),
    ].filter(Boolean);
    if (ids.some(id => TERMINAL_IDS.test(id)))
        return 'terminal';
    if (ids.some(id => FILES_IDS.test(id)))
        return 'files';
    return 'default';
}

function shortcutFor(action, kind) {
    if (!kind)
        return null;
    const entry = SHORTCUTS[action];
    return kind in entry ? entry[kind] : entry.default;
}

function openHome() {
    try {
        Gio.AppInfo.launch_default_for_uri(GLib.filename_to_uri(GLib.get_home_dir(), null), null);
    } catch (e) {
        console.error('[ParchaOSGlobalMenu] Failed to open home folder:', e);
    }
}

function openSpecialDir(dirType) {
    const path = GLib.get_user_special_dir(dirType);
    if (!path)
        return;
    try {
        Gio.AppInfo.launch_default_for_uri(GLib.filename_to_uri(path, null), null);
    } catch (e) {
        console.error('[ParchaOSGlobalMenu] Failed to open folder:', e);
    }
}

// ---------------------------------------------------------------------
// A single top-bar text button (File, Edit, ... or the bold app-name
// button). Thin wrapper around PanelMenu.Button with just a label.
// ---------------------------------------------------------------------
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

// ---------------------------------------------------------------------
// Adaptive bar tint. The bar switches between
// light text (over dark wallpaper) and dark text (over light wallpaper).
// The strip of wallpaper under the bar on the primary monitor is sampled
// from the background image itself, with the same zoom/scale placement
// GNOME uses, and the text color with the better WCAG contrast against
// its average luminance wins. Re-sampled whenever the wallpaper, its
// placement, the color scheme or the monitor layout changes.
// ---------------------------------------------------------------------
const SAMPLE_WIDTH = 480;          // wallpaper is decoded at this width
const LIGHT_BAR_THRESHOLD = 0.22;  // WCAG crossover is ~0.18; bias to white text

function srgbToLinear(c) {
    c /= 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
}

function relativeLuminance(r, g, b) {
    return 0.2126 * srgbToLinear(r) + 0.7152 * srgbToLinear(g) + 0.0722 * srgbToLinear(b);
}

function parseColor(str) {
    const m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})/i.exec(str ?? '');
    return m ? m.slice(1).map(h => parseInt(h, 16)) : [0, 0, 0];
}

class MenuBarTint {
    constructor(panel) {
        this._panel = panel;
        this._cancellable = new Gio.Cancellable();
        this._background = new Gio.Settings({schema_id: 'org.gnome.desktop.background'});
        this._interface = new Gio.Settings({schema_id: 'org.gnome.desktop.interface'});
        this._fileMonitor = null;
        this._timeoutId = 0;
        this._light = false;
        this._signals = [
            // The overview (and lock screen) draw their own dark backdrop
            // behind the bar, so it goes back to light text there.
            [Main.overview, Main.overview.connect('showing', () => this._apply())],
            [Main.overview, Main.overview.connect('hidden', () => this._apply())],
            [Main.sessionMode, Main.sessionMode.connect('updated', () => this._apply())],
            [this._background, this._background.connect('changed', () => this._queue())],
            [this._interface, this._interface.connect('changed::color-scheme', () => this._queue())],
            [Main.layoutManager, Main.layoutManager.connect('monitors-changed', () => this._queue())],
        ];
        this._queue();
    }

    destroy() {
        this._cancellable.cancel();
        if (this._timeoutId)
            GLib.source_remove(this._timeoutId);
        this._timeoutId = 0;
        for (const [obj, id] of this._signals)
            obj.disconnect(id);
        this._signals = [];
        this._fileMonitor?.cancel();
        this._fileMonitor = null;
        this._panel.remove_style_class_name('parchaos-menubar-light');
    }

    // Wallpaper tools often rewrite the same file (GNOME's own
    // ~/.config/background), so settings changes alone aren't enough.
    _queue() {
        if (this._timeoutId)
            GLib.source_remove(this._timeoutId);
        this._timeoutId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 300, () => {
            this._timeoutId = 0;
            this._update().catch(e => console.warn(`ParchaOS menu bar tint: ${e.message}`));
            return GLib.SOURCE_REMOVE;
        });
    }

    _pictureUri() {
        const dark = this._interface.get_string('color-scheme') === 'prefer-dark';
        const uri = this._background.get_string(dark ? 'picture-uri-dark' : 'picture-uri');
        return uri || this._background.get_string('picture-uri');
    }

    _watch(file) {
        if (this._fileMonitor && this._watched?.equal(file))
            return;
        this._fileMonitor?.cancel();
        this._watched = file;
        try {
            this._fileMonitor = file.monitor_file(Gio.FileMonitorFlags.NONE, null);
            this._fileMonitor.connect('changed', (_m, _f, _o, event) => {
                if (event === Gio.FileMonitorEvent.CHANGES_DONE_HINT || event === Gio.FileMonitorEvent.CREATED)
                    this._queue();
            });
        } catch {
            this._fileMonitor = null;
        }
    }

    async _loadPixbuf(file) {
        // GNOME dynamic wallpapers are XML slideshows; use the first image.
        if (file.get_path()?.endsWith('.xml')) {
            const [bytes] = await file.load_contents_async(this._cancellable);
            const m = /<file>\s*([^<]+?)\s*<\/file>/.exec(new TextDecoder().decode(bytes));
            if (!m)
                return null;
            file = Gio.File.new_for_path(m[1]);
        }
        const stream = await file.read_async(GLib.PRIORITY_DEFAULT, this._cancellable);
        return new Promise((resolve, reject) => {
            GdkPixbuf.Pixbuf.new_from_stream_at_scale_async(stream, SAMPLE_WIDTH, -1, true,
                this._cancellable, (_src, res) => {
                    try {
                        resolve(GdkPixbuf.Pixbuf.new_from_stream_finish(res));
                    } catch (e) {
                        reject(e);
                    }
                });
        });
    }

    // Average relative luminance of the part of the image that ends up
    // under the bar, given GNOME's picture-options placement.
    _stripLuminance(pixbuf, monitor, barHeight) {
        const w = pixbuf.get_width(), h = pixbuf.get_height();
        const opt = this._background.get_string('picture-options');
        let x0 = 0, x1 = w, y0 = 0, y1;

        if (opt === 'zoom' || opt === 'spanned') {
            const scale = Math.max(monitor.width / w, monitor.height / h);
            const cropX = (w * scale - monitor.width) / 2 / scale;
            const cropY = (h * scale - monitor.height) / 2 / scale;
            x0 = cropX;
            x1 = w - cropX;
            y0 = cropY;
            y1 = cropY + barHeight / scale;
        } else if (opt === 'scaled' || opt === 'centered') {
            const scale = opt === 'scaled' ? Math.min(monitor.width / w, monitor.height / h) : 1;
            const top = (monitor.height - h * scale) / 2;
            if (top >= barHeight) // bar sits over the plain primary color
                return relativeLuminance(...parseColor(this._background.get_string('primary-color')));
            y0 = Math.max(0, -top / scale);
            y1 = y0 + barHeight / scale;
        } else if (opt === 'none') {
            return relativeLuminance(...parseColor(this._background.get_string('primary-color')));
        } else { // stretched, wallpaper (tiled)
            y1 = barHeight * h / monitor.height;
        }

        x0 = Math.max(0, Math.floor(x0));
        x1 = Math.min(w, Math.ceil(x1));
        y0 = Math.max(0, Math.floor(y0));
        y1 = Math.min(h, Math.max(y0 + 1, Math.ceil(y1)));

        const pixels = pixbuf.get_pixels();
        const stride = pixbuf.get_rowstride();
        const n = pixbuf.get_n_channels();
        let sum = 0, count = 0;
        for (let y = y0; y < y1; y++) {
            for (let x = x0; x < x1; x++) {
                const i = y * stride + x * n;
                sum += relativeLuminance(pixels[i], pixels[i + 1], pixels[i + 2]);
                count++;
            }
        }
        return count ? sum / count : 0;
    }

    async _update() {
        const monitor = Main.layoutManager.primaryMonitor;
        if (!monitor)
            return;
        let luminance = 0;
        const uri = this._pictureUri();
        if (uri && this._background.get_string('picture-options') !== 'none') {
            const file = Gio.File.new_for_uri(uri);
            this._watch(file);
            const pixbuf = await this._loadPixbuf(file);
            if (!pixbuf)
                return;
            luminance = this._stripLuminance(pixbuf, monitor, this._panel.height || 32);
        } else {
            luminance = relativeLuminance(...parseColor(this._background.get_string('primary-color')));
        }

        this._light = luminance > LIGHT_BAR_THRESHOLD;
        console.debug(`ParchaOS menu bar tint: luminance ${luminance.toFixed(3)} -> ${this._light ? 'light' : 'dark'}`);
        this._apply();
    }

    _apply() {
        const overDesktop = !Main.overview.visible && !Main.overview.animationInProgress &&
            Main.sessionMode.currentMode === 'user';
        if (this._light && overDesktop)
            this._panel.add_style_class_name('parchaos-menubar-light');
        else
            this._panel.remove_style_class_name('parchaos-menubar-light');
    }
}

const MenuBarButton = GObject.registerClass({
    GTypeName: 'ParchaOSMenuBarButton',
}, class MenuBarButton extends PanelMenu.Button {
    _init(labelText, { bold = false } = {}) {
        super._init(0.0, labelText, false);

        this._label = new St.Label({
            text: labelText,
            y_align: Clutter.ActorAlign.CENTER,
            style_class: bold ? 'parchaos-menubar-app-label' : 'parchaos-menubar-label',
        });
        this.add_child(this._label);
    }

    setLabelText(text) {
        this._label.set_text(text);
    }
});

// ---------------------------------------------------------------------
// Weather indicator: real location via Geoclue, real conditions via
// GWeather, no API key. Hidden until real data arrives.
// ---------------------------------------------------------------------
const WeatherIndicator = GObject.registerClass({
    GTypeName: 'ParchaOSWeatherIndicator',
}, class WeatherIndicator extends PanelMenu.Button {
    _init() {
        super._init(0.0, 'Weather', false);

        const box = new St.BoxLayout({
            style_class: 'parchaos-weather-box',
            y_align: Clutter.ActorAlign.CENTER,
        });
        this._conditionIcon = new St.Icon({
            icon_name: 'weather-clear-symbolic',
            style_class: 'system-status-icon parchaos-weather-icon',
            icon_size: 16,
        });
        this._label = new St.Label({
            text: '',
            y_align: Clutter.ActorAlign.CENTER,
            style_class: 'parchaos-weather-label',
        });
        box.add_child(this._conditionIcon);
        box.add_child(this._label);
        this.add_child(box);

        this.visible = false;

        this._weatherInfo = null;
        this._weatherUpdatedId = 0;
        this._geoclueSimple = null;
        this._locationId = 0;
        this._cancellable = new Gio.Cancellable();
        this._updateTimerId = 0;

        // The popover: the place and temperature, an alert, the next five hours and
        // up to two other places (ticket #173), then "Open Weather". The data credit
        // stays (MET Norway's data is CC BY 4.0 and needs attribution).
        this._pop = new St.BoxLayout({
            vertical: true,
            style_class: 'parchaos-weather-pop',
        });
        const content = new PopupMenu.PopupBaseMenuItem({ reactive: false, can_focus: false });
        content.add_style_class_name('parchaos-weather-pop-item');
        content.add_child(this._pop);
        this.menu.addMenuItem(content);
        const openItem = new PopupMenu.PopupMenuItem('Open Weather');
        openItem.add_style_class_name('parchaos-weather-open');
        openItem.connect('activate', () => this._openWeatherApp());
        this.menu.addMenuItem(openItem);
        const creditItem = new PopupMenu.PopupMenuItem('Weather data: MET Norway', { reactive: false });
        creditItem.add_style_class_name('parchaos-weather-credit');
        this.menu.addMenuItem(creditItem);
        this._data = null;
        this._snapshotBusy = false;
        this.menu.connect('open-state-changed', (_m, open) => {
            if (open)
                this._refreshSnapshot();
        });
        this.connect('destroy', () => this._onDestroy());

        const fixture = GLib.getenv('PARCHAOS_WEATHER_FIXTURE');   // tests: a fixed snapshot
        if (fixture) {
            this._useFixture(fixture);
        } else {
            const place = GLib.getenv('PARCHAOS_WEATHER_PLACE');   // tests: "lat,lon" instead of Geoclue
            if (place)
                this._setPlace(...place.split(',').map(Number));
            else
                this._startGeolocation();
            this._updateTimerId = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 900, () => {
                this._weatherInfo?.update();
                this._refreshSnapshot();
                return GLib.SOURCE_CONTINUE;
            });
        }
    }

    _useFixture(path) {
        try {
            const [ok, bytes] = GLib.file_get_contents(path);
            if (ok)
                this._applyData(JSON.parse(new TextDecoder().decode(bytes)));
        } catch (e) {
            console.error('[ParchaOSGlobalMenu] Bad weather fixture:', e);
        }
    }

    // Parcha Sky prints the popover's data (it shares the app's forecast cache and
    // adds alerts and the other places); GWeather alone fills the top when the app
    // is not installed.
    _refreshSnapshot() {
        if (GLib.getenv('PARCHAOS_WEATHER_FIXTURE') || this._snapshotBusy || !this._location)
            return;
        this._snapshotBusy = true;
        try {
            const proc = Gio.Subprocess.new(
                ['parchaos-sky', '--snapshot', String(this._location.lat), String(this._location.lon),
                    this._location.name],
                Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE);
            proc.communicate_utf8_async(null, this._cancellable, (p, res) => {
                this._snapshotBusy = false;
                try {
                    const [, out] = p.communicate_utf8_finish(res);
                    const data = JSON.parse(out);
                    if (!data.error)
                        this._applyData(data);
                } catch (e) {
                    // cancelled, or no usable answer: keep what is shown
                }
            });
        } catch (e) {
            this._snapshotBusy = false;   // parchaos-sky is not installed
        }
    }

    _applyData(data) {
        this._data = data;
        this._conditionIcon.icon_name = data.alert ? 'dialog-warning-symbolic' : data.icon;
        this._label.set_text(this._fmtTemp(data.temp, data.imperial));
        this.visible = true;
        this._buildPopover(data);
    }

    _fmtTemp(c, imperial) {
        if (c === null || c === undefined)
            return '–';
        return imperial ? `${Math.round(c * 9 / 5 + 32)}°F` : `${Math.round(c)}°C`;
    }

    _deg(c, imperial) {
        if (c === null || c === undefined)
            return '–';
        return `${Math.round(imperial ? c * 9 / 5 + 32 : c)}°`;
    }

    _buildPopover(d) {
        this._pop.destroy_all_children();
        const label = (text, cls, extra = {}) => new St.Label({ text, style_class: cls, ...extra });
        const rule = () => this._pop.add_child(new St.Widget({ style_class: 'parchaos-weather-rule' }));

        // place + temperature on the left, condition and the day's range on the right
        const head = new St.BoxLayout({ style_class: 'parchaos-weather-head' });
        const left = new St.BoxLayout({ vertical: true, x_expand: true });
        const place = new St.BoxLayout();
        place.add_child(label(d.place, 'parchaos-weather-place', { y_align: Clutter.ActorAlign.CENTER }));
        place.add_child(new St.Icon({ icon_name: 'find-location-symbolic', icon_size: 12,
            style_class: 'parchaos-weather-locator', y_align: Clutter.ActorAlign.CENTER }));
        left.add_child(place);
        left.add_child(label(this._deg(d.temp, d.imperial), 'parchaos-weather-big'));
        head.add_child(left);
        const right = new St.BoxLayout({ vertical: true, x_align: Clutter.ActorAlign.END });
        right.add_child(new St.Icon({ icon_name: d.icon, icon_size: 28, x_align: Clutter.ActorAlign.END }));
        right.add_child(label(d.cond, 'parchaos-weather-cond', { x_align: Clutter.ActorAlign.END }));
        right.add_child(label(`H:${this._deg(d.hi, d.imperial)} L:${this._deg(d.lo, d.imperial)}`,
            'parchaos-weather-range', { x_align: Clutter.ActorAlign.END }));
        head.add_child(right);
        this._pop.add_child(head);

        if (d.alert) {
            rule();
            const row = new St.BoxLayout({ style_class: 'parchaos-weather-alert' });
            row.add_child(new St.Icon({ icon_name: 'dialog-warning-symbolic', icon_size: 16 }));
            row.add_child(label(d.alert, 'parchaos-weather-alert-text', { y_align: Clutter.ActorAlign.CENTER }));
            this._pop.add_child(row);
        }

        if (d.hours?.length) {
            rule();
            const hours = new St.BoxLayout({ style_class: 'parchaos-weather-hours' });
            for (const h of d.hours) {
                const col = new St.BoxLayout({ vertical: true, x_expand: true,
                    style_class: 'parchaos-weather-hour' });
                const when = GLib.DateTime.new_from_unix_local(h.time);
                col.add_child(label(when.format(d.imperial ? '%-I %p' : '%H:%M'), 'parchaos-weather-hour-name',
                    { x_align: Clutter.ActorAlign.CENTER }));
                col.add_child(new St.Icon({ icon_name: h.icon, icon_size: 28, x_align: Clutter.ActorAlign.CENTER }));
                // the chance of rain when the forecast gives one, else how much is coming
                let rain = '';
                if (h.pop !== null && h.pop !== undefined && h.pop >= 20)
                    rain = `${Math.round(h.pop)}%`;
                else if ((h.precip ?? 0) >= (d.imperial ? 0.25 : 0.2))   // a hundredth of an inch
                    rain = d.imperial ? `${(h.precip / 25.4).toFixed(2).replace(/^0/, '')}″` : `${h.precip.toFixed(1)} mm`;
                col.add_child(label(rain, 'parchaos-weather-rain', { x_align: Clutter.ActorAlign.CENTER }));
                col.add_child(label(this._deg(h.temp, d.imperial), 'parchaos-weather-hour-temp',
                    { x_align: Clutter.ActorAlign.CENTER }));
                hours.add_child(col);
            }
            this._pop.add_child(hours);
        }

        if (d.others?.length) {
            rule();
            for (const o of d.others) {
                const row = new St.BoxLayout({ style_class: 'parchaos-weather-other' });
                row.add_child(label(o.name, 'parchaos-weather-other-name',
                    { x_expand: true, y_align: Clutter.ActorAlign.CENTER }));
                row.add_child(new St.Icon({ icon_name: o.icon, icon_size: 26, style_class: 'parchaos-weather-other-icon' }));
                row.add_child(label(this._deg(o.temp, d.imperial), 'parchaos-weather-other-temp',
                    { y_align: Clutter.ActorAlign.CENTER }));
                this._pop.add_child(row);
            }
        }
        rule();
    }

    _startGeolocation() {
        const appId = 'org.parchaos.globalmenu';
        const cb = (_src, result) => this._onGeoclueSimpleReady(result);
        try {
            if (Geoclue.Simple.new_with_thresholds)
                Geoclue.Simple.new_with_thresholds(appId, Geoclue.AccuracyLevel.CITY, 0, 100, this._cancellable, cb);
            else
                Geoclue.Simple.new(appId, Geoclue.AccuracyLevel.CITY, this._cancellable, cb);
        } catch (e) {
            console.error('[ParchaOSGlobalMenu] Failed to start Geoclue for weather:', e);
        }
    }

    _onGeoclueSimpleReady(result) {
        try {
            this._geoclueSimple = Geoclue.Simple.new_finish(result);
        } catch (e) {
            // Location turned off (or not allowed) is a normal choice: the
            // weather just stays hidden.
            if (!e.matches?.(Gio.IOErrorEnum, Gio.IOErrorEnum.CANCELLED))
                console.debug(`[ParchaOSGlobalMenu] No location for weather: ${e.message}`);
            return;
        }
        this._locationId = this._geoclueSimple.connect('notify::location',
            () => this._onLocationUpdated());
        this._onLocationUpdated();
    }

    _onLocationUpdated() {
        const geoclueLocation = this._geoclueSimple?.get_location();
        if (geoclueLocation)
            this._setPlace(geoclueLocation.latitude, geoclueLocation.longitude);
    }

    _setPlace(latitude, longitude) {
        const world = GWeather.Location.get_world();
        if (!world)
            return;

        const location = world.find_nearest_city(latitude, longitude);
        if (!location)
            return;
        this._location = {
            lat: latitude,
            lon: longitude,
            name: location.get_city_name() || location.get_name(),
        };

        if (this._weatherInfo && this._weatherUpdatedId)
            this._weatherInfo.disconnect(this._weatherUpdatedId);

        this._weatherInfo = new GWeather.Info({
            application_id: 'org.parchaos.globalmenu',
            contact_info: SITE_URL,
            location,
            enabled_providers: GWeather.Provider.MET_NO | GWeather.Provider.METAR,
        });
        this._weatherUpdatedId = this._weatherInfo.connect('updated', () => this._onWeatherUpdated());
        this._weatherInfo.update();
    }

    _onWeatherUpdated() {
        if (!this._weatherInfo?.is_valid())
            return;
        // The snapshot (when Parcha Sky is installed) fills the whole popover; until it
        // arrives, or without it, GWeather's own reading fills the top.
        if (!this._data) {
            this._conditionIcon.icon_name = this._weatherInfo.get_symbolic_icon_name();
            this._label.set_text(this._weatherInfo.get_temp_summary());
            this.visible = true;
            this._buildBasicPopover();
        }
        this._refreshSnapshot();
    }

    _buildBasicPopover() {
        this._pop.destroy_all_children();
        const head = new St.BoxLayout({ style_class: 'parchaos-weather-head' });
        const left = new St.BoxLayout({ vertical: true, x_expand: true });
        left.add_child(new St.Label({ text: this._location?.name ?? this._weatherInfo.get_location_name(),
            style_class: 'parchaos-weather-place' }));
        left.add_child(new St.Label({ text: this._weatherInfo.get_temp_summary(), style_class: 'parchaos-weather-big' }));
        head.add_child(left);
        this._pop.add_child(head);
    }

    _openWeatherApp() {
        try {
            // Parcha Sky, ParchaOS's weather app; GNOME Weather where it isn't installed
            const apps = Shell.AppSystem.get_default();
            const app = apps.lookup_app('org.parchaos.Sky.desktop') ??
                apps.lookup_app('org.gnome.Weather.desktop');
            app?.activate();
        } catch (e) {
            console.error('[ParchaOSGlobalMenu] Failed to open Weather app:', e);
        }
    }

    _onDestroy() {
        if (this._updateTimerId) {
            GLib.source_remove(this._updateTimerId);
            this._updateTimerId = 0;
        }
        // A Geoclue client that's still starting would otherwise call back
        // into this destroyed indicator.
        this._cancellable.cancel();
        if (this._geoclueSimple && this._locationId)
            this._geoclueSimple.disconnect(this._locationId);
        this._locationId = 0;
        if (this._weatherInfo && this._weatherUpdatedId)
            this._weatherInfo.disconnect(this._weatherUpdatedId);
        this._weatherUpdatedId = 0;
        this._weatherInfo = null;
        this._geoclueSimple = null;
    }
});

// ---------------------------------------------------------------------
// A simple confirm/cancel modal for power actions.
// ---------------------------------------------------------------------
// ModalDialog is a GObject class: subclasses must be registered, or
// constructing one throws "Tried to construct an object without a GType"
// (which silently broke Log Out/Restart/Shut Down).
const ConfirmDialog = GObject.registerClass(
class ConfirmDialog extends ModalDialog.ModalDialog {
    _init(message, onConfirm) {
        super._init({ styleClass: 'parchaos-confirm-dialog' });

        const label = new St.Label({
            text: message,
            style_class: 'parchaos-confirm-dialog-label',
        });
        this.contentLayout.add_child(label);

        this.setButtons([
            {
                label: 'Cancel',
                action: () => this.close(),
                key: Clutter.KEY_Escape,
            },
            {
                label: 'Confirm',
                action: () => {
                    this.close();
                    onConfirm();
                },
                default: true,
            },
        ]);
    }
});

// ---------------------------------------------------------------------
// A menu row with the command on the left and its keyboard shortcut (or a
// small badge) on the right, dimmed.
// ---------------------------------------------------------------------
const MenuEntry = GObject.registerClass({
    GTypeName: 'ParchaOSMenuEntry',
}, class MenuEntry extends PopupMenu.PopupBaseMenuItem {
    _init(text, hint = '', badge = false, icon = null) {
        super._init();
        if (icon) {
            this.add_child(new St.Icon({
                icon_name: icon,
                icon_size: 16,
                y_align: Clutter.ActorAlign.CENTER,
                style_class: 'parchaos-menu-row-icon',
            }));
        }
        this.label = new St.Label({
            text,
            x_expand: true,
            y_align: Clutter.ActorAlign.CENTER,
        });
        this.add_child(this.label);
        this.hint = new St.Label({
            text: hint,
            style_class: badge ? 'parchaos-menu-badge' : 'parchaos-menu-hint',
            y_align: Clutter.ActorAlign.CENTER,
            visible: hint !== '',
        });
        if (!badge)
            this.hint.opacity = 140;
        if (badge)
            this.hint.set_style('background-color: rgba(128, 128, 128, 0.38); border-radius: 999px;');
        this.add_child(this.hint);
        this.accessible_name = text;
    }

    setHint(text) {
        this.hint.text = text;
        this.hint.visible = text !== '';
    }
});

// ---------------------------------------------------------------------
// Force Quit: a list of the running apps; the chosen one is killed.
// ---------------------------------------------------------------------
const ForceQuitDialog = GObject.registerClass(
class ForceQuitDialog extends ModalDialog.ModalDialog {
    _init() {
        super._init({ styleClass: 'parchaos-confirm-dialog' });
        this.contentLayout.add_child(new St.Label({
            text: 'Force Quit Applications',
            style_class: 'parchaos-about-title',
        }));
        const hint = new St.Label({
            text: 'If an app is not responding, choose it and press Force Quit.',
            style_class: 'parchaos-confirm-dialog-label',
        });
        hint.clutter_text.line_wrap = true;
        this.contentLayout.add_child(hint);

        this._selected = null;
        this._rows = [];
        const list = new St.BoxLayout({ orientation: Clutter.Orientation.VERTICAL, style_class: 'parchaos-forcequit-list' });
        const apps = Shell.AppSystem.get_default().get_running()
            .filter(app => app.get_pids().length > 0);
        apps.sort((a, b) => a.get_name().localeCompare(b.get_name()));
        for (const app of apps) {
            const inner = new St.BoxLayout({ style: 'spacing: 10px;', x_align: Clutter.ActorAlign.START });
            inner.add_child(new St.Icon({ gicon: app.get_icon(), icon_size: 22 }));
            inner.add_child(new St.Label({ text: app.get_name(), y_align: Clutter.ActorAlign.CENTER }));
            const row = new St.Button({
                style_class: 'parchaos-forcequit-row',
                x_expand: true,
                can_focus: true,
                toggle_mode: true,
                child: inner,
            });
            row.connect('clicked', () => {
                for (const other of this._rows)
                    other.checked = other === row;
                this._selected = app;
                this._quit.reactive = true;
                this._quit.can_focus = true;
                this._quit.opacity = 255;
            });
            this._rows.push(row);
            list.add_child(row);
        }
        if (apps.length === 0) {
            list.add_child(new St.Label({
                text: 'No apps are open.',
                style_class: 'parchaos-confirm-dialog-label',
            }));
        }
        this.contentLayout.add_child(new St.ScrollView({
            style_class: 'parchaos-forcequit-scroll',
            child: list,
            overlay_scrollbars: true,
        }));

        this.addButton({ label: 'Cancel', action: () => this.close(), key: Clutter.KEY_Escape });
        this._quit = this.addButton({
            label: 'Force Quit',
            action: () => {
                const app = this._selected;
                this.close();
                for (const pid of app?.get_pids() ?? [])
                    GLib.spawn_command_line_async(`kill -9 ${pid}`);
            },
            default: true,
        });
        this._quit.opacity = 120;
        this._quit.reactive = false;
    }
});

// ---------------------------------------------------------------------
// The menus after the app name. An entry either sends the focused app one
// of SHORTCUTS' actions, runs a function (given the tracked window), or is
// a separator.
// ---------------------------------------------------------------------
const SEPARATOR = null;

function openSiteLink(path) {
    try {
        Gio.AppInfo.launch_default_for_uri(`${SITE_URL}${path}`, null);
    } catch (e) {
        console.error('[ParchaOSGlobalMenu] Failed to open', path, e);
    }
}

function openSystemSettings() {
    const apps = Shell.AppSystem.get_default();
    (apps.lookup_app('org.gnome.Settings.desktop') ??
        apps.lookup_app('gnome-control-center.desktop'))?.activate();
}

// Mutter 18 (GNOME 50) replaced get_maximized() with is_maximized() and
// dropped the MaximizeFlags argument to maximize()/unmaximize().
function isMaximized(window) {
    if (typeof window.is_maximized === 'function')
        return window.is_maximized();
    return window.get_maximized() !== 0;
}

function setMaximized(window, maximized) {
    const flags = typeof window.is_maximized === 'function' ? [] : [Meta.MaximizeFlags.BOTH];
    if (maximized)
        window.maximize(...flags);
    else
        window.unmaximize(...flags);
}

function toggleMaximized(window) {
    if (!window)
        return;
    setMaximized(window, !isMaximized(window));
}

function openUri(uri) {
    try {
        Gio.AppInfo.launch_default_for_uri(uri, null);
    } catch (e) {
        console.error('[ParchaOSGlobalMenu] Failed to open', uri, e);
    }
}

function tileWindow(window, side) {
    if (!window)
        return;
    const area = window.get_work_area_current_monitor();
    if (isMaximized(window))
        setMaximized(window, false);
    const width = Math.floor(area.width / 2);
    window.move_resize_frame(false, side === 'left' ? area.x : area.x + width, area.y, width, area.height);
}

function centerWindow(window) {
    if (!window)
        return;
    const area = window.get_work_area_current_monitor();
    const rect = window.get_frame_rect();
    window.move_frame(false, area.x + Math.floor((area.width - rect.width) / 2),
        area.y + Math.floor((area.height - rect.height) / 2));
}

function bringAllToFront(window) {
    const app = window ? Shell.WindowTracker.get_default().get_window_app(window) : null;
    for (const w of app?.get_windows() ?? [])
        w.raise();
}

// The last few documents and folders opened, newest first.
function recentItems(limit = 10) {
    try {
        const file = GLib.build_filenamev([GLib.get_user_data_dir(), 'recently-used.xbel']);
        const marks = new GLib.BookmarkFile();
        marks.load_from_file(file);
        const items = marks.get_uris().map(uri => ({
            uri,
            title: marks.get_title(uri) || GLib.path_get_basename(GLib.filename_from_uri(uri)[0]),
            when: marks.get_modified(uri),
        }));
        items.sort((a, b) => b.when - a.when);
        return items.slice(0, limit);
    } catch (e) {
        return [];
    }
}

// How many updates are waiting, written by parchaos-updates-check.
function pendingUpdates() {
    try {
        const path = GLib.build_filenamev([GLib.get_user_cache_dir(), 'parchaos', 'updates-count']);
        const [ok, bytes] = GLib.file_get_contents(path);
        return ok ? parseInt(new TextDecoder().decode(bytes).trim(), 10) || 0 : 0;
    } catch (e) {
        return 0;
    }
}

// hint: shown next to the item when the item is not a SHORTCUTS action.
const MENU_TABLE = [
    {
        role: 'file', title: 'File', items: [
            { label: 'New Window', shortcut: 'new-window' },
            { label: 'New Tab', shortcut: 'new-tab' },
            { label: 'New Folder', shortcut: 'new-folder' },
            SEPARATOR,
            { label: 'Open', shortcut: 'open' },
            { label: 'Get Info', shortcut: 'get-info' },
            { label: 'Rename', shortcut: 'rename' },
            { label: 'Quick Look', shortcut: 'quick-look' },
            SEPARATOR,
            { label: 'Move to Trash', shortcut: 'trash' },
            SEPARATOR,
            { label: 'Print\u2026', shortcut: 'print' },
            // Closed directly: Ctrl+W closes a tab in browsers and does
            // nothing in a terminal.
            { label: 'Close Window', hint: 'c W', run: w => w?.delete(global.get_current_time()) },
        ],
    },
    {
        role: 'edit', title: 'Edit', items: [
            { label: 'Undo', shortcut: 'undo' },
            { label: 'Redo', shortcut: 'redo' },
            SEPARATOR,
            { label: 'Cut', shortcut: 'cut' },
            { label: 'Copy', shortcut: 'copy' },
            { label: 'Paste', shortcut: 'paste' },
            { label: 'Select All', shortcut: 'select-all' },
            SEPARATOR,
            { label: 'Find\u2026', shortcut: 'find' },
        ],
    },
    {
        role: 'view', title: 'View', items: [
            { label: 'as Icons', shortcut: 'view-icons' },
            { label: 'as List', shortcut: 'view-list' },
            SEPARATOR,
            { label: 'Show Hidden Files', shortcut: 'hidden-files' },
            SEPARATOR,
            { label: 'Zoom In', shortcut: 'zoom-in' },
            { label: 'Zoom Out', shortcut: 'zoom-out' },
            { label: 'Actual Size', shortcut: 'zoom-reset' },
            SEPARATOR,
            { label: 'Reload', shortcut: 'reload' },
            { label: 'Enter Full Screen', run: w => w && (w.is_fullscreen() ? w.unmake_fullscreen() : w.make_fullscreen()) },
        ],
    },
    {
        role: 'go', title: 'Go', items: [
            { label: 'Back', shortcut: 'back' },
            { label: 'Forward', shortcut: 'forward' },
            { label: 'Enclosing Folder', shortcut: 'enclosing' },
            SEPARATOR,
            { label: 'Recents', run: () => openUri('recent:///') },
            { label: 'Home', run: () => openHome() },
            { label: 'Desktop', run: () => openSpecialDir(GLib.UserDirectory.DIRECTORY_DESKTOP) },
            { label: 'Documents', run: () => openSpecialDir(GLib.UserDirectory.DIRECTORY_DOCUMENTS) },
            { label: 'Downloads', run: () => openSpecialDir(GLib.UserDirectory.DIRECTORY_DOWNLOAD) },
            { label: 'Pictures', run: () => openSpecialDir(GLib.UserDirectory.DIRECTORY_PICTURES) },
            { label: 'Music', run: () => openSpecialDir(GLib.UserDirectory.DIRECTORY_MUSIC) },
            { label: 'Videos', run: () => openSpecialDir(GLib.UserDirectory.DIRECTORY_VIDEOS) },
            SEPARATOR,
            { label: 'Computer', run: () => openUri('other-locations:///') },
            { label: 'Network', run: () => openUri('network:///') },
            { label: 'Trash', run: () => openUri('trash:///') },
            SEPARATOR,
            { label: 'Go to Folder\u2026', shortcut: 'go-to-folder' },
        ],
    },
    {
        role: 'window', title: 'Window', items: [
            { label: 'Minimize', run: w => w?.minimize() },
            { label: 'Zoom', run: w => toggleMaximized(w) },
            SEPARATOR,
            { label: 'Move Window to Left Half', run: w => tileWindow(w, 'left') },
            { label: 'Move Window to Right Half', run: w => tileWindow(w, 'right') },
            { label: 'Center Window', run: w => centerWindow(w) },
            SEPARATOR,
            { label: 'Bring All to Front', run: w => bringAllToFront(w) },
            // The app's open windows are listed here when the menu opens.
            { windows: true },
        ],
    },
    {
        role: 'help', title: 'Help', items: [
            // Ticket #136: "ParchaOS Help" opened the site's front page and
            // never reached support. The support form is the documented
            // channel (README, LEGAL, SOURCES all point at /support), so
            // that is what a help-seeking click should open. The FAQ keeps
            // its own item rather than being lost behind the change.
            { label: 'ParchaOS Help', run: () => openSiteLink('/support') },
            { label: 'Questions & Answers (FAQ)', run: () => openSiteLink('/#faq') },
            SEPARATOR,
            { label: 'Keyboard Shortcuts', run: () => openSiteLink('/#faq') },
            { label: 'What\u2019s New', run: () => openSiteLink('/changelog') },
            SEPARATOR,
            { label: 'Report a Bug or Feature Request\u2026', run: () => openSiteLink('/support') },
        ],
    },
];

export default class ParchaOSGlobalMenuExtension extends Extension {
    enable() {
        Main.panel.add_style_class_name('parchaos-menubar');
        this._styleSettings = styleSettings();
        applyStyleClass(Main.panel, this._styleSettings);
        this._styleChangedId = this._styleSettings?.connect('changed::style',
            () => applyStyleClass(Main.panel, this._styleSettings)) ?? 0;
        this._menuBarButtons = [];
        this._shortcutItems = [];
        this._trackedWindow = null;
        this._focusSignal = 0;

        this._buildSystemMenu();
        this._bindKeys();
        this._buildAppNameMenu();
        for (const menu of MENU_TABLE)
            this._buildTableMenu(menu);

        // Menu spacing like the reference bar (~2x the text height between
        // items). Set on the buttons themselves so a panel-wide padding
        // setting (e.g. Just Perfection's) doesn't spread the menus out.
        for (const [index, button] of this._menuBarButtons.entries()) {
            // Padding from the reference menu bar: the logo item is 33 px
            // wide around a 16 px glyph; the app name and menu items have
            // 11 px each side with no gap between them.
            const pad = {logo: 8}[button.roleId] ?? 11;
            button.add_style_class_name('parchaos-menubar-button');
            button.set_style(`-natural-hpadding: ${pad}px; -minimum-hpadding: ${pad}px;`);
            Main.panel.addToStatusArea(`parchaos-global-menu-${button.roleId}`, button, index + 1, 'left');
        }

        this._tint = new MenuBarTint(Main.panel);

        this._weatherIndicator = new WeatherIndicator();
        Main.panel.addToStatusArea('parchaos-weather', this._weatherIndicator, 0, 'right');

        this._focusSignal = global.display.connect('notify::focus-window',
            () => this._followFocus());
        this._followFocus();
    }

    disable() {
        this._unbindKeys();
        Main.panel.remove_style_class_name('parchaos-menubar');
        this._tint?.destroy();
        this._tint = null;
        if (this._styleChangedId)
            this._styleSettings.disconnect(this._styleChangedId);
        this._styleChangedId = 0;
        this._styleSettings = null;
        for (const s of ['glass', 'classic'])
            Main.panel.remove_style_class_name(`parchaos-style-${s}`);
        if (this._focusSignal) {
            global.display.disconnect(this._focusSignal);
            this._focusSignal = 0;
        }

        for (const button of this._menuBarButtons)
            button.destroy();
        this._menuBarButtons = [];
        this._shortcutItems = [];
        this._windowList = null;
        this._recentItem = null;
        this._updatesItem = null;
        this._logoMenu = null;
        _keyboard = null;

        if (this._weatherIndicator) {
            this._weatherIndicator.destroy();
            this._weatherIndicator = null;
        }

        this._trackedWindow = null;
    }

    // Lock Screen, Log Out and Force Quit answer to the keys the menu shows.
    _bindKeys() {
        try {
            this._keySettings = this.getSettings();
        } catch (e) {
            console.error('[ParchaOSGlobalMenu] no settings schema, shortcuts off:', e);
            return;
        }
        const modes = Shell.ActionMode.NORMAL | Shell.ActionMode.OVERVIEW;
        const bind = (name, handler) =>
            Main.wm.addKeybinding(name, this._keySettings, Meta.KeyBindingFlags.NONE, modes, handler);
        bind('lock-screen', () => Main.screenShield?.lock(true));
        bind('log-out', () => this._logOut?.());
        bind('force-quit', () => new ForceQuitDialog().open());
    }

    _unbindKeys() {
        if (!this._keySettings)
            return;
        for (const name of ['lock-screen', 'log-out', 'force-quit'])
            Main.wm.removeKeybinding(name);
        this._keySettings = null;
    }

    // --- System (logo) menu ---

    _buildSystemMenu() {
        const logoBtn = new PanelMenu.Button(0.0, 'ParchaOS', false);
        logoBtn.roleId = 'logo';
        // Symbolic vector logo drawn for 16 px: crisp, follows the panel's
        // text color, and centered like the menu labels next to it.
        const icon = new St.Icon({
            gicon: Gio.icon_new_for_string(`${this.path}/parchaos-menu-icon-symbolic.svg`),
            style_class: 'parchaos-menubar-logo-icon',
            // Set in code: the shell theme's panel icon rules can override
            // a CSS icon-size and blew the logo up to ~28 px.
            icon_size: 16,
            y_align: Clutter.ActorAlign.CENTER,
        });
        logoBtn.add_child(icon);

        const powerAction = (question, argv) => () =>
            this._confirm(question, () => GLib.spawn_command_line_async(argv));
        const openStore = () => {
            const apps = Shell.AppSystem.get_default();
            (apps.lookup_app('org.gnome.Software.desktop') ?? apps.lookup_app('gnome-software.desktop'))?.activate();
        };
        const name = GLib.get_real_name();
        this._logOut = powerAction('Log out now? Any unsaved work will be lost.',
            'gnome-session-quit --logout --no-prompt');
        const systemEntries = [
            { label: 'About ParchaOS', icon: 'computer-symbolic', run: () => this._showAboutDialog() },
            SEPARATOR,
            { label: 'System Settings\u2026', icon: 'emblem-system-symbolic', run: openSystemSettings, updates: true },
            { label: 'Parcha Store', icon: 'system-software-install-symbolic', run: openStore },
            SEPARATOR,
            { label: 'Recent Items', recent: true },
            SEPARATOR,
            { label: 'Force Quit\u2026', hint: 'ac \u238B', run: () => new ForceQuitDialog().open() },
            SEPARATOR,
            { label: 'Sleep', run: () => GLib.spawn_command_line_async('systemctl suspend') },
            { label: 'Restart\u2026', run: powerAction('Restart now? Any unsaved work will be lost.',
                'gnome-session-quit --reboot --no-prompt') },
            { label: 'Shut Down\u2026', run: powerAction('Shut down now? Any unsaved work will be lost.',
                'gnome-session-quit --power-off --no-prompt') },
            SEPARATOR,
            { label: 'Lock Screen', hint: 'kc Q', run: () => Main.screenShield?.lock(true) },
            { label: name && name !== 'Unknown' ? `Log Out ${name}\u2026` : 'Log Out\u2026', hint: 'cs Q',
                run: () => this._logOut() },
        ];
        this._fillMenu(logoBtn.menu, systemEntries);
        // Dynamic parts are refreshed each time the menu opens.
        logoBtn.menu.connect('open-state-changed', (_m, open) => {
            if (open)
                this._refreshSystemMenu();
        });
        this._logoMenu = logoBtn.menu;

        this._menuBarButtons.push(logoBtn);
    }

    _confirm(message, onConfirm) {
        new ConfirmDialog(message, onConfirm).open();
    }

    // "About <App>": GTK/libadwaita apps export an "about" action on the
    // session bus (org.gtk.Actions on the app's object path) -- activate
    // that to show the app's own About window. Apps without one (Chromium,
    // Electron, X11 apps) get a simple dialog built from their .desktop info.
    _showAppAbout() {
        const window = this._trackedWindow;
        const app = window
            ? Shell.WindowTracker.get_default().get_window_app(window)
            : Shell.AppSystem.get_default().lookup_app(DEFAULT_APP_ID);
        const busName = window?.get_gtk_unique_bus_name?.();
        const appPath = window?.get_gtk_application_object_path?.();
        if (!busName || !appPath) {
            this._showGenericAppAbout(app);
            return;
        }
        Gio.DBus.session.call(busName, appPath, 'org.gtk.Actions', 'Activate',
            new GLib.Variant('(sava{sv})', ['about', [], {}]),
            null, Gio.DBusCallFlags.NONE, -1, null, (conn, res) => {
                try {
                    conn.call_finish(res);
                } catch (e) {
                    this._showGenericAppAbout(app);
                }
            });
    }

    _showGenericAppAbout(app) {
        if (!app)
            return;
        const dialog = new ModalDialog.ModalDialog({ styleClass: 'parchaos-about-dialog' });
        const box = new St.BoxLayout({ orientation: Clutter.Orientation.VERTICAL, x_align: Clutter.ActorAlign.CENTER });
        box.add_child(app.create_icon_texture(96));
        box.add_child(new St.Label({ text: app.get_name(), style: 'font-weight: bold; font-size: 1.3em; text-align: center;' }));
        const description = app.get_description();
        if (description)
            box.add_child(new St.Label({ text: description, style: 'text-align: center;' }));
        dialog.contentLayout.add_child(box);
        dialog.setButtons([{ label: 'OK', action: () => dialog.close(), key: Clutter.KEY_Escape, default: true }]);
        dialog.open();
    }

    _showAboutDialog() {
        const dialog = new ModalDialog.ModalDialog({ styleClass: 'parchaos-about-dialog' });
        const box = new St.BoxLayout({ orientation: Clutter.Orientation.VERTICAL, style_class: 'parchaos-about-box' });

        // The full-color mark from parchaos-release, or the menu glyph.
        const logo = new St.Icon({
            icon_name: 'parchaos-logo',
            fallback_gicon: Gio.icon_new_for_string(`${this.path}/parchaos-menu-icon-symbolic.svg`),
            icon_size: 88,
            style_class: 'parchaos-about-logo',
            x_align: Clutter.ActorAlign.CENTER,
        });
        box.add_child(logo);

        const osRelease = this._readOsRelease();
        box.add_child(new St.Label({
            text: osRelease.name ?? 'ParchaOS',
            style_class: 'parchaos-about-title',
            x_align: Clutter.ActorAlign.CENTER,
        }));
        const gnome = Config.PACKAGE_VERSION;
        const version = [osRelease.version ? `Version ${osRelease.version}` : null,
            gnome ? `GNOME ${gnome}` : null].filter(v => v).join(' · ');
        box.add_child(new St.Label({
            text: version || 'Version unknown',
            style_class: 'parchaos-about-version',
            x_align: Clutter.ActorAlign.CENTER,
        }));

        const specs = new St.Widget({
            style_class: 'parchaos-about-specs',
            layout_manager: new Clutter.GridLayout({ column_spacing: 14, row_spacing: 6 }),
        });
        let row = 0;
        for (const [label, value] of this._systemSpecs()) {
            if (!value)
                continue;
            const l = new St.Label({ text: label, style_class: 'parchaos-about-spec-label', x_align: Clutter.ActorAlign.END });
            const v = new St.Label({ style_class: 'parchaos-about-spec-value', x_expand: true });
            v.clutter_text.line_wrap = true;
            specs.layout_manager.attach(l, 0, row, 1, 1);
            specs.layout_manager.attach(v, 1, row, 1, 1);
            row++;
            if (typeof value === 'string') {
                v.text = value;
                continue;
            }
            // Filled in when the lookup finishes; hidden if it finds nothing.
            l.hide();
            v.hide();
            value.then(text => {
                if (!text || !v.get_parent())
                    return;
                v.text = text;
                l.show();
                v.show();
            }).catch(() => {});
        }
        box.add_child(specs);

        box.add_child(new St.Label({
            text: 'ParchaOS is built on Fedora Linux and GNOME.',
            style_class: 'parchaos-about-footer',
            x_align: Clutter.ActorAlign.CENTER,
        }));

        dialog.contentLayout.add_child(box);
        dialog.setButtons([
            {
                label: 'More Info…',
                action: () => {
                    dialog.close();
                    try {
                        Gio.Subprocess.new(['gnome-control-center', 'system', 'about'], Gio.SubprocessFlags.NONE);
                    } catch (e) {
                        logError(e, 'parchaos-global-menu: could not open Settings');
                    }
                },
            },
            {
                label: 'Legal and Privacy',
                action: () => {
                    dialog.close();
                    try {
                        Gio.AppInfo.launch_default_for_uri(
                            Gio.File.new_for_path('/usr/share/doc/parchaos/LEGAL.md').get_uri(), null);
                    } catch (e) {
                        logError(e, 'parchaos-global-menu: could not open the legal notice');
                    }
                },
            },
            { label: 'Close', action: () => dialog.close(), default: true },
        ]);
        dialog.open();
    }

    // Runs argv without blocking the compositor; resolves to its stdout.
    _commandOutput(argv) {
        return new Promise(resolve => {
            try {
                const proc = Gio.Subprocess.new(argv,
                    Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE);
                proc.communicate_utf8_async(null, null, (p, res) => {
                    try {
                        const [, out] = p.communicate_utf8_finish(res);
                        resolve(p.get_successful() ? (out ?? '').trim() : '');
                    } catch (e) {
                        resolve('');
                    }
                });
            } catch (e) {
                resolve('');
            }
        });
    }

    _readFile(path) {
        try {
            const [ok, contents] = GLib.file_get_contents(path);
            return ok ? new TextDecoder().decode(contents).trim() : '';
        } catch (e) {
            return '';
        }
    }

    // [label, value] rows for the About card; empty values are skipped.
    _systemSpecs() {
        const vendor = this._readFile('/sys/class/dmi/id/sys_vendor');
        const product = this._readFile('/sys/class/dmi/id/product_name');
        const board = this._readFile('/sys/class/dmi/id/board_name');
        const model = [vendor, product && !/to be filled|system product name/i.test(product) ? product : board]
            .filter(v => v && !/to be filled/i.test(v)).join(' ');

        const cpuinfo = this._readFile('/proc/cpuinfo');
        const cpu = (cpuinfo.match(/^model name\s*:\s*(.+)$/m)?.[1] ?? '')
            .replace(/\(R\)|\(TM\)/g, '').replace(/\s+/g, ' ').trim();

        // Graphics: the main display controller (discrete before integrated).
        const gpu = this._commandOutput(['lspci', '-mm']).then(out => out.split('\n')
            .filter(l => /"(VGA compatible controller|3D controller|Display controller)"/.test(l))
            .map(l => {
                const f = [...l.matchAll(/"([^"]*)"/g)].map(m => m[1]);
                const name = (f[2] ?? '').replace(/^.*\[(.+)\]$/, '$1');
                const brand = /AMD|ATI/.test(f[1]) ? 'AMD' : /NVIDIA/i.test(f[1]) ? 'NVIDIA' : /Intel/i.test(f[1]) ? 'Intel' : '';
                return `${brand} ${name}`.trim();
            })
            .sort((a, b) => /Graphics$/.test(a) - /Graphics$/.test(b))[0] ?? '');

        const memKb = Number(this._readFile('/proc/meminfo').match(/^MemTotal:\s*(\d+)/m)?.[1] ?? 0);
        // MemTotal excludes memory the kernel reserves; round up to the
        // installed size (installed RAM comes in even gigabytes).
        const memGb = memKb ? Math.ceil(memKb / 1024 / 1024 / 2) * 2 : 0;

        let storage = '';
        try {
            const info = Gio.File.new_for_path('/').query_filesystem_info('filesystem::size,filesystem::free', null);
            const gb = n => `${Math.round(n / 1e9)} GB`;
            storage = `${gb(info.get_attribute_uint64('filesystem::free'))} available of ${gb(info.get_attribute_uint64('filesystem::size'))}`;
        } catch (e) {
            // leave empty
        }

        return [
            ['Computer', model],
            ['Processor', cpu],
            ['Graphics', gpu],
            ['Memory', memGb ? `${memGb} GB` : ''],
            ['Storage', storage],
            ['Kernel', this._readFile('/proc/sys/kernel/osrelease')],
        ];
    }

    // NAME and VERSION from /etc/os-release (missing ones stay undefined).
    _readOsRelease() {
        const fields = {};
        for (const line of this._readFile('/etc/os-release').split('\n')) {
            const eq = line.indexOf('=');
            if (eq > 0)
                fields[line.slice(0, eq)] = line.slice(eq + 1).replace(/^"|"$/g, '');
        }
        return { name: fields.NAME, version: fields.VERSION };
    }

    // --- App name menu ---

    _buildAppNameMenu() {
        const appBtn = new MenuBarButton(DEFAULT_APP_NAME, { bold: true });
        appBtn.roleId = 'app';
        const menu = appBtn.menu;

        this._aboutAppItem = new MenuEntry(`About ${DEFAULT_APP_NAME}`);
        this._aboutAppItem.connect('activate', () => this._showAppAbout());
        menu.addMenuItem(this._aboutAppItem);
        menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        this._settingsAppItem = this._shortcutItem(menu, 'Settings\u2026', 'settings');
        menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        this._hideAppItem = new MenuEntry(`Hide ${DEFAULT_APP_NAME}`, hintText('c H'));
        this._hideAppItem.connect('activate', () => {
            const app = this._activeApp();
            if (app)
                app.get_windows().forEach(w => w.minimize());
            else
                this._trackedWindow?.minimize();
        });
        menu.addMenuItem(this._hideAppItem);

        this._hideOthersItem = new MenuEntry('Hide Others', hintText('ac H'));
        this._hideOthersItem.connect('activate', () => {
            const mine = this._activeApp();
            for (const actor of global.get_window_actors()) {
                const w = actor.meta_window;
                if (w.get_window_type() !== Meta.WindowType.NORMAL)
                    continue;
                if (Shell.WindowTracker.get_default().get_window_app(w) !== mine)
                    w.minimize();
            }
        });
        menu.addMenuItem(this._hideOthersItem);

        this._showAllItem = new MenuEntry('Show All');
        this._showAllItem.connect('activate', () => {
            for (const actor of global.get_window_actors()) {
                if (actor.meta_window.minimized)
                    actor.meta_window.unminimize();
            }
        });
        menu.addMenuItem(this._showAllItem);
        menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        this._quitAppItem = new MenuEntry(`Quit ${DEFAULT_APP_NAME}`, hintText('c Q'));
        this._quitAppItem.connect('activate', () => {
            const app = this._activeApp();
            if (app)
                app.request_quit();
            else
                this._trackedWindow?.delete(global.get_current_time());
        });
        menu.addMenuItem(this._quitAppItem);

        // Hints follow the keyboard style, which can change while running.
        menu.connect('open-state-changed', (_m, open) => {
            if (!open)
                return;
            this._hideAppItem.setHint(hintText('c H'));
            this._hideOthersItem.setHint(hintText('ac H'));
            this._quitAppItem.setHint(hintText('c Q'));
        });

        this._appNameButton = appBtn;
        this._menuBarButtons.push(appBtn);
    }

    // Keeps the menu bar on the last real app window that had focus, so
    // clicking the bar itself (which takes focus) doesn't reset it.
    _followFocus() {
        const focused = global.display.focus_window;
        const open = new Set(global.get_window_actors().map(a => a.meta_window));
        if (this._trackedWindow && !open.has(this._trackedWindow))
            this._trackedWindow = null;
        if (focused && !this._isIgnoredWindow(focused))
            this._trackedWindow = focused;

        const appName = this._displayNameFor(this._trackedWindow);
        this._appNameButton.setLabelText(appName);
        this._aboutAppItem.label.set_text(`About ${appName}`);
        this._hideAppItem.label.set_text(`Hide ${appName}`);
        this._quitAppItem.label.set_text(`Quit ${appName}`);

        const isIdleState = appName === DEFAULT_APP_NAME && !this._trackedWindow;
        this._hideAppItem.setSensitive(!isIdleState);
        this._hideOthersItem.setSensitive(!isIdleState);
        this._quitAppItem.setSensitive(!isIdleState);
        this._updateShortcutItems();
    }

    _activeApp() {
        const win = this._trackedWindow;
        return win ? Shell.WindowTracker.get_default().get_window_app(win) : null;
    }

    // A menu item that sends the focused app one of SHORTCUTS' actions.
    _shortcutItem(menu, label, action) {
        const item = new MenuEntry(label, hintText(HINTS[action]));
        item.connect('activate', () => {
            // With no app focused the menu bar belongs to the file
            // manager, so New Window opens one.
            if (action === 'new-window' && !this._trackedWindow) {
                openHome();
                return;
            }
            const combo = shortcutFor(action, appKind(this._trackedWindow));
            if (combo)
                sendKeyCombo(...combo);
        });
        menu.addMenuItem(item);
        this._shortcutItems.push([item, action]);
        return item;
    }

    _updateShortcutItems() {
        const kind = appKind(this._trackedWindow);
        for (const [item, action] of this._shortcutItems) {
            item.setHint(hintText(HINTS[action]));
            item.setSensitive(shortcutFor(action, kind) !== null ||
                (action === 'new-window' && !kind));
        }
    }

    _isIgnoredWindow(window) {
        const wmClass = window.get_wm_class?.() ?? '';
        if (wmClass && /gnome-shell|gdm/i.test(wmClass))
            return true;

        const gtkAppId = window.get_gtk_application_id?.() ?? '';
        return IGNORED_APP_IDS.includes(wmClass) || IGNORED_APP_IDS.includes(gtkAppId);
    }

    // The name shown next to the logo: the app's own name from its
    // .desktop entry, found through the window tracker or, for windows it
    // can't match, by the window's class; the window title as a last resort.
    _displayNameFor(window) {
        if (!window)
            return DEFAULT_APP_NAME;
        const tracked = Shell.WindowTracker.get_default().get_window_app(window)?.get_name();
        if (tracked)
            return tracked;
        for (const id of [window.get_gtk_application_id?.(), window.get_wm_class?.()]) {
            if (!id)
                continue;
            const info = Gio.DesktopAppInfo.new(`${id}.desktop`) ??
                Gio.DesktopAppInfo.new(`${id.toLowerCase()}.desktop`);
            if (info)
                return info.get_display_name();
        }
        return window.get_title?.() || DEFAULT_APP_NAME;
    }

    // Builds one MENU_TABLE entry as a menu bar button.
    _buildTableMenu({ role, title, items }) {
        const button = new MenuBarButton(title);
        button.roleId = role;
        this._fillMenu(button.menu, items);
        this._menuBarButtons.push(button);
    }

    // Adds entries (see MENU_TABLE) to a popup menu.
    _fillMenu(menu, entries) {
        for (const entry of entries) {
            if (entry === SEPARATOR) {
                menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
            } else if (entry.shortcut) {
                this._shortcutItem(menu, entry.label, entry.shortcut);
            } else if (entry.windows) {
                this._windowList = {menu, items: []};
                menu.connect('open-state-changed', (_m, open) => {
                    if (open)
                        this._refreshWindowList();
                });
            } else if (entry.recent) {
                this._recentItem = new PopupMenu.PopupSubMenuMenuItem(entry.label);
                menu.addMenuItem(this._recentItem);
            } else {
                const item = new MenuEntry(entry.label, entry.hint ? hintText(entry.hint) : '', !!entry.updates, entry.icon);
                if (entry.updates)
                    this._updatesItem = item;
                item.connect('activate', () => entry.run(this._trackedWindow));
                menu.addMenuItem(item);
            }
        }
    }

    // The Recent Items submenu and the updates badge are read when the
    // logo menu opens.
    _refreshSystemMenu() {
        const updates = pendingUpdates();
        this._updatesItem?.setHint(updates > 0 ? (updates === 1 ? '1 update' : `${updates} updates`) : '');

        const sub = this._recentItem?.menu;
        if (!sub)
            return;
        sub.removeAll();
        const items = recentItems();
        if (items.length === 0) {
            const none = new PopupMenu.PopupMenuItem('No recent items');
            none.setSensitive(false);
            sub.addMenuItem(none);
            return;
        }
        for (const {uri, title} of items) {
            const item = new PopupMenu.PopupMenuItem(title);
            item.connect('activate', () => openUri(uri));
            sub.addMenuItem(item);
        }
    }

    // The Window menu ends with the app's open windows, the current one
    // ticked.
    _refreshWindowList() {
        const list = this._windowList;
        if (!list)
            return;
        for (const item of list.items)
            item.destroy();
        list.items = [];
        const app = this._activeApp();
        const windows = (app?.get_windows() ?? []).filter(w => w.get_window_type() === Meta.WindowType.NORMAL);
        if (windows.length === 0)
            return;
        const sep = new PopupMenu.PopupSeparatorMenuItem();
        list.menu.addMenuItem(sep);
        list.items.push(sep);
        for (const w of windows) {
            const item = new PopupMenu.PopupMenuItem(w.get_title() || this._displayNameFor(w));
            if (w === this._trackedWindow)
                item.setOrnament(PopupMenu.Ornament.CHECK);
            item.connect('activate', () => Main.activateWindow(w));
            list.menu.addMenuItem(item);
            list.items.push(item);
        }
    }
}
