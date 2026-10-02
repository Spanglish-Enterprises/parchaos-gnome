#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Rebuilds po/parchaos-whatsnew.pot from the strings marked _() in files/parchaos-whatsnew and merges it
# into every po/<lang>.po. (The release content has its own translations inside whatsnew.json.)
set -eu
cd "$(dirname "$0")"
xgettext --language=Python --from-code=UTF-8 --keyword=_ --add-comments \
    --package-name=parchaos-whatsnew \
    --msgid-bugs-address=https://www.parchaos.org/support \
    -o po/parchaos-whatsnew.pot files/parchaos-whatsnew
for po in po/*.po; do
    [ -e "$po" ] && msgmerge --quiet --update --backup=none "$po" po/parchaos-whatsnew.pot
done
echo "updated po/parchaos-whatsnew.pot"
