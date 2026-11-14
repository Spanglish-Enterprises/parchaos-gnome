#!/bin/bash
# Usage: scripts/devshot/run.sh PLAN.json [seconds] (steps: wait, shot, spawn, move, press, type, combo, showApps, menu, ...); env: EXTS="uuid uuid" (repo extensions to load),
# SETTINGS="dconf-path value;..." (written before the shell starts), FAKE_POWER="percent state" (a private system bus with a
# fake laptop battery and power profiles, see fake-power.py), VSIZE="WxH [WxH...]" (one virtual monitor each, default 1600x900), EXTDIRS="dir..." (built extension
# directories copied in as user extensions; name their uuids in SYSEXTS to enable them), EXTRAENV="VAR=value ..." (more environment for
# the shell). Output in $OUT (default /tmp/devshot-out).
# Runs a throwaway headless shell in a private session bus and HOME. Never touches the real desktop.
set -u
cd "$(dirname "$0")/../.." || exit 1
REPO=$PWD
OUT=${OUT:-/tmp/devshot-out}; mkdir -p "$OUT"; rm -f "$OUT"/done "$OUT"/*.png
cp "$1" "$OUT/plan.json"
W=$(mktemp -d); H=$W/home; mkdir -p "$H/.local/share/gnome-shell/extensions" "$H/Desktop" "$W/run" "$W/schemas"; chmod 700 "$W/run"
for u in ${EXTS:-}; do
  pkg=${u%@*}; src=$REPO/packaging/$pkg/files; [ -f "$src/metadata.json" ] || src=$REPO/packaging/$pkg; [ -f "$src/metadata.json" ] || src=$REPO/scripts/glass-demo/$u
  d=$H/.local/share/gnome-shell/extensions/$u; mkdir -p "$d"; cp -r "$src/." "$d/"
  if ls "$d"/*.gschema.xml >/dev/null 2>&1; then mkdir -p "$d/schemas"; mv "$d"/*.gschema.xml "$d/schemas/"; glib-compile-schemas "$d/schemas"; fi
done
for d in ${EXTDIRS:-}; do cp -r "$d" "$H/.local/share/gnome-shell/extensions/"; cp "$d"/schemas/*.gschema.xml "$W/schemas/" 2>/dev/null; done
cp -r scripts/devshot/devshot@parchaos.test "$H/.local/share/gnome-shell/extensions/"
cp packaging/parchaos-desktop/files/org.parchaos.desktop.gschema.xml "$W/schemas/"
true
glib-compile-schemas "$W/schemas"
VMON=""; for v in ${VSIZE:-1600x900}; do VMON="$VMON --virtual-monitor $v"; done
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
if [ -n "\${FAKE_POWER:-}" ]; then
  export DBUS_SYSTEM_BUS_ADDRESS=\$(dbus-daemon --session --fork --print-address)
  FAKE_POWER_LOG=$OUT/power-profile python3 $REPO/scripts/devshot/fake-power.py \$FAKE_POWER & sleep 1
fi
if [ -n "\${DEVKIT:-}" ]; then exec gnome-shell --devkit --wayland --no-x11 > $W/shell.log 2>&1; else exec gnome-shell --headless $VMON --wayland-display=devshot-0 --no-x11 > $W/shell.log 2>&1; fi
IN
if [ -n "${DEVKIT:-}" ]; then RT=/run/user/$(id -u); WL=${WAYLAND_DISPLAY:-wayland-0}; else RT=$W/run; WL=; fi
env -u DBUS_SESSION_BUS_ADDRESS -u DISPLAY ${WL:+WAYLAND_DISPLAY=$WL} ${DEVKIT:+DEVKIT=1} HOME=$H XDG_CONFIG_HOME=$H/.config XDG_DATA_HOME=$H/.local/share \
  XDG_CACHE_HOME=$H/.cache XDG_STATE_HOME=$H/.local/state XDG_RUNTIME_DIR=$RT DEVSHOT_OUT=$OUT SETTINGS="${SETTINGS:-}" FAKE_POWER="${FAKE_POWER:-}" VSIZE="${VSIZE:-1600x900}" ${PARCHAOS_PROC:+PARCHAOS_PROC=$PARCHAOS_PROC} PARCHAOS_GLASS_JS=$REPO/packaging/parchaos-glass/glass.js ${EXTRAENV:-} \
  timeout "${2:-90}" dbus-run-session -- bash "$W/inner.sh"
cp "$W/shell.log" "$OUT/shell.log"; echo "out: $OUT (log $OUT/shell.log)"
