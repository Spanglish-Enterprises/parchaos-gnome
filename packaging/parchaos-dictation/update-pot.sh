#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Rebuilds po/parchaos-dictation.pot from the strings marked _() in extension.js and merges it
# into every po/<lang>.po.
set -eu
cd "$(dirname "$0")"
xgettext --language=JavaScript --from-code=UTF-8 --keyword=_ --keyword=N_ --add-comments \
    --package-name=parchaos-dictation \
    --msgid-bugs-address=https://www.parchaos.org/support \
    -o po/parchaos-dictation.pot extension.js
for po in po/*.po; do
    [ -e "$po" ] && msgmerge --quiet --update --backup=none "$po" po/parchaos-dictation.pot
done
echo "updated po/parchaos-dictation.pot"
