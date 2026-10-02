// Smoke test for scripts/smoke-test.sh: exercises the ParchaOS shell
// extensions in a headless GNOME Shell and writes one line per check to
// $SMOKE_OUT/results.txt ("PASS name" / "FAIL name: reason"), then ends
// the shell. JS errors the shell logs are checked by the script itself.
//
// Original code for ParchaOS, GPL-3.0-or-later.

import GLib from 'gi://GLib';
import GdkPixbuf from 'gi://GdkPixbuf';
import Gio from 'gi://Gio';
import Shell from 'gi://Shell';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

const OUT = GLib.getenv('SMOKE_OUT');
const UUIDS = (GLib.getenv('SMOKE_UUIDS') || '').split(',').filter(u => u);

function write(line) {
    const stream = Gio.File.new_for_path(`${OUT}/results.txt`).append_to(Gio.FileCreateFlags.NONE, null);
    stream.write_all(`${line}\n`, null);
    stream.close(null);
}

const sleep = ms => new Promise(resolve => GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, () => {
    resolve();
    return GLib.SOURCE_REMOVE;
}));

const ext = uuid => Main.extensionManager.lookup(uuid);

let started = false;

export default class SmokeTest extends Extension {
    enable() {
        // The checks below rewrite enabled-extensions (disable/enable of each
        // ParchaOS extension), and every rewrite makes the Shell enable this
        // extension again -- which used to start another complete run on top of
        // the first. The overlapping runs disabled extensions under each other:
        // a false "controls is disabled" failure and a disposed-menu error.
        // Run once per shell.
        if (started)
            return;
        started = true;
        if (GLib.getenv('SMOKE_DEBUG'))
            write(`RUN START ${GLib.get_monotonic_time()}`);
        this._run().catch(e => write(`FAIL harness: ${e}\n${e.stack}`)).finally(() => {
            write('DONE');
            GLib.timeout_add(GLib.PRIORITY_DEFAULT, 500, () => {
                global.context?.terminate?.();
                return GLib.SOURCE_REMOVE;
            });
        });
    }

    disable() {}

    async _check(name, fn) {
        // SMOKE_DEBUG=1: also report every extension's state after each check,
        // to find which step switched one off.
        const states = () => GLib.getenv('SMOKE_DEBUG')
            ? ' [' + UUIDS.map(u => `${u.split('@')[0].replace('parchaos-', '')}=${Main.extensionManager.lookup(u)?.state}`).join(' ') + ']'
            : '';
        try {
            await fn();
            write(`PASS ${name}${states()}`);
        } catch (e) {
            write(`FAIL ${name}: ${e}${states()}`);
        }
    }

