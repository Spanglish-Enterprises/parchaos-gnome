#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Rebuilds po/parchaos-global-menu.pot from the strings marked _() in files/extension.js and merges it
# into every po/<lang>.po.
set -eu
cd "$(dirname "$0")"
xgettext --language=JavaScript --from-code=UTF-8 --keyword=_ --add-comments \
    --package-name=parchaos-global-menu \
    --msgid-bugs-address=https://www.parchaos.org/support \
    -o po/parchaos-global-menu.pot files/extension.js
for po in po/*.po; do
    [ -e "$po" ] && msgmerge --quiet --update --backup=none "$po" po/parchaos-global-menu.pot
done
echo "updated po/parchaos-global-menu.pot"
