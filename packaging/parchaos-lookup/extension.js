// SPDX-License-Identifier: GPL-3.0-or-later
// Screen Lookup (ticket #180): press the shortcut, drag a box around part of the screen, and
// choose what to do with the text in it: copy it, search the web for it, or ask the assistant.
//
// The text is read on this computer (parchaos-lookup-ocr, Tesseract). Nothing leaves the
// machine unless Search the Web is chosen; Ask the Assistant only fills in the assistant's
// question box, and nothing is sent until the user sends it there.
//
// Original code for ParchaOS, GPL-3.0-or-later.

import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import Mtk from 'gi://Mtk';
import Pango from 'gi://Pango';
import Shell from 'gi://Shell';
import St from 'gi://St';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import Gettext from 'gettext';

const DOMAIN = 'parchaos-lookup';
Gettext.bindtextdomain(DOMAIN, GLib.getenv('PARCHAOS_LOCALEDIR') ?? '/usr/share/locale');
const _ = s => Gettext.dgettext(DOMAIN, s);

// Tests point this at a stand-in so no OCR engine is needed.
const OCR = GLib.getenv('PARCHAOS_LOOKUP_OCR') ?? '/usr/libexec/parchaos-lookup/parchaos-lookup-ocr';
const SEARCH_URL = 'https://duckduckgo.com/?q=';
const MIN_SIZE = 8;          // px; a smaller box is taken as a click and cancels
const PREVIEW_CHARS = 400;

Gio._promisify(Shell.Screenshot.prototype, 'screenshot_area');
Gio._promisify(Gio.Subprocess.prototype, 'communicate_utf8_async');

export default class LookupExtension extends Extension {
    enable() {
        this._settings = this.getSettings();
        Main.wm.addKeybinding('lookup-shortcut', this._settings, Meta.KeyBindingFlags.NONE,
            Shell.ActionMode.NORMAL | Shell.ActionMode.OVERVIEW, () => this.begin());
    }

    disable() {
        Main.wm.removeKeybinding('lookup-shortcut');
        this._endSelection();
        this._closePopover();
        this._settings = null;
    }

    /** Dims the screen and lets a box be dragged; Escape or a click cancels. */
    begin() {
        if (this._shade || this._catcher)
            return;
        const shade = new St.Widget({
            style_class: 'parchaos-lookup-shade', reactive: true, can_focus: true,
            x: 0, y: 0, width: global.stage.width, height: global.stage.height,
        });
        const box = new St.Widget({style_class: 'parchaos-lookup-box', visible: false});
        shade.add_child(box);
        const hint = new St.Label({style_class: 'parchaos-lookup-hint', text: _('Drag around the text to look up')});
        shade.add_child(hint);
        Main.uiGroup.add_child(shade);
        const monitor = Main.layoutManager.primaryMonitor;
        hint.set_position(monitor.x + Math.round((monitor.width - hint.width) / 2), monitor.y + Math.round(monitor.height * 0.12));

        this._shade = shade;
        this._grab = Main.pushModal(shade, {actionMode: Shell.ActionMode.POPUP});
        shade.grab_key_focus();
        shade.set_cursor_type?.(Clutter.CursorType.CROSSHAIR);

        let start = null;
        const rect = () => {
            const [x, y] = global.get_pointer();
            return {
                x: Math.min(start[0], x), y: Math.min(start[1], y),
                width: Math.abs(x - start[0]), height: Math.abs(y - start[1]),
            };
        };
        shade.connect('button-press-event', (_a, event) => {
            if (event.get_button() !== Clutter.BUTTON_PRIMARY)
                return Clutter.EVENT_PROPAGATE;
            start = event.get_coords().map(Math.round);
            hint.hide();
            return Clutter.EVENT_STOP;
        });
        shade.connect('motion-event', () => {
            if (start) {
                const r = rect();
                box.set_position(r.x, r.y);
                box.set_size(r.width, r.height);
                box.show();
            }
            return Clutter.EVENT_STOP;
        });
        shade.connect('button-release-event', () => {
            if (!start)
                return Clutter.EVENT_STOP;
            const r = rect();
            this._endSelection();
            if (r.width >= MIN_SIZE && r.height >= MIN_SIZE)
                this._lookUp(r).catch(e => logError(e, 'parchaos-lookup'));
            return Clutter.EVENT_STOP;
        });
        shade.connect('key-press-event', (_a, event) => {
            if (event.get_key_symbol() === Clutter.KEY_Escape)
                this._endSelection();
            return Clutter.EVENT_STOP;
        });
    }

    _endSelection() {
        if (this._grab) {
            Main.popModal(this._grab);
            this._grab = null;
        }
        this._shade?.destroy();
        this._shade = null;
    }

    async _lookUp(rect) {
        // Let the shade disappear from the screen before taking the picture.
        await new Promise(resolve => GLib.timeout_add(GLib.PRIORITY_DEFAULT, 80, () => {
            resolve();
            return GLib.SOURCE_REMOVE;
        }));
        const dir = GLib.build_filenamev([GLib.get_user_runtime_dir(), 'parchaos-lookup']);
        GLib.mkdir_with_parents(dir, 0o700);
        const path = GLib.build_filenamev([dir, 'area.png']);
        const file = Gio.File.new_for_path(path);
        const stream = file.replace(null, false, Gio.FileCreateFlags.PRIVATE | Gio.FileCreateFlags.REPLACE_DESTINATION, null);
        await new Shell.Screenshot().screenshot_area(rect.x, rect.y, rect.width, rect.height, stream);
        stream.close(null);

        this._showPopover(rect, null);
        let text = '';
        try {
            const proc = Gio.Subprocess.new([OCR, path], Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE);
            const [out] = await proc.communicate_utf8_async(null, null);
            text = (out ?? '').trim();
        } catch (e) {
            logError(e, 'parchaos-lookup: reading the text failed');
        } finally {
            try {
                file.delete(null);
            } catch (e) {
                // already gone
            }
        }
        if (this._catcher)
            this._showPopover(rect, text);
    }

