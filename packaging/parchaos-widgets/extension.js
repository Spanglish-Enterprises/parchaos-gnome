// SPDX-License-Identifier: GPL-3.0-or-later
// Desktop widgets (ticket #165): weather, today's calendar, a sticky note and a clock that live
// on the desktop, under the windows.
//
// The widgets sit just above the desktop icons window and below every app window, so they stay
// on the wallpaper and can still be clicked. Edit mode (the desktop menu's Edit Widgets…, or the
// widgets-editing setting) shows a bar to add widgets, lets them be dragged, and gives each a
// remove button. The list and positions are kept in org.parchaos.desktop desktop-widgets (JSON);
// a note's text is kept in ~/.local/share/parchaos/widgets/<id>.txt.
//
// Weather comes from the menu bar's weather item (the same reading, no second request); the
// calendar from GNOME's calendar server, like the clock menu. Each widget follows the Glass or
// Classic style and the light or dark appearance.
//
// Original code for ParchaOS, GPL-3.0-or-later.

import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import St from 'gi://St';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Calendar from 'resource:///org/gnome/shell/ui/calendar.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import Gettext from 'gettext';

import {KINDS, nextPlace, parseWidgets} from './layout.js';

const DOMAIN = 'parchaos-widgets';
Gettext.bindtextdomain(DOMAIN, GLib.getenv('PARCHAOS_LOCALEDIR') ?? '/usr/share/locale');
const _ = s => Gettext.dgettext(DOMAIN, s);

const KIND_LABELS = {
    weather: () => _('Weather'),
    calendar: () => _('Calendar'),
    note: () => _('Note'),
    clock: () => _('Clock'),
};
const KIND_ICONS = {
    weather: 'weather-few-clouds-symbolic',
    calendar: 'x-office-calendar-symbolic',
    note: 'document-edit-symbolic',
    clock: 'preferences-system-time-symbolic',
};
const MAX_EVENTS = 4;
const NOTES_DIR = GLib.build_filenamev([GLib.get_user_data_dir(), 'parchaos', 'widgets']);

function newId() {
    return GLib.uuid_string_random().slice(0, 8);
}

// --- The widgets ---

class Widget {
    constructor(owner, spec) {
        this.owner = owner;
        this.spec = spec;
        this.actor = new St.BoxLayout({
            style_class: `parchaos-widget parchaos-widget-${spec.kind}`,
            orientation: Clutter.Orientation.VERTICAL,
            reactive: true,
            x: spec.x,
            y: spec.y,
        });
        this.remove = new St.Button({
            style_class: 'parchaos-widget-remove', icon_name: 'window-close-symbolic',
            visible: false, can_focus: true, accessible_name: _('Remove Widget'),
        });
        this.remove.connect('clicked', () => owner.removeWidget(spec.id));
        this.body = new St.BoxLayout({orientation: Clutter.Orientation.VERTICAL, x_expand: true});
        const top = new St.Widget({layout_manager: new Clutter.BinLayout()});
        top.add_child(this.body);
        top.add_child(this.remove);
        this.remove.set_x_align(Clutter.ActorAlign.END);
        this.remove.set_y_align(Clutter.ActorAlign.START);
        this.actor.add_child(top);
        this.actor.connect('button-press-event', (_a, event) => this._onPress(event));
    }

    setEditing(editing) {
        this.remove.visible = editing;
        if (editing)
            this.actor.add_style_pseudo_class('editing');
        else
            this.actor.remove_style_pseudo_class('editing');
    }

    _onPress(event) {
        if (!this.owner.editing || event.get_button() !== Clutter.BUTTON_PRIMARY)
            return Clutter.EVENT_PROPAGATE;
        this.owner.startDrag(this, event);
        return Clutter.EVENT_STOP;
    }

    destroy() {
        this.actor.destroy();
    }
}

class ClockWidget extends Widget {
    constructor(owner, spec) {
        super(owner, spec);
        this._time = new St.Label({style_class: 'parchaos-widget-clock-time'});
        this._date = new St.Label({style_class: 'parchaos-widget-clock-date'});
        this.body.add_child(this._time);
        this.body.add_child(this._date);
        this._tick();
    }

