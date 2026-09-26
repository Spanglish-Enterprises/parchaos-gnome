#!/bin/bash
# Static checks for the repository. Runs in CI on every push and pull
# request, and locally: scripts/lint.sh
#
# Needs: shellcheck, rpm-build (rpmspec), glib2 (glib-compile-schemas),
# desktop-file-utils, python3, nodejs.

set -u
cd "$(dirname "$0")/.."
status=0
fail() { echo "FAIL: $*"; status=1; }

echo "== shellcheck (errors) =="
# Profile scripts are sourced by engine/build-iso.sh, so they have no
# shebang; check them as bash.
shellcheck --shell=bash -S error engine/*.sh profiles/*/*.sh || fail shellcheck-profiles
mapfile -t helpers < <(grep -rlE '^#!/(usr/)?bin/(env )?(ba)?sh' packaging/*/files scripts 2>/dev/null)
[ ${#helpers[@]} -eq 0 ] || shellcheck -S error "${helpers[@]}" || fail shellcheck-helpers

echo "== rpmspec parse =="
for spec in packaging/*/*.spec; do
    rpmspec -P "$spec" >/dev/null 2>&1 || { rpmspec -P "$spec" 2>&1 | tail -3; fail "$spec"; }
done

echo "== GSettings schemas =="
while IFS= read -r schema; do
    dir=$(mktemp -d)
    cp "$schema" "$dir/"
    glib-compile-schemas --strict --dry-run "$dir" || fail "$schema"
    rm -rf "$dir"
done < <(find packaging -name '*.gschema.xml')

echo "== desktop files =="
while IFS= read -r desktop; do
    out=$(desktop-file-validate "$desktop" 2>&1 | grep -i 'error') && { echo "$out"; fail "$desktop"; }
done < <(find packaging -name '*.desktop')

echo "== Python syntax =="
mapfile -t pyfiles < <({ find packaging scripts -name '*.py'; grep -rlE '^#!/usr/bin/(env )?python3' packaging/*/files 2>/dev/null; } | sort -u)
[ ${#pyfiles[@]} -eq 0 ] || python3 - "${pyfiles[@]}" <<'PY' || fail python
import ast, sys
bad = 0
for path in sys.argv[1:]:
    try:
        ast.parse(open(path).read(), path)
    except SyntaxError as e:
        print(f'{path}: {e}')
        bad = 1
sys.exit(bad)
PY

echo "== GNOME Shell extension JavaScript syntax =="
while IFS= read -r js; do
    node --check "$js" 2>&1 | head -5 | grep . && fail "$js"
done < <(find packaging -path '*/files/*' -name '*.js')

[ $status -eq 0 ] && echo "All checks passed."
exit $status