    /** The glass popover by the selection: "Reading..." while `text` is null, then the actions. */
    _showPopover(rect, text) {
        this._closePopover();
        this._actions = null;
        const catcher = new St.Widget({
            reactive: true, can_focus: true, x: 0, y: 0, width: global.stage.width, height: global.stage.height,
        });
        const popover = new St.BoxLayout({style_class: 'parchaos-lookup-popover', orientation: Clutter.Orientation.VERTICAL, reactive: true});
        catcher.add_child(popover);
        Main.uiGroup.add_child(catcher);
        this._catcher = catcher;
        this._popGrab = Main.pushModal(catcher, {actionMode: Shell.ActionMode.POPUP});
        catcher.grab_key_focus();
        catcher.connect('button-press-event', (_a, event) => {
            const [x, y] = event.get_coords();
            const [px, py] = popover.get_transformed_position();
            if (x < px || y < py || x > px + popover.width || y > py + popover.height)
                this._closePopover();
            return Clutter.EVENT_PROPAGATE;
        });
        catcher.connect('key-press-event', (_a, event) => {
            if (event.get_key_symbol() === Clutter.KEY_Escape) {
                this._closePopover();
                return Clutter.EVENT_STOP;
            }
            return Clutter.EVENT_PROPAGATE;
        });

        if (text === null) {
            popover.add_child(new St.Label({style_class: 'parchaos-lookup-status', text: _('Reading the text…')}));
        } else if (!text) {
            popover.add_child(new St.Label({style_class: 'parchaos-lookup-status', text: _('No text found in that area.')}));
        } else {
            const preview = new St.Label({
                style_class: 'parchaos-lookup-text',
                text: text.length > PREVIEW_CHARS ? `${text.slice(0, PREVIEW_CHARS)}…` : text,
            });
            preview.clutter_text.line_wrap = true;
            popover.add_child(preview);
            const actions = new St.BoxLayout({style_class: 'parchaos-lookup-actions'});
            popover.add_child(actions);
            this._actions = actions;
            const copy = this._action(actions, 'edit-copy-symbolic', _('Copy Text'), () => {
                St.Clipboard.get_default().set_text(St.ClipboardType.CLIPBOARD, text);
                copy.child.get_last_child().text = _('Copied');
                GLib.timeout_add(GLib.PRIORITY_DEFAULT, 600, () => {
                    this._closePopover();
                    return GLib.SOURCE_REMOVE;
                });
            });
            this._action(actions, 'system-search-symbolic', _('Search the Web'), () => {
                this._closePopover();
                const query = text.replace(/\s+/g, ' ').slice(0, 300);
                Gio.AppInfo.launch_default_for_uri(SEARCH_URL + encodeURIComponent(query), global.create_app_launch_context(0, -1));
            });
            if (GLib.find_program_in_path('parchaos-assistant')) {
                this._action(actions, 'chat-message-new-symbolic', _('Ask the Assistant'), () => {
                    this._closePopover();
                    Gio.Subprocess.new(['parchaos-assistant', '--ask', text.slice(0, 2000)], Gio.SubprocessFlags.NONE);
                });
            }
        }

        // Below the selection, or above it when there is no room; inside its monitor.
        const index = global.display.get_monitor_index_for_rect(new Mtk.Rectangle(rect));
        const monitor = Main.layoutManager.monitors[index] ?? Main.layoutManager.primaryMonitor;
        // As wide as the row of actions (the text wraps to fit), within reason.
        const [, rowWidth] = this._actions?.get_preferred_width(-1) ?? [0, 0];
        const width = Math.min(Math.max(rowWidth + 40, 300), 640);
        popover.width = width;
        const [, natHeight] = popover.get_preferred_height(width);
        let x = Math.round(rect.x + rect.width / 2 - width / 2);
        let y = rect.y + rect.height + 10;
        if (y + natHeight > monitor.y + monitor.height - 10)
            y = Math.max(monitor.y + 10, rect.y - natHeight - 10);
        x = Math.max(monitor.x + 10, Math.min(x, monitor.x + monitor.width - width - 10));
        popover.set_position(x, y);
    }

    _action(container, icon, label, callback) {
        const content = new St.BoxLayout({style_class: 'parchaos-lookup-action-content'});
        content.add_child(new St.Icon({icon_name: icon, icon_size: 16}));
        const text = new St.Label({text: label, y_align: Clutter.ActorAlign.CENTER});
        text.clutter_text.ellipsize = Pango.EllipsizeMode.NONE;
        content.add_child(text);
        const button = new St.Button({style_class: 'parchaos-lookup-action', child: content, can_focus: true});
        button.connect('clicked', callback);
        container.add_child(button);
        return button;
    }

    _closePopover() {
        if (this._popGrab) {
            Main.popModal(this._popGrab);
            this._popGrab = null;
        }
        this._catcher?.destroy();
        this._catcher = null;
    }
}