    _tick() {
        const now = GLib.DateTime.new_now_local();
        const settings = this.owner.interface;
        const h24 = settings.get_string('clock-format') === '24h';
        this._time.text = now.format(h24 ? '%H:%M' : '%-l:%M');
        this._date.text = now.format('%A, %B %-e');
        // Wake again at the start of the next minute.
        this._timer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 60 - now.get_second(), () => {
            this._timer = 0;
            this._tick();
            return GLib.SOURCE_REMOVE;
        });
    }

    destroy() {
        if (this._timer)
            GLib.source_remove(this._timer);
        super.destroy();
    }
}

class WeatherWidget extends Widget {
    constructor(owner, spec) {
        super(owner, spec);
        const row = new St.BoxLayout({style_class: 'parchaos-widget-weather-row'});
        this._icon = new St.Icon({style_class: 'parchaos-widget-weather-icon', icon_name: 'weather-few-clouds-symbolic'});
        this._temp = new St.Label({style_class: 'parchaos-widget-weather-temp', y_align: Clutter.ActorAlign.CENTER});
        row.add_child(this._icon);
        row.add_child(this._temp);
        this._place = new St.Label({style_class: 'parchaos-widget-title'});
        this._sky = new St.Label({style_class: 'parchaos-widget-detail'});
        this.body.add_child(this._place);
        this.body.add_child(row);
        this.body.add_child(this._sky);
        this._timer = GLib.timeout_add_seconds(GLib.PRIORITY_LOW, 60, () => {
            this.refresh();
            return GLib.SOURCE_CONTINUE;
        });
        this.refresh();
    }

    // The menu bar's weather item already has the reading; follow it.
    refresh() {
        const indicator = Main.panel.statusArea['parchaos-weather'];
        const info = indicator?._weatherInfo;
        if (!indicator || !indicator.visible) {
            this._place.text = _('Weather');
            this._temp.text = '–';
            this._sky.text = _('Waiting for the weather…');
            return;
        }
        this._place.text = indicator._location?.name ?? info?.get_location_name?.() ?? _('Weather');
        this._icon.icon_name = indicator._conditionIcon?.icon_name ?? 'weather-few-clouds-symbolic';
        this._temp.text = indicator._label?.text ?? '–';
        let sky = '';
        try {
            sky = info?.is_valid() ? info.get_conditions() : '';
            if (!sky || sky === '-')
                sky = info?.get_sky() ?? '';
        } catch (e) {
            sky = '';
        }
        this._sky.text = indicator._data?.summary ?? sky;
    }

    destroy() {
        if (this._timer)
            GLib.source_remove(this._timer);
        super.destroy();
    }
}

class CalendarWidget extends Widget {
    constructor(owner, spec) {
        super(owner, spec);
        this._title = new St.Label({style_class: 'parchaos-widget-title'});
        this._list = new St.BoxLayout({orientation: Clutter.Orientation.VERTICAL, style_class: 'parchaos-widget-events'});
        this.body.add_child(this._title);
        this.body.add_child(this._list);
        this._source = owner.eventSource;
        this._source?.connectObject('changed', () => this.refresh(), this);
        // Past events drop off, and the day rolls over at midnight.
        this._timer = GLib.timeout_add_seconds(GLib.PRIORITY_LOW, 600, () => {
            this.refresh();
            return GLib.SOURCE_CONTINUE;
        });
        this.refresh();
    }

