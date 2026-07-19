#!/usr/bin/env python3
"""Reflection-artifact metric for the grain-mirror scene.

Splits the gold-face ROI into column bands and compares high-frequency
energy (mean absolute Laplacian of luminance) per band between a
reflections-on and a reflections-off shot of the same build. Reflection
artifacts (speckle, ladder echoes, hall-of-mirrors recursion) are
spatially localized, so the verdict is the WORST band ratio, not the
mean. Broken build measures ~2.1; a clean build should sit near 1.0.

Usage: metric_mirror.py <shot_on.png> <shot_off.png>
Exits 0 iff the worst band ratio <= THRESHOLD.
"""

import sys

import numpy as np
from PIL import Image

# gold faces in the 3840x2160 grain-mirror framing
ROI = (1450, 890, 2750, 1340)
BAND_W = 100  # artifacts are localized: judge the worst column band
OFF_FLOOR = 1.0  # ignore bands with no meaningful off-energy (near-black)
THRESHOLD = 1.45
MIN_NIGHT_LUMA = 4.0  # scene must be dark (midnight) - guards against
MAX_NIGHT_LUMA = 60.0  # vanilla-fallback or wrong-save renders


def hf_bands(path):
    im = Image.open(path).convert("L").crop(ROI)
    a = np.asarray(im, dtype=np.float64)
    mean_luma = a.mean()
    lap = np.abs(
        4 * a[1:-1, 1:-1] - a[:-2, 1:-1] - a[2:, 1:-1] - a[1:-1, :-2] - a[1:-1, 2:]
    )
    bands = np.array(
        [
            lap[:, i : i + BAND_W].mean()
            for i in range(0, lap.shape[1] - BAND_W + 1, BAND_W)
        ]
    )
    return bands, mean_luma


def main():
    on_path, off_path = sys.argv[1], sys.argv[2]
    b_on, luma_on = hf_bands(on_path)
    b_off, luma_off = hf_bands(off_path)
    print(f"reflections ON : bands={np.round(b_on, 2)} luma={luma_on:.1f}")
    print(f"reflections OFF: bands={np.round(b_off, 2)} luma={luma_off:.1f}")
    for name, luma in (("on", luma_on), ("off", luma_off)):
        if not (MIN_NIGHT_LUMA <= luma <= MAX_NIGHT_LUMA):
            print(
                f"FAIL: {name}-shot luminance {luma:.1f} outside night range "
                f"[{MIN_NIGHT_LUMA},{MAX_NIGHT_LUMA}] - wrong scene or "
                f"shader fell back to vanilla (compile error?)"
            )
            sys.exit(1)
    if b_off.mean() < 0.5:
        print("FAIL: off-shot implausibly flat - capture broken")
        sys.exit(1)
    ratios = b_on / np.maximum(b_off, OFF_FLOOR)
    worst = float(ratios.max())
    print(f"band ratios: {np.round(ratios, 2)}")
    print(f"worst band: {worst:.3f}  (threshold {THRESHOLD})")
    if worst <= THRESHOLD:
        print("PASS: reflection-added high-frequency energy within bound")
        sys.exit(0)
    print(
        "FAIL: reflections add excessive localized high-frequency structure "
        "(speckle/ladder/recursion artifacts)"
    )
    sys.exit(1)


if __name__ == "__main__":
    main()
