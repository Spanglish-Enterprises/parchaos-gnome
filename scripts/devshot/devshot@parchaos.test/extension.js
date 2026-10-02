// SPDX-License-Identifier: GPL-3.0-or-later
// devshot: drives a headless GNOME Shell from $DEVSHOT_OUT/plan.json (a list of steps) and
// writes screenshots there. Steps: wait, shot, move [x,y], press n, release n, drag [x0,y0,x1,y1],
// type "text", combo ["KEY_A",...], log, screenshotTaken "name", slowdown N. Test tool only; never run against a real session.
import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Shell from 'gi://Shell';
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

const OUT = GLib.getenv('DEVSHOT_OUT');
const wait = ms => new Promise(r => GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, () => { r(); return GLib.SOURCE_REMOVE; }));
async function shot(name) {
    log(`DEVSHOT shot ${name} at ${GLib.get_monotonic_time()}`);
    const f = Gio.File.new_for_path(`${OUT}/${name}.png`);
    const s = f.replace(null, false, 0, null);
    const sh = new Shell.Screenshot();
    await new Promise(r => sh.screenshot(false, s, () => r()));
    s.close(null);
}
export default class X extends Extension {
    enable() {
        (async () => {
            const plan = JSON.parse(new TextDecoder().decode(Gio.File.new_for_path(`${OUT}/plan.json`).load_contents(null)[1]));
            const seat = global.stage.context.get_backend().get_default_seat();
            const dev = seat.create_virtual_device(Clutter.InputDeviceType.POINTER_DEVICE);
            const kbd = seat.create_virtual_device(Clutter.InputDeviceType.KEYBOARD_DEVICE);
            const t = () => GLib.get_monotonic_time();
            for (const step of plan) {
                if (step.wait) await wait(step.wait);
                else if (step.shot) await shot(step.shot);
                // Slows every shell animation down (the shell's own slow-down factor), to photograph a transition.
                else if (step.slowdown) St.Settings.get().slow_down_factor = step.slowdown;
                // Saves a screenshot and announces it as the capture tool does ("screenshot-taken").
                else if (step.screenshotTaken) {
                    await shot(step.screenshotTaken);
                    Main.screenshotUI.emit('screenshot-taken', Gio.File.new_for_path(`${OUT}/${step.screenshotTaken}.png`));
                }
                else if (step.move) dev.notify_absolute_motion(t(), step.move[0], step.move[1]);
                else if (step.press) dev.notify_button(t(), step.press, Clutter.ButtonState.PRESSED);
                else if (step.release) {
                    dev.notify_button(t(), step.release, Clutter.ButtonState.RELEASED);
                    log(`DEVSHOT release at ${GLib.get_monotonic_time()}`);
                }
                else if (step.drag) {
                    const [x0, y0, x1, y1] = step.drag;
                    dev.notify_absolute_motion(t(), x0, y0); await wait(200);
                    dev.notify_button(t(), 1, Clutter.ButtonState.PRESSED); await wait(200);
                    for (let i = 1; i <= 20; i++) { dev.notify_absolute_motion(t(), x0 + (x1 - x0) * i / 20, y0 + (y1 - y0) * i / 20); await wait(40); }
                    await wait(300);
                    dev.notify_button(t(), 1, Clutter.ButtonState.RELEASED);
                } else if (step.type) {
                    for (const ch of step.type) {
                        const sym = Clutter.unicode_to_keysym(ch.codePointAt(0));
                        kbd.notify_keyval(t(), sym, Clutter.KeyState.PRESSED); await wait(30);
                        kbd.notify_keyval(t(), sym, Clutter.KeyState.RELEASED); await wait(60);
                    }
                } else if (step.combo) {
                    const ks = step.combo.map(k => Clutter[k]);
                    for (const k of ks) { kbd.notify_keyval(t(), k, Clutter.KeyState.PRESSED); await wait(30); }
                    for (const k of [...ks].reverse()) { kbd.notify_keyval(t(), k, Clutter.KeyState.RELEASED); await wait(30); }
                } else if (step.log) log(step.log);
                else if (step.notify) Main.notify(step.notify[0], step.notify[1]);
                else if (step.osd) Main.osdWindowManager.showAll(Gio.ThemedIcon.new('audio-volume-high-symbolic'), 'Volume', step.osd / 100, 1);
                else if (step.states) log('DEVSHOT states ' + Main.extensionManager.getUuids().map(u => `${u}=${Main.extensionManager.lookup(u)?.state}`).join(' '));
            }
            Gio.File.new_for_path(`${OUT}/done`).create(0, null);
        })().catch(e => log(`devshot ERR ${e}${e.stack}`));
    }
    disable() {}
}
