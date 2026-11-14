// SPDX-License-Identifier: GPL-3.0-or-later
// Launcher search beyond apps (tickets #34/#150): the GNOME search providers installed on the
// system - files (Parcher, through LocalSearch), Settings, the calculator (sums and unit
// conversions), Photo search, Clocks, Contacts, Weather... - each answering in its own group
// under the app results. The same D-Bus interface the overview uses, so any app's provider
// works, and the user's choices in GNOME Settings > Search (which providers, in what order)
// apply.
//
// Original code for ParchaOS, GPL-3.0-or-later.

import Gio from 'gi://Gio';

import * as RemoteSearch from 'resource:///org/gnome/shell/ui/remoteSearch.js';

const MAX_PER_PROVIDER = 3;
// Shown first when they answer, in this order; the rest follow in GNOME's own order.
const FIRST = [
    'org.gnome.Calculator.desktop',
    'org.gnome.Nautilus.desktop',
    'org.parchaos.ImageSearch.desktop',
    'org.gnome.Settings.desktop',
];

export function rank(providerId, index) {
    const first = FIRST.indexOf(providerId);
    return first >= 0 ? first : FIRST.length + index;
}

export class ProviderSearch {
    constructor() {
        this._settings = new Gio.Settings({schema_id: 'org.gnome.desktop.search-providers'});
        this._providers = null;
        this._settings.connectObject('changed', () => {
            this._providers = null;
        }, this);
    }

    _all() {
        if (this._providers === null) {
            try {
                this._providers = RemoteSearch.loadRemoteSearchProviders(this._settings);
            } catch (e) {
                logError(e, 'parchaos-launcher: could not load the search providers');
                this._providers = [];
            }
        }
        return this._providers;
    }

    /**
     * Asks every provider about `text`. `onSection({provider, rank, metas, terms})` is called as
     * each one answers with results; a cancelled search calls nothing more.
     */
    search(text, cancellable, onSection) {
        const terms = text.split(/\s+/).filter(t => t.length > 0);
        if (!terms.length)
            return;
        this._all().forEach(async (provider, index) => {
            try {
                const ids = await provider.getInitialResultSet(terms, cancellable);
                if (cancellable.is_cancelled() || !ids?.length)
                    return;
                const metas = await provider.getResultMetas(ids.slice(0, MAX_PER_PROVIDER), cancellable);
                if (cancellable.is_cancelled() || !metas?.length)
                    return;
                onSection({provider, rank: rank(provider.appInfo.get_id(), index), metas, terms});
            } catch (e) {
                if (!e.matches?.(Gio.IOErrorEnum, Gio.IOErrorEnum.CANCELLED))
                    log(`parchaos-launcher: ${provider.appInfo.get_id()} did not answer: ${e.message}`);
            }
        });
    }

    destroy() {
        this._settings.disconnectObject(this);
    }
}
