#!/bin/bash
# Headless smoke test for the ParchaOS GNOME Shell extensions, straight
# from this repository (no RPMs needed). Starts a throwaway headless
# GNOME Shell with the extensions enabled, lets the smoke@parchaos.test
# extension drive them (Controls, launcher, About card, style switch,
# disable/enable), and fails on any failed check or any JS error the
# shell logs for a ParchaOS extension.
#
#   scripts/smoke-test.sh            needs gnome-shell, dbus, glib2
#
# Original code for ParchaOS, GPL-3.0-or-later.

set -u
cd "$(dirname "$0")/.." || exit 1
WORK=$(mktemp -d)
[ -n "${SMOKE_KEEP:-}" ] && echo "work dir: $WORK" || trap 'rm -rf "$WORK"' EXIT

EXTS=(parchaos-controls parchaos-global-menu parchaos-launcher parchaos-session parchaos-live-icons parchaos-dictation parchaos-speak)
export HOME=$WORK/home XDG_CONFIG_HOME=$WORK/home/.config XDG_DATA_HOME=$WORK/home/.local/share
export XDG_CACHE_HOME=$WORK/home/.cache XDG_STATE_HOME=$WORK/home/.local/state
export XDG_RUNTIME_DIR=$WORK/run SMOKE_OUT=$WORK/out
mkdir -p "$XDG_RUNTIME_DIR" "$SMOKE_OUT" && chmod 700 "$XDG_RUNTIME_DIR"
unset WAYLAND_DISPLAY DISPLAY DBUS_SESSION_BUS_ADDRESS

dest=$XDG_DATA_HOME/gnome-shell/extensions
uuids=()
for pkg in "${EXTS[@]}"; do
    # Most packages keep the extension in files/; parchaos-dictation keeps it
    # next to its spec, with its settings schema beside it.
    src=packaging/$pkg/files
    [ -f "$src/metadata.json" ] || src=packaging/$pkg
    uuid=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["uuid"])' \
        "$src/metadata.json")
    mkdir -p "$dest/$uuid"
    if [ "$src" = "packaging/$pkg" ]; then
        cp "$src/extension.js" "$src/metadata.json" "$dest/$uuid/"
        if ls "$src"/*.gschema.xml >/dev/null 2>&1; then
            mkdir -p "$dest/$uuid/schemas"
            cp "$src"/*.gschema.xml "$dest/$uuid/schemas/"
            glib-compile-schemas "$dest/$uuid/schemas"
        fi
    else
        cp -r "$src/." "$dest/$uuid/"
        # A schema shipped beside the extension goes where GNOME Shell looks.
        if ls "$dest/$uuid"/*.gschema.xml >/dev/null 2>&1; then
            mkdir -p "$dest/$uuid/schemas"
            mv "$dest/$uuid"/*.gschema.xml "$dest/$uuid/schemas/"
            glib-compile-schemas "$dest/$uuid/schemas"
        fi
    fi
    uuids+=("$uuid")
done
cp -r scripts/smoke/smoke@parchaos.test "$dest/"

# The ParchaOS settings schema, from parchaos-desktop.
mkdir -p "$WORK/schemas"
cp packaging/parchaos-desktop/files/org.parchaos.desktop.gschema.xml "$WORK/schemas/"
glib-compile-schemas "$WORK/schemas"
export GSETTINGS_SCHEMA_DIR=$WORK/schemas

SMOKE_UUIDS=$(IFS=,; echo "${uuids[*]}")
export SMOKE_UUIDS
enabled=$(printf "'%s', " "smoke@parchaos.test" "${uuids[@]}")

dbus-run-session -- bash -c "
    gsettings set org.gnome.shell enabled-extensions \"[${enabled%, }]\"
    gsettings set org.gnome.shell disable-extension-version-validation true
    gsettings set org.gnome.shell welcome-dialog-last-shown-version '999'
    timeout 90 gnome-shell --headless --virtual-monitor 1280x800 --no-x11 \
        --wayland-display=smoke-0 >'$WORK/shell.log' 2>&1
" >>"$WORK/shell.log" 2>&1 || true

status=0
if [ ! -s "$SMOKE_OUT/results.txt" ]; then
    echo "FAIL: the smoke test never ran. Shell log:"
    tail -40 "$WORK/shell.log"
    exit 1
fi
cat "$SMOKE_OUT/results.txt"
grep -q '^FAIL' "$SMOKE_OUT/results.txt" && status=1
grep -q '^DONE' "$SMOKE_OUT/results.txt" || { echo "FAIL: the smoke test didn't finish"; status=1; }

# JS errors from ParchaOS code (stack frames name the extension's path).
if grep -A12 -E 'JS ERROR|JS WARNING|-CRITICAL|Exception in callback' "$WORK/shell.log" | grep -qE '@parchaos\.org'; then
    echo "FAIL: JS errors from ParchaOS extensions:"
    grep -A12 -E 'JS ERROR|JS WARNING|-CRITICAL|Exception in callback' "$WORK/shell.log" | grep -B6 -A6 '@parchaos\.org' | head -60
    status=1
fi
[ $status -eq 0 ] && echo "Smoke test passed."
exit $status
