#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Rebuilds po/parchaos-updates.pot from the gettext/ngettext calls in files/usr/bin/parchaos-updates-check
# and merges it into every po/<lang>.po.
set -eu
cd "$(dirname "$0")"
xgettext --language=Shell --from-code=UTF-8 --keyword=gettext --keyword=ngettext:1,2 --add-comments \
    --package-name=parchaos-updates \
    --msgid-bugs-address=https://www.parchaos.org/support \
    -o po/parchaos-updates.pot files/usr/bin/parchaos-updates-check
for po in po/*.po; do
    [ -e "$po" ] && msgmerge --quiet --update --backup=none "$po" po/parchaos-updates.pot
done
echo "updated po/parchaos-updates.pot"