    refresh() {
        const now = GLib.DateTime.new_now_local();
        this._title.text = now.format(_('Today, %B %-e'));
        this._list.destroy_all_children();
        const start = new Date();
        start.setHours(0, 0, 0, 0);
        const end = new Date(start.getTime() + 24 * 3600 * 1000);
        let events = [];
        try {
            this._source?.requestRange(start, end);
            events = this._source?.getEvents(start, end) ?? [];
        } catch (e) {
            events = [];
        }
        events = events.filter(e => e.end >= new Date()).slice(0, MAX_EVENTS);
        if (!events.length) {
            this._list.add_child(new St.Label({text: _('No more events today'), style_class: 'parchaos-widget-detail'}));
            return;
        }
        const h24 = this.owner.interface.get_string('clock-format') === '24h';
        for (const event of events) {
            const row = new St.BoxLayout({style_class: 'parchaos-widget-event'});
            const allDay = event.date.getHours() === 0 && event.end.getTime() - event.date.getTime() >= 24 * 3600 * 1000 - 1000;
            const when = allDay ? _('All day')
                : GLib.DateTime.new_from_unix_local(Math.floor(event.date.getTime() / 1000)).format(h24 ? '%H:%M' : '%-l:%M %p');
            row.add_child(new St.Label({text: when, style_class: 'parchaos-widget-event-time'}));
            row.add_child(new St.Label({text: event.summary ?? '', style_class: 'parchaos-widget-event-name', x_expand: true}));
            this._list.add_child(row);
        }
    }

    destroy() {
        this._source?.disconnectObject(this);
        if (this._timer)
            GLib.source_remove(this._timer);
        super.destroy();
    }
}

class NoteWidget extends Widget {
    constructor(owner, spec) {
        super(owner, spec);
        this._path = GLib.build_filenamev([NOTES_DIR, `${spec.id}.txt`]);
        this._entry = new St.Entry({
            style_class: 'parchaos-widget-note-text', can_focus: true,
            hint_text: _('Write a note'), x_expand: true,
        });
        const text = this._entry.clutter_text;
        text.single_line_mode = false;
        text.line_wrap = true;
        text.activatable = false;
        try {
            const [, bytes] = GLib.file_get_contents(this._path);
            this._entry.text = new TextDecoder().decode(bytes);
        } catch (e) {
            // a new note
        }
        this.body.add_child(this._entry);
        text.connect('text-changed', () => this._queueSave());
        // Typing needs the keyboard: hold it while the note is being written.
        this._entry.connect('button-press-event', () => {
            if (!owner.editing)
                owner.focusNote(this);
            return Clutter.EVENT_PROPAGATE;
        });
    }

    get entry() {
        return this._entry;
    }

    _queueSave() {
        if (this._saveId)
            GLib.source_remove(this._saveId);
        this._saveId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 600, () => {
            this._saveId = 0;
            this.save();
            return GLib.SOURCE_REMOVE;
        });
    }

    save() {
        try {
            GLib.mkdir_with_parents(NOTES_DIR, 0o700);
            GLib.file_set_contents(this._path, this._entry.text ?? '');
        } catch (e) {
            logError(e, 'parchaos-widgets: could not save the note');
        }
    }

    forget() {
        try {
            Gio.File.new_for_path(this._path).delete(null);
        } catch (e) {
            // never saved
        }
    }

    destroy() {
        if (this._saveId) {
            GLib.source_remove(this._saveId);
            this._saveId = 0;
            this.save();
        }
        super.destroy();
    }
}

const WIDGET_CLASSES = {weather: WeatherWidget, calendar: CalendarWidget, note: NoteWidget, clock: ClockWidget};

// --- The layer that holds them ---

export default class WidgetsExtension extends Extension {
    enable() {
        this._desktop = new Gio.Settings({schema_id: 'org.parchaos.desktop'});
        this.interface = new Gio.Settings({schema_id: 'org.gnome.desktop.interface'});
        this.editing = false;
        this._widgets = new Map();
        this.eventSource = null;
        try {
            this.eventSource = new Calendar.DBusEventSource();
        } catch (e) {
            logError(e, 'parchaos-widgets: no calendar server');
        }

        this._layer = new St.Widget({style_class: 'parchaos-widgets-layer', reactive: false});
        global.window_group.add_child(this._layer);
        this._restack();
        global.display.connectObject('restacked', () => this._restack(), this);
        this._desktop.connectObject(
            'changed::desktop-widgets', () => this._sync(),
            'changed::widgets-editing', () => this._setEditing(this._desktop.get_boolean('widgets-editing')),
            'changed::style', () => this._applyStyle(), this);
        this.interface.connectObject('changed::color-scheme', () => this._applyStyle(), this);
        this._applyStyle();
        this._sync();
        // Edit mode is never left on across a restart.
        if (this._desktop.get_boolean('widgets-editing'))
            this._desktop.set_boolean('widgets-editing', false);
    }

