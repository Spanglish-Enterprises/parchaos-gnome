#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Rebuilds po/parchaos-launcher.pot from the strings marked _() in files/extension.js and merges it
# into every po/<lang>.po.
set -eu
cd "$(dirname "$0")"
xgettext --language=JavaScript --from-code=UTF-8 --keyword=_ --keyword=N_ --add-comments \
    --package-name=parchaos-launcher \
    --msgid-bugs-address=https://www.parchaos.org/support \
    -o po/parchaos-launcher.pot files/extension.js
for po in po/*.po; do
    [ -e "$po" ] && msgmerge --quiet --update --backup=none "$po" po/parchaos-launcher.pot
done
echo "updated po/parchaos-launcher.pot"
