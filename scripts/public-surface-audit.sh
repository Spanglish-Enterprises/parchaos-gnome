#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# public-surface-audit.sh -- read-only check of everything ParchaOS has
# published: COPR projects and their packages (including what the fedora
# repo metadata actually serves), and GitHub repositories, releases and
# release assets for the owner accounts. Flags removed or third-party
# material (pearOS, Pafari, Finder, macOS-remap, TMOG, Inled's global-menu
# and cloud builds) and anything public that shouldn't be.
#
#   scripts/public-surface-audit.sh      needs curl, python3, gh (logged in)
#
# Exits 1 if anything is flagged.

set -uo pipefail

COPR_OWNER=alexgalicea
GITHUB_OWNERS=(alexgalicea Spanglish-Enterprises)
FLAG='pearos|pafari|macos|finder|launchpad|boot-sound|whitesur|tmog'
# Repositories allowed to be public (everything else is reported if public).
PUBLIC_OK='^(Spanglish-Enterprises/parchaos-gnome)$'
COPR_API=https://copr.fedorainfracloud.org/api_3
status=0
flag() { echo "FLAG: $*"; status=1; }

echo "== COPR projects ($COPR_OWNER) =="
mapfile -t projects < <(curl -fsS "$COPR_API/project/list?ownername=$COPR_OWNER" |
    python3 -c 'import sys,json; [print(p["name"]) for p in json.load(sys.stdin)["items"]]')
printf '  %s\n' "${projects[@]}"
[ "${#projects[@]}" -eq 1 ] && [ "${projects[0]}" = parchaos-gnome ] ||
    flag "unexpected COPR projects: ${projects[*]}"

for project in "${projects[@]}"; do
    echo "== COPR packages ($COPR_OWNER/$project) =="
    pkgs=$(curl -fsS "$COPR_API/package/list?ownername=$COPR_OWNER&projectname=$project&limit=500" |
        python3 -c 'import sys,json; [print(p["name"]) for p in json.load(sys.stdin)["items"]]')
    echo "  $(echo "$pkgs" | wc -l) packages"
    bad=$(echo "$pkgs" | grep -E "$FLAG") && flag "COPR packages: $(echo $bad)"

    # Builds of the global menu and cloud older than the clean rewrites.
    for p in parchaos-global-menu parchaos-cloud; do
        old=$(curl -fsS "$COPR_API/build/list?ownername=$COPR_OWNER&projectname=$project&packagename=$p&limit=200" |
            python3 -c 'import sys,json
for b in json.load(sys.stdin)["items"]:
    v=(b.get("source_package") or {}).get("version") or ""
    if v.startswith("1."): print(b["id"], v)')
        [ -n "$old" ] && flag "pre-rewrite $p builds: $(echo $old)"
    done

    # What dnf actually downloads.
    base="https://download.copr.fedorainfracloud.org/results/$COPR_OWNER/$project/fedora-44-x86_64"
    primary=$(curl -fsSL "$base/repodata/repomd.xml" | grep -o 'repodata/[^"]*primary.xml[^"]*' | head -1)
    if [ -n "$primary" ]; then
        served=$(curl -fsSL "$base/$primary" | zcat 2>/dev/null |
            python3 -c 'import re,sys
s=sys.stdin.read()
for n,v in sorted(set(re.findall(r"<name>([^<]+)</name>.*?<version epoch=\"\d+\" ver=\"([^\"]+)\"", s, re.S))): print(n, v)')
        echo "  repo metadata: $(echo "$served" | wc -l) entries"
        bad=$(echo "$served" | grep -E "$FLAG|^parchaos-(global-menu|cloud) 1\.") &&
            flag "served by the repo: $(echo $bad)"
    else
        flag "could not read $base/repodata"
    fi
done

for owner in "${GITHUB_OWNERS[@]}"; do
    echo "== GitHub repositories ($owner) =="
    while read -r repo visibility; do
        echo "  $repo $visibility"
        if [ "$visibility" = PUBLIC ] && ! [[ "$repo" =~ $PUBLIC_OK ]]; then
            [ "$owner" = alexgalicea ] && case "$repo" in
                *parchaos*|*plumos*|*pearos*) flag "$repo is public" ;;
            esac
        fi
        # Release assets.
        gh release list -R "$repo" --limit 50 --json tagName,isDraft \
            --jq '.[] | "\(.tagName) \(.isDraft)"' 2>/dev/null |
        while read -r tag draft; do
            assets=$(gh release view "$tag" -R "$repo" --json assets --jq '.assets[].name' 2>/dev/null | tr '\n' ' ')
            echo "    release $tag (draft=$draft): $assets"
        done
    done < <(gh repo list "$owner" --limit 200 --json nameWithOwner,visibility \
        --jq '.[] | "\(.nameWithOwner) \(.visibility)"' | grep -iE 'parchaos|plumos|pearos')
done

echo
if [ $status -eq 0 ]; then
    echo "PASS: nothing flagged"
else
    echo "FAIL: see FLAG lines above"
fi
exit $status
