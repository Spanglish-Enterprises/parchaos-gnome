#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Rebuilds po/parchaos-welcome.pot from the strings marked _() in files/parchaos-welcome and merges it
# into every po/<lang>.po.
set -eu
cd "$(dirname "$0")"
xgettext --language=Python --from-code=UTF-8 --keyword=_ --add-comments \
    --package-name=parchaos-welcome \
    --msgid-bugs-address=https://www.parchaos.org/support \
    -o po/parchaos-welcome.pot files/parchaos-welcome
for po in po/*.po; do
    [ -e "$po" ] && msgmerge --quiet --update --backup=none "$po" po/parchaos-welcome.pot
done
echo "updated po/parchaos-welcome.pot"
