#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Rebuilds po/parchaos-nearby.pot from the strings marked _() or N_() in parchaos-nearby and merges
# it into every po/<lang>.po.
set -eu
cd "$(dirname "$0")"
xgettext --language=Python --from-code=UTF-8 --keyword=_ --keyword=N_ --add-comments \
    --package-name=parchaos-nearby \
    --msgid-bugs-address=https://www.parchaos.org/support \
    -o po/parchaos-nearby.pot parchaos-nearby
for po in po/*.po; do
    [ -e "$po" ] && msgmerge --quiet --update --backup=none "$po" po/parchaos-nearby.pot
done
echo "updated po/parchaos-nearby.pot"
