#!/usr/bin/env python3
"""Photon Nocturne v1.1 performance patch.

Applies the v1.1 perf defaults to a clean Photon Nocturne v1.0 tree
(source zip sha256 71b65e7eb8d804c56e1a27adecb13c460b15b8a4e6d43297920b68d1979849d5).
Every replacement must match exactly once or the script aborts.

Run from the pack root: python3 tools/nocturne-v1.1.patch.py
"""

import sys

EDITS = [
    # C1 — cloud raymarch step cuts (the only candidate fps win)
    (
        "#define CLOUDS_CUMULUS_PRIMARY_STEPS_H 40 //",
        "#define CLOUDS_CUMULUS_PRIMARY_STEPS_H 32 //",
    ),
    (
        "#define CLOUDS_CUMULUS_PRIMARY_STEPS_Z 20 //",
        "#define CLOUDS_CUMULUS_PRIMARY_STEPS_Z 16 //",
    ),
    (
        "#define CLOUDS_CUMULUS_CONGESTUS_PRIMARY_STEPS 20 //",
        "#define CLOUDS_CUMULUS_CONGESTUS_PRIMARY_STEPS 16 //",
    ),
    (
        "#define CLOUDS_ALTOCUMULUS_PRIMARY_STEPS_H 12 //",
        "#define CLOUDS_ALTOCUMULUS_PRIMARY_STEPS_H 10 //",
    ),
    (
        "#define CLOUDS_ALTOCUMULUS_PRIMARY_STEPS_Z 6 //",
        "#define CLOUDS_ALTOCUMULUS_PRIMARY_STEPS_Z 5 //",
    ),
    (
        "#define CLOUDS_CUMULUS_LIGHTING_STEPS 6 //",
        "#define CLOUDS_CUMULUS_LIGHTING_STEPS 5 //",
    ),
    (
        "#define CLOUDS_CUMULUS_CONGESTUS_LIGHTING_STEPS 6 //",
        "#define CLOUDS_CUMULUS_CONGESTUS_LIGHTING_STEPS 5 //",
    ),
    # C3 — contact-shadow trim
    ("#define SHADOW_SSRT_STEPS 10 //", "#define SHADOW_SSRT_STEPS 8 //"),
    # C4 — SSS march trim
    ("#define SSS_STEPS 12 //", "#define SSS_STEPS 10 //"),
    # version banner
    ("PHOTON NOCTURNE v1.0", "PHOTON NOCTURNE v1.1"),
]

LANG_EDITS = [
    (
        "option.INFO                            = §5Photon Nocturne§r",
        "option.INFO                            = §5Photon Nocturne v1.1§r",
    ),
]


def apply(path, edits):
    src = open(path).read()
    for old, new in edits:
        if src.count(old) != 1:
            sys.exit(f"ABORT: {src.count(old)} matches for: {old!r}")
        src = src.replace(old, new)
    open(path, "w").write(src)
    print(f"{path}: {len(edits)} edits OK")


apply("shaders/settings.glsl", EDITS)
apply("shaders/lang/en_US.lang", LANG_EDITS)
