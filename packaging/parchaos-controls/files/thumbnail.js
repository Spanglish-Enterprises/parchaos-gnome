// SPDX-License-Identifier: GPL-3.0-or-later
// Screenshot thumbnail (ticket #155). After a capture from GNOME's screenshot tool, a small
// preview slides in at the bottom right in place of GNOME's "Screenshot captured" banner. Click
// it (or Mark Up) to draw arrows, boxes and text or crop it in the markup app; Copy puts it on
// the clipboard again; Show in Files; Delete moves it to the Trash. It goes away by itself after a
// few seconds unless the pointer is on it; Escape closes it while the pointer is on it.
//
// Original code for ParchaOS, GPL-3.0-or-later.

import Clutter from 'gi://Clutter';
import Cogl from 'gi://Cogl';
import GdkPixbuf from 'gi://GdkPixbuf';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import St from 'gi://St';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';

const WIDTH = 240;
const MAX_HEIGHT = 170;
const SHOW_SECONDS = 7;
const MARGIN = 18;
// Markup apps, first installed wins: Drawing (crop, arrows, shapes, text), then Swappy.
const MARKUP_APPS = [
    ['com.github.maoschanz.drawing.desktop', 'drawing'],
    ['swappy.desktop', 'swappy', '-f'],
];

function markupCommand(path) {
    for (const [, bin, ...flags] of MARKUP_APPS) {
        if (GLib.find_program_in_path(bin))
            return [bin, ...flags, path];
    }
    return null;
}

function imageContent(path) {
    const pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, WIDTH * 2, MAX_HEIGHT * 2, true);
    const content = St.ImageContent.new_with_preferred_size(pixbuf.width, pixbuf.height);
    const context = global.stage.context.get_backend().get_cogl_context();
    content.set_bytes(context, pixbuf.read_pixel_bytes(),
        pixbuf.has_alpha ? Cogl.PixelFormat.RGBA_8888 : Cogl.PixelFormat.RGB_888,
        pixbuf.width, pixbuf.height, pixbuf.rowstride);
    return [content, pixbuf.width, pixbuf.height];
}

export class ScreenshotThumbnail {
    constructor(gettext) {
        this._ = gettext;
        Main.screenshotUI.connectObject('screenshot-taken', (_ui, file) => this._show(file), this);
    }

    _show(file) {
        this._dismiss(false);
        this._dropBanner();
        const path = file.get_path();
        let content, w, h;
        try {
            [content, w, h] = imageContent(path);
        } catch (e) {
            logError(e, 'parchaos-controls: could not read the screenshot');
            return;
        }
        const _ = this._;
        const scale = Math.min(WIDTH / w, MAX_HEIGHT / h);
        const card = new St.BoxLayout({
            style_class: 'parchaos-shot-card',
            orientation: Clutter.Orientation.VERTICAL,
            reactive: true,
            track_hover: true,
            opacity: 0,
        });
        const image = new St.Button({style_class: 'parchaos-shot-image', accessible_name: _('Mark Up')});
        image.set_child(new St.Widget({content, width: Math.round(w * scale), height: Math.round(h * scale)}));
        image.connect('clicked', () => this._markUp(path));
        card.add_child(image);

        const row = new St.BoxLayout({style_class: 'parchaos-shot-actions', x_align: Clutter.ActorAlign.CENTER});
        const action = (icon, label, callback) => {
            const button = new St.Button({
                style_class: 'parchaos-shot-action',
                child: new St.Icon({icon_name: icon, icon_size: 16}),
                accessible_name: label,
            });
            button.connect('clicked', callback);
            button.connect('notify::hover', () => this._tip(button.hover ? label : null));
            row.add_child(button);
        };
        action('document-edit-symbolic', _('Mark Up'), () => this._markUp(path));
        action('edit-copy-symbolic', _('Copy'), () => this._copy(path));
        action('folder-open-symbolic', _('Show in Files'), () => this._showInFiles(file));
        action('user-trash-symbolic', _('Delete'), () => this._delete(file));
        action('window-close-symbolic', _('Close'), () => this._dismiss(true));
        card.add_child(row);
        this._label = new St.Label({style_class: 'parchaos-shot-tip', text: ' ', x_align: Clutter.ActorAlign.CENTER});
        card.add_child(this._label);

        Main.layoutManager.addTopChrome(card);
        this._card = card;
        const area = Main.layoutManager.getWorkAreaForMonitor(Main.layoutManager.primaryIndex);
        const [, cardW] = card.get_preferred_width(-1);
        const [, cardH] = card.get_preferred_height(cardW);
        card.set_position(area.x + area.width - cardW - MARGIN, area.y + area.height - cardH - MARGIN);
        card.translation_x = 40;
        card.ease({opacity: 255, translation_x: 0, duration: 220, mode: Clutter.AnimationMode.EASE_OUT_QUAD});

        // Stays while the pointer is on it; Escape only belongs to it then.
        card.connect('notify::hover', () => {
            if (card.hover) {
                this._stopTimer();
                this._grabEscape();
            } else {
                this._releaseEscape();
                this._startTimer();
            }
        });
        this._startTimer();
    }

