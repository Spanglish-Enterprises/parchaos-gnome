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

echo "== license metadata =="
# Every package states a real SPDX license and ships its license text.
for spec in packaging/*/*.spec; do
    grep -qE '^License:.*NOASSERTION' "$spec" && fail "$spec: License is NOASSERTION"
    grep -q '^%license ' "$spec" || fail "$spec: no %license file"
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

echo "== Python unit tests =="
for t in packaging/*/tests/test_*.py; do
    [ -e "$t" ] || continue
    python3 "$t" || fail "$t"
done

echo "== Parcher natural-language search (C unit test) =="
if command -v gcc >/dev/null 2>&1 && pkg-config --exists glib-2.0; then
    nl=$(mktemp -d)
    # The test builds the parser exactly as the patch ships it.
    python3 - "$nl" <<'PY' || fail "could not read the parser out of the Parcher patch"
import re, sys
out = sys.argv[1]
patch = open('packaging/parcher/0005-natural-language-search.patch', encoding='utf-8').read()
for block in re.split(r'(?m)^(?=diff --git )', patch):
    m = re.match(r'diff --git a/src/(parcher-natural-search\.[ch]) ', block)
    if not m or 'new file mode' not in block:
        continue
    body = block.split('\n@@', 1)[1].split('\n', 1)[1]
    lines = [l[1:] for l in body.split('\n') if l.startswith('+')]
    open(f'{out}/{m.group(1)}', 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
PY
    if gcc -Wall -Wextra -Werror -I"$nl" -o "$nl/t" packaging/parcher/tests/natural-search-test.c \
        $(pkg-config --cflags --libs glib-2.0) && TZ=America/Chicago "$nl/t"; then :; else
        fail "packaging/parcher/tests/natural-search-test.c"
    fi
    rm -rf "$nl"
else
    echo "skipped (needs gcc and glib2-devel)"
fi

echo "== file-type icon mapping =="
python3 -B packaging/parchaos-icon-theme/parchaos-icons/mime-map.py --self-test || fail mime-map

echo "== GNOME Shell extension JavaScript syntax =="
# GNOME Shell loads extensions as ES modules, which are strict mode (`interface`,
# `package`, `let` as a name... are reserved). Node parses a plain .js file as
# sloppy-mode CommonJS unless it happens to detect ESM syntax, so check a copy
# named .mjs to get the same rules the Shell applies. The smoke-test extension
# is included: a syntax error there (`const interface = ...`) meant the whole
# smoke test silently never ran, and this check used to skip scripts/.
# Without node, gjs (part of GNOME) parses the same code as an ES module.
js_tmp=$(mktemp -d)
cat > "$js_tmp/parse.js" <<'JS'
const text = new TextDecoder().decode(imports.gi.GLib.file_get_contents(ARGV[0])[1]);
try { Reflect.parse(text, {target: 'module'}); } catch (e) { print(`${ARGV[0]}: ${e.message}`); }
JS
have_js=1
command -v node >/dev/null 2>&1 || command -v gjs >/dev/null 2>&1 || { echo "skipped (needs node or gjs)"; have_js=0; }
while [ "$have_js" = 1 ] && IFS= read -r js; do
    if command -v node >/dev/null 2>&1; then
        cp "$js" "$js_tmp/check.mjs"
        node --check "$js_tmp/check.mjs" 2>&1 | head -5 | grep . && fail "$js"
    else
        gjs "$js_tmp/parse.js" "$js" 2>&1 | head -5 | grep . && fail "$js"
    fi
done < <(find packaging scripts/smoke \( -path 'packaging/*/files/*' -o -path 'scripts/smoke/*' \) -name '*.js')
rm -rf "$js_tmp"

echo "== no macOS-comparison narratives =="
# Ticket #102: ADDED lines in packaging/**, docs/** and README.md must not
# narrate macOS fidelity (trade-dress risk); pre-existing text is cleaned
# up separately. Allow-listed as nominative/rationale: the naming-policy
# doc, trademark-rationale wording (replaced/renamed/trademark/...), terms
# that sit inside quotes or backticks (icon file names, sed replacements),
# and the icon-theme's de-apple-ing scripts and README, which exist to
# discuss exactly those names.
narrative_lines=""
if [ -d .git ]; then
    narrative_range=HEAD
    # In CI, compare against the pushed/PR base so "new lines" is non-empty.
    if [ -n "${GITHUB_EVENT_PATH:-}" ] && [ -f "${GITHUB_EVENT_PATH}" ]; then
        narrative_base=$(python3 - "$GITHUB_EVENT_PATH" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
sha = (d.get("pull_request") or {}).get("base", {}).get("sha") or d.get("before") or ""
if sha and set(sha) != {"0"}:
    print(sha)
PY
)
        if [ -n "$narrative_base" ] && git fetch -q --depth=1 origin "$narrative_base" 2>/dev/null; then
            narrative_range=$narrative_base
        fi
    fi
    # Lines added relative to that base (empty on a clean tree at HEAD).
    narrative_lines=$(git diff --unified=0 "$narrative_range" -- packaging docs README.md 2>/dev/null |
        awk '/^\+\+\+ / { f = ($0 ~ /^\+\+\+ b\//) ? substr($0, 7) : ""; next }
             /^\+/ && f != "" { print f ": " substr($0, 2) }' || true)
    # Untracked files are new in their entirety.
    narrative_new=$(while IFS= read -r f; do
        [ -f "$f" ] && awk -v f="$f" '{ print f ": " $0 }' "$f"
    done < <(git ls-files --others --exclude-standard -- packaging docs README.md 2>/dev/null) || true)
    if [ -n "$narrative_new" ]; then
        narrative_lines="${narrative_lines}
${narrative_new}"
    fi
fi
if [ -n "$narrative_lines" ]; then
    bad=$(printf '%s\n' "$narrative_lines" |
        grep -Ei 'macOS|Apple|Finder|Spotlight|Launchpad|iCloud|Safari|genie' |
        grep -vEi '^docs/DEVELOPMENT\.md: .*(naming|approved|policy|Apple-|not renamed|renamed from)' |
        grep -vEi 'trademark|trade dress|naming policy|instead of|in place of|replac|remov|renam|copied|reproduce|original artwork' |
        grep -vEi "[\`'\"][^\`'\"]*(macos|apple|finder|spotlight|launchpad|icloud|safari)[^\`'\"]*[\`'\"]" |
        grep -vE '^packaging/parchaos-icon-theme/parchaos-icons/' ||
        true)
    [ -z "$bad" ] || { echo "$bad"; fail macos-narrative; }
fi

echo "== spec changelog headers =="
if grep -n '^%%*changelog' packaging/*/*.spec | grep -v ':%changelog$'; then
    echo "a spec has a garbled %changelog header (must be exactly %changelog)"
    fail=1
fi

echo "== packages.sh vs parchaos-desktop Requires =="
# Every non-comment, non-conditional package in packages.sh should appear
# in the meta-package's Requires list.
mapfile -t pkg_list < <(grep -vE '^\s*#|^\s*$|^\s*if |^\s*fi\b|^\s*\[|^\s*then' profiles/parchaos/packages.sh | grep -oE '^[a-z0-9][a-z0-9+._-]*' | sort -u)
mapfile -t req_list < <(grep '^Requires:' packaging/parchaos-desktop/parchaos-desktop.spec | sed 's/^Requires:\s*//' | sort -u)
missing=()
for pkg in "${pkg_list[@]}"; do
    grep -qx "$pkg" <<<"${req_list[*]}" || missing+=("$pkg")
done
[ ${#missing[@]} -eq 0 ] || { echo "Missing from Requires: ${missing[*]}"; fail packages-requires; }

[ $status -eq 0 ] && echo "All checks passed."
exit $status
