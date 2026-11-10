// SPDX-License-Identifier: GPL-3.0-or-later
// Privacy report (ticket #159): which apps used the microphone, the camera, the location or
// screen sharing, kept for seven days so ParchaOS Settings > Privacy can show them.
//
// Sources, all already on the desktop: the sound mixer's recording streams (microphone, with the
// app's name), PipeWire's video streams read with pw-dump whenever the camera turns on (camera),
// the location agent's grants (passed in from RecentActivity), and GNOME's screen-sharing and
// recording handles (no app name is known for those). The log stays on this computer in
// ~/.local/share/parchaos/privacy-log.json, readable only by the user; the privacy-report setting
// turns it off, and turning it off deletes the file.
//
// Original code for ParchaOS, GPL-3.0-or-later.

import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Gvc from 'gi://Gvc';
import Shell from 'gi://Shell';

import * as Volume from 'resource:///org/gnome/shell/ui/status/volume.js';

const KEEP_DAYS = 7;
const CAMERA_POLL_S = 10;   // while the camera is on, look for apps joining it

export const LOG_FILE = GLib.getenv('PARCHAOS_PRIVACY_LOG') ??
    GLib.build_filenamev([GLib.get_user_data_dir(), 'parchaos', 'privacy-log.json']);

function now() {
    return Math.floor(GLib.get_real_time() / 1e6);
}

/** Camera users from pw-dump output: [{app, name}] for every video capture stream. */
export function cameraStreams(dump) {
    const users = [];
    for (const object of dump ?? []) {
        const props = object?.info?.props ?? {};
        if (props['media.class'] !== 'Stream/Input/Video')
            continue;
        const app = props['pipewire.access.portal.app_id'] || props['application.id'] || '';
        const name = props['application.name'] || props['application.process.binary'] || app;
        if (name)
            users.push({app, name});
    }
    return users;
}

/** Drops events that ended more than KEEP_DAYS ago. */
export function prune(events, at = now()) {
    const since = at - KEEP_DAYS * 86400;
    return events.filter(e => (e.end ?? at) >= since);
}

export class PrivacyLog {
    constructor(settings) {
        this._settings = settings;
        this._open = new Map();   // key -> event still going on
        this._screens = 0;
        this._events = [];
        this._enabled = !!settings?.settings_schema.has_key('privacy-report') &&
            settings.get_boolean('privacy-report');
        this._enabledId = settings?.settings_schema.has_key('privacy-report')
            ? settings.connect('changed::privacy-report', () => this._setEnabled(settings.get_boolean('privacy-report')))
            : 0;
        if (this._enabled)
            this._start();
    }

    _setEnabled(on) {
        if (on === this._enabled)
            return;
        this._enabled = on;
        if (on) {
            this._start();
        } else {
            this._stop();
            this._events = [];
            this._open.clear();
            try {
                Gio.File.new_for_path(LOG_FILE).delete(null);
            } catch (e) {
                // not there
            }
        }
    }

    _start() {
        this._load();
        // Microphone: the mixer lists every recording stream with the app that opened it.
        this._mixer = Volume.getMixerControl();
        this._mixer.connectObject(
            'stream-added', (_m, id) => this._onStream(id, true),
            'stream-removed', (_m, id) => this._onStream(id, false), this);
        for (const stream of this._mixer.get_source_outputs?.() ?? [])
            this._onStream(stream.get_id(), true);
        // Camera: GNOME knows when a camera is in use; PipeWire says by whom.
        if (Shell.CameraMonitor) {
            this._camera = new Shell.CameraMonitor();
            this._camera.connectObject('notify::cameras-in-use', () => this._onCamera(), this);
            this._onCamera();
        }
        // Screen sharing and recording through the portals.
        const controller = global.backend.get_remote_access_controller?.();
        controller?.connectObject('new-handle', (_c, handle) => {
            const key = `screen:${++this._screens}`;
            this._begin(key, 'screen', '', '');
            handle.connectObject('stopped', () => this._end(key), this);
        }, this);
        this._controller = controller;
    }

    _stop() {
        this._mixer?.disconnectObject(this);
        this._mixer = null;
        this._camera?.disconnectObject(this);
        this._camera = null;
        this._controller?.disconnectObject(this);
        this._controller = null;
        if (this._pollId)
            GLib.source_remove(this._pollId);
        this._pollId = 0;
        for (const key of [...this._open.keys()])
            this._end(key);
        this._save();
    }

