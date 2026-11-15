#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Rebuilds po/parchaos-boot.pot from the strings marked _() in
# parchaos-earlier-version and merges it into every po/<lang>.po.
set -eu
cd "$(dirname "$0")"
xgettext --language=Python --from-code=UTF-8 --keyword=_ --add-comments \
    --package-name=parchaos-boot \
    --msgid-bugs-address=https://www.parchaos.org/support \
    -o po/parchaos-boot.pot files/parchaos-earlier-version
for po in po/*.po; do
    [ -e "$po" ] && msgmerge --quiet --update --backup=none "$po" po/parchaos-boot.pot
done
echo "updated po/parchaos-boot.pot"
