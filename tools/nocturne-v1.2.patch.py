#!/usr/bin/env python3
"""Photon Nocturne v1.2 performance patch (apply to a clean v1.1 tree).

Source: Photon Nocturne v1.1.zip
sha256 d43ed6ec5acb0541adb6dc5c2b2f11d35dda0e11bf809c952483cbc0a88e3eda

Changes (cost-attribution driven, 2026-07-19 experiment runs):
  1. VL fog march: max steps 25 -> 16 (half-res + dithered light shafts are
     low-frequency; density integral is unaffected — it converges with step
     count, only shadow-shaft edges could change).
  2. VL fog march: early-exit once transmittance is saturated (opaque fog
     stops contributing; remaining steps were wasted work).
  3. FXAA off by default: it ran AFTER TAA (already anti-aliased) and before
     CAS (re-sharpens); removing it saves a full-screen pass and yields a
     slightly sharper image. Re-enable anytime via the Post-Processing menu.

Every replacement must match exactly once or the script aborts.
Run from the pack root: python3 tools/nocturne-v1.2.patch.py
"""

import sys

FILES = {
    "shaders/include/fog/overworld/constants.glsl": [
        (
            "const uint air_fog_max_step_count = 25;",
            "const uint air_fog_max_step_count = 16;",
        ),
    ],
    "shaders/include/fog/overworld/raymarched.glsl": [
        (
            "        transmittance *= step_transmittance;\n    }",
            "        transmittance *= step_transmittance;\n"
            "\n"
            "        // fog ahead is already opaque - nothing further contributes\n"
            "        if (max_of(transmittance) < 0.01) {\n"
            "            break;\n"
            "        }\n"
            "    }",
        ),
    ],
    "shaders/settings.glsl": [
        ("  #define FXAA\n", "//#define FXAA\n"),
        ("PHOTON NOCTURNE v1.1", "PHOTON NOCTURNE v1.2"),
    ],
    "shaders/lang/en_US.lang": [
        (
            "option.INFO                            = §5Photon Nocturne v1.1§r",
            "option.INFO                            = §5Photon Nocturne v1.2§r",
        ),
    ],
}


for path, edits in FILES.items():
    src = open(path).read()
    for old, new in edits:
        if src.count(old) != 1:
            sys.exit(f"ABORT: {src.count(old)} matches in {path} for: {old!r}")
        src = src.replace(old, new)
    open(path, "w").write(src)
    print(f"{path}: {len(edits)} edits OK")