    async _run() {
        await sleep(4000);
        Main.overview.hide();
        await sleep(500);

        for (const uuid of UUIDS) {
            await this._check(`enabled ${uuid}`, () => {
                const e = ext(uuid);
                if (!e)
                    throw new Error('not found');
                if (e.state !== 1)
                    throw new Error(`state ${e.state} ${e.error ?? ''}`);
            });
        }

        if (ext('parchaos-controls@parchaos.org')) {
            await this._check('controls open/close x3', async () => {
                for (let i = 0; i < 3; i++) {
                    Main.panel.toggleQuickSettings();
                    await sleep(400);
                    Main.panel.closeQuickSettings();
                    await sleep(300);
                }
            });
        }

        // The "recently" pill above the tiles: a location request the shell grants shows
        // "<App> recently", a refused one does not, and a screenshot shows "Screenshot taken".
        const controlsButton = Main.panel.statusArea['parchaos-controls'];
        if (controlsButton) {
            await this._check('controls recently pill', async () => {
                const Location = await import('resource:///org/gnome/shell/ui/status/location.js');
                const agent = Location.getGeoclueAgent();
                const pillText = async () => {
                    controlsButton.menu.open();
                    await sleep(600);
                    const pill = controlsButton._panel?._recentPill;
                    const text = pill ? pill.child.get_children()[1].text : null;
                    controlsButton.menu.close();
                    await sleep(300);
                    return text;
                };
                if (await pillText() !== null)
                    throw new Error('a pill showed before anything happened');

                const location = new Gio.Settings({schema_id: 'org.gnome.system.location'});
                const store = agent._permStoreProxy;
                // A stand-in permission store where both apps were allowed before, so the shell
                // decides without its permission dialog (which would wait for a click).
                agent._permStoreProxy = {
                    LookupAsync: () => Promise.resolve([{
                        'org.gnome.Weather': ['EXACT', '0'],
                        'org.gnome.Settings': ['EXACT', '0'],
                    }]),
                    SetAsync: () => Promise.resolve(),
                };
                const ask = async (desktopId, enabled) => {
                    location.set_boolean('enabled', enabled);
                    location.set_string('max-accuracy-level', 'exact');
                    await sleep(200);
                    let reply = null;
                    await agent.AuthorizeAppAsync([desktopId, 8], {return_value: v => {
                        reply = v.deepUnpack();
                    }});
                    return reply;
                };
                try {
                    const weather = Shell.AppSystem.get_default().lookup_app('org.gnome.Weather.desktop');
                    if (!weather)
                        throw new Error('org.gnome.Weather is not installed here');
                    const granted = await ask('org.gnome.Weather', true);
                    if (!granted?.[0])
                        throw new Error(`the shell did not grant the test request: ${JSON.stringify(granted)}`);
                    let text = await pillText();
                    if (text !== `${weather.get_name()} recently`)
                        throw new Error(`after a granted request the pill said ${JSON.stringify(text)}`);
                    const refused = await ask('org.gnome.Settings', false);
                    if (refused?.[0])
                        throw new Error('a request with location off was granted');
                    text = await pillText();
                    if (text !== `${weather.get_name()} recently`)
                        throw new Error(`a refused request changed the pill to ${JSON.stringify(text)}`);
                } finally {
                    agent._permStoreProxy = store;
                    location.reset('enabled');
                    location.reset('max-accuracy-level');
                }

                const file = Gio.File.new_for_path(`${GLib.get_home_dir()}/smoke-shot.png`);
                file.replace_contents(new Uint8Array([0x89, 0x50, 0x4e, 0x47]), null, false, 0, null);
                Main.screenshotUI.emit('screenshot-taken', file);
                const text = await pillText();
                if (text !== 'Screenshot taken')
                    throw new Error(`after a screenshot the pill said ${JSON.stringify(text)}`);
            });
        }

        // Suggestions learn from use, privately: a used control that is not in the panel leads
        // Suggestions; the history file is the user's only (0600) and holds control names,
        // scores and times only; turning learning off deletes it.
        if (controlsButton) {
            await this._check('controls suggestions learn from use', async () => {
                const desktop = new Gio.Settings({schema_id: 'org.parchaos.desktop'});
                const file = Gio.File.new_for_path(`${GLib.get_user_data_dir()}/parchaos/controls-usage.json`);
                desktop.set_strv('controls-hidden', ['lock', 'night-light', 'screenshot']);
                try {
                    const shot = Gio.File.new_for_path(`${GLib.get_home_dir()}/smoke-learn.png`);
                    shot.replace_contents(new Uint8Array([0x89, 0x50, 0x4e, 0x47]), null, false, 0, null);
                    Main.screenshotUI.emit('screenshot-taken', shot);
                    await sleep(6500);
                    if (!file.query_exists(null))
                        throw new Error('no usage file after a screenshot');
                    const info = file.query_info('unix::mode', 0, null);
                    const mode = info.get_attribute_uint32('unix::mode') & 0o777;
                    if (mode !== 0o600)
                        throw new Error(`usage file mode is ${mode.toString(8)}, not 600`);
                    const data = JSON.parse(new TextDecoder().decode(file.load_contents(null)[1]));
                    const keys = JSON.stringify(Object.keys(data).sort()) + JSON.stringify(Object.keys(data.controls));
                    if (keys !== '["controls","version"]["screenshot"]')
                        throw new Error(`usage file holds more than expected: ${keys}`);
                    if (JSON.stringify(Object.keys(data.controls.screenshot).sort()) !== '["last","score"]')
                        throw new Error('a usage entry holds more than a score and a time');

                    controlsButton.menu.open();
                    await sleep(600);
                    controlsButton._panel._setEditing(true);
                    await sleep(1200);
                    const picker = controlsButton._picker;
                    if (!picker)
                        throw new Error('edit mode did not open the picker');
                    const firstTile = picker._gallery.get_children()
                        .find(c => c.get_children?.()[0]?._controlItem)?.get_children()[0];
                    const first = firstTile?._controlItem?.id;
                    controlsButton._panel.finishEditing();
                    await sleep(600);
                    controlsButton.menu.close();
                    await sleep(300);
                    if (first !== 'screenshot')
                        throw new Error(`the first suggestion is ${first}, not the used control`);

                    desktop.set_boolean('learn-usage', false);
                    await sleep(500);
                    if (file.query_exists(null))
                        throw new Error('turning learning off left the usage file');
                } finally {
                    desktop.reset('learn-usage');
                    desktop.reset('controls-hidden');
                }
            });
        }

        const launcher = ext('parchaos-launcher@parchaos.org')?.stateObj;
        if (launcher) {
            await this._check('launcher open, folder, close', async () => {
                launcher.toggle();
                await sleep(800);
                const view = launcher._launcher;
                if (!view)
                    throw new Error('launcher did not open');
                view._tiles.find(t => t.item.type === 'folder')?.emit('activate');
                await sleep(400);
                view.close();
                await sleep(600);
            });
        }

        if (launcher) {
            // Helper replies (removable apps, uninstall plan) arriving after
            // the launcher closed must not touch it.
            await this._check('launcher closed during edit mode and uninstall check', async () => {
                launcher.toggle();
                await sleep(600);
                const view = launcher._launcher;
                view._setEditing(true);
                view.close();
                await sleep(400);
                launcher.toggle();
                await sleep(600);
                const again = launcher._launcher;
                const app = again._tiles.find(t => t.item.type === 'app')?.item.app;
                if (app)
                    again._confirmRemove(app);
                again.close();
                await sleep(2500);
            });
        }

        if (launcher) {
            // Search, edit mode, and drag while the launcher is open.
            await this._check('launcher search/edit/drag', async () => {
                launcher.toggle();
                await sleep(800);
                const view = launcher._launcher;
                if (!view)
                    throw new Error('launcher did not open');
                // Search
                view._searchEntry?.set_text('a');
                await sleep(300);
                view._searchEntry?.set_text('');
                await sleep(200);
                // Edit mode
                view._setEditing(true);
                await sleep(300);
                view._setEditing(false);
                await sleep(200);
                // Drag (simulate by calling the drag handler directly)
                const tiles = view._tiles;
                if (tiles.length >= 2) {
                    const src = tiles[0];
                    const dst = tiles[1];
                    view._onDragStart?.(src);
                    view._onDragEnd?.(src, dst);
                }
                view.close();
                await sleep(600);
            });
        }

        if (launcher) {
            // Disable while the launcher is open — must not crash.
            await this._check('launcher disable while open', async () => {
                launcher.toggle();
                await sleep(800);
                await Main.extensionManager.disableExtension('parchaos-launcher@parchaos.org');
                await sleep(500);
                await Main.extensionManager.enableExtension('parchaos-launcher@parchaos.org');
                for (let i = 0; i < 30 && ext('parchaos-launcher@parchaos.org').state !== 1; i++)
                    await sleep(100);
                if (ext('parchaos-launcher@parchaos.org').state !== 1)
                    throw new Error(`state ${ext('parchaos-launcher@parchaos.org').state}`);
            });
        }

        // The Screenshot launcher (ticket #130) reaches GNOME Shell's capture
        // tool through a D-Bus method that Parcha Controls exports.
        if (ext('parchaos-controls@parchaos.org')) {
            await this._check('screenshot launcher opens the capture tool', async () => {
                if (Main.screenshotUI.visible)
                    throw new Error('the capture tool was already open');
                await new Promise((resolve, reject) => Gio.DBus.session.call(
                    'org.parchaos.Shell', '/org/parchaos/Shell', 'org.parchaos.Shell',
                    'OpenScreenshotUI', null, null, Gio.DBusCallFlags.NONE, 5000, null,
                    (conn, res) => {
                        try {
                            conn.call_finish(res);
                            resolve();
                        } catch (e) {
                            reject(e);
                        }
                    }));
                await sleep(1200);
                const opened = Main.screenshotUI.visible;
                Main.screenshotUI.close();
                await sleep(300);
                if (!opened)
                    throw new Error('the call succeeded but the capture tool did not open');
            });
        }

        const menu = ext('parchaos-global-menu@parchaos.org')?.stateObj;
        if (menu) {
            await this._check('about card', async () => {
                menu._showAboutDialog();
                await sleep(1500);
                Main.layoutManager.modalDialogGroup.get_children().forEach(d => d.close?.());
            });
        }

        // Window > Zoom and the tiling items act on a real app window. Mutter
        // 18 dropped get_maximized() and the MaximizeFlags argument, which
        // left these items throwing on every click without a visible error.
        if (menu) {
            await this._check('window menu zoom and tiling', async () => {
                const windowMenu = menu._menuBarButtons.find(b => b.roleId === 'window')?.menu;
                const item = label => windowMenu?._getMenuItems()
                    .find(i => i.label?.get_text?.() === label);
                for (const label of ['Zoom', 'Move Window to Left Half']) {
                    if (!item(label))
                        throw new Error(`no "${label}" item in the Window menu`);
                }

                const [, pid] = GLib.spawn_async(null, ['gjs', '-c', [
                    "imports.gi.versions.Gtk = '4.0';",
                    "const {Gtk, GLib} = imports.gi; Gtk.init();",
                    "const w = new Gtk.Window({title: 'smoke-window', default_width: 400, default_height: 300});",
                    "w.present(); new GLib.MainLoop(null, false).run();",
                ].join(' ')], null, GLib.SpawnFlags.SEARCH_PATH, null);
                try {
                    let win = null;
                    for (let i = 0; i < 40 && !win; i++) {
                        await sleep(250);
                        win = global.get_window_actors().map(a => a.meta_window)
                            .find(w => w.get_title() === 'smoke-window') ?? null;
                    }
                    if (!win)
                        throw new Error('the test window never appeared');
                    win.activate(global.get_current_time());
                    await sleep(500);
                    if (menu._trackedWindow !== win)
                        throw new Error('the menu bar did not track the test window');

                    const maximized = () => win.is_maximized?.() ?? win.get_maximized() !== 0;
                    item('Zoom').activate(null);
                    await sleep(500);
                    if (!maximized())
                        throw new Error('Zoom did not maximize the window');
                    item('Zoom').activate(null);
                    await sleep(500);
                    if (maximized())
                        throw new Error('Zoom again did not restore the window');

                    item('Zoom').activate(null);
                    await sleep(500);
                    item('Move Window to Left Half').activate(null);
                    await sleep(500);
                    const area = win.get_work_area_current_monitor();
                    const rect = win.get_frame_rect();
                    if (maximized() || rect.x !== area.x || Math.abs(rect.width - area.width / 2) > 1)
                        throw new Error(`left half gave ${rect.x},${rect.width} in a ${area.x},${area.width} area`);
                } finally {
                    GLib.spawn_command_line_sync(`kill ${pid}`);
                    GLib.spawn_close_pid(pid);
                    await sleep(300);
                }
            });
        }

        const schema = Gio.SettingsSchemaSource.get_default().lookup('org.parchaos.desktop', true);
        if (schema) {
            await this._check('style switch', async () => {
                const settings = new Gio.Settings({settings_schema: schema});
                for (const style of ['classic', 'glass']) {
                    settings.set_string('style', style);
                    await sleep(400);
                }
            });
        }

        // The menu bar picks light or dark text from the wallpaper under it.
        // Exercises the real path (decode the image, average its top strip,
        // set a style class): a light wallpaper must give the light bar, a
        // dark one must not. Catches errors in the async image loading, which
        // otherwise only show up as a bar that silently never tints.
        if (ext('parchaos-global-menu@parchaos.org')) {
            await this._check('menu bar tint follows the wallpaper', async () => {
                const bg = new Gio.Settings({schema_id: 'org.gnome.desktop.background'});
                const image = (name, rgba) => {
                    const px = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, false, 8, 64, 64);
                    px.fill(rgba);
                    const path = `${OUT}/${name}.png`;
                    px.savev(path, 'png', [], []);
                    return path;
                };
                const light = image('bg-light', 0xf2efe8ff);
                const dark = image('bg-dark', 0x1b2233ff);
                bg.set_string('picture-options', 'zoom');
                for (const [path, wantLight] of [[light, true], [dark, false], [light, true]]) {
                    bg.set_string('picture-uri', `file://${path}`);
                    bg.set_string('picture-uri-dark', `file://${path}`);
                    for (let i = 0; i < 40 && Main.panel.has_style_class_name('parchaos-menubar-light') !== wantLight; i++)
                        await sleep(100);
                    if (Main.panel.has_style_class_name('parchaos-menubar-light') !== wantLight)
                        throw new Error(`bar not ${wantLight ? 'light' : 'dark'} for ${path}`);
                }
            });
        }

