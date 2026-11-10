// SPDX-License-Identifier: GPL-3.0-or-later
// Ongoing activity (ticket #179): a small capsule in the menu bar, left of the status icons, for
// what is going on right now: a screen recording (elapsed time, Stop), a file transfer or download
// an app reports progress for, or media playing. Only the newest one shows in the capsule; clicking
// it lists them all with their actions. Nothing shows when nothing is going on.
//
// Sources: GNOME's screenshot tool for recordings, the LauncherEntry progress signal apps (Parcher,
// browsers) already send for the dock, and GNOME's own MPRIS player list for media.
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

const LAUNCHER_ENTRY = 'com.canonical.Unity.LauncherEntry';
// Progress that stops being reported (an app quit mid-download) is dropped after this long.
const PROGRESS_STALE_S = 30;
const TITLE_CHARS = 22;

/** "m:ss" or "h:mm:ss" for a number of seconds. */
export function elapsed(seconds) {
    const s = Math.max(0, Math.floor(seconds));
    const h = Math.floor(s / 3600), m = Math.floor(s / 60) % 60, r = s % 60;
    const two = n => String(n).padStart(2, '0');
    return h ? `${h}:${two(m)}:${two(r)}` : `${m}:${two(r)}`;
}

/** The desktop id in a LauncherEntry app URI ("application://org.gnome.Nautilus.desktop"). */
export function desktopIdOf(uri) {
    return uri?.startsWith('application://') ? uri.slice('application://'.length) : null;
}

function shorten(text) {
    return text.length > TITLE_CHARS ? `${text.slice(0, TITLE_CHARS - 1)}…` : text;
}

function now() {
    return GLib.get_monotonic_time() / 1e6;
}