    disable() {
        this._endDrag();
        this._unfocusNote();
        this._setEditing(false);
        global.display.disconnectObject(this);
        this._desktop.disconnectObject(this);
        this.interface.disconnectObject(this);
        for (const widget of this._widgets.values())
            widget.destroy();
        this._widgets.clear();
        this._bar?.destroy();
        this._bar = null;
        this._layer.destroy();
        this._layer = null;
        this.eventSource?.destroy?.();
        this.eventSource = null;
        this._desktop = null;
        this.interface = null;
    }

    // Just above the desktop window (the icons), below every app window.
    _restack() {
        if (!this._layer)
            return;
        const actors = global.get_window_actors();
        const desktop = actors.filter(a => a.meta_window?.get_window_type() === Meta.WindowType.DESKTOP).pop();
        if (desktop && desktop.get_parent() === global.window_group)
            global.window_group.set_child_above_sibling(this._layer, desktop);
        else
            global.window_group.set_child_below_sibling(this._layer, null);
    }

    _applyStyle() {
        const dark = this.interface.get_string('color-scheme') === 'prefer-dark';
        const classic = this._desktop.get_string('style') === 'classic';
        for (const [cls, on] of [['parchaos-widgets-dark', dark], ['parchaos-widgets-light', !dark],
            ['parchaos-widgets-classic', classic], ['parchaos-widgets-glass', !classic]]) {
            if (on)
                this._layer.add_style_class_name(cls);
            else
                this._layer.remove_style_class_name(cls);
        }
    }

    _load() {
        return parseWidgets(this._desktop.get_string('desktop-widgets'));
    }

    _save(list) {
        this._desktop.set_string('desktop-widgets', JSON.stringify(list));
    }

    _sync() {
        const list = this._load();
        const ids = new Set(list.map(w => w.id));
        for (const [id, widget] of this._widgets) {
            if (!ids.has(id)) {
                widget.destroy();
                this._widgets.delete(id);
            }
        }
        for (const spec of list) {
            const existing = this._widgets.get(spec.id);
            if (existing) {
                existing.spec = spec;
                existing.actor.set_position(spec.x, spec.y);
                continue;
            }
            const widget = new WIDGET_CLASSES[spec.kind](this, spec);
            this._layer.add_child(widget.actor);
            widget.setEditing(this.editing);
            this._widgets.set(spec.id, widget);
        }
    }

    addWidget(kind) {
        const list = this._load();
        const area = Main.layoutManager.getWorkAreaForMonitor(Main.layoutManager.primaryIndex);
        const place = nextPlace(list, area);
        list.push({id: newId(), kind, x: Math.round(place.x), y: Math.round(place.y)});
        this._save(list);
    }

    removeWidget(id) {
        const widget = this._widgets.get(id);
        if (widget instanceof NoteWidget)
            widget.forget();
        this._save(this._load().filter(w => w.id !== id));
    }

    // --- Edit mode: the bar of widgets to add, remove buttons, dragging ---

    _setEditing(editing) {
        if (editing === this.editing)
            return;
        this.editing = editing;
        for (const widget of this._widgets.values())
            widget.setEditing(editing);
        if (editing)
            this._showBar();
        else
            this._hideBar();
    }

