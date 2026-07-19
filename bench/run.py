#!/usr/bin/env python3
"""nocturne bench orchestrator.

Launches the NocturneBench Prism instance into baked scene saves on an
invisible 4K headless Wayland output, captures true-4K screenshots with grim,
logs per-frame times with MangoHud, and collects everything under
bench/runs/. Fully unattended: no in-game input is ever needed.

Usage (from bench/.venv/bin/python or ./bench/nb):
  run.py run --shaders "Photon Nocturne.zip" --scenes smoke --mode both
  run.py run --shaders "Photon Nocturne.zip,photon_v1.3b.zip" --scenes all \
             --mode perf --warmup 30 --duration 60
  run.py prewarm --scenes all          # generate chunks into templates
  run.py scout --points "0,0;800,0;0,800" --y 160 --time 6000
  run.py list
"""

import argparse
import datetime as dt
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

BENCH = Path(__file__).resolve().parent
sys.path.insert(0, str(BENCH))
import scene as scenelib  # noqa: E402

INSTANCE = Path.home() / ".local/opt/prismlauncher/instances/NocturneBench"
MC_DIR = INSTANCE / "minecraft"
OUTPUT = "NBENCH"
OUTPUT_POS = (6000, 0)  # far from the real monitor's coordinate space
RES = (3840, 2160)
PRISM = str(Path.home() / ".local/bin/prismlauncher")

WORLD_LOADED_RE = re.compile(
    r"logged in with entity id|Starting Program \(Compute\)|joined the game"
)


def log(msg):
    print(f"[nbench {dt.datetime.now():%H:%M:%S}] {msg}", flush=True)


# ---------------------------------------------------------------- hyprland
_HYPR_SIG = None


def _hypr_env():
    """Env with a *verified-live* Hyprland signature (the inherited one may
    be from a dead session)."""
    global _HYPR_SIG
    env = dict(os.environ)
    if _HYPR_SIG is None:
        d = Path("/run/user/%d/hypr" % os.getuid())
        candidates = [env.get("HYPRLAND_INSTANCE_SIGNATURE")] + [
            p.name
            for p in sorted(d.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
            if d.exists()
        ]
        for sig in filter(None, candidates):
            probe = dict(env, HYPRLAND_INSTANCE_SIGNATURE=sig)
            r = subprocess.run(["hyprctl", "monitors"], capture_output=True, env=probe)
            if r.returncode == 0:
                _HYPR_SIG = sig
                break
        else:
            raise RuntimeError("no live Hyprland session found")
    env["HYPRLAND_INSTANCE_SIGNATURE"] = _HYPR_SIG
    return env


def hypr(*args, json_out=False):
    cmd = ["hyprctl"] + (["-j"] if json_out else []) + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True, env=_hypr_env())
    if r.returncode != 0:
        raise RuntimeError(f"hyprctl {args} failed: {r.stderr.strip()}")
    return json.loads(r.stdout) if json_out else r.stdout.strip()


def ensure_output():
    mons = hypr("monitors", json_out=True)
    if not any(m["name"] == OUTPUT for m in mons):
        hypr("output", "create", "headless", OUTPUT)
        time.sleep(0.5)
    hypr(
        "keyword",
        "monitor",
        f"{OUTPUT},{RES[0]}x{RES[1]}@60,{OUTPUT_POS[0]}x{OUTPUT_POS[1]},1",
    )
    mons = hypr("monitors", json_out=True)
    m = next(m for m in mons if m["name"] == OUTPUT)
    assert (m["width"], m["height"]) == RES, (
        f"headless output is {m['width']}x{m['height']}"
    )
    log(f"headless output {OUTPUT} at {RES[0]}x{RES[1]} ready")


def remove_output():
    try:
        hypr("output", "remove", OUTPUT)
    except Exception:
        pass


