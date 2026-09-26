// ParchaOS Live Icons -- the Clock icon shows the current time and the
// Calendar icon shows today's date, wherever the shell draws app icons
// (dock, launcher, app switcher).
//
// Shell.App.create_icon_texture() is wrapped for the two apps: it returns
// an St.Icon whose image is an SVG rendered from the same design as the
// static ParchaOS icons (parchaos-icon-theme's generate.py), with the
// hands or date filled in. A timer refreshes every live icon once a
// minute (the calendar only when the date changes).
//
// Original code and artwork for ParchaOS, GPL-3.0-or-later (code) and
// CC BY-SA 4.0 (artwork).

import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import Shell from 'gi://Shell';
import St from 'gi://St';

import {Extension, InjectionManager} from 'resource:///org/gnome/shell/extensions/extension.js';

const CLOCK_ID = 'org.gnome.clocks.desktop';
const CALENDAR_ID = 'org.gnome.Calendar.desktop';
const DIR = GLib.build_filenamev([GLib.get_user_runtime_dir(), 'parchaos-live-icons']);

const DEFS = (top, bottom) => `<defs><filter id="sh" x="-10%" y="-10%" width="120%" height="125%"><feDropShadow dx="0" dy="6" stdDeviation="9" flood-color="#000" flood-opacity="0.22"/></filter><linearGradient id="gloss" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0.28"/><stop offset="0.45" stop-color="#fff" stop-opacity="0"/></linearGradient><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${top}"/><stop offset="1" stop-color="${bottom}"/></linearGradient></defs>`;
const TILE = '<rect x="32" y="28" width="448" height="448" rx="104" fill="url(#bg)" filter="url(#sh)"/><rect x="32" y="28" width="448" height="448" rx="104" fill="url(#gloss)"/><rect x="33" y="29" width="446" height="446" rx="103" fill="none" stroke="#fff" stroke-opacity="0.35" stroke-width="2"/>';
const svg = (top, bottom, body) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">${DEFS(top, bottom)}${TILE}${body}</svg>`;

function clockSvg(now) {
    const h = now.get_hour() % 12;
    const m = now.get_minute();
    const hourAngle = (h + m / 60) * 30;
    const minuteAngle = m * 6;
    let ticks = '';
    for (let i = 0; i < 12; i++) {
        const long = i % 3 === 0;
        ticks += `<rect x="251" y="${long ? 112 : 118}" width="10" height="${long ? 40 : 26}" rx="5" fill="#fff" fill-opacity="${long ? 1 : 0.7}" transform="rotate(${i * 30} 256 252)"/>`;
    }
    return svg('#2fa3a8', '#13535c', `${ticks
    }<rect x="248" y="162" width="16" height="96" rx="8" fill="#fff" transform="rotate(${minuteAngle} 256 252)"/>` +
        `<rect x="249" y="186" width="14" height="72" rx="7" fill="#f2b632" transform="rotate(${hourAngle} 256 252)"/>` +
        '<circle cx="256" cy="252" r="16" fill="#f2b632"/><circle cx="256" cy="252" r="6" fill="#13535c"/>');
}

function calendarSvg(now) {
    const weekday = now.format('%a').toUpperCase();
    const day = now.get_day_of_month();
    return svg('#9d82f0', '#5b3fb0',
        '<rect x="118" y="150" width="276" height="266" rx="30" fill="#fff"/>' +
        '<path d="M148 150h216a30 30 0 0 1 30 30v44H118v-44a30 30 0 0 1 30-30z" fill="#7a55d6"/>' +
        '<rect x="178" y="126" width="18" height="56" rx="9" fill="#3d2a82"/>' +
        '<rect x="316" y="126" width="18" height="56" rx="9" fill="#3d2a82"/>' +
        `<text x="256" y="207" font-family="sans-serif" font-size="40" font-weight="700" letter-spacing="3" text-anchor="middle" fill="#fff">${weekday}</text>` +
        `<text x="256" y="366" font-family="sans-serif" font-size="136" font-weight="700" text-anchor="middle" fill="#3d2a82">${day}</text>`);
}

const LIVE = {
    [CLOCK_ID]: {render: clockSvg, key: now => now.format('%H%M')},
    [CALENDAR_ID]: {render: calendarSvg, key: now => now.format('%Y%m%d')},
};

export default class LiveIconsExtension extends Extension {
    enable() {
        GLib.mkdir_with_parents(DIR, 0o700);
        this._icons = new Map(Object.keys(LIVE).map(id => [id, new Set()]));
        this._current = new Map();
        this._refresh();

        const self = this;
        this._injections = new InjectionManager();
        this._injections.overrideMethod(Shell.App.prototype, 'create_icon_texture', original => function (size) {
            const id = this.get_id();
            if (!(id in LIVE) || !self._current.get(id))
                return original.call(this, size);
            return self._liveIcon(id, size);
        });

        this._scheduleTick();
    }

    disable() {
        this._injections?.clear();
        this._injections = null;
        if (this._tickId)
            GLib.source_remove(this._tickId);
        this._tickId = 0;
        // Icons created while enabled keep their last image; the next
        // redraw (e.g. dock refresh) uses the theme icon again.
        this._icons = null;
        this._current = null;
    }

    _liveIcon(id, size) {
        const icon = new St.Icon({
            gicon: this._current.get(id),
            icon_size: size,
            style_class: 'icon-dropshadow',
        });
        const set = this._icons.get(id);
        set.add(icon);
        icon.connect('destroy', () => set.delete(icon));
        return icon;
    }

    // Wake just after each minute boundary.
    _scheduleTick() {
        const now = GLib.DateTime.new_now_local();
        const ms = (60 - now.get_second()) * 1000 - Math.floor(now.get_microsecond() / 1000) + 200;
        this._tickId = GLib.timeout_add(GLib.PRIORITY_LOW, ms, () => {
            this._tickId = 0;
            this._refresh();
            this._scheduleTick();
            return GLib.SOURCE_REMOVE;
        });
    }

    _refresh() {
        const now = GLib.DateTime.new_now_local();
        for (const [id, live] of Object.entries(LIVE)) {
            const key = live.key(now);
            const name = `${id.replace('.desktop', '')}-${key}.svg`;
            const path = GLib.build_filenamev([DIR, name]);
            const prev = this._current.get(id);
            if (prev && prev.get_file().get_basename() === name)
                continue;
            try {
                // A new file name per state: St caches icon textures by file.
                GLib.file_set_contents(path, live.render(now));
            } catch (e) {
                logError(e, 'parchaos-live-icons: could not write icon');
                continue;
            }
            const gicon = new Gio.FileIcon({file: Gio.File.new_for_path(path)});
            this._current.set(id, gicon);
            for (const icon of this._icons.get(id))
                icon.gicon = gicon;
            if (prev) {
                try {
                    prev.get_file().delete(null);
                } catch (e) {
                    // already gone
                }
            }
        }
    }
}
