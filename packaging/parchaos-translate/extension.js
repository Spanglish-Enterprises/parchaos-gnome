// SPDX-License-Identifier: GPL-3.0-or-later
// Parcha Translate (ticket #152): select text in any app, press Ctrl+Alt+T, and a small glass
// popup by the pointer shows it in English or Spanish, translated on this computer
// (parchaos-translate, Opus-MT models). Copy puts the translation on the clipboard; the arrows
// button is for a wrong guess: it reads the text as the other language. The first time, the
// popup offers the one-time set-up.
//
// Original code for ParchaOS, GPL-3.0-or-later.

import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import Pango from 'gi://Pango';
import Shell from 'gi://Shell';
import St from 'gi://St';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import Gettext from 'gettext';

const DOMAIN = 'parchaos-translate';
Gettext.bindtextdomain(DOMAIN, GLib.getenv('PARCHAOS_LOCALEDIR') ?? '/usr/share/locale');
const _ = s => Gettext.dgettext(DOMAIN, s);

// Tests point this at a stand-in or an unpacked engine.
const TRANSLATE = GLib.getenv('PARCHAOS_TRANSLATE') ?? 'parchaos-translate';
const MAX_CHARS = 5000;
const WIDTH = 420;
const LONG_TEXT = 700;     // characters; longer translations scroll

Gio._promisify(Gio.Subprocess.prototype, 'communicate_utf8_async');

function capitalize(text) {
    return text.charAt(0).toLocaleUpperCase() + text.slice(1);
}

function langName(code) {
    return code === 'es' ? _('Spanish') : _('English');
}

export default class TranslateExtension extends Extension {
    enable() {
        this._settings = this.getSettings();
        Main.wm.addKeybinding('translate-shortcut', this._settings, Meta.KeyBindingFlags.NONE,
            Shell.ActionMode.NORMAL | Shell.ActionMode.OVERVIEW, () => this.begin());
    }

    disable() {
        Main.wm.removeKeybinding('translate-shortcut');
        this._close();
        this._settings = null;
    }

    begin() {
        if (this._catcher) {
            this._close();
            return;
        }
        const clipboard = St.Clipboard.get_default();
        clipboard.get_text(St.ClipboardType.PRIMARY, (_c, primary) => {
            if (primary && primary.trim()) {
                this.show(primary.trim());
                return;
            }
            clipboard.get_text(St.ClipboardType.CLIPBOARD, (_c2, copied) => {
                if (copied && copied.trim())
                    this.show(copied.trim());
                else
                    Main.notify(_('Translate'), _('Select some text first, then press the shortcut.'));
            });
        });
    }

    /** Opens the popup for `text` and translates it (to = null: into the other language). */
    show(text, to = null) {
        this._text = text.slice(0, MAX_CHARS);
        const [px, py] = global.get_pointer();
        this._anchor = this._anchor ?? [px, py];
        this._open();
        this._status(_('Translating…'));
        this._run(to).catch(e => logError(e, 'parchaos-translate'));
    }

    async _run(to) {
        const argv = [TRANSLATE, '--json'];
        if (to)
            argv.push('--to', to);
        let result = null;
        try {
            const proc = Gio.Subprocess.new(argv, Gio.SubprocessFlags.STDIN_PIPE |
                Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE);
            this._proc = proc;
            const [out] = await proc.communicate_utf8_async(this._text, null);
            result = JSON.parse((out ?? '').trim() || 'null');
        } catch (e) {
            result = {error: 'failed'};
        }
        if (!this._catcher)
            return;
        if (!result || result.error === 'failed' || (!result.error && typeof result.text !== 'string'))
            this._status(_('Could not translate this text.'));
        else if (result.error)
            this._offerSetup(result.error);
        else
            this._result(result);
    }

