// SPDX-License-Identifier: GPL-3.0-or-later
// Parcha Glass: development demo, draws a few test panes so the glass can be tuned.
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import {GlassPane} from './glass.js';

export default class ParchaGlass extends Extension {
    enable() {
        this._panes = [];
        const demo = [[120, 100, 200, 78, 39, 10.5], [120, 220, 78, 78, 39, 10.5], [380, 100, 200, 78, 39, 26], [380, 220, 78, 78, 39, 26], [640, 100, 200, 78, 39, 48], [640, 220, 78, 78, 39, 48], [900, 100, 200, 78, 39, 80], [900, 220, 78, 78, 39, 80]];
        for (const [x, y, w, h, r, disp] of demo) {
            const pane = new GlassPane({radius: r, disp, falloff: 1.6});
            pane.set_position(x, y);
            pane.set_size(w, h);
            Main.layoutManager.uiGroup.add_child(pane);
            this._panes.push(pane);
        }
    }

    disable() {
        for (const p of this._panes ?? [])
            p.destroy();
        this._panes = null;
    }
}