const ActivityButton = GObject.registerClass(
class ActivityButton extends PanelMenu.Button {
    _init(gettext, mediaSource) {
        const _ = gettext;
        super._init(0.5, _('Ongoing Activity'));
        this._ = gettext;
        this._media = mediaSource;
        this.add_style_class_name('parchaos-activity');
        const box = new St.BoxLayout({style_class: 'parchaos-activity-capsule', y_align: Clutter.ActorAlign.CENTER});
        this._icon = new St.Icon({icon_size: 14, style_class: 'parchaos-activity-icon'});
        this._label = new St.Label({y_align: Clutter.ActorAlign.CENTER, style_class: 'parchaos-activity-label'});
        box.add_child(this._icon);
        box.add_child(this._label);
        this.add_child(box);
        this.container.hide();

        this._since = new Map();     // activity id -> when it started
        this._progress = new Map();  // desktop id -> {value, updated}
        this._recordingSince = 0;

        // Screen recordings from GNOME's screenshot tool; its own red indicator steps aside while
        // this capsule shows the recording.
        Main.screenshotUI.connectObject('notify::screencast-in-progress', () => {
            this._recordingSince = Main.screenshotUI.screencast_in_progress ? now() : 0;
            this._sync();
        }, this);
        // Its own code shows and hides the button inside, so the container is ours to hide.
        this._recordingIndicator = Main.panel.statusArea.screenRecording?.container ?? null;

        this._entryId = Gio.DBus.session.signal_subscribe(null, LAUNCHER_ENTRY, 'Update', null, null,
            Gio.DBusSignalFlags.NONE, (_c, _sender, _path, _iface, _signal, params) => {
                const [uri, props] = params.deep_unpack();
                const id = desktopIdOf(uri);
                if (!id)
                    return;
                const visible = props['progress-visible']?.deep_unpack();
                const value = props.progress?.deep_unpack();
                if (visible === false)
                    this._progress.delete(id);
                else if (typeof value === 'number' && (visible || this._progress.has(id)))
                    this._progress.set(id, {value, updated: now()});
                this._sync();
            });

        this._media.connectObject('player-added', () => this._watchPlayers(), 'player-removed', () => this._sync(), this);
        this._watchPlayers();

        // The recording clock and stale progress need a tick; it runs only while something shows.
        this._tickId = 0;
        this._sync();
    }

    _watchPlayers() {
        for (const player of this._media.players)
            player.connectObject('changed', () => this._sync(), this);
        this._sync();
    }

    /** Everything going on now, newest first. */
    activities() {
        const _ = this._;
        const list = [];
        if (this._recordingSince) {
            list.push({
                id: 'recording', icon: 'media-record-symbolic', urgent: true,
                short: elapsed(now() - this._recordingSince),
                title: _('Screen Recording'), subtitle: elapsed(now() - this._recordingSince),
                actions: [['media-playback-stop-symbolic', _('Stop'), () => Main.screenshotUI.stopScreencast()]],
            });
        }
        const appSystem = Shell.AppSystem.get_default();
        for (const [id, {value, updated}] of this._progress) {
            if (now() - updated > PROGRESS_STALE_S) {
                this._progress.delete(id);
                continue;
            }
            const app = appSystem.lookup_app(id);
            const pct = _('%d%%').format(Math.round(value * 100));
            list.push({
                id: `progress:${id}`, gicon: app?.get_icon(), icon: 'folder-download-symbolic',
                short: pct, title: app?.get_name() ?? _('Transfer'), subtitle: pct, value,
                activate: () => app?.activate(), actions: [],
            });
        }
        for (const player of this._media.players) {
            if (player.status !== 'Playing')
                continue;
            const title = player.trackTitle || player.app?.get_name() || _('Playing');
            list.push({
                id: `media:${player._busName ?? title}`, gicon: player.app?.get_icon(), icon: 'audio-x-generic-symbolic',
                short: shorten(title), title, subtitle: (player.trackArtists ?? []).join(', ') || player.app?.get_name() || '',
                activate: () => player.raise(),
                actions: [
                    ['media-playback-pause-symbolic', _('Pause'), () => player.playPause()],
                    ['media-skip-forward-symbolic', _('Next'), () => player.next()],
                ],
            });
        }
        const t = now();
        for (const a of list) {
            if (!this._since.has(a.id))
                this._since.set(a.id, t);
            a.since = this._since.get(a.id);
        }
        for (const id of [...this._since.keys()]) {
            if (!list.some(a => a.id === id))
                this._since.delete(id);
        }
        // A recording always leads (it is the one thing that must not be forgotten); then newest.
        return list.sort((a, b) => (b.urgent ?? 0) - (a.urgent ?? 0) || b.since - a.since);
    }

    _sync() {
        const list = this.activities();
        const top = list[0];
        this.container.visible = !!top;
        if (this._recordingIndicator)
            this._recordingIndicator.visible = !this._recordingSince;
        if (!top) {
            this.menu.close();
            this._stopTick();
            return;
        }
        if (top.gicon)
            this._icon.gicon = top.gicon;
        else
            this._icon.icon_name = top.icon;
        this._label.text = top.short;
        this.remove_style_class_name('parchaos-activity-recording');
        if (top.id === 'recording')
            this.add_style_class_name('parchaos-activity-recording');
        if (list.some(a => a.id === 'recording' || a.id.startsWith('progress:')))
            this._startTick();
        else
            this._stopTick();
        // GNOME does not open an empty menu, so the rows are kept current all the time. With the
        // same activities they are updated in place, so hovering one is not lost every second.
        if (this._rows && list.length === this._rows.size && list.every(a => this._rows.has(a.id))) {
            for (const a of list) {
                const row = this._rows.get(a.id);
                if (row.subtitle && a.subtitle)
                    row.subtitle.text = a.subtitle;
                row.setValue?.(a.value);
            }
        } else {
            this._fillMenu(list);
        }
    }

    _startTick() {
        if (this._tickId)
            return;
        this._tickId = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 1, () => {
            this._sync();
            return GLib.SOURCE_CONTINUE;
        });
    }

    _stopTick() {
        if (this._tickId)
            GLib.source_remove(this._tickId);
        this._tickId = 0;
    }

    _fillMenu(list = this.activities()) {
        this.menu.removeAll();
        this._rows = new Map();
        for (const a of list) {
            const row = {};
            this._rows.set(a.id, row);
            const item = new PopupMenu.PopupBaseMenuItem({style_class: 'parchaos-activity-row', reactive: !!a.activate});
            item.add_child(a.gicon ? new St.Icon({gicon: a.gicon, icon_size: 24})
                : new St.Icon({icon_name: a.icon, icon_size: 20}));
            const text = new St.BoxLayout({orientation: Clutter.Orientation.VERTICAL, x_expand: true});
            text.add_child(new St.Label({text: a.title, style_class: 'parchaos-activity-title'}));
            if (a.subtitle) {
                row.subtitle = new St.Label({text: a.subtitle, style_class: 'parchaos-activity-subtitle'});
                text.add_child(row.subtitle);
            }
            if (typeof a.value === 'number') {
                const bar = new St.Widget({style_class: 'parchaos-activity-bar', x_expand: true});
                const fill = new St.Widget({style_class: 'parchaos-activity-bar-fill'});
                bar.add_child(fill);
                let value = a.value;
                row.setValue = v => {
                    value = v ?? value;
                    fill.set_size(Math.round(bar.width * value), bar.height);
                };
                bar.connect('notify::width', () => row.setValue());
                text.add_child(bar);
            }
            item.add_child(text);
            for (const [icon, label, callback] of a.actions) {
                const button = new St.Button({
                    style_class: 'parchaos-activity-action', accessible_name: label,
                    child: new St.Icon({icon_name: icon, icon_size: 16}), y_align: Clutter.ActorAlign.CENTER,
                });
                button.connect('clicked', () => {
                    callback();
                    this.menu.close();
                });
                item.add_child(button);
            }
            if (a.activate)
                item.connect('activate', () => a.activate());
            this.menu.addMenuItem(item);
        }
    }

    _onDestroy() {
        this._stopTick();
        if (this._entryId)
            Gio.DBus.session.signal_unsubscribe(this._entryId);
        this._entryId = 0;
        Main.screenshotUI.disconnectObject(this);
        this._media.disconnectObject(this);
        for (const player of this._media.players)
            player.disconnectObject(this);
        if (this._recordingIndicator)
            this._recordingIndicator.visible = true;
        super._onDestroy();
    }
});

/** Adds the capsule to the menu bar, left of the status icons. */
export function addActivityButton(gettext, mediaSource) {
    const button = new ActivityButton(gettext, mediaSource);
    Main.panel.addToStatusArea('parchaos-activity', button, 0, 'right');
    // Adding it shows it; hide it again until something is going on.
    button._sync();
    return button;
}