    _onStream(id, added) {
        const key = `mic:${id}`;
        if (!added) {
            this._end(key);
            return;
        }
        const stream = this._mixer.lookup_stream_id(id);
        if (!(stream instanceof Gvc.MixerSourceOutput) || stream.is_event_stream)
            return;
        const app = stream.get_application_id() ?? '';
        const name = stream.get_name() || app;
        // The shell's own sound feedback and level meters are not apps using the microphone.
        if (!name || /gnome-shell|parchaos/i.test(`${app} ${name}`))
            return;
        this._begin(key, 'microphone', app, name);
    }

    _onCamera() {
        if (this._camera.cameras_in_use) {
            this._readCameraUsers();
            this._pollId ||= GLib.timeout_add_seconds(GLib.PRIORITY_LOW, CAMERA_POLL_S, () => {
                this._readCameraUsers();
                return GLib.SOURCE_CONTINUE;
            });
        } else {
            if (this._pollId)
                GLib.source_remove(this._pollId);
            this._pollId = 0;
            for (const key of [...this._open.keys()]) {
                if (key.startsWith('camera:'))
                    this._end(key);
            }
        }
    }

    _readCameraUsers() {
        let proc;
        try {
            proc = Gio.Subprocess.new(['pw-dump'], Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE);
        } catch (e) {
            this._begin('camera:unknown', 'camera', '', '');
            return;
        }
        proc.communicate_utf8_async(null, null, (p, res) => {
            let users = [];
            try {
                const [, out] = p.communicate_utf8_finish(res);
                users = cameraStreams(JSON.parse(out || '[]'));
            } catch (e) {
                // unreadable: still note that the camera was used
            }
            if (!this._camera?.cameras_in_use)
                return;
            if (!users.length)
                users = [{app: '', name: ''}];
            for (const {app, name} of users)
                this._begin(`camera:${app || name}`, 'camera', app, name);
        });
    }

    /** A location grant (from the location agent); it has no end. */
    noteLocation(app) {
        if (!this._enabled)
            return;
        const t = now();
        this._events.push({kind: 'location', app: app.get_id(), name: app.get_name(), start: t, end: t});
        this._save();
    }

    _begin(key, kind, app, name) {
        if (this._open.has(key))
            return;
        // Desktop ids are what Settings can look up for names and icons.
        const appInfo = app ? Shell.AppSystem.get_default().lookup_app(app.endsWith('.desktop') ? app : `${app}.desktop`) : null;
        const event = {kind, app: appInfo?.get_id() ?? app, name: appInfo?.get_name() ?? name, start: now(), end: null};
        this._open.set(key, event);
        this._events.push(event);
        this._save();
    }

    _end(key) {
        const event = this._open.get(key);
        if (!event)
            return;
        this._open.delete(key);
        event.end = now();
        this._save();
    }

    _load() {
        try {
            const [, bytes] = GLib.file_get_contents(LOG_FILE);
            const data = JSON.parse(new TextDecoder().decode(bytes));
            // Anything left open by a shell that stopped ended when that shell did; drop the end.
            this._events = data?.version === 1 && Array.isArray(data.events)
                ? prune(data.events.map(e => ({...e, end: e.end ?? e.start}))) : [];
        } catch (e) {
            this._events = [];
        }
    }

    _save() {
        if (!this._enabled)
            return;
        this._events = prune(this._events);
        try {
            GLib.mkdir_with_parents(GLib.path_get_dirname(LOG_FILE), 0o700);
            const file = Gio.File.new_for_path(LOG_FILE);
            const bytes = new TextEncoder().encode(JSON.stringify({version: 1, events: this._events}));
            file.replace_contents(bytes, null, false, Gio.FileCreateFlags.PRIVATE | Gio.FileCreateFlags.REPLACE_DESTINATION, null);
        } catch (e) {
            logError(e, 'parchaos-controls: could not save the privacy report');
        }
    }

    destroy() {
        this._stop();
        if (this._enabledId)
            this._settings.disconnect(this._enabledId);
        this._enabledId = 0;
    }
}