    // -- the popup --------------------------------------------------------------------------
    _open() {
        if (this._catcher) {
            this._body.destroy_all_children();
            return;
        }
        const catcher = new St.Widget({
            reactive: true, can_focus: true, x: 0, y: 0, width: global.stage.width, height: global.stage.height,
        });
        const popup = new St.BoxLayout({
            style_class: 'parchaos-translate-popup', orientation: Clutter.Orientation.VERTICAL,
            reactive: true, width: WIDTH,
        });
        const body = new St.BoxLayout({orientation: Clutter.Orientation.VERTICAL, style_class: 'parchaos-translate-body'});
        popup.add_child(body);
        catcher.add_child(popup);
        Main.uiGroup.add_child(catcher);
        this._catcher = catcher;
        this._popup = popup;
        this._body = body;
        this._grab = Main.pushModal(catcher, {actionMode: Shell.ActionMode.POPUP});
        catcher.grab_key_focus();
        catcher.connect('button-press-event', (_a, event) => {
            const [x, y] = event.get_coords();
            const [bx, by] = popup.get_transformed_position();
            if (x < bx || y < by || x > bx + popup.width || y > by + popup.height)
                this._close();
            return Clutter.EVENT_PROPAGATE;
        });
        catcher.connect('key-press-event', (_a, event) => {
            if (event.get_key_symbol() === Clutter.KEY_Escape) {
                this._close();
                return Clutter.EVENT_STOP;
            }
            return Clutter.EVENT_PROPAGATE;
        });
        popup.connect('notify::height', () => this._place());
    }

    /** Below and to the right of the pointer, inside its monitor. */
    _place() {
        if (!this._popup)
            return;
        const [ax, ay] = this._anchor;
        const index = global.display.get_current_monitor();
        const m = Main.layoutManager.monitors[index] ?? Main.layoutManager.primaryMonitor;
        const w = this._popup.width, h = this._popup.height;
        let x = ax - Math.round(w / 2), y = ay + 18;
        if (y + h > m.y + m.height - 10)
            y = Math.max(m.y + 10, ay - h - 18);
        x = Math.max(m.x + 10, Math.min(x, m.x + m.width - w - 10));
        this._popup.set_position(x, y);
    }

    _label(text, style) {
        const label = new St.Label({text, style_class: style});
        label.clutter_text.line_wrap = true;
        label.clutter_text.line_wrap_mode = Pango.WrapMode.WORD_CHAR;
        label.clutter_text.ellipsize = Pango.EllipsizeMode.NONE;
        return label;
    }

    _status(text) {
        this._body.destroy_all_children();
        this._body.add_child(this._label(text, 'parchaos-translate-status'));
        this._place();
    }

    _button(container, icon, label, callback, style = '') {
        const content = new St.BoxLayout({style_class: 'parchaos-translate-button-content'});
        if (icon)
            content.add_child(new St.Icon({icon_name: icon, icon_size: 16}));
        if (label) {
            const text = new St.Label({text: label, y_align: Clutter.ActorAlign.CENTER});
            text.clutter_text.ellipsize = Pango.EllipsizeMode.NONE;
            content.add_child(text);
        }
        const button = new St.Button({
            style_class: `parchaos-translate-button ${style}`, child: content, can_focus: true,
            accessible_name: label ?? '',
        });
        button.connect('clicked', callback);
        container.add_child(button);
        return button;
    }

