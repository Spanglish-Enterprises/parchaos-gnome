#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Rebuilds po/parchaos-assistant.pot from the strings marked _() in files/parchaos-assistant and merges it
# into every po/<lang>.po.
set -eu
cd "$(dirname "$0")"
xgettext --language=Python --from-code=UTF-8 --keyword=_ --add-comments \
    --package-name=parchaos-assistant \
    --msgid-bugs-address=https://www.parchaos.org/support \
    -o po/parchaos-assistant.pot files/parchaos-assistant
for po in po/*.po; do
    [ -e "$po" ] && msgmerge --quiet --update --backup=none "$po" po/parchaos-assistant.pot
done
echo "updated po/parchaos-assistant.pot"
