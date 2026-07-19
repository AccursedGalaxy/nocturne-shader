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