    _result({from, to, text}) {
        this._body.destroy_all_children();
        const header = new St.BoxLayout({style_class: 'parchaos-translate-header'});
        // Translators: the direction of a translation, e.g. "Spanish → English".
        header.add_child(new St.Label({
            text: capitalize(_('%s → %s').format(langName(from), langName(to))),
            style_class: 'parchaos-translate-direction', y_align: Clutter.ActorAlign.CENTER, x_expand: true,
        }));
        const swap = this._button(header, 'media-playlist-repeat-symbolic', null,
            () => this.show(this._text, from), 'parchaos-translate-icon');
        // Translators: for when the language was guessed wrong, e.g. "Translate from Spanish instead".
        swap.tooltip_text = _('Translate from %s instead').format(langName(to));
        swap.accessible_name = swap.tooltip_text;
        this._body.add_child(header);

        const label = this._label(text, 'parchaos-translate-text');
        if (text.length > LONG_TEXT) {
            // Long text scrolls inside the popup instead of running off the screen.
            const scroll = new St.ScrollView({
                style_class: 'parchaos-translate-scroll', hscrollbar_policy: St.PolicyType.NEVER,
                vscrollbar_policy: St.PolicyType.AUTOMATIC, overlay_scrollbars: true,
            });
            const box = new St.BoxLayout({orientation: Clutter.Orientation.VERTICAL});
            box.add_child(label);
            scroll.child = box;
            this._body.add_child(scroll);
        } else {
            this._body.add_child(label);
        }

        const actions = new St.BoxLayout({style_class: 'parchaos-translate-actions'});
        const copy = this._button(actions, 'edit-copy-symbolic', _('Copy'), () => {
            St.Clipboard.get_default().set_text(St.ClipboardType.CLIPBOARD, text);
            copy.child.get_last_child().text = _('Copied');
            GLib.timeout_add(GLib.PRIORITY_DEFAULT, 600, () => {
                this._close();
                return GLib.SOURCE_REMOVE;
            });
        });
        actions.add_child(new St.Label({
            text: _('Translated on this computer'), style_class: 'parchaos-translate-note',
            x_expand: true, x_align: Clutter.ActorAlign.END, y_align: Clutter.ActorAlign.CENTER,
        }));
        this._body.add_child(actions);
        this._place();
        copy.grab_key_focus();
    }

    // -- first use ---------------------------------------------------------------------------
    _offerSetup(state) {
        this._body.destroy_all_children();
        this._body.add_child(this._label(_('Set Up Translation'), 'parchaos-translate-title'));
        this._body.add_child(this._label(
            _('Translation between English and Spanish runs on this computer, so nothing you ' +
              'translate is sent anywhere. It needs a one-time download of about 230 MB.') +
            (state === 'no-engine' ? ` ${_('You will be asked for your password to add the translation engine.')}` : ''),
            'parchaos-translate-text'));
        const actions = new St.BoxLayout({style_class: 'parchaos-translate-actions'});
        actions.add_child(new St.Widget({x_expand: true}));
        this._button(actions, null, _('Not Now'), () => this._close());
        this._button(actions, null, _('Set Up'), () => this._setup().catch(e => logError(e, 'parchaos-translate')),
            'parchaos-translate-suggested');
        this._body.add_child(actions);
        this._place();
    }

    async _setup() {
        this._status(_('Getting ready…'));
        const proc = Gio.Subprocess.new([TRANSLATE, 'setup'],
            Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE);
        this._proc = proc;
        const stream = new Gio.DataInputStream({base_stream: proc.get_stdout_pipe()});
        let ok = false, failed = '';
        for (;;) {
            // eslint-disable-next-line no-await-in-loop
            const [line] = await new Promise((resolve, reject) => stream.read_line_async(GLib.PRIORITY_DEFAULT, null, (s, res) => {
                try {
                    resolve(s.read_line_finish_utf8(res));
                } catch (e) {
                    reject(e);
                }
            }));
            if (line === null)
                break;
            if (!this._catcher)
                continue;
            if (line === 'step engine')
                this._status(_('Adding the translation engine…'));
            else if (line === 'step download')
                this._status(_('Downloading the translation models…'));
            else if (line.startsWith('progress '))
                // Translators: download progress, e.g. "Downloading… 42%"
                this._status(_('Downloading… %d%%').format(parseInt(line.slice(9))));
            else if (line === 'ready')
                ok = true;
            else if (line.startsWith('error '))
                failed = line.slice(6).split(' ')[0];
        }
        if (!this._catcher)
            return;
        if (ok)
            this.show(this._text);
        else if (failed === 'engine')
            this._status(_('The translation engine was not added. Press the shortcut to try again.'));
        else
            this._status(_('The download did not finish. Check the internet connection and press the shortcut to try again.'));
    }

    _close() {
        if (this._grab) {
            Main.popModal(this._grab);
            this._grab = null;
        }
        this._catcher?.destroy();
        this._catcher = null;
        this._popup = null;
        this._body = null;
        this._anchor = null;
    }
}
