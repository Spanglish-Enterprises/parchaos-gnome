// SPDX-License-Identifier: GPL-3.0-or-later
// Desktop widgets (ticket #165): the saved list and where a new widget goes. No Shell imports,
// so the tests can load it with plain gjs.
//
// Original code for ParchaOS, GPL-3.0-or-later.

export const KINDS = ['weather', 'calendar', 'note', 'clock'];

/** The saved widget list: [{id, kind, x, y}], dropping anything unknown or malformed. */
export function parseWidgets(json) {
    try {
        const list = JSON.parse(json || '[]');
        return Array.isArray(list)
            ? list.filter(w => w && KINDS.includes(w.kind) && typeof w.id === 'string' &&
                Number.isFinite(w.x) && Number.isFinite(w.y))
            : [];
    } catch (e) {
        return [];
    }
}

/** Where a new widget goes: down the right side of the screen (the icons start at the left), then the next column in. */
export function nextPlace(widgets, area, size = {width: 260, height: 180}) {
    const margin = 24;
    let x = area.x + area.width - size.width - margin;
    let y = area.y + margin;
    const taken = r => widgets.some(w => Math.abs(w.x - r.x) < size.width && Math.abs(w.y - r.y) < size.height);
    while (taken({x, y})) {
        y += size.height + margin;
        if (y + size.height > area.y + area.height) {
            y = area.y + margin;
            x -= size.width + margin;
            if (x < area.x)
                return {x: area.x + margin, y: area.y + margin};
        }
    }
    return {x, y};
}

