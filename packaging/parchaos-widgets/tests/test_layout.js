// SPDX-License-Identifier: GPL-3.0-or-later
// Tests for the desktop widgets' layout helpers (ticket #165). Run: gjs -m tests/test_layout.js
import {nextPlace, parseWidgets} from '../layout.js';

let failures = 0;
const check = (ok, what) => {
    if (!ok) {
        failures++;
        print(`FAIL ${what}`);
    }
};

check(parseWidgets('').length === 0, 'empty setting');
check(parseWidgets('not json').length === 0, 'broken setting');
const list = parseWidgets(JSON.stringify([
    {id: 'a', kind: 'clock', x: 10, y: 20},
    {id: 'b', kind: 'rocket', x: 0, y: 0},
    {id: 'c', kind: 'note', x: 'left', y: 0},
    {kind: 'weather', x: 1, y: 1},
]));
check(list.length === 1 && list[0].id === 'a', 'unknown kinds and bad positions are dropped');

const area = {x: 0, y: 32, width: 1600, height: 868};
const first = nextPlace([], area);
check(first.x === 1600 - 260 - 24 && first.y === 32 + 24, `first widget top right (got ${JSON.stringify(first)})`);
const second = nextPlace([{...first, id: 'a', kind: 'clock'}], area);
check(second.x === first.x && second.y === first.y + 180 + 24, 'second below the first');
const column = [];
for (let i = 0; i < 5; i++)
    column.push({...nextPlace(column, area), id: `${i}`, kind: 'note'});
check(column[3].x === first.x && column[4].x < first.x, 'four fit in a column, the fifth starts the next one in');

print(failures === 0 ? 'widgets layout: all checks passed' : `widgets layout: ${failures} check(s) failed`);
imports.system.exit(failures === 0 ? 0 : 1);
