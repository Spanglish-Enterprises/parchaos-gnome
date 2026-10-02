#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Rebuilds po/parchaos-sky.pot from the strings marked _() and N_() in files/parchaos-sky and
# merges it into every po/<lang>.po. Translators then fill in the new strings.
set -eu
cd "$(dirname "$0")"
xgettext --language=Python --from-code=UTF-8 --keyword=_ --keyword=N_ --add-comments \
    --package-name=parchaos-sky \
    --msgid-bugs-address=https://www.parchaos.org/support \
    -o po/parchaos-sky.pot files/parchaos-sky
for po in po/*.po; do
    msgmerge --quiet --update --backup=none "$po" po/parchaos-sky.pot
done
echo "updated po/parchaos-sky.pot"
