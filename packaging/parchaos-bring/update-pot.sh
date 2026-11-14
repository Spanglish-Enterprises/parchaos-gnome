#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Rebuilds po/parchaos-bring.pot from the strings marked _() or N_() in parchaos-bring and merges
# it into every po/<lang>.po.
set -eu
cd "$(dirname "$0")"
xgettext --language=Python --from-code=UTF-8 --keyword=_ --keyword=N_ --keyword=ngettext:1,2 --add-comments \
    --package-name=parchaos-bring \
    --msgid-bugs-address=https://www.parchaos.org/support \
    -o po/parchaos-bring.pot parchaos-bring bringlib.py
for po in po/*.po; do
    [ -e "$po" ] && msgmerge --quiet --update --backup=none "$po" po/parchaos-bring.pot
done
echo "updated po/parchaos-bring.pot"
