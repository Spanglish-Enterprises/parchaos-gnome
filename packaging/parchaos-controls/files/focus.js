// SPDX-License-Identifier: GPL-3.0-or-later
// Focus modes (ticket #154): Work, Sleep and Personal next to GNOME's Do Not Disturb.
//
// Do Not Disturb stays GNOME's own switch (no banners at all). A focus mode instead lets the
// apps listed for it (org.parchaos.desktop focus-mode-apps) show banners and sends every other
// app's notifications straight to the notification list; urgent ones, such as alarms, always
// show. A mode can switch to the dark appearance while it is on (focus-mode-dark) and puts the
// previous appearance back when it ends. The nightly schedule (parchaos-focus-schedule) turns
// Sleep on and off.
//
// Original code for ParchaOS, GPL-3.0-or-later.

import Gio from 'gi://Gio';
import GObject from 'gi://GObject';

import * as MessageTray from 'resource:///org/gnome/shell/ui/messageTray.js';

export const MODES = ['work', 'sleep', 'personal'];
// The states the Focus control steps through, in order.
export const STATES = ['dnd', ...MODES];

export const MODE_ICONS = {
    'dnd': 'notifications-disabled-symbolic',
    'work': 'x-office-calendar-symbolic',
    'sleep': 'weather-clear-night-symbolic',
    'personal': 'avatar-default-symbolic',
};

/** Whether a notification from `appId` may show a banner in `mode`. */
export function allowed(mode, appId, modeApps, urgency) {
    if (!mode || urgency === MessageTray.Urgency.CRITICAL)
        return true;
    // GNOME keeps per-app notification ids canonical (org-gnome-calendar); compare in that form.
    const bare = id => id.replace(/\.desktop$/, '').toLowerCase().replace(/[^a-z0-9-]/g, '-').replace(/--+/g, '-');
    return !!appId && (modeApps[mode] ?? []).some(id => bare(id) === bare(appId));
}

function appIdOf(notification) {
    const source = notification.source;
    return source?.app?.get_id?.() ?? source?.policy?.id ?? '';
}

/**
 * The Focus state as one object for the Control Center tile: 'off', 'dnd' or a mode, with
 * `checked` and `icon-name` in the shape the tile circles read.
 */
export const FocusState = GObject.registerClass({
    Properties: {
        'checked': GObject.ParamSpec.boolean('checked', null, null, GObject.ParamFlags.READWRITE, false),
        'icon-name': GObject.ParamSpec.string('icon-name', null, null, GObject.ParamFlags.READWRITE,
            MODE_ICONS.dnd),
    },
    Signals: {'changed': {}},
}, class FocusState extends GObject.Object {
    _init(desktop) {
        super._init();
        this._desktop = desktop;
        this._banners = new Gio.Settings({schema_id: 'org.gnome.desktop.notifications'});
        this._last = 'dnd';
        this._desktop.connectObject('changed::focus-mode', () => this._sync(), this);
        this._banners.connectObject('changed::show-banners', () => this._sync(), this);
        this._sync();
    }

    get state() {
        const mode = this._desktop.get_string('focus-mode');
        if (mode)
            return mode;
        return this._banners.get_boolean('show-banners') ? 'off' : 'dnd';
    }

    set state(next) {
        if (next !== 'off')
            this._last = next;
        this._desktop.set_string('focus-mode', MODES.includes(next) ? next : '');
        this._banners.set_boolean('show-banners', next !== 'dnd');
    }

    /** On and off, back to the last state used. */
    toggle() {
        this.state = this.state === 'off' ? this._last : 'off';
    }

    /** The next state in STATES (from off, the first). */
    next() {
        const i = STATES.indexOf(this.state);
        this.state = STATES[(i + 1) % STATES.length];
    }

    _sync() {
        const state = this.state;
        if (state !== 'off')
            this._last = state;
        this.checked = state !== 'off';
        this.icon_name = MODE_ICONS[state] ?? MODE_ICONS.dnd;
        this.emit('changed');
    }

    destroy() {
        this._desktop.disconnectObject(this);
        this._banners.disconnectObject(this);
    }
});

/** The banner rule and the dark appearance, for as long as the extension runs. */
export class FocusModes {
    constructor(desktop, injections) {
        this._desktop = desktop;
        this._interface = new Gio.Settings({schema_id: 'org.gnome.desktop.interface'});
        const self = this;
        injections.overrideMethod(MessageTray.MessageTray.prototype, '_onNotificationRequestBanner',
            original => function (source, notification) {
                const mode = self._desktop.get_string('focus-mode');
                if (mode && !allowed(mode, appIdOf(notification),
                    self._desktop.get_value('focus-mode-apps').deepUnpack(), notification.urgency))
                    return;
                original.call(this, source, notification);
            });
        this._mode = desktop.get_string('focus-mode');
        desktop.connectObject('changed::focus-mode', () => this._modeChanged(), this);
    }

    _modeChanged() {
        const mode = this._desktop.get_string('focus-mode');
        const dark = this._desktop.get_strv('focus-mode-dark');
        const wasDark = dark.includes(this._mode), isDark = dark.includes(mode);
        if (isDark && !wasDark) {
            this._scheme = this._interface.get_string('color-scheme');
            this._interface.set_string('color-scheme', 'prefer-dark');
        } else if (wasDark && !isDark && this._scheme !== undefined) {
            // Only put it back if nobody changed it meanwhile.
            if (this._interface.get_string('color-scheme') === 'prefer-dark')
                this._interface.set_string('color-scheme', this._scheme);
            this._scheme = undefined;
        }
        this._mode = mode;
    }

    destroy() {
        this._desktop.disconnectObject(this);
    }
}