    _showBar() {
        const bar = new St.BoxLayout({style_class: 'parchaos-widgets-bar', reactive: true});
        bar.add_child(new St.Label({text: _('Add a widget:'), style_class: 'parchaos-widgets-bar-title', y_align: Clutter.ActorAlign.CENTER}));
        for (const kind of KINDS) {
            const content = new St.BoxLayout({style_class: 'parchaos-widgets-bar-item'});
            content.add_child(new St.Icon({icon_name: KIND_ICONS[kind], icon_size: 16}));
            content.add_child(new St.Label({text: KIND_LABELS[kind](), y_align: Clutter.ActorAlign.CENTER}));
            const button = new St.Button({style_class: 'parchaos-widgets-bar-button', child: content, can_focus: true});
            button.connect('clicked', () => this.addWidget(kind));
            bar.add_child(button);
        }
        const done = new St.Button({style_class: 'parchaos-widgets-bar-done', label: _('Done'), can_focus: true});
        done.connect('clicked', () => this._desktop.set_boolean('widgets-editing', false));
        bar.add_child(done);
        Main.layoutManager.addTopChrome(bar);
        const monitor = Main.layoutManager.primaryMonitor;
        const [, w] = bar.get_preferred_width(-1);
        const [, h] = bar.get_preferred_height(w);
        bar.set_position(monitor.x + Math.round((monitor.width - w) / 2), monitor.y + monitor.height - h - 120);
        this._bar = bar;
    }

    _hideBar() {
        if (this._bar)
            Main.layoutManager.removeChrome(this._bar);
        this._bar?.destroy();
        this._bar = null;
    }

    startDrag(widget, event) {
        const [x, y] = event.get_coords();
        this._drag = {widget, dx: x - widget.actor.x, dy: y - widget.actor.y};
        widget.actor.add_style_pseudo_class('dragging');
        this._dragGrab = Main.pushModal(widget.actor, {actionMode: Shell.ActionMode.POPUP});
        this._dragId = global.stage.connect('captured-event', (_s, ev) => {
            const type = ev.type();
            if (type === Clutter.EventType.MOTION) {
                const [mx, my] = ev.get_coords();
                widget.actor.set_position(Math.round(mx - this._drag.dx), Math.round(my - this._drag.dy));
                return Clutter.EVENT_STOP;
            }
            if (type === Clutter.EventType.BUTTON_RELEASE) {
                this._endDrag(true);
                return Clutter.EVENT_STOP;
            }
            return Clutter.EVENT_PROPAGATE;
        });
    }

    _endDrag(save = false) {
        if (!this._drag)
            return;
        const {widget} = this._drag;
        this._drag = null;
        global.stage.disconnect(this._dragId);
        this._dragId = 0;
        if (this._dragGrab) {
            Main.popModal(this._dragGrab);
            this._dragGrab = null;
        }
        widget.actor.remove_style_pseudo_class('dragging');
        if (save) {
            const list = this._load();
            const spec = list.find(w => w.id === widget.spec.id);
            if (spec) {
                spec.x = Math.round(widget.actor.x);
                spec.y = Math.round(widget.actor.y);
                this._save(list);
            }
        }
    }

    // --- Writing in a note: the keyboard is held until a click elsewhere or Escape ---

    focusNote(note) {
        if (this._noteGrab)
            return;
        this._note = note;
        this._noteGrab = Main.pushModal(note.actor, {actionMode: Shell.ActionMode.POPUP});
        note.entry.grab_key_focus();
        note.actor.add_style_pseudo_class('writing');
        this._noteId = global.stage.connect('captured-event', (_s, ev) => {
            const type = ev.type();
            if (type === Clutter.EventType.KEY_PRESS && ev.get_key_symbol() === Clutter.KEY_Escape) {
                this._unfocusNote();
                return Clutter.EVENT_STOP;
            }
            if (type === Clutter.EventType.BUTTON_PRESS) {
                const [x, y] = ev.get_coords();
                const [ax, ay] = note.actor.get_transformed_position();
                if (x < ax || y < ay || x > ax + note.actor.width || y > ay + note.actor.height) {
                    this._unfocusNote();
                    return Clutter.EVENT_PROPAGATE;
                }
            }
            return Clutter.EVENT_PROPAGATE;
        });
    }

    _unfocusNote() {
        if (!this._noteGrab)
            return;
        global.stage.disconnect(this._noteId);
        this._noteId = 0;
        Main.popModal(this._noteGrab);
        this._noteGrab = null;
        this._note?.actor.remove_style_pseudo_class('writing');
        this._note?.save();
        this._note = null;
        global.stage.set_key_focus(null);
    }
}
