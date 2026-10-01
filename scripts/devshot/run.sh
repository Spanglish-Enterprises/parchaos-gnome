#!/bin/bash
# Usage: scripts/devshot/run.sh PLAN.json [seconds] ; env: EXTS="uuid uuid" (repo extensions to load),
# SETTINGS="dconf-path value;..." (written before the shell starts). Output in $OUT (default /tmp/devshot-out).
# Runs a throwaway headless shell in a private session bus and HOME. Never touches the real desktop.
set -u
cd "$(dirname "$0")/../.." || exit 1
REPO=$PWD
OUT=${OUT:-/tmp/devshot-out}; mkdir -p "$OUT"; rm -f "$OUT"/done "$OUT"/*.png
cp "$1" "$OUT/plan.json"
W=$(mktemp -d); H=$W/home; mkdir -p "$H/.local/share/gnome-shell/extensions" "$W/run" "$W/schemas"; chmod 700 "$W/run"
for u in ${EXTS:-}; do
  pkg=${u%@*}; src=$REPO/packaging/$pkg/files; [ -f "$src/metadata.json" ] || src=$REPO/packaging/$pkg
  d=$H/.local/share/gnome-shell/extensions/$u; mkdir -p "$d"; cp -r "$src/." "$d/"
  if ls "$d"/*.gschema.xml >/dev/null 2>&1; then mkdir -p "$d/schemas"; mv "$d"/*.gschema.xml "$d/schemas/"; glib-compile-schemas "$d/schemas"; fi
done
cp -r scripts/devshot/devshot@parchaos.test "$H/.local/share/gnome-shell/extensions/"
cp packaging/parchaos-desktop/files/org.parchaos.desktop.gschema.xml "$W/schemas/"
for s in /usr/share/gnome-shell/extensions/liquid-glass@thinkingcoding1231.gmail.com/schemas; do [ -d "$s" ] && cp "$s"/*.gschema.xml "$W/schemas/" 2>/dev/null; done
glib-compile-schemas "$W/schemas"
EN=$(printf "'%s', " devshot@parchaos.test ${EXTS:-} ${SYSEXTS:-})
cat > "$W/inner.sh" <<IN
export GSETTINGS_SCHEMA_DIR=$W/schemas:/usr/share/glib-2.0/schemas
dconf reset -f /
dconf write /org/gnome/shell/enabled-extensions "[${EN%, }]"
dconf write /org/gnome/shell/disable-user-extensions false
dconf write /org/gnome/shell/disable-extension-version-validation true
dconf write /org/gnome/shell/welcome-dialog-last-shown-version "'999'"
IFS=';' read -ra KV <<< "\${SETTINGS:-}"
for kv in "\${KV[@]}"; do [ -n "\$kv" ] && dconf write \${kv%% *} "\${kv#* }"; done
exec gnome-shell --headless --virtual-monitor 1600x900 --wayland-display=devshot-0 --no-x11 > $W/shell.log 2>&1
IN
env -u DBUS_SESSION_BUS_ADDRESS -u WAYLAND_DISPLAY -u DISPLAY HOME=$H XDG_CONFIG_HOME=$H/.config XDG_DATA_HOME=$H/.local/share \
  XDG_CACHE_HOME=$H/.cache XDG_STATE_HOME=$H/.local/state XDG_RUNTIME_DIR=$W/run DEVSHOT_OUT=$OUT SETTINGS="${SETTINGS:-}" \
  timeout "${2:-90}" dbus-run-session -- bash "$W/inner.sh"
cp "$W/shell.log" "$OUT/shell.log"; echo "out: $OUT (log $OUT/shell.log)"
