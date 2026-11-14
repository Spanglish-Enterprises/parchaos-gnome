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
import Gettext from 'gettext';

// Translations (tickets #146/#53), bound to the domain directly like the menu bar.
const DOMAIN = 'parchaos-speak';
Gettext.bindtextdomain(DOMAIN, GLib.getenv('PARCHAOS_LOCALEDIR') ?? '/usr/share/locale');
const _ = s => Gettext.dgettext(DOMAIN, s);

// Tests point this at a stand-in so no speech engine is needed.
const SAY = GLib.getenv('PARCHAOS_SPEAK_SAY') ?? '/usr/libexec/parchaos-speak/parchaos-speak-say';
// Parcha Reader (ticket #184), when installed: the selected text in a calm reading window.
const READER = GLib.getenv('PARCHAOS_READER') ?? 'parchaos-reader';

export default class SpeakExtension extends Extension {
    enable() {
        this._proc = null;
        this._settings = this.getSettings();
        Main.wm.addKeybinding('toggle-shortcut', this._settings, Meta.KeyBindingFlags.NONE,
            Shell.ActionMode.NORMAL | Shell.ActionMode.OVERVIEW, () => this.toggle());
        this._reader = this._settings.settings_schema.has_key('reader-shortcut');
        if (this._reader) {
            Main.wm.addKeybinding('reader-shortcut', this._settings, Meta.KeyBindingFlags.NONE,
                Shell.ActionMode.NORMAL | Shell.ActionMode.OVERVIEW, () => this.openReader());
        }
    }

    disable() {
        Main.wm.removeKeybinding('toggle-shortcut');
        if (this._reader)
            Main.wm.removeKeybinding('reader-shortcut');
        this._stop();
        this._settings = null;
    }

    toggle() {
        if (this._proc) {
            this._stop();
            return;
        }
        this._withSelection(text => {
            if (text)
                this._speak(text);
            else
                Main.notify(_('Speak'), _('Select some text first, then press the shortcut.'));
        });
    }

    /** Opens the selected text in Parcha Reader; with nothing selected, the Reader reads the app's page. */
    openReader() {
        if (!GLib.find_program_in_path(READER))
            return;
        this._withSelection(text => {
            try {
                const proc = Gio.Subprocess.new([READER], Gio.SubprocessFlags.STDIN_PIPE);
                proc.communicate_utf8_async(text ?? '', null, null);
            } catch (e) {
                logError(e, 'parchaos-speak: could not open the reader');
            }
        }, false);
    }

    // What is highlighted is the primary selection; fall back to the
    // clipboard so text that was just copied can be used too.
    _withSelection(callback, useClipboard = true) {
        const clipboard = St.Clipboard.get_default();
        clipboard.get_text(St.ClipboardType.PRIMARY, (_c, primary) => {
            if (primary && primary.trim()) {
                callback(primary);
                return;
            }
            if (!useClipboard) {
                callback(null);
                return;
            }
            clipboard.get_text(St.ClipboardType.CLIPBOARD, (_c2, copied) =>
                callback(copied && copied.trim() ? copied : null));
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
