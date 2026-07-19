# Photon Nocturne v1.0

A moody, atmospheric edit of **Photon v1.3b** by SixthSurge.
Edit tuned 2026-07-19 for the CoupleTime pack. Water is stock Photon — untouched.

## What changed (all in `shaders/settings.glsl`)

### Color grading — cinematic teal & orange
| Setting | Stock | Nocturne |
|---|---|---|
| GRADE_BRIGHTNESS | 1.00 | 0.97 |
| GRADE_CONTRAST | 1.00 | 1.12 |
| GRADE_SATURATION | 1.00 | 0.96 |
| GRADE_WHITE_BALANCE | 6500 | 6200 (cooler) |
| GRADE_ORANGE_SAT_BOOST | 0.00 | 0.12 |
| GRADE_TEAL_SAT_BOOST | 0.10 | 0.22 |
| GRADE_GREEN_SAT_BOOST | 0.00 | −0.08 (muted foliage) |
| GRADE_GREEN_HUE_SHIFT | 0.0 | 3.0 (greens toward teal) |
| PURKINJE_SHIFT_INTENSITY | 1.00 | 1.20 (bluer, darker nights) |
| VIGNETTE_INTENSITY | 1.00 | 1.30 |
| BLOOM_INTENSITY | 1.00 | 1.15 |

### Lighting — softer sun, deeper shadows, cozy torchlight
- SUN_I 0.90, noon blue 0.96, evening G/B 0.93/0.85 (golden dusks)
- MOON tint 0.70/0.80/1.00 at intensity 0.90 (bluer moonlight)
- BLOCKLIGHT 1.00/0.68/0.48 at intensity 1.10 (warm ember glow)
- SKYLIGHT_I 0.95 · CAVE_LIGHTING_I 0.85 · SHADING_STRENGTH 1.05
- CLOUD_SHADOWS_INTENSITY 0.90

### Sky — heavier skies, rich nights
- Cloud coverage up: cumulus 1.10 (density 1.05), altocumulus 1.10, cirrus 1.15
- Stars 1.30 intensity / 0.65 coverage · GALAXY enabled at 1.10
- Auroras now appear rarely in normal biomes (stock: never)
- Atmosphere saturation boost 1.15 · Crepuscular rays 1.20

### Fog — hazy air (water fog untouched)
- OVERWORLD_FOG_INTENSITY 1.20 · BLOOMY_FOG enabled at 1.2
- Mie haze: morning 0.0095, noon 0.0004, evening 0.0075, midnight 0.0070, blue hour 0.0035

Everything remains adjustable in-game — these are just new defaults, so the
sliders in Shader Pack Settings show Nocturne values as the starting point.

## Credits
- Base shader: Photon by SixthSurge (see LICENSE)
- Nocturne edit: Robin

---

# v1.1 — performance pass (2026-07-19)

Council-reviewed (critic: GPT-5.6-sol, 3 rounds). Motivation: session
telemetry showed the RX 6800 XT fully pinned (median 99% busy, ~238 W,
100 °C hotspot) — cloud march cost converts directly to fps and heat.

**Status: PENDING in-game acceptance.** These are new defaults, not
validated results. No fps number is claimed until measured (protocol below).
v1.0 stays in shaderpacks/ as instant rollback.

## Changed defaults (all remain in-game sliders)

| Change | Setting | v1.0 | v1.1 |
|---|---|---|---|
| C1 clouds | CLOUDS_CUMULUS_PRIMARY_STEPS_H / _Z | 40 / 20 | 32 / 16 |
| C1 clouds | CLOUDS_CUMULUS_CONGESTUS_PRIMARY_STEPS | 20 | 16 |
| C1 clouds | CLOUDS_ALTOCUMULUS_PRIMARY_STEPS_H / _Z | 12 / 6 | 10 / 5 |
| C1 clouds | CUMULUS / CONGESTUS _LIGHTING_STEPS | 6 / 6 | 5 / 5 |
| C3 contact shadows | SHADOW_SSRT_STEPS | 10 | 8 |
| C4 subsurface | SSS_STEPS | 12 | 10 |