    _tip(text) {
        if (this._label)
            this._label.text = text ?? ' ';
    }

    // GNOME's own banner says the same thing; the thumbnail takes its place.
    _dropBanner() {
        for (const source of Main.messageTray.getSources()) {
            const names = source.icon?.get_names?.() ?? [source.iconName];
            if (!names.includes('screenshooter-symbolic'))
                continue;
            for (const n of [...source.notifications]) {
                if (n.gicon instanceof St.ImageContent)
                    n.destroy();
            }
        }
    }

    _startTimer() {
        this._stopTimer();
        this._timerId = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, SHOW_SECONDS, () => {
            this._timerId = 0;
            this._dismiss(true);
            return GLib.SOURCE_REMOVE;
        });
    }

    _stopTimer() {
        if (this._timerId)
            GLib.source_remove(this._timerId);
        this._timerId = 0;
    }

    _grabEscape() {
        if (this._escapeAction)
            return;
        const action = global.display.grab_accelerator('Escape', Meta.KeyBindingFlags.NONE);
        if (action === Meta.KeyBindingAction.NONE)
            return;
        this._escapeAction = action;
        Main.wm.allowKeybinding(Meta.external_binding_name_for_action(action), Shell.ActionMode.ALL);
        this._acceleratorId = global.display.connect('accelerator-activated', (_d, id) => {
            if (id === this._escapeAction)
                this._dismiss(true);
        });
    }

    _releaseEscape() {
        if (this._acceleratorId)
            global.display.disconnect(this._acceleratorId);
        this._acceleratorId = 0;
        if (this._escapeAction) {
            Main.wm.allowKeybinding(Meta.external_binding_name_for_action(this._escapeAction), Shell.ActionMode.NONE);
            global.display.ungrab_accelerator(this._escapeAction);
        }
        this._escapeAction = 0;
    }

    _launch(argv) {
        try {
            const launcher = new Gio.SubprocessLauncher({flags: Gio.SubprocessFlags.NONE});
            launcher.spawnv(argv);
        } catch (e) {
            logError(e, `parchaos-controls: could not run ${argv[0]}`);
        }
    }

    _markUp(path) {
        const argv = markupCommand(path);
        if (argv) {
            this._launch(argv);
        } else {
            Gio.app_info_launch_default_for_uri(Gio.File.new_for_path(path).get_uri(),
                global.create_app_launch_context(0, -1));
        }
        this._dismiss(true);
    }

    _copy(path) {
        try {
            const [, bytes] = GLib.file_get_contents(path);
            St.Clipboard.get_default().set_content(St.ClipboardType.CLIPBOARD, 'image/png', new GLib.Bytes(bytes));
            this._tip(this._('Copied'));
        } catch (e) {
            logError(e, 'parchaos-controls: could not copy the screenshot');
        }
    }

    _showInFiles(file) {
        const app = Gio.app_info_get_default_for_type('inode/directory', false);
        app?.launch([file], global.create_app_launch_context(0, -1));
        this._dismiss(true);
    }

    _delete(file) {
        try {
            file.trash(null);
        } catch (e) {
            logError(e, 'parchaos-controls: could not move the screenshot to the Trash');
        }
        this._dismiss(true);
    }

    _dismiss(animate) {
        this._stopTimer();
        this._releaseEscape();
        const card = this._card;
        this._card = null;
        this._label = null;
        if (!card)
            return;
        if (!animate) {
            card.destroy();
            return;
        }
        card.reactive = false;
        card.ease({
            opacity: 0, translation_x: 40, duration: 180, mode: Clutter.AnimationMode.EASE_IN_QUAD,
            onStopped: () => card.destroy(),
        });
    }

    destroy() {
        Main.screenshotUI.disconnectObject(this);
        this._dismiss(false);
    }
}
