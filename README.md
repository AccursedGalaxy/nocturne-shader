# Nocturne Shader

Robin's moody, performance-tuned Minecraft shader, evolved from
[Photon](https://github.com/sixthsurge/photon) v1.3b by SixthSurge
(see LICENSE — personal-modification terms).

- **Look**: teal-orange cinematic grade, cool white balance, warm ember
  blocklight, hazy fog, galaxy nights. Water is stock Photon.
- **Perf discipline**: every optimization is measured before it ships.
  The harness lives in the CoupleTime instance's `perflogs/`
  (`perfbench` for session A/B with CI verdicts, `experiment` for
  subsystem cost attribution, `RESULTS.md` for the record).

## Workflow

1. Edit shader source (`shaders/`), one logical change per commit.
2. `./build.sh` → installs a versioned zip into the shaderpacks folder
   (a dirty tree is labeled `-dirty`, so measurements always trace to a
   commit).
3. Play a session on it; `perflogs/perfbench compare` old vs new.
4. Record verdict in `perflogs/RESULTS.md` (link the commit hash).
   Quality gate: NOCTURNE.md scene matrix — same or better, always.

## History

- `photon-v1.3b` tag — unmodified upstream
- `v1.0` — look edit (44 setting defaults)
- `v1.1` — council-reviewed perf defaults (clouds −20% steps, etc.)
- `v1.2` — fog march cap + early-exit, FXAA off (measured: median −2.1%,
  p99 −8.2%)

Cost map (2026-07-19, 1440p RX 6800 XT, baseline 6.65 ms): VL fog 0.69 ·
clouds 0.69 · shadows ~0.56 · SSR ~0.52 · GTAO ~0 · base render ~4.2 ms
(63%) — round 2 targets the base render.
