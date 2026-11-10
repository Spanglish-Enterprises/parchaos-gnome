// SPDX-License-Identifier: GPL-3.0-or-later
// Which apps are using a lot of the processor, for the battery menu (ticket #174).
//
// Read locally from /proc: each process's CPU time and the app it belongs to, taken from the
// systemd scope GNOME Shell and Flatpak start every app in (app-gnome-<id>-<n>.scope and the
// like). Nothing is stored or sent anywhere; the samples live only in memory.
//
// Original code for ParchaOS, GPL-3.0-or-later.

import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

// Kernel clock ticks per second for /proc/<pid>/stat times (USER_HZ, 100 on every Fedora arch).
export const TICKS_PER_SECOND = 100;
// An app counts as "using much power" from a tenth of one processor, averaged over the sample.
export const BUSY_SHARE = 0.1;

const LAUNCHERS = ['gnome', 'flatpak', 'kde', 'snap', 'xdg\\x2dautostart', 'xdg-autostart'];
const UNIT = new RegExp(
    `^app-(?:(?:${LAUNCHERS.map(l => l.replace(/\\/g, '\\\\')).join('|')})-)?` +
    '(.+?)(?:-[0-9]+|@[^.]*)?\\.(?:scope|service|slice)$');

/** The desktop id (without .desktop) an app's processes run under, from /proc/<pid>/cgroup; or null. */
export function appIdFromCgroup(text) {
    for (const line of text.trim().split('\n').reverse()) {
        const path = line.split(':').slice(2).join(':');
        const units = path.split('/').filter(u => u.startsWith('app-')).reverse();
        for (const unit of units) {
            const m = UNIT.exec(unit);
            // D-Bus-activated services (app-dbus-:1.2-<name>@0.service) are not apps.
            if (m && m[1] && !m[1].startsWith('dbus\\x2d'))
                return m[1].replace(/\\x([0-9a-fA-F]{2})/g, (_s, hex) => String.fromCharCode(parseInt(hex, 16)));
        }
    }
    return null;
}

/** User plus system CPU ticks from the text of /proc/<pid>/stat, or 0. */
export function ticksFromStat(text) {
    // The command name (field 2) can hold spaces and parentheses; the fields after it are fixed.
    const rest = text.slice(text.lastIndexOf(')') + 2).split(' ');
    const ticks = Number(rest[11]) + Number(rest[12]);
    return Number.isFinite(ticks) ? ticks : 0;
}

/**
 * Apps whose CPU use between two samples reached BUSY_SHARE, busiest first:
 * [[appId, share of one processor]], at most `count` of them.
 */
export function busyApps(before, after, seconds, count = 2) {
    if (!(seconds > 0))
        return [];
    const busy = [];
    for (const [id, ticks] of after) {
        // An app missing from the first sample started since. A process that exited takes its
        // ticks with it, so a total can shrink; that counts as idle.
        const share = Math.max(0, ticks - (before.get(id) ?? 0)) / TICKS_PER_SECOND / seconds;
        if (share >= BUSY_SHARE)
            busy.push([id, share]);
    }
    return busy.sort((a, b) => b[1] - a[1]).slice(0, count);
}

function readText(path) {
    try {
        const [, bytes] = GLib.file_get_contents(path);
        return new TextDecoder().decode(bytes);
    } catch (e) {
        return null;
    }
}

/** Samples total CPU ticks per app; keeps the last few samples so a minute can be compared. */
export class EnergySampler {
    constructor(procDir = GLib.getenv('PARCHAOS_PROC') ?? '/proc') {
        this._proc = procDir;
        this._apps = new Map(); // pid -> app id ('' when the process is not part of an app)
        this._samples = [];
    }

    sample() {
        const totals = new Map();
        const seen = new Set();
        let children;
        try {
            children = Gio.File.new_for_path(this._proc).enumerate_children(
                'standard::name', Gio.FileQueryInfoFlags.NONE, null);
        } catch (e) {
            return totals;
        }
        let info;
        while ((info = children.next_file(null))) {
            const pid = info.get_name();
            if (!/^[0-9]+$/.test(pid))
                continue;
            seen.add(pid);
            // A process stays in the scope it was started in, so its app is looked up once.
            if (!this._apps.has(pid))
                this._apps.set(pid, appIdFromCgroup(readText(`${this._proc}/${pid}/cgroup`) ?? '') ?? '');
            const id = this._apps.get(pid);
            if (!id)
                continue;
            const stat = readText(`${this._proc}/${pid}/stat`);
            if (stat)
                totals.set(id, (totals.get(id) ?? 0) + ticksFromStat(stat));
        }
        children.close(null);
        for (const pid of this._apps.keys()) {
            if (!seen.has(pid))
                this._apps.delete(pid);
        }
        return totals;
    }

    /** Take a sample now and keep it, dropping samples older than `keepSeconds`. */
    record(keepSeconds = 90) {
        const now = GLib.get_monotonic_time() / 1e6;
        this._samples.push({time: now, totals: this.sample()});
        this._samples = this._samples.filter(s => now - s.time <= keepSeconds);
    }

    /** The busiest apps over about the last minute (or since the oldest sample kept). */
    busyNow(count = 2) {
        const now = GLib.get_monotonic_time() / 1e6;
        const totals = this.sample();
        const older = this._samples.find(s => now - s.time <= 75) ?? this._samples[0];
        return older ? busyApps(older.totals, totals, now - older.time, count) : [];
    }

    clear() {
        this._samples = [];
        this._apps.clear();
    }
}
