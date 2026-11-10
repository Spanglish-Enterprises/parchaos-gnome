// SPDX-License-Identifier: GPL-3.0-or-later
// More controls for Edit Controls (ticket #172, docs/controls-catalog.md). Every control here
// starts hidden and is added from the picker; each appears only when what it stands for is on the
// system (an app installed, a backlit keyboard, an extension running). Names are plain words and
// GNOME's own terms; icons are Adwaita's and GNOME Settings' own symbols.
//
// Original code for ParchaOS, GPL-3.0-or-later.

import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import Shell from 'gi://Shell';
import St from 'gi://St';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';

// id -> category, picker icon and sizes (first is the default).
export const CATALOG = {
    'calculator': {category: 'Utilities', icon: 'accessories-calculator-symbolic', sizes: [[1, 1]]},
    'timer': {category: 'Clock', icon: 'appointment-soon-symbolic', sizes: [[1, 1]]},
    'alarm': {category: 'Clock', icon: 'alarm-symbolic', sizes: [[1, 1]]},
    'stopwatch': {category: 'Clock', icon: 'org.gnome.clocks-symbolic', sizes: [[1, 1]]},
    'new-note': {category: 'Notes', icon: 'document-new-symbolic', sizes: [[1, 1]]},
    'weather': {category: 'Weather', icon: 'weather-few-clouds-symbolic', sizes: [[2, 1]]},
    'keyboard-brightness': {category: 'Display', icon: 'keyboard-brightness-symbolic', sizes: [[4, 1], [2, 1]]},
    'screen-recording': {category: 'Shortcuts', icon: 'media-record-symbolic', sizes: [[1, 1], [2, 1]]},
    'keep-awake': {category: 'System', icon: 'view-reveal-symbolic', sizes: [[1, 1]]},
    'camera-off': {category: 'Privacy', icon: 'camera-disabled-symbolic', sizes: [[1, 1]]},
    'microphone-off': {category: 'Privacy', icon: 'microphone-disabled-symbolic', sizes: [[1, 1]]},
    'location': {category: 'Privacy', icon: 'location-services-active-symbolic', sizes: [[1, 1]]},
    'larger-text': {category: 'Accessibility', icon: 'font-size-symbolic', sizes: [[1, 1]]},
    'zoom': {category: 'Accessibility', icon: 'zoom-in-symbolic', sizes: [[1, 1]]},
    'high-contrast': {category: 'Accessibility', icon: 'preferences-desktop-accessibility-symbolic', sizes: [[1, 1]]},
    'show-desktop': {category: 'Desktop', icon: 'user-desktop-symbolic', sizes: [[1, 1]]},
    'back-up-now': {category: 'Utilities', icon: 'org.gnome.DejaDup-symbolic', sizes: [[1, 1], [2, 1]]},
    'clipboard': {category: 'Utilities', icon: 'edit-paste-symbolic', sizes: [[1, 1]]},
    'dictation': {category: 'Accessibility', icon: 'audio-input-microphone-symbolic', sizes: [[1, 1]]},
    'speak-selection': {category: 'Accessibility', icon: 'audio-speakers-symbolic', sizes: [[1, 1]]},
    'snapshots': {category: 'Utilities', icon: 'document-revert-symbolic', sizes: [[1, 1]]},
};

// Opening one of these apps by any route counts as using its control (Suggestions).
export const CATALOG_APPS = {
    'org.gnome.Calculator.desktop': 'calculator',
    'org.gnome.DejaDup.desktop': 'back-up-now',
};

// On/off state in the shape the tile circles read (checked, icon-name).
export const ToggleState = GObject.registerClass({
    Properties: {
        'checked': GObject.ParamSpec.boolean('checked', null, null, GObject.ParamFlags.READWRITE, false),
        'icon-name': GObject.ParamSpec.string('icon-name', null, null, GObject.ParamFlags.READWRITE, ''),
    },
}, class ToggleState extends GObject.Object {
    set(checked) {
        if (this.checked !== checked)
            this.checked = checked;
    }

    destroy() {
        this._onDestroy?.();
    }
});

