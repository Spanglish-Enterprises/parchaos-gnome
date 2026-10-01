// SPDX-License-Identifier: GPL-3.0-or-later
// Parcha Glass: development demo, draws a few test panes so the glass can be tuned.
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import {GlassPane} from './glass.js';

export default class ParchaGlass extends Extension {
    enable() {
        this._panes = [];
        const demo = [[200, 120, 380, 200, 34], [640, 120, 190, 78, 39], [640, 230, 78, 78, 39], [740, 230, 78, 78, 39], [200, 380, 620, 90, 28]];
        for (const [x, y, w, h, r] of demo) {
            const pane = new GlassPane({radius: r});
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
