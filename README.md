# Nocturne

A moody edit of [Photon](https://github.com/sixthsurge/photon) by SixthSurge,
built for Minecraft 1.20.1 with Iris. Nocturne trades Photon's neutral daylight
for something darker and warmer: teal-leaning skies, golden dusks, ember-colored
torchlight, hazy mornings, and nights with visible stars and a galaxy band.

Water is untouched from stock Photon. It was already right.

## Performance

Every optimization in Nocturne is measured before it ships. Changes get A/B
tested against per-frame logs from real play sessions, and anything that
does not beat the noise floor gets reverted. So far, compared to the base
look edit on a Radeon RX 6800 XT at 1440p:

- cloud raymarch steps cut about 20% (no visible difference after temporal
  accumulation)
- fog march capped at 16 steps with an early exit once fog turns opaque
- FXAA removed from the default chain, since TAA already covers it and the
  image comes out slightly sharper

Measured result across both rounds: about 5% higher average fps and an 8%
better 1% low, with identical visuals. Modest, honest numbers. More rounds
are planned; the goal is to keep or improve quality while making it
substantially faster.

## Install

1. Grab the zip from [Releases](../../releases).
2. Drop it into your `shaderpacks` folder.
3. Select it in Iris (Options > Video Settings > Shader Packs).

Tested with Iris 1.7.6 on Fabric, Minecraft 1.20.1. Anything Photon v1.3b
runs on should work.

All the original Photon settings remain available in the shader options
menu. Nocturne only changes defaults, so if you disagree with a choice,
the slider is still there.

## Versions

- v1.0: the look edit. 44 changed defaults across grading, lighting, sky,
  and fog.
- v1.1: performance defaults, reviewed before release. Cloud steps, contact
  shadows, subsurface scattering.
- v1.2: fog march cap and early exit, FXAA off. First release with measured
  frame-time verification.

## Credits and license

Nocturne is a derivative of Photon Shaders, copyright SixthSurge. The
original license is included in this repository and applies here.

Per Photon's license, Nocturne is not distributed on monetized platforms
(Modrinth, CurseForge) and never will be without SixthSurge's written
permission. If you like this pack, go star Photon. The hard parts are his.
