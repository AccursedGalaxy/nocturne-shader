#!/bin/bash
# Build Photon Nocturne from this repo and install it into the CoupleTime
# shaderpacks folder (zip + sibling sha256).
#
#   ./build.sh            -> version from `git describe` (e.g. v1.2-3-gabc123)
#   ./build.sh v1.3       -> explicit version name
#
# A dirty working tree gets "-dirty" appended so a measured session can
# never silently point at uncommitted code.
set -euo pipefail
cd "$(dirname "$0")"

SP="/home/aki/.local/opt/prismlauncher/instances/CoupleTime/minecraft/shaderpacks"
VER="${1:-$(git describe --tags --always)}"
git diff --quiet HEAD -- shaders LICENSE NOCTURNE.md tools 2>/dev/null || VER="${VER}-dirty"

NAME="Photon Nocturne ${VER}.zip"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

zip -q -r "$TMP/$NAME" shaders LICENSE NOCTURNE.md tools -x '*/__pycache__/*'
mv "$TMP/$NAME" "$SP/$NAME"
( cd "$SP" && sha256sum "$NAME" | tee "$NAME.sha256" )
echo "installed: $SP/$NAME  (commit $(git rev-parse --short HEAD))"