def find_window(java_pid, timeout=30):
    """Find the Minecraft window belonging to our java process."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        for c in hypr("clients", json_out=True):
            if c.get("pid") == java_pid:
                return c["address"]
        time.sleep(1)
    return None


def window_geom(addr):
    for c in hypr("clients", json_out=True):
        if c["address"] == addr:
            return tuple(c["at"]), tuple(c["size"])
    return None, None


WORKSPACE = "name:nbench"


def place_window(addr):
    """Send the window to a dedicated workspace on the headless output and
    fullscreen it there — pixel-exact float placement of xwayland windows
    across outputs proved unreliable. Fullscreening needs focus, so focus
    is borrowed for a moment and handed straight back."""
    prev = hypr("activewindow", json_out=True).get("address")
    hypr("dispatch", "movetoworkspacesilent", f"{WORKSPACE},address:{addr}")
    hypr("dispatch", "moveworkspacetomonitor", f"{WORKSPACE} {OUTPUT}")
    for attempt in range(10):
        c = next(
            (c for c in hypr("clients", json_out=True) if c["address"] == addr),
            {},
        )
        if not c.get("fullscreen"):
            hypr("dispatch", "focuswindow", f"address:{addr}")
            hypr("dispatch", "fullscreen", "0")
            time.sleep(1)
            if prev and prev != addr:
                hypr("dispatch", "focuswindow", f"address:{prev}")
            c = next(
                (c for c in hypr("clients", json_out=True) if c["address"] == addr),
                {},
            )
        if c.get("fullscreen") and tuple(c.get("size", ())) == RES:
            log(f"window fullscreen on {OUTPUT} at {c['at']} size {c['size']}")
            return
        log(f"fullscreen not settled: at={c.get('at')} size={c.get('size')}, retry")
        time.sleep(2)
    raise RuntimeError("window never reached fullscreen 4K on " + OUTPUT)


def screenshot(addr, dest):
    """Capture the headless output — the game is fullscreen on it, above
    any bars, so the capture is exactly the 4K framebuffer."""
    subprocess.run(["grim", "-o", OUTPUT, str(dest)], check=True, env=_hypr_env())
    log(f"screenshot -> {dest}")


# ---------------------------------------------------------------- game
def set_shader(pack):
    props = MC_DIR / "config/iris.properties"
    enable = "false" if pack in (None, "off", "none") else "true"
    lines = [
        "#Iris config, managed by nocturne bench",
        "colorSpace=SRGB",
        "disableUpdateMessage=true",
        "enableDebugOptions=false",
        "maxShadowRenderDistance=8",
        f"enableShaders={enable}",
    ]
    if enable == "true":
        if not (MC_DIR / "shaderpacks" / pack).exists():
            raise SystemExit(f"shaderpack not installed: {pack}")
        lines.append(f"shaderPack={pack}")
    props.write_text("\n".join(lines) + "\n")


def write_run_env(mangohud_conf):
    env_file = BENCH / "run.env"
    if mangohud_conf:
        env_file.write_text(f"NBENCH_MANGOHUD_CONF={mangohud_conf}\n")
    else:
        env_file.unlink(missing_ok=True)


def mangohud_conf(out_dir):
    conf = out_dir / "mangohud.conf"
    conf.write_text(
        f"output_folder={out_dir}\n"
        "log_interval=0\n"
        "log_duration=14400\n"
        "autostart_log=15\n"
        "fps\n"
        "frametime\n"
        "position=top-left\n"
        "font_size=20\n"
        "background_alpha=0.4\n"
    )
    return conf


def bench_java_pid():
    """The game process: a java process whose cwd is the instance's
    minecraft dir (Prism passes launch params via stdin, so the cmdline
    doesn't name the instance reliably)."""
    r = subprocess.run(["pgrep", "-x", "java"], capture_output=True, text=True)
    for p in r.stdout.split():
        try:
            if os.readlink(f"/proc/{p}/cwd") == str(MC_DIR):
                return int(p)
        except OSError:
            continue
    return None


def wait_for_java(timeout=90):
    deadline = time.time() + timeout
    while time.time() < deadline:
        pid = bench_java_pid()
        if pid:
            return pid
        time.sleep(1)
    return None


def wait_world_loaded(log_file, log_offset, timeout):
    """Poll the instance log for the world-join marker. Returns True/False."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if log_file.exists():
            text = log_file.read_text(errors="replace")[log_offset:]
            if WORLD_LOADED_RE.search(text):
                return True
        if bench_java_pid() is None:
            raise RuntimeError(f"game process died while loading (check {log_file})")
        time.sleep(2)
    return False


def close_game(java_pid, addr, timeout=30):
    if addr:
        try:
            hypr("dispatch", "closewindow", f"address:{addr}")
        except Exception:
            pass
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not _pid_alive(java_pid):
            return
        time.sleep(1)
    log("graceful close timed out, killing")
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.kill(java_pid, sig)
        except ProcessLookupError:
            return
        time.sleep(5)
        if not _pid_alive(java_pid):
            return


def _pid_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


# ---------------------------------------------------------------- one run
def run_one(sc, shader, out_dir, mode, warmup, duration, shots, prewarm=False):
    out_dir.mkdir(parents=True, exist_ok=True)
    if bench_java_pid():
        raise SystemExit("a NocturneBench game is already running; aborting")

    save_name = scenelib.install(sc, MC_DIR / "saves", run_on_template=prewarm)
    set_shader(shader)
    # MangoHud logging needs the overlay rendered (no_display kills the GL
    # logger), so perf sessions carry the overlay and never take screenshots;
    # cmd_run expands mode=both into a shot session + a perf session.
    perf = mode == "perf" and not prewarm
    write_run_env(mangohud_conf(out_dir) if perf else None)
    autostart = 15  # keep in sync with mangohud_conf

    log_file = MC_DIR / "logs/latest.log"
    log_offset = 0  # latest.log is rotated per session; read from start

    meta = {
        "scene": sc,
        "shader": shader,
        "mode": mode,
        "warmup": warmup,
        "duration": duration,
        "res": RES,
        "mangohud_autostart": autostart if perf else None,
        "t_launch": time.time(),
    }
    log(f"launching scene={sc['name']} shader={shader}")
    launcher = subprocess.Popen(
        [PRISM, "-l", "NocturneBench", "-w", save_name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=_hypr_env(),
        start_new_session=True,
    )

    java_pid = wait_for_java(timeout=180)
    if not java_pid:
        launcher.poll()
        raise RuntimeError(
            "game process never appeared (first launch may "
            "need asset downloads — check Prism)"
        )
    meta["t_java"] = time.time()
    log(f"java pid {java_pid}")

    addr = find_window(java_pid, timeout=120)
    if not addr:
        close_game(java_pid, None)
        raise RuntimeError("no game window appeared")
    place_window(addr)
    log(f"window {addr} placed on {OUTPUT}")

    try:
        loaded = wait_world_loaded(
            log_file, log_offset, timeout=600 if prewarm else 300
        )
        meta["t_world"] = time.time()
        if not loaded:
            log("WARN: world-join marker not seen; proceeding on timeout")
        log(f"world loaded, warming up {warmup}s (chunks + shader compile)")
        time.sleep(warmup)
        meta["t_measure_start"] = time.time()

        if mode == "shot" or prewarm:
            for i in range(shots):
                screenshot(addr, out_dir / f"shot-{i:02d}.png")
                if i + 1 < shots:
                    time.sleep(2)
        if perf:
            log(f"measuring {duration}s")
            time.sleep(duration)
        meta["t_measure_end"] = time.time()
    finally:
        close_game(java_pid, addr)
        write_run_env(None)
        (out_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    log(f"done: {out_dir}")
    return meta


# ---------------------------------------------------------------- commands
def sanitize(s):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s)


def cmd_run(args):
    scenes = scenelib.load_scenes()
    picked = (
        [s for s in scenes.values() if s["name"] != "smoke"]
        if args.scenes == "all"
        else [scenes[n] for n in args.scenes.split(",")]
    )
    shaders = [s.strip() for s in args.shaders.split(",")]
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = BENCH / "runs" / f"{stamp}-{sanitize(args.label)}"
    ensure_output()
    try:
        modes = ["shot", "perf"] if args.mode == "both" else [args.mode]
        for shader in shaders:
            for sc in picked:
                out = run_dir / sanitize(shader) / sc["name"]
                for mode in modes:
                    run_one(
                        sc, shader, out, mode, args.warmup, args.duration, args.shots
                    )
    finally:
        if not args.keep_output:
            remove_output()
    log(f"run complete: {run_dir}")
    print(run_dir)


def cmd_prewarm(args):
    scenes = scenelib.load_scenes()
    picked = (
        list(scenes.values())
        if args.scenes == "all"
        else [scenes[n] for n in args.scenes.split(",")]
    )
    ensure_output()
    try:
        for sc in picked:
            out = BENCH / "runs" / "prewarm" / sc["name"]
            run_one(sc, args.shader, out, "shot", args.warmup, 0, 1, prewarm=True)
            # re-bake level.dat so the canonical viewpoint/time survives the
            # game's own save, while the generated region files stay
            scenelib.bake_template(sc)
    finally:
        remove_output()


def cmd_scout(args):
    pts = [tuple(map(int, p.split(","))) for p in args.points.split(";")]
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = BENCH / "runs" / f"{stamp}-scout"
    ensure_output()
    try:
        for i, (x, z) in enumerate(pts):
            for yaw in (0, 90, 180, 270) if args.pan else (args.yaw,):
                # single shared template ("scout") so generated chunks
                # accumulate across points instead of regenerating
                sc = {
                    "name": "scout-" + args.world if args.world else "scout",
                    "pos": [x, args.y, z],
                    "rot": [yaw, args.pitch],
                    "time": args.time,
                }
                if args.world:
                    sc["world"] = args.world
                else:
                    sc["seed"] = args.seed
                out = run_dir / f"{i:02d}-{x}_{z}-y{yaw}"
                run_one(sc, args.shader, out, "shot", args.warmup, 0, 1, prewarm=True)
    finally:
        remove_output()
    log(f"scout complete: {run_dir}")
    print(run_dir)


TIME_NAMES = {
    "dawn": 23000,
    "sunrise": 400,
    "morning": 1000,
    "noon": 6000,
    "afternoon": 9000,
    "dusk": 12300,
    "sunset": 12300,
    "night": 15000,
    "midnight": 18000,
}


def parse_time(v):
    return TIME_NAMES[v] if v in TIME_NAMES else int(v)


def cmd_import(args):
    dest, info = scenelib.import_world(args.zip, args.name)
    log(f"imported {dest.name}: version={info['version']} spawn={info['spawn']}")
    log(f"next: nb open {args.name}")


def cmd_import(args):
    dest, info = scenelib.import_world(args.zip, args.name)
    log(f"imported {dest.name}: version={info['version']} spawn={info['spawn']}")
    log(f"next: nb open {args.name}")


def cmd_open(args):
    dest = scenelib.open_for_editing(args.world)
    log(f"world ready: {dest.name} (CoupleTime instance, creative)")
    log("fly to a viewpoint, press Esc (pause = save), then run:")
    log(f"  nb mark <scene-name> --world {args.world} --time dusk")


def cmd_mark(args):
    save = scenelib.edit_save_dir(args.world)
    if not save.exists():
        raise SystemExit(f"no edit save for {args.world!r} — run: nb open {args.world}")
    pos, rot = scenelib.read_player_view(save)
    scene = {
        "name": args.name,
        "world": args.world,
        "pos": pos,
        "rot": rot,
        "time": parse_time(args.time),
    }
    if args.desc:
        scene["desc"] = args.desc
    path = BENCH / "scenes.json"
    data = json.loads(path.read_text())
    data["scenes"] = [s for s in data["scenes"] if s["name"] != args.name]
    data["scenes"].append(scene)
    path.write_text(json.dumps(data, indent=2) + "\n")
    log(f"marked {args.name}: pos={pos} rot={rot} time={scene['time']}")
    if args.shoot:
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        out = BENCH / "runs" / f"{stamp}-mark-{sanitize(args.name)}"
        ensure_output()
        try:
            run_one(
                scene, args.shader, out / sanitize(args.name), "shot", args.warmup, 0, 1
            )
        finally:
            remove_output()
        log(f"preview: {out}")


def cmd_list(args):
    for name, sc in scenelib.load_scenes().items():
        print(
            f"{name:24s} {'world=' + sc['world'] if sc.get('world') else 'seed=' + str(sc.get('seed'))} "
            f"pos={sc['pos']} time={sc['time']} {sc.get('desc', '')}"
        )


def main():
    ap = argparse.ArgumentParser(prog="nbench")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("run", help="screenshot/perf runs over scenes×shaders")
    p.add_argument(
        "--shaders", required=True, help="comma-separated shaderpack zips (or 'off')"
    )
    p.add_argument("--scenes", default="all")
    p.add_argument("--mode", choices=["shot", "perf", "both"], default="shot")
    p.add_argument("--warmup", type=int, default=25)
    p.add_argument("--duration", type=int, default=60)
    p.add_argument("--shots", type=int, default=1)
    p.add_argument("--label", default="run")
    p.add_argument("--keep-output", action="store_true")
    p.set_defaults(fn=cmd_run)

    p = sub.add_parser("prewarm", help="generate chunks into scene templates")
    p.add_argument("--scenes", default="all")
    p.add_argument("--shader", default="off")
    p.add_argument("--warmup", type=int, default=90)
    p.set_defaults(fn=cmd_prewarm)

    p = sub.add_parser("scout", help="screenshot candidate viewpoints")
    p.add_argument("--points", required=True, help="'x,z;x,z;...'")
    p.add_argument("--seed", type=int)
    p.add_argument(
        "--world", help="scout an existing world from worlds-src/ instead of a seed"
    )
    p.add_argument("--y", type=int, default=160)
    p.add_argument("--yaw", type=int, default=0)
    p.add_argument("--pitch", type=int, default=15)
    p.add_argument("--pan", action="store_true", help="4 yaw directions/point")
    p.add_argument("--time", type=int, default=6000)
    p.add_argument("--shader", default="Photon Nocturne.zip")
    p.add_argument("--warmup", type=int, default=20)
    p.set_defaults(fn=cmd_scout)

    p = sub.add_parser("import", help="import a downloaded map zip into worlds-src")
    p.add_argument("zip")
    p.add_argument("--name", required=True)
    p.set_defaults(fn=cmd_import)

    p = sub.add_parser(
        "open", help="install a world into CoupleTime for viewpoint picking"
    )
    p.add_argument("world")
    p.set_defaults(fn=cmd_open)

    p = sub.add_parser(
        "mark", help="save current player view in an edit world as a scene"
    )
    p.add_argument("name")
    p.add_argument("--world", required=True)
    p.add_argument(
        "--time", default="noon", help="tick or name (dawn/noon/dusk/night/midnight...)"
    )
    p.add_argument("--desc", default="")
    p.add_argument("--shoot", action="store_true", help="take a 4K preview right away")
    p.add_argument("--shader", default="Photon Nocturne.zip")
    p.add_argument("--warmup", type=int, default=25)
    p.set_defaults(fn=cmd_mark)

    p = sub.add_parser("list", help="list scenes")
    p.set_defaults(fn=cmd_list)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
