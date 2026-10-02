#!/bin/bash
# Build source RPMs for ParchaOS packages from this repository.
#
#   scripts/build-srpm.sh [-o OUTDIR] [PACKAGE...]   default: every package
#
# For each packaging/<name>/<name>.spec: gathers the local sources (the
# package directory's own files, a *-files.tar.gz of its files/ tree when
# the spec asks for one, generated artwork for the icon theme), downloads
# remote sources, checks that every Source and Patch exists, and runs
# rpmbuild -bs. Prints the SRPM paths; exits non-zero if any package fails.
#
# Original code for ParchaOS, GPL-3.0-or-later.

set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

OUT=build/srpms
if [ "${1:-}" = -o ]; then
    OUT=$2
    shift 2
fi
mkdir -p "$OUT"
OUT=$(realpath "$OUT")

if [ $# -eq 0 ]; then
    mapfile -t all < <(find packaging -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort)
    set -- "${all[@]}"
fi

status=0
for name in "$@"; do
    dir=packaging/$name
    spec=$dir/$name.spec
    [ -f "$spec" ] || { echo "SKIP $name: no $spec"; continue; }
    top=$(mktemp -d)
    mkdir -p "$top/SOURCES"

    # Standard license texts any spec can list as a Source for %license:
    # LICENSE (GPL-3.0), LICENSE-ARTWORK (CC BY-SA 4.0) and GPL-2.0.txt.
    cp LICENSE LICENSE-ARTWORK LICENSES/GPL-2.0.txt "$top/SOURCES/"
    # The legal and privacy notice installed by parchaos-release.
    cp docs/LEGAL.md docs/SOURCES.md "$top/SOURCES/"

    # Local sources: files next to the spec, and generated artwork.
    find "$dir" -maxdepth 1 -type f ! -name '*.spec' -exec cp {} "$top/SOURCES/" \;
    [ -d "$dir/po" ] && find "$dir/po" -name '*.po' -exec cp {} "$top/SOURCES/" \;
    [ -d "$dir/files" ] && find "$dir/files" -type f -exec cp {} "$top/SOURCES/" \;
    [ -d "$dir/parchaos-icons" ] && cp "$dir"/parchaos-icons/*.svg "$dir"/parchaos-icons/*.py "$dir"/parchaos-icons/*.txt "$dir"/parchaos-icons/*.tsv "$dir"/parchaos-icons/*.ini "$top/SOURCES/" 2>/dev/null
    # Specs with a tarball of their files/ tree among the sources (always
    # rebuilt here, never reused from an earlier build).
    tarball=$(rpmspec -P "$spec" 2>/dev/null | awk '/^Source[0-9]*:/ {print $2}' | grep -- '-files\.tar\.gz$' || true)
    if [ -n "$tarball" ]; then
        tar czf "$top/SOURCES/$(basename "$tarball")" -C "$dir/files" .
    fi
    # Remote sources (http/https URLs).
    spectool -g -C "$top/SOURCES" "$spec" >/dev/null 2>&1 || true

    # Every Source/Patch must now exist.
    missing=0
    while read -r src; do
        [ -e "$top/SOURCES/$(basename "$src")" ] || { echo "MISSING $name: $src"; missing=1; }
    done < <(rpmspec -P "$spec" 2>/dev/null | awk '/^(Source|Patch)[0-9]*:/ {print $2}')
    if [ $missing -ne 0 ]; then
        status=1
        rm -rf "$top"
        continue
    fi

    if srpm=$(rpmbuild -bs --define "_topdir $top" "$spec" 2>&1 | awk '/^Wrote:/ {print $2}') && [ -n "$srpm" ]; then
        cp "$srpm" "$OUT/"
        echo "$OUT/$(basename "$srpm")"
    else
        echo "FAIL $name: rpmbuild -bs"
        status=1
    fi
    rm -rf "$top"
done
exit $status
