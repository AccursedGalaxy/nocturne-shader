#!/bin/bash
# Verify gate for the reflection-artifact fix (grain-mirror scene).
#
# Builds the shader pack from THIS CHECKOUT'S WORKING TREE (uncommitted
# edits included - works from driver-agent worktrees), installs it into
# the NocturneBench instance, renders Robin's exact recursion viewpoint
# twice (reflections on / off via Iris settings override), and gates on
# metric_mirror.py. Fails on shader compile errors in the game log.
# The capture pipeline itself always runs from the canonical bench dir
# (worktree checkouts lack the gitignored .venv/worlds/runs).
# Exit 0 = artifact within bound, exit 1 = still present/broken.
set -euo pipefail

TREE="$(cd "$(dirname "$0")/.." && pwd)"     # this checkout (maybe a worktree)
BENCH="$HOME/dev/nocturne-shader/bench"      # canonical pipeline
SP="$HOME/.local/opt/prismlauncher/instances/NocturneBench/minecraft/shaderpacks"
TXT="$SP/Photon Nocturne.zip.txt"
LOG="$HOME/.local/opt/prismlauncher/instances/NocturneBench/minecraft/logs/latest.log"

# leftover bench game blocks the runner
for pid in $(pgrep -x java || true); do
    if [[ "$(readlink /proc/$pid/cwd 2>/dev/null)" == *NocturneBench* ]]; then
        kill -9 "$pid" 2>/dev/null || true
    fi
done
sleep 2

# build from the working tree - NOT git archive (uncommitted edits count)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
( cd "$TREE" && zip -q -r "$TMP/pack.zip" shaders LICENSE -x '*/__pycache__/*' )
printf 'verify_mirror tree build %s\n' "$(date +%F-%T)" > "$TMP/version.txt"
( cd "$TMP" && zip -q pack.zip version.txt )
cp "$TMP/pack.zip" "$SP/Photon Nocturne.zip"

cd "$BENCH"

shoot() { # $1 = on|off
    ./nb run --shaders "Photon Nocturne.zip" --scenes grain-mirror --mode shot 2>&1 | tail -1
    if grep -q "SHADER COMPILER, type=ERROR" "$LOG"; then
        echo "FAIL: shader compile errors in game log ($1 shot)"
        grep -m3 "SHADER COMPILER, type=ERROR" "$LOG"
        exit 1
    fi
    local run
    run=$(ls -td runs/*-run | head -1)
    cp "$run/Photon_Nocturne.zip/grain-mirror/shot-00.png" "/tmp/verify-mirror-$1.png"
}

rm -f "$TXT"
shoot on

printf 'ENVIRONMENT_REFLECTIONS=false\n' > "$TXT"
shoot off
rm -f "$TXT"

.venv/bin/python metric_mirror.py /tmp/verify-mirror-on.png /tmp/verify-mirror-off.png
