#!/bin/bash
# Verify gate for the reflection-artifact fix (grain-mirror scene).
#
# Deploys the CURRENT repo tree to the NocturneBench instance, renders the
# scene twice (reflections on / off via Iris settings override), and gates
# on metric_mirror.py. Also fails on any shader compile error in the game
# log. Exit 0 = fixed within bound, exit 1 = artifact still present/broken.
set -euo pipefail
cd "$(dirname "$0")"

SP="$HOME/.local/opt/prismlauncher/instances/NocturneBench/minecraft/shaderpacks"
TXT="$SP/Photon Nocturne.zip.txt"
LOG="$HOME/.local/opt/prismlauncher/instances/NocturneBench/minecraft/logs/latest.log"

# any leftover bench game blocks the runner
for pid in $(pgrep -x java || true); do
    if [[ "$(readlink /proc/$pid/cwd 2>/dev/null)" == *NocturneBench* ]]; then
        kill -9 "$pid" 2>/dev/null || true
    fi
done
sleep 2

../deploy.sh HEAD NocturneBench >/dev/null

shoot() { # $1 = label
    ./nb run --shaders "Photon Nocturne.zip" --scenes grain-mirror --mode shot 2>&1 | tail -1
    local run
    run=$(ls -td runs/*-run | head -1)
    if grep -q "SHADER COMPILER, type=ERROR" "$LOG"; then
        echo "FAIL: shader compile errors in game log ($1 shot)"
        grep -m3 "SHADER COMPILER, type=ERROR" "$LOG"
        exit 1
    fi
    cp "$run/Photon_Nocturne.zip/grain-mirror/shot-00.png" "/tmp/verify-mirror-$1.png"
}

rm -f "$TXT"
shoot on

printf 'ENVIRONMENT_REFLECTIONS=false\n' > "$TXT"
shoot off
rm -f "$TXT"

.venv/bin/python metric_mirror.py /tmp/verify-mirror-on.png /tmp/verify-mirror-off.png
