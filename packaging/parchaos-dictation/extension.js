// SPDX-License-Identifier: GPL-3.0-or-later
// Parcha Dictation: one shortcut starts listening, the same shortcut stops
// and types what was said at the cursor, in any app (ticket #119).
// Original code for ParchaOS, GPL-3.0-or-later.

import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import St from 'gi://St';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';

const LIBEXEC = '/usr/libexec/parchaos-dictation';
// Tests point these at stand-ins so no microphone or model is needed.
const RECORDER = GLib.getenv('PARCHAOS_DICTATION_RECORDER');
const TRANSCRIBER = GLib.getenv('PARCHAOS_DICTATION_TRANSCRIBER') ?? `${LIBEXEC}/parchaos-dictation-transcribe`;
const MODELS = GLib.getenv('PARCHAOS_DICTATION_MODEL_TOOL') ?? `${LIBEXEC}/parchaos-dictation-model`;

function run(argv) {
    return new Promise((resolve, reject) => {
        const proc = Gio.Subprocess.new(argv, Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE);
        proc.communicate_utf8_async(null, null, (p, res) => {
            try {
                const [, out] = p.communicate_utf8_finish(res);
                resolve({ok: p.get_successful(), out: (out ?? '').trim()});
            } catch (e) {
                reject(e);
            }
        });
    });
}

export default class DictationExtension extends Extension {
    enable() {
        this._state = 'idle';
        this._keyboard = null;
        this._indicator = new PanelMenu.Button(0.0, 'Parcha Dictation', true);
        this._icon = new St.Icon({icon_name: 'audio-input-microphone-symbolic', style_class: 'system-status-icon'});
        this._indicator.add_child(this._icon);
        this._indicator.hide();
        Main.panel.addToStatusArea('parchaos-dictation', this._indicator);

        this._settings = this.getSettings();
        Main.wm.addKeybinding('toggle-shortcut', this._settings, Meta.KeyBindingFlags.NONE,
            Shell.ActionMode.NORMAL | Shell.ActionMode.OVERVIEW, () => this.toggle());
        this._indicator.connect('button-press-event', () => { this.toggle(); return Clutter.EVENT_STOP; });
    }

    disable() {
        Main.wm.removeKeybinding('toggle-shortcut');
        this._killRecorder();
        this._indicator?.destroy();
        this._indicator = null;
        this._settings = null;
        this._keyboard = null;
    }

    toggle() {
        if (this._state === 'idle')
            this._start().catch(e => this._fail(e));
        else if (this._state === 'recording')
            this._stop().catch(e => this._fail(e));
    }

    _show(state, symbol) {
        this._state = state;
        this._indicator.show();
        this._icon.icon_name = symbol;
        this._icon.style = state === 'recording' ? 'color: #ff4d6d;' : '';
    }

    _hide() {
        this._state = 'idle';
        this._indicator?.hide();
    }

    _fail(err) {
        console.error(`parchaos-dictation: ${err}`);
        this._hide();
        Main.notify('Dictation', 'Something went wrong. Nothing was typed.');
    }

    async _start() {
        if (!(await run([MODELS, 'status'])).ok) {
            this._show('working', 'folder-download-symbolic');
            Main.notify('Dictation', 'Getting the speech model (148 MB) once. Press the shortcut again when this message says it is ready.');
            const got = await run([MODELS, 'download']);
            this._hide();
            Main.notify('Dictation', got.ok ? 'Ready. Press the shortcut and speak.' : 'The download failed. Check your connection and try again.');
            return;
        }
        this._wav = GLib.build_filenamev([GLib.get_user_runtime_dir(), 'parchaos-dictation.wav']);
        const argv = RECORDER ? [RECORDER, this._wav]
            : ['pw-record', '--rate', '16000', '--channels', '1', '--format', 's16', this._wav];
        this._recorder = Gio.Subprocess.new(argv, Gio.SubprocessFlags.STDERR_SILENCE);
        this._show('recording', 'audio-input-microphone-symbolic');
    }

    _killRecorder() {
        try { this._recorder?.send_signal(2); } catch (e) { /* already gone */ }
    }

    async _stop() {
        const recorder = this._recorder;
        this._recorder = null;
        this._show('working', 'content-loading-symbolic');
        recorder.send_signal(2); // SIGINT: pw-record finishes the WAV header
        await new Promise(resolve => recorder.wait_async(null, () => resolve()));
        const result = await run([TRANSCRIBER, this._wav]);
        try { Gio.File.new_for_path(this._wav).delete(null); } catch (e) { /* ignore */ }
        this._hide();
        if (!result.ok)
            throw new Error('transcription failed');
        if (result.out)
            this._type(result.out);
    }

    // Typed as key presses, so it works in terminals and never touches the clipboard.
    _type(text) {
        if (!this._keyboard) {
            const seat = Clutter.get_default_backend().get_default_seat();
            this._keyboard = seat.create_virtual_device(Clutter.InputDeviceType.KEYBOARD_DEVICE);
        }
        for (const ch of text) {
            if (ch === '\n' || ch === '\r')
                continue;
            const keyval = Clutter.unicode_to_keysym(ch.codePointAt(0));
            this._keyboard.notify_keyval(0, keyval, Clutter.KeyState.PRESSED);
            this._keyboard.notify_keyval(0, keyval, Clutter.KeyState.RELEASED);
        }
    }
}
