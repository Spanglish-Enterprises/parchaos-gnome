#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Rebuilds po/parchaos-app-store.pot from the gettext calls in files/usr/libexec/parchaos-app-leftovers
# and merges it into every po/<lang>.po.
set -eu
cd "$(dirname "$0")"
xgettext --language=Shell --from-code=UTF-8 --keyword=gettext --add-comments \
    --package-name=parchaos-app-store \
    --msgid-bugs-address=https://www.parchaos.org/support \
    -o po/parchaos-app-store.pot files/usr/libexec/parchaos-app-leftovers
for po in po/*.po; do
    [ -e "$po" ] && msgmerge --quiet --update --backup=none "$po" po/parchaos-app-store.pot
done
echo "updated po/parchaos-app-store.pot"
