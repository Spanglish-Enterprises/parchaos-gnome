// Smoke test for scripts/smoke-test.sh: exercises the ParchaOS shell
// extensions in a headless GNOME Shell and writes one line per check to
// $SMOKE_OUT/results.txt ("PASS name" / "FAIL name: reason"), then ends
// the shell. JS errors the shell logs are checked by the script itself.
//
// Original code for ParchaOS, GPL-3.0-or-later.

import GLib from 'gi://GLib';
import GdkPixbuf from 'gi://GdkPixbuf';
import Gio from 'gi://Gio';
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

        const menu = ext('parchaos-global-menu@parchaos.org')?.stateObj;
        if (menu) {
            await this._check('about card', async () => {
                menu._showAboutDialog();
                await sleep(1500);
                Main.layoutManager.modalDialogGroup.get_children().forEach(d => d.close?.());
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