        // Color-scheme toggle: theme-sync should follow.
        const desktopIface = new Gio.Settings({schema_id: 'org.gnome.desktop.interface'});
        await this._check('color-scheme toggle', async () => {
            for (const scheme of ['prefer-light', 'prefer-dark']) {
                desktopIface.set_string('color-scheme', scheme);
                await sleep(400);
            }
            desktopIface.set_string('color-scheme', 'prefer-dark');
            await sleep(300);
        });

        // EndSessionDialog hooks: session extension must save without crashing.
        const session = ext('parchaos-session@parchaos.org')?.stateObj;
        if (session) {
            await this._check('session EndSessionDialog hooks', async () => {
                // Trigger the _confirm path that the injection hooks into.
                session._ending = true;
                session._save();
                session._ending = false;
                await sleep(300);
            });
        }

        for (const uuid of UUIDS) {
            await this._check(`disable/enable ${uuid}`, async () => {
                // These go through the enabled-extensions setting, so the
                // extension comes back asynchronously.
                await Main.extensionManager.disableExtension(uuid);
                await sleep(300);
                await Main.extensionManager.enableExtension(uuid);
                for (let i = 0; i < 30 && ext(uuid).state !== 1; i++)
                    await sleep(100);
                if (ext(uuid).state !== 1)
                    throw new Error(`state ${ext(uuid).state} ${ext(uuid).error ?? ''}`);
            });
        }
    }
}
