/**
 * ParchaOS Global Menu
 *
 * A global application menu bar for GNOME Shell: an app-name
 * label with About/Hide/Quit, standard File/Edit/View/Go/Window/Help
 * menus, a system logo menu with real power actions, and a weather
 * indicator.
 *
 * This is an original, from-scratch implementation written against
 * docs/global-menu-rewrite-spec.md (a plain feature description) and
 * GNOME Shell's own public extension APIs. It is not derived from, and
 * was not written by reading, any other project's global-menu source.
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
import Meta from 'gi://Meta';
import GWeather from 'gi://GWeather';
import Geoclue from 'gi://Geoclue';
import * as Config from 'resource:///org/gnome/shell/misc/config.js';

const DEFAULT_APP_NAME = 'Parcher';
const DEFAULT_APP_ID = 'org.gnome.Nautilus.desktop';

// The public ParchaOS website (help, FAQ, bug reports).
const SITE_URL = 'https://parchaos-website.vercel.app';

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
        const seat = Clutter.get_default_backend().get_default_seat();
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

const SHORTCUTS = {
    'new-window': {default: [CTRL, Clutter.KEY_n], terminal: [CTRL_SHIFT, Clutter.KEY_N]},
    'undo': {default: [CTRL, Clutter.KEY_z], terminal: null},
    // Ctrl+Shift+Z is the redo GTK, Chromium, Electron and LibreOffice
    // all accept; Ctrl+Y isn't bound in most GTK 4 apps.
    'redo': {default: [CTRL_SHIFT, Clutter.KEY_Z], terminal: null},
    'cut': {default: [CTRL, Clutter.KEY_x], terminal: null},
    'copy': {default: [CTRL, Clutter.KEY_c], terminal: [CTRL_SHIFT, Clutter.KEY_C]},
    'paste': {default: [CTRL, Clutter.KEY_v], terminal: [CTRL_SHIFT, Clutter.KEY_V]},
    'view-icons': {default: null, files: [CTRL, Clutter.KEY_1]},
    'view-list': {default: null, files: [CTRL, Clutter.KEY_2]},
    'hidden-files': {default: null, files: [CTRL, Clutter.KEY_h]},
    'back': {default: [[Clutter.KEY_Alt_L], Clutter.KEY_Left], terminal: null},
};

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
        super._init(0.0, 'Weather', true);

        const box = new St.BoxLayout({
            style_class: 'parchaos-weather-box',
            y_align: Clutter.ActorAlign.CENTER,
        });
        this._icon = new St.Icon({
            icon_name: 'weather-clear-symbolic',
            style_class: 'system-status-icon parchaos-weather-icon',
            icon_size: 16,
        });
        this._label = new St.Label({
            text: '',
            y_align: Clutter.ActorAlign.CENTER,
            style_class: 'parchaos-weather-label',
        });
        box.add_child(this._icon);
        box.add_child(this._label);
        this.add_child(box);

        this.visible = false;

        this._weatherInfo = null;
        this._weatherUpdatedId = 0;
        this._geoclueSimple = null;
        this._locationId = 0;
        this._cancellable = new Gio.Cancellable();
        this._updateTimerId = 0;

        this.connect('button-press-event', () => {
            this._openWeatherApp();
            return Clutter.EVENT_STOP;
        });
        this.connect('destroy', () => this._onDestroy());

        this._startGeolocation();

        this._updateTimerId = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 1800, () => {
            this._weatherInfo?.update();
            return GLib.SOURCE_CONTINUE;
        });
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
            if (!e.matches?.(Gio.IOErrorEnum, Gio.IOErrorEnum.CANCELLED))
                console.error('[ParchaOSGlobalMenu] Geoclue unavailable for weather:', e);
            return;
        }
        this._locationId = this._geoclueSimple.connect('notify::location',
            () => this._onLocationUpdated());
        this._onLocationUpdated();
    }

    _onLocationUpdated() {
        const geoclueLocation = this._geoclueSimple?.get_location();
        const world = GWeather.Location.get_world();
        if (!geoclueLocation || !world)
            return;

        const location = world.find_nearest_city(geoclueLocation.latitude, geoclueLocation.longitude);
        if (!location)
            return;

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
        this._icon.icon_name = this._weatherInfo.get_symbolic_icon_name();
        this._label.set_text(this._weatherInfo.get_temp_summary());
        this.visible = true;
    }

    _openWeatherApp() {
        try {
            const app = Shell.AppSystem.get_default().lookup_app('org.gnome.Weather.desktop');
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

export default class ParchaOSGlobalMenuExtension extends Extension {
    enable() {
        Main.panel.add_style_class_name('parchaos-menubar');
        this._styleSettings = styleSettings();
        applyStyleClass(Main.panel, this._styleSettings);
        this._styleChangedId = this._styleSettings?.connect('changed::style',
            () => applyStyleClass(Main.panel, this._styleSettings)) ?? 0;
        this._menuBarButtons = [];
        this._shortcutItems = [];
        this._activeAppWindow = null;
        this._focusNotifyId = 0;

        this._createLogoMenu();
        this._createAppMenu();
        this._createFileMenu();
        this._createEditMenu();
        this._createViewMenu();
        this._createGoMenu();
        this._createWindowMenu();
        this._createHelpMenu();

        // Menu spacing like the reference bar (~2x the text height between
        // items). Set on the buttons themselves so a panel-wide padding
        // setting (e.g. Just Perfection's) doesn't spread the menus out.
        let pos = 1;
        for (const button of this._menuBarButtons) {
            // Padding from the reference menu bar: the logo item is 33 px
            // wide around a 16 px glyph; the app name and menu items have
            // 11 px each side with no gap between them.
            const pad = {logo: 8}[button.roleId] ?? 11;
            button.add_style_class_name('parchaos-menubar-button');
            button.set_style(`-natural-hpadding: ${pad}px; -minimum-hpadding: ${pad}px;`);
            Main.panel.addToStatusArea(`parchaos-global-menu-${button.roleId}`, button, pos++, 'left');
        }

        this._weatherIndicator = new WeatherIndicator();
        Main.panel.addToStatusArea('parchaos-weather', this._weatherIndicator, 0, 'right');

        this._focusNotifyId = global.display.connect('notify::focus-window', () => {
            this._onFocusWindowChanged();
        });
        this._onFocusWindowChanged();
    }

    disable() {
        Main.panel.remove_style_class_name('parchaos-menubar');
        if (this._styleChangedId)
            this._styleSettings.disconnect(this._styleChangedId);
        this._styleChangedId = 0;
        this._styleSettings = null;
        for (const s of ['glass', 'classic'])
            Main.panel.remove_style_class_name(`parchaos-style-${s}`);
        if (this._focusNotifyId) {
            global.display.disconnect(this._focusNotifyId);
            this._focusNotifyId = 0;
        }

        for (const button of this._menuBarButtons)
            button.destroy();
        this._menuBarButtons = [];
        this._shortcutItems = [];
        _keyboard = null;

        if (this._weatherIndicator) {
            this._weatherIndicator.destroy();
            this._weatherIndicator = null;
        }

        this._activeAppWindow = null;
    }

    // --- Logo menu ---

    _createLogoMenu() {
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

        const aboutItem = new PopupMenu.PopupMenuItem('About ParchaOS');
        aboutItem.connect('activate', () => this._showAboutDialog());
        logoBtn.menu.addMenuItem(aboutItem);

        logoBtn.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        const settingsItem = new PopupMenu.PopupMenuItem('System Settings…');
        settingsItem.connect('activate', () => {
            const app = Shell.AppSystem.get_default().lookup_app('org.gnome.Settings.desktop')
                ?? Shell.AppSystem.get_default().lookup_app('gnome-control-center.desktop');
            app?.activate();
        });
        logoBtn.menu.addMenuItem(settingsItem);

        logoBtn.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        const lockItem = new PopupMenu.PopupMenuItem('Lock Screen');
        lockItem.connect('activate', () => Main.screenShield?.lock(true));
        logoBtn.menu.addMenuItem(lockItem);

        const logoutItem = new PopupMenu.PopupMenuItem('Log Out…');
        logoutItem.connect('activate', () => {
            this._confirm('Log out now? Any unsaved work will be lost.', () => {
                GLib.spawn_command_line_async('gnome-session-quit --logout --no-prompt');
            });
        });
        logoBtn.menu.addMenuItem(logoutItem);

        const restartItem = new PopupMenu.PopupMenuItem('Restart…');
        restartItem.connect('activate', () => {
            this._confirm('Restart now? Any unsaved work will be lost.', () => {
                GLib.spawn_command_line_async('gnome-session-quit --reboot --no-prompt');
            });
        });
        logoBtn.menu.addMenuItem(restartItem);

        const shutdownItem = new PopupMenu.PopupMenuItem('Shut Down…');
        shutdownItem.connect('activate', () => {
            this._confirm('Shut down now? Any unsaved work will be lost.', () => {
                GLib.spawn_command_line_async('gnome-session-quit --power-off --no-prompt');
            });
        });
        logoBtn.menu.addMenuItem(shutdownItem);

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
        const window = this._activeAppWindow;
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

    _readOsRelease() {
        const result = {};
        try {
            const [ok, contents] = GLib.file_get_contents('/etc/os-release');
            if (ok) {
                const text = new TextDecoder().decode(contents);
                for (const line of text.split('\n')) {
                    const m = line.match(/^([A-Z_]+)=(.*)$/);
                    if (!m)
                        continue;
                    const value = m[2].replace(/^"|"$/g, '');
                    if (m[1] === 'NAME')
                        result.name = value;
                    if (m[1] === 'VERSION')
                        result.version = value;
                }
            }
        } catch (e) {
            // Fine to leave result empty; the dialog just shows "unknown".
        }
        return result;
    }

    // --- App menu ---

    _createAppMenu() {
        const appBtn = new MenuBarButton(DEFAULT_APP_NAME, { bold: true });
        appBtn.roleId = 'app';

        this._aboutAppItem = new PopupMenu.PopupMenuItem(`About ${DEFAULT_APP_NAME}`);
        this._aboutAppItem.connect('activate', () => this._showAppAbout());
        appBtn.menu.addMenuItem(this._aboutAppItem);

        this._hideAppItem = new PopupMenu.PopupMenuItem(`Hide ${DEFAULT_APP_NAME}`);
        this._hideAppItem.connect('activate', () => {
            const app = this._activeApp();
            if (app)
                app.get_windows().forEach(w => w.minimize());
            else
                this._activeAppWindow?.minimize();
        });
        appBtn.menu.addMenuItem(this._hideAppItem);

        this._quitAppItem = new PopupMenu.PopupMenuItem(`Quit ${DEFAULT_APP_NAME}`);
        this._quitAppItem.connect('activate', () => {
            const app = this._activeApp();
            if (app)
                app.request_quit();
            else
                this._activeAppWindow?.delete(global.get_current_time());
        });
        appBtn.menu.addMenuItem(this._quitAppItem);

        this._appMenuButton = appBtn;
        this._menuBarButtons.push(appBtn);
    }

    _onFocusWindowChanged() {
        const window = global.display.focus_window;

        if (this._activeAppWindow) {
            const stillOpen = global.get_window_actors()
                .map(a => a.meta_window)
                .includes(this._activeAppWindow);
            if (!stillOpen)
                this._activeAppWindow = null;
        }

        if (window && !this._isIgnoredWindow(window))
            this._activeAppWindow = window;

        const appName = this._getAppName(this._activeAppWindow);
        this._appMenuButton.setLabelText(appName);
        this._aboutAppItem.label.set_text(`About ${appName}`);
        this._hideAppItem.label.set_text(`Hide ${appName}`);
        this._quitAppItem.label.set_text(`Quit ${appName}`);

        const isIdleState = appName === DEFAULT_APP_NAME && !this._activeAppWindow;
        this._hideAppItem.setSensitive(!isIdleState);
        this._quitAppItem.setSensitive(!isIdleState);
        this._updateShortcutItems();
    }

    _activeApp() {
        const win = this._activeAppWindow;
        return win ? Shell.WindowTracker.get_default().get_window_app(win) : null;
    }

    // A menu item that sends the focused app one of SHORTCUTS' actions.
    _shortcutItem(menu, label, action) {
        const item = new PopupMenu.PopupMenuItem(label);
        item.connect('activate', () => {
            // With no app focused the menu bar belongs to the file
            // manager, so New Window opens one.
            if (action === 'new-window' && !this._activeAppWindow) {
                openHome();
                return;
            }
            const combo = shortcutFor(action, appKind(this._activeAppWindow));
            if (combo)
                sendKeyCombo(...combo);
        });
        menu.addMenuItem(item);
        this._shortcutItems.push([item, action]);
        return item;
    }

    _updateShortcutItems() {
        const kind = appKind(this._activeAppWindow);
        for (const [item, action] of this._shortcutItems) {
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

    _getAppName(window) {
        if (!window)
            return DEFAULT_APP_NAME;

        const app = Shell.WindowTracker.get_default().get_window_app(window);
        if (app?.get_name())
            return app.get_name();

        const wmClass = window.get_wm_class?.();
        if (wmClass)
            return wmClass.charAt(0).toUpperCase() + wmClass.slice(1);

        return window.get_title?.() ?? DEFAULT_APP_NAME;
    }

    // --- File menu ---

    _createFileMenu() {
        const fileBtn = new MenuBarButton('File');
        fileBtn.roleId = 'file';

        this._shortcutItem(fileBtn.menu, 'New Window', 'new-window');

        // Closing is done directly: Ctrl+W closes a tab in browsers and
        // does nothing in a terminal.
        const closeWindowItem = new PopupMenu.PopupMenuItem('Close Window');
        closeWindowItem.connect('activate', () => {
            this._activeAppWindow?.delete(global.get_current_time());
        });
        fileBtn.menu.addMenuItem(closeWindowItem);

        this._menuBarButtons.push(fileBtn);
    }

    // --- Edit menu ---

    _createEditMenu() {
        const editBtn = new MenuBarButton('Edit');
        editBtn.roleId = 'edit';

        this._shortcutItem(editBtn.menu, 'Undo', 'undo');
        this._shortcutItem(editBtn.menu, 'Redo', 'redo');
        editBtn.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        this._shortcutItem(editBtn.menu, 'Cut', 'cut');
        this._shortcutItem(editBtn.menu, 'Copy', 'copy');
        this._shortcutItem(editBtn.menu, 'Paste', 'paste');

        this._menuBarButtons.push(editBtn);
    }

    // --- View menu ---

    _createViewMenu() {
        const viewBtn = new MenuBarButton('View');
        viewBtn.roleId = 'view';

        this._shortcutItem(viewBtn.menu, 'as Icons', 'view-icons');
        this._shortcutItem(viewBtn.menu, 'as List', 'view-list');
        viewBtn.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        this._shortcutItem(viewBtn.menu, 'Show Hidden Files', 'hidden-files');

        this._menuBarButtons.push(viewBtn);
    }

    // --- Go menu ---

    _createGoMenu() {
        const goBtn = new MenuBarButton('Go');
        goBtn.roleId = 'go';

        this._shortcutItem(goBtn.menu, 'Back', 'back');

        goBtn.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        const homeItem = new PopupMenu.PopupMenuItem('Home');
        homeItem.connect('activate', () => openHome());
        goBtn.menu.addMenuItem(homeItem);

        const documentsItem = new PopupMenu.PopupMenuItem('Documents');
        documentsItem.connect('activate', () => openSpecialDir(GLib.UserDirectory.DIRECTORY_DOCUMENTS));
        goBtn.menu.addMenuItem(documentsItem);

        const downloadsItem = new PopupMenu.PopupMenuItem('Downloads');
        downloadsItem.connect('activate', () => openSpecialDir(GLib.UserDirectory.DIRECTORY_DOWNLOAD));
        goBtn.menu.addMenuItem(downloadsItem);

        const picturesItem = new PopupMenu.PopupMenuItem('Pictures');
        picturesItem.connect('activate', () => openSpecialDir(GLib.UserDirectory.DIRECTORY_PICTURES));
        goBtn.menu.addMenuItem(picturesItem);

        this._menuBarButtons.push(goBtn);
    }

    // --- Window menu ---

    _createWindowMenu() {
        const windowBtn = new MenuBarButton('Window');
        windowBtn.roleId = 'window';

        const minimizeItem = new PopupMenu.PopupMenuItem('Minimize');
        minimizeItem.connect('activate', () => this._activeAppWindow?.minimize());
        windowBtn.menu.addMenuItem(minimizeItem);

        const zoomItem = new PopupMenu.PopupMenuItem('Zoom');
        zoomItem.connect('activate', () => {
            const win = this._activeAppWindow;
            if (!win)
                return;
            if (win.get_maximized())
                win.unmaximize(Meta.MaximizeFlags.BOTH);
            else
                win.maximize(Meta.MaximizeFlags.BOTH);
        });
        windowBtn.menu.addMenuItem(zoomItem);

        this._menuBarButtons.push(windowBtn);
    }

    // --- Help menu ---

    _createHelpMenu() {
        const helpBtn = new MenuBarButton('Help');
        helpBtn.roleId = 'help';

        const helpItem = new PopupMenu.PopupMenuItem('ParchaOS Help');
        helpItem.connect('activate', () => {
            try {
                Gio.AppInfo.launch_default_for_uri(`${SITE_URL}/#faq`, null);
            } catch (e) {
                console.error('[ParchaOSGlobalMenu] Failed to open help link:', e);
            }
        });
        helpBtn.menu.addMenuItem(helpItem);

        helpBtn.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        const reportBugItem = new PopupMenu.PopupMenuItem('Report a Bug or Feature Request…');
        reportBugItem.connect('activate', () => {
            try {
                Gio.AppInfo.launch_default_for_uri(`${SITE_URL}/support`, null);
            } catch (e) {
                console.error('[ParchaOSGlobalMenu] Failed to open support link:', e);
            }
        });
        helpBtn.menu.addMenuItem(reportBugItem);

        this._menuBarButtons.push(helpBtn);
    }
}