function settingsFor(schemaId, key) {
    const schema = Gio.SettingsSchemaSource.get_default()?.lookup(schemaId, true);
    return schema?.has_key(key) ? new Gio.Settings({settings_schema: schema}) : null;
}

/** A switch over one setting: isOn(settings) reads it, turn(settings, on) writes it. */
function settingToggle(schemaId, key, icon, isOn, turn) {
    const settings = settingsFor(schemaId, key);
    if (!settings)
        return null;
    const state = new ToggleState({'icon-name': icon});
    const sync = () => state.set(isOn(settings));
    const id = settings.connect(`changed::${key}`, sync);
    state._onDestroy = () => settings.disconnect(id);
    sync();
    state.toggle = () => turn(settings, !state.checked);
    return state;
}

function boolToggle(schemaId, key, icon, invert = false) {
    return settingToggle(schemaId, key, icon,
        s => s.get_boolean(key) !== invert,
        (s, on) => s.set_boolean(key, on !== invert));
}

function appInstalled(id) {
    return Shell.AppSystem.get_default().lookup_app(id);
}

function launch(argv) {
    try {
        Gio.Subprocess.new(argv, Gio.SubprocessFlags.NONE);
    } catch (e) {
        logError(e, `parchaos-controls: could not run ${argv[0]}`);
    }
}

// Opens a menu-bar menu another extension owns, once Control Center has closed.
function openStatusMenu(role) {
    GLib.timeout_add(GLib.PRIORITY_DEFAULT, 250, () => {
        Main.panel.statusArea[role]?.menu?.open();
        return GLib.SOURCE_REMOVE;
    });
}

function extensionObject(uuid) {
    const ext = Main.extensionManager.lookup(uuid);
    return ext?.state === 1 ? ext.stateObj : null;   // 1 = ENABLED / ACTIVE
}

// Keep Awake lasts beyond the panel (which is rebuilt every time it opens): one inhibitor
// for the whole shell, through GNOME's session manager (idle and suspend).
const keepAwake = {cookie: 0, state: null};

function setKeepAwake(on) {
    const bus = Gio.DBus.session;
    if (on && !keepAwake.cookie) {
        try {
            const reply = bus.call_sync('org.gnome.SessionManager', '/org/gnome/SessionManager',
                'org.gnome.SessionManager', 'Inhibit',
                new GLib.Variant('(susu)', ['org.parchaos.Controls', 0, 'Keep Awake', 4 | 8]),
                null, Gio.DBusCallFlags.NONE, 2000, null);
            [keepAwake.cookie] = reply.deepUnpack();
        } catch (e) {
            logError(e, 'parchaos-controls: could not keep the computer awake');
        }
    } else if (!on && keepAwake.cookie) {
        try {
            bus.call_sync('org.gnome.SessionManager', '/org/gnome/SessionManager', 'org.gnome.SessionManager',
                'Uninhibit', new GLib.Variant('(u)', [keepAwake.cookie]), null, Gio.DBusCallFlags.NONE, 2000, null);
        } catch (e) {
            logError(e, 'parchaos-controls: could not end Keep Awake');
        }
        keepAwake.cookie = 0;
    }
    keepAwake.state?.set(!!keepAwake.cookie);
}

/** Ends Keep Awake and restores minimized windows when the extension is turned off. */
export function resetCatalog() {
    setKeepAwake(false);
    showDesktop.windows = null;
}

// Show Desktop: minimizes the windows of this workspace; tapping again brings back those it hid.
const showDesktop = {windows: null};

function toggleShowDesktop() {
    if (showDesktop.windows) {
        for (const w of showDesktop.windows) {
            if (w.get_display())
                w.unminimize();
        }
        showDesktop.windows = null;
        return;
    }
    const workspace = global.workspace_manager.get_active_workspace();
    showDesktop.windows = workspace.list_windows()
        .filter(w => !w.minimized && !w.skip_taskbar && w.get_window_type() === 0);
    for (const w of showDesktop.windows)
        w.minimize();
}

