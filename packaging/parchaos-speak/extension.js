// SPDX-License-Identifier: GPL-3.0-or-later
// Parcha Speak: select text in any app, press the shortcut, and it is read
// aloud; press it again to stop (ticket #162).
// Original code for ParchaOS, GPL-3.0-or-later.

import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import St from 'gi://St';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

// Tests point this at a stand-in so no speech engine is needed.
const SAY = GLib.getenv('PARCHAOS_SPEAK_SAY') ?? '/usr/libexec/parchaos-speak/parchaos-speak-say';

export default class SpeakExtension extends Extension {
    enable() {
        this._proc = null;
        this._settings = this.getSettings();
        Main.wm.addKeybinding('toggle-shortcut', this._settings, Meta.KeyBindingFlags.NONE,
            Shell.ActionMode.NORMAL | Shell.ActionMode.OVERVIEW, () => this.toggle());
    }

    disable() {
        Main.wm.removeKeybinding('toggle-shortcut');
        this._stop();
        this._settings = null;
    }

    toggle() {
        if (this._proc) {
            this._stop();
            return;
        }
        // What is highlighted is the primary selection; fall back to the
        // clipboard so text that was just copied can be read too.
        const clipboard = St.Clipboard.get_default();
        clipboard.get_text(St.ClipboardType.PRIMARY, (_c, primary) => {
            if (primary && primary.trim()) {
                this._speak(primary);
                return;
            }
            clipboard.get_text(St.ClipboardType.CLIPBOARD, (_c2, copied) => {
                if (copied && copied.trim())
                    this._speak(copied);
                else
                    Main.notify('Speak', 'Select some text first, then press the shortcut.');
            });
        });
    }

    _speak(text) {
        const proc = Gio.Subprocess.new(
            [SAY, '--speed', String(this._settings.get_int('speed'))],
            Gio.SubprocessFlags.STDIN_PIPE | Gio.SubprocessFlags.STDERR_SILENCE);
        this._proc = proc;
        proc.communicate_utf8_async(text, null, () => {
            if (this._proc === proc)
                this._proc = null;
        });
    }

    _stop() {
        const proc = this._proc;
        this._proc = null;
        proc?.force_exit();
    }
}
