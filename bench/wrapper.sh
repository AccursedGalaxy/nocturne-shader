#!/bin/sh
# Prism WrapperCommand for NocturneBench.
# The orchestrator (bench/run.py) writes bench/run.env before each launch to
# select the MangoHud config for that run. No run.env -> launch untouched.
BENCH="$(dirname "$(readlink -f "$0")")"
if [ -f "$BENCH/run.env" ]; then
    . "$BENCH/run.env"
fi
if [ -n "$NBENCH_MANGOHUD_CONF" ] && command -v mangohud >/dev/null 2>&1; then
    export MANGOHUD_CONFIGFILE="$NBENCH_MANGOHUD_CONF"
    exec mangohud --dlsym "$@"
fi
exec "$@"
