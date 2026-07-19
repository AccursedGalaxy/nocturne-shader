# nocturne bench — unattended shader screenshot & perf pipeline

Launches Minecraft (dedicated lean **NocturneBench** Prism instance: Fabric
1.20.1 + Sodium + Iris only), loads a baked scene save, renders on an
**invisible 4K headless Wayland output**, captures true-3840×2160
screenshots, logs per-frame times with MangoHud, and writes a report.
Zero in-game input; nothing appears on the real monitor (focus is borrowed
for ~1 s per launch to fullscreen the window on the headless output).

## Quick start

```sh
bench/nb list                                          # scene library
bench/nb run --shaders "Photon Nocturne.zip" --scenes all --mode both
bench/nb run --shaders "Photon Nocturne.zip,photon_v1.3b.zip" \
             --scenes V1,V6 --mode perf --duration 60
bench/.venv/bin/python bench/report.py bench/runs/<run-dir>   # REPORT.md + gallery.html
```

- `--mode shot` — clean 4K screenshots (no MangoHud).
- `--mode perf` — MangoHud per-frame CSV (overlay visible; `no_display`
  breaks the GL logger, so perf sessions never take screenshots).
- `--mode both` — expands to a shot session **plus** a perf session.

## How it works

| Piece | Mechanism |
|---|---|
| Launch | `prismlauncher -l NocturneBench -w <save>` (quickplay straight into the world) |
| Scene | save baked by `scene.py` (nbtlib): fixed seed, spectator player at pos/yaw/pitch, DayTime, daylight/weather/mob-spawn frozen, peaceful |
| Display | `hyprctl output create headless NBENCH` @ 3840×2160; window sent to workspace `nbench` on it and fullscreened |
| Screenshot | `grim -o NBENCH` (game is fullscreen → capture *is* the framebuffer) |
| Perf | Prism WrapperCommand → `wrapper.sh` reads `run.env` → `mangohud --dlsym`, autostart CSV logging after 15 s |
| Exit | `hyprctl dispatch closewindow` (clean quit), SIGTERM/SIGKILL fallback |
| Detection | game = java process whose `/proc/<pid>/cwd` is the instance's minecraft dir (Prism passes params via stdin) |

Scene *templates* live in `bench/worlds/<scene>/` (gitignored; region files
are chunk cache). Each run copies the template into the instance's `saves/`
so runs never mutate it. `nb prewarm` runs on the template itself
(symlinked) so generated chunks persist; re-bake restores the canonical
viewpoint afterwards.

## Scenes

Defined in `scenes.json`: `name`, `seed`, `pos [x,y,z]`, `rot [yaw,pitch]`,
`time` (0 dawn / 6000 noon / 12500 dusk / 18000 midnight), optional
`weather: rain`. Player is a spectator — no HUD, no hand, can float
anywhere. `nb scout --points "x,z;..." --pan` screenshots candidate
viewpoints (shared chunk-cache template) for curating new scenes.

## Perf analysis

`report.py` trims each CSV to the measurement window (wall-clock stamps in
`meta.json` vs MangoHud's `elapsed`), prints median/p95/p99/1 %-low, and
A/B-compares shaders per scene with a chunked-bootstrap 95 % CI
(SIGNIFICANT vs NOISE) — same method as the CoupleTime `perflogs/perfbench`
harness. Acceptance gates for shader releases stay as in `NOCTURNE.md`
(≥3 % median frametime, no worse 1 % low).

## Caveats

- One game at a time; the run aborts if a NocturneBench java is alive.
- Perf numbers are only comparable between runs on an idle GPU — don't
  game while a perf run is active (screenshots are fine).
- First-ever launch may download assets; window-wait timeout is 180 s.
- The Prism GUI window may appear on first CLI launch; harmless.
- Bench instance renderDistance 17, vsync off, sound muted, matches
  CoupleTime's graphics options otherwise.
