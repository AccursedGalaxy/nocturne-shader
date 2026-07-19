#!/bin/bash
# Deploy Nocturne to Prism instances under the stable name "Photon Nocturne.zip".
#
#   ./deploy.sh                     build HEAD -> CoupleTime
#   ./deploy.sh v1.2                build a tag/commit -> CoupleTime
#   ./deploy.sh v1.2 Homestead      -> a specific instance
#   ./deploy.sh v1.2 --all          -> every instance that has a shaderpacks dir
#   ./deploy.sh --list              show what's installed where
#
# The filename never changes, so Iris keeps the pack selected and your
# slider settings ("Photon Nocturne.zip.txt") survive every update and
# rollback. The deployed version is stamped into version.txt inside the
# zip and into a .sha256 sidecar.
set -euo pipefail
cd "$(dirname "$0")"

INSTANCES_DIR="$HOME/.local/opt/prismlauncher/instances"
NAME="Photon Nocturne.zip"

if [[ "${1:-}" == "--list" ]]; then
    for sp in "$INSTANCES_DIR"/*/minecraft/shaderpacks; do
        inst=$(basename "$(dirname "$(dirname "$sp")")")
        if [[ -f "$sp/$NAME" ]]; then
            ver=$(unzip -p "$sp/$NAME" version.txt 2>/dev/null || echo "unknown (pre-deploy.sh zip)")
            echo "$inst: $ver"
        else
            echo "$inst: not installed"
        fi
    done
    exit 0
fi

REF="${1:-HEAD}"
shift || true

TARGETS=()
if [[ "${1:-}" == "--all" ]]; then
    for sp in "$INSTANCES_DIR"/*/minecraft/shaderpacks; do
        TARGETS+=("$(basename "$(dirname "$(dirname "$sp")")")")
    done
elif [[ $# -gt 0 ]]; then
    TARGETS=("$@")
else
    TARGETS=(CoupleTime)
fi

DESC=$(git describe --tags --always "$REF")
if [[ "$REF" == "HEAD" ]] && ! git diff --quiet HEAD -- shaders LICENSE NOCTURNE.md 2>/dev/null; then
    echo "WARNING: uncommitted changes are NOT included (git archive builds from the commit)"
    DESC="${DESC}(+uncommitted-ignored)"
fi

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
git archive "$REF" | tar -x -C "$TMP"
printf '%s (commit %s, deployed %s)\n' "$DESC" "$(git rev-parse --short "$REF")" "$(date +%F)" > "$TMP/version.txt"
( cd "$TMP" && zip -q -r pack.zip shaders LICENSE NOCTURNE.md version.txt $( [[ -d tools ]] && echo tools ) -x '*/__pycache__/*' )

for inst in "${TARGETS[@]}"; do
    sp="$INSTANCES_DIR/$inst/minecraft/shaderpacks"
    if [[ ! -d "$sp" ]]; then
        echo "SKIP $inst: no shaderpacks dir at $sp"
        continue
    fi
    cp "$TMP/pack.zip" "$sp/$NAME"
    ( cd "$sp" && sha256sum "$NAME" > "$NAME.sha256" )
    echo "$inst: installed $DESC as \"$NAME\""
done