/**
 * Adds every catalogue control that applies. helpers: {_, add, smallToggle, smallAction, sliderTile,
 * tile, labels, close} from the panel.
 */
export function addCatalogControls(h) {
    const {_, add, smallToggle, smallAction, close} = h;
    const action = (id, name, icon, run) => add(id, name, 1, 1, smallAction(icon, name, () => {
        close();
        run();
    }));
    const toggle = (id, name, state, onTap) => {
        if (!state)
            return;
        const t = smallToggle(state, name, onTap ?? (() => state.toggle()));
        t.connect('destroy', () => state.destroy());
        add(id, name, 1, 1, t);
    };

    if (appInstalled('org.gnome.Calculator.desktop'))
        action('calculator', _('Calculator'), CATALOG.calculator.icon, () => appInstalled('org.gnome.Calculator.desktop').activate());

    // Clocks opens on the panel it last showed; set that first.
    if (appInstalled('org.gnome.clocks.desktop')) {
        const clocks = panel => {
            settingsFor('org.gnome.clocks.state.window', 'panel-id')?.set_string('panel-id', panel);
            appInstalled('org.gnome.clocks.desktop').activate();
        };
        action('timer', _('Timer'), CATALOG.timer.icon, () => clocks('timer'));
        action('alarm', _('Alarm'), CATALOG.alarm.icon, () => clocks('alarm'));
        action('stopwatch', _('Stopwatch'), CATALOG.stopwatch.icon, () => clocks('stopwatch'));
    }

    // A new note: an empty Markdown file in ~/Documents/Notes named after the time, in Text Editor.
    if (GLib.find_program_in_path('gnome-text-editor')) {
        action('new-note', _('New Note'), CATALOG['new-note'].icon, () => {
            const docs = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOCUMENTS) ?? GLib.get_home_dir();
            const dir = GLib.build_filenamev([docs, _('Notes')]);
            GLib.mkdir_with_parents(dir, 0o755);
            const name = GLib.DateTime.new_now_local().format('%Y-%m-%d %H.%M.%S');
            const path = GLib.build_filenamev([dir, `${name}.md`]);
            try {
                GLib.file_set_contents(path, '');
            } catch (e) {
                logError(e, 'parchaos-controls: could not create the note');
                return;
            }
            launch(['gnome-text-editor', path]);
        });
    }

    // Weather mirrors the menu bar's weather item (same data, same place).
    const weather = Main.panel.statusArea['parchaos-weather'];
    if (weather?.visible && weather._conditionIcon && weather._label) {
        const t = h.tile(2, 1, 'parchaos-controls-focus');
        const row = new St.BoxLayout({x_expand: true, y_align: Clutter.ActorAlign.CENTER,
            style: 'padding: 0 14px 0 12px; spacing: 10px;'});
        const icon = new St.Icon({icon_size: 24, style_class: 'parchaos-controls-circle-icon'});
        const {box, t: title, s: sub} = h.labels(_('Weather'), '');
        row.add_child(icon);
        row.add_child(box);
        t.add_child(row);
        const sync = () => {
            icon.icon_name = weather._conditionIcon.icon_name;
            title.text = weather._label.text || _('Weather');
            sub.text = weather._data?.place ?? _('Weather');
        };
        sync();
        t.reactive = true;
        t.connect('button-release-event', () => {
            close();
            openStatusMenu('parchaos-weather');
            return Clutter.EVENT_STOP;
        });
        add('weather', _('Weather'), 2, 1, t);
    }

    // Keyboard brightness, only with a backlit keyboard (UPower reports a maximum above 0).
    try {
        const call = (method, args = null) => Gio.DBus.system.call_sync('org.freedesktop.UPower',
            '/org/freedesktop/UPower/KbdBacklight', 'org.freedesktop.UPower.KbdBacklight', method, args,
            null, Gio.DBusCallFlags.NONE, 300, null).deepUnpack()[0];
        const max = call('GetMaxBrightness');
        if (max > 0) {
            const {tile: t, slider} = h.sliderTile(_('Keyboard Brightness'), 'keyboard-brightness-symbolic');
            slider.value = call('GetBrightness') / max;
            slider.connect('notify::value', () => {
                try {
                    call('SetBrightness', new GLib.Variant('(i)', [Math.round(slider.value * max)]));
                } catch (e) {
                    logError(e, 'parchaos-controls: could not set the keyboard brightness');
                }
            });
            add('keyboard-brightness', _('Keyboard Brightness'), 4, 1, t);
        }
    } catch (e) {
        // no UPower, or no backlit keyboard
    }

    action('screen-recording', _('Screen Recording'), CATALOG['screen-recording'].icon, () => {
        GLib.timeout_add(GLib.PRIORITY_DEFAULT, 250, () => {
            Main.screenshotUI.open(1).catch(logError);   // 1 = screencast mode
            return GLib.SOURCE_REMOVE;
        });
    });

    keepAwake.state = new ToggleState({'icon-name': CATALOG['keep-awake'].icon});
    keepAwake.state.set(!!keepAwake.cookie);
    const awake = keepAwake.state;
    awake.toggle = () => setKeepAwake(!keepAwake.cookie);
    awake._onDestroy = () => {
        if (keepAwake.state === awake)
            keepAwake.state = null;
    };
    toggle('keep-awake', _('Keep Awake'), awake);

    toggle('camera-off', _('Camera Off'), boolToggle('org.gnome.desktop.privacy', 'disable-camera', CATALOG['camera-off'].icon));
    toggle('microphone-off', _('Microphone Off'),
        boolToggle('org.gnome.desktop.privacy', 'disable-microphone', CATALOG['microphone-off'].icon));
    toggle('location', _('Location'), boolToggle('org.gnome.system.location', 'enabled', CATALOG.location.icon));
    toggle('larger-text', _('Larger Text'), settingToggle('org.gnome.desktop.interface', 'text-scaling-factor',
        CATALOG['larger-text'].icon, s => s.get_double('text-scaling-factor') > 1.01,
        (s, on) => s.set_double('text-scaling-factor', on ? 1.25 : 1.0)));
    toggle('zoom', _('Zoom'), boolToggle('org.gnome.desktop.a11y.applications', 'screen-magnifier-enabled', CATALOG.zoom.icon));
    toggle('high-contrast', _('High Contrast'),
        boolToggle('org.gnome.desktop.a11y.interface', 'high-contrast', CATALOG['high-contrast'].icon));

    action('show-desktop', _('Show Desktop'), CATALOG['show-desktop'].icon, toggleShowDesktop);

    if (GLib.find_program_in_path('deja-dup'))
        action('back-up-now', _('Back Up Now'), CATALOG['back-up-now'].icon, () => launch(['deja-dup', '--backup']));

    if (Main.panel.statusArea.clipboardIndicator)
        action('clipboard', _('Clipboard History'), CATALOG.clipboard.icon, () => openStatusMenu('clipboardIndicator'));

    const dictation = extensionObject('parchaos-dictation@parchaos.org');
    if (dictation?.toggle)
        action('dictation', _('Dictation'), CATALOG.dictation.icon, () => dictation.toggle());
    const speak = extensionObject('parchaos-speak@parchaos.org');
    if (speak?.toggle) {
        // Reads what is selected now, so the panel must be gone first (it would take the selection's focus).
        action('speak-selection', _('Speak Selection'), CATALOG['speak-selection'].icon,
            () => GLib.timeout_add(GLib.PRIORITY_DEFAULT, 300, () => {
                speak.toggle();
                return GLib.SOURCE_REMOVE;
            }));
    }

    if (Main.panel.statusArea['wisp@epogonii.github.io'])
        action('snapshots', _('Snapshots'), CATALOG.snapshots.icon, () => openStatusMenu('wisp@epogonii.github.io'));
}
