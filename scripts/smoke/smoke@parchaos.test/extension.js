// Smoke test for scripts/smoke-test.sh: exercises the ParchaOS shell
// extensions in a headless GNOME Shell and writes one line per check to
// $SMOKE_OUT/results.txt ("PASS name" / "FAIL name: reason"), then ends
// the shell. JS errors the shell logs are checked by the script itself.
//
// Original code for ParchaOS, GPL-3.0-or-later.

import GLib from 'gi://GLib';
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

export default class SmokeTest extends Extension {
    enable() {
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
        try {
            await fn();
            write(`PASS ${name}`);
        } catch (e) {
            write(`FAIL ${name}: ${e}`);
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
