#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Rebuilds po/parchaos-settings.pot from the strings marked with _() in
# files/parchaos-settings (ticket #53). Translators copy the .pot to
# po/<lang>.po and translate it.
set -eu
cd "$(dirname "$0")"
xgettext --language=Python --from-code=UTF-8 --keyword=_ --add-comments \
    --package-name=parchaos-settings \
    --msgid-bugs-address=https://github.com/Spanglish-Enterprises/parchaos-gnome/issues \
    -o po/parchaos-settings.pot files/parchaos-settings
echo "updated po/parchaos-settings.pot"