Dropped from the pass: SSR_INTERSECTION_STEPS_ROUGH (stays 8) — inert under
default settings (rough SSR branch only compiles with SPECULAR_MAPPING +
labPBR pack; water is guarded by `if (!is_water)` and always uses the smooth
path). Changing it risked an untested behavior change for zero gain.
**No SSR or water value differs from v1.0.**

## If something looks off — symptom → one slider

| Symptom | Restore (Shader Pack Settings) |
|---|---|
| Cloud banding at horizon | Sky → Clouds → Cumulus → Primary Steps H → 40 |
| Cloud banding overhead | ... Primary Steps Z → 20 |
| Cloud shimmer/ghosting on fast pans | both of the above |
| Dark/flickery cloud undersides | Lighting Steps → 6 |
| Shadow gaps at object bases | Lighting → Shadows → SSRT Steps → 10 |
| Foliage/skin backlight stepping | Lighting → Shadows → SSS Steps → 12 |

## If fps still tanks — opt-in levers (not defaults)

1. Post-Processing → TAAU + render scale 0.75 (~big win, softens image).
2. Lighting → Shadows → Entity Shadows OFF (entity-heavy bases).

## Acceptance runs (to do in-game, per change)

Stages: C1 sliders only → scenes V1 day horizon clouds, V2 zenith, V4 fast
360° pans day+dusk; C3 only → V5 low-sun long shadows + object bases; C4
only → V3 sunrise/sunset backlit foliage + a mob; combined → V6 night
fog/blocklight/stars sweep. Frame-time A/B via MangoHud CSVs (perflogs/,
Shift+F2; interleave v1.0/v1.1 runs, 60 s warm-up, compare median + 1% low;
≥3% median improvement before any fps number is written here).

## Provenance

Source: Photon Nocturne v1.0.zip
sha256 71b65e7eb8d804c56e1a27adecb13c460b15b8a4e6d43297920b68d1979849d5.
Patch: tools/nocturne-v1.1.patch.py (in this zip; asserts every edit
matches exactly once). Files changed vs v1.0: shaders/settings.glsl,
shaders/lang/en_US.lang, NOCTURNE.md, + added tools/. The v1.1 zip's own
sha256 is published next to it as "Photon Nocturne v1.1.zip.sha256" (a zip
cannot contain its own hash).

---

# v1.2 — measured optimization round 1 (2026-07-19)

Driven by the cost-attribution experiments (6 in-game runs, perflogs/
experiment): baseline 6.65 ms median; VL fog and clouds each ~0.69 ms
(10.4%); shadows/SSR at the noise floor; GTAO free; ~63% of the frame is
the base render.

## Changes
1. VL fog march capped at 16 steps (was 25) — light shafts are half-res,
   dithered, and low-frequency; the fog density integral is analytic and
   unaffected. (fog/overworld/constants.glsl)
2. VL fog march early-exits once transmittance saturates — steps behind
   opaque fog were pure waste. Free win. (fog/overworld/raymarched.glsl)
3. FXAA off by default — it ran after TAA (already anti-aliased) and
   before CAS (re-sharpens). One full-screen pass saved, slightly sharper
   image. QUALITY-POSITIVE. Re-enable: Post-Processing → FXAA.

## Acceptance (pending)
- Perf: median frametime v1.2 < v1.1 by ≥3% on matched-environment
  sessions (perfbench compare), else no claim ships.
- Quality: V6 night-fog scene (shaft banding at fog edges is the one risk
  from change 1), plus edge crawl check on high-contrast edges (change 3).

## Provenance
Source: Photon Nocturne v1.1.zip sha256 d43ed6ec5acb0541adb6dc5c2b2f11d3
5dda0e11bf809c952483cbc0a88e3eda; patch: tools/nocturne-v1.2.patch.py
(in this zip). v1.2 zip sha256: sibling .sha256 file.
