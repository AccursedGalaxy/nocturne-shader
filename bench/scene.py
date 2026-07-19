"""Scene baking for the nocturne bench pipeline.

A *scene* is a fully-deterministic singleplayer save: fixed seed, fixed
player viewpoint (spectator, flying), fixed time of day, weather locked,
daylight cycle and mob spawning off. Scenes are defined in scenes.json and
baked into Minecraft save folders with a hand-built level.dat (1.20.1,
DataVersion 3465).

Templates live in bench/worlds/<scene>/ (kept out of git via .gitignore —
region files are cache). Each run copies the template into the instance's
saves/ so runs never mutate the template; --prewarm runs on the template
itself so generated chunks are kept for later runs.
"""

import json
import shutil
from pathlib import Path

from nbtlib import File, Compound, List, String, Int, Long, Byte, Double, Float

BENCH = Path(__file__).resolve().parent
DATA_VERSION = 3465  # 1.20.1

GAMERULES = {
    "doDaylightCycle": "false",
    "doWeatherCycle": "false",
    "doMobSpawning": "false",
    "doFireTick": "false",
    "doInsomnia": "false",
    "doTraderSpawning": "false",
    "doPatrolSpawning": "false",
    "spawnRadius": "0",
}


def load_scenes(path=None):
    with open(path or BENCH / "scenes.json") as f:
        return {s["name"]: s for s in json.load(f)["scenes"]}


def dimensions_tag():
    def noise(dim_type, settings, preset):
        return Compound(
            {
                "type": String(dim_type),
                "generator": Compound(
                    {
                        "type": String("minecraft:noise"),
                        "settings": String(settings),
                        "biome_source": Compound(
                            {
                                "type": String("minecraft:multi_noise"),
                                "preset": String(preset),
                            }
                        ),
                    }
                ),
            }
        )

    return Compound(
        {
            "minecraft:overworld": noise(
                "minecraft:overworld", "minecraft:overworld", "minecraft:overworld"
            ),
            "minecraft:the_nether": noise(
                "minecraft:the_nether", "minecraft:nether", "minecraft:nether"
            ),
            "minecraft:the_end": Compound(
                {
                    "type": String("minecraft:the_end"),
                    "generator": Compound(
                        {
                            "type": String("minecraft:noise"),
                            "settings": String("minecraft:end"),
                            "biome_source": Compound(
                                {"type": String("minecraft:the_end")}
                            ),
                        }
                    ),
                }
            ),
        }
    )


def level_dat(scene):
    x, y, z = scene["pos"]
    yaw, pitch = scene["rot"]
    gamerules = Compound({k: String(v) for k, v in GAMERULES.items()})
    data = Compound(
        {
            "DataVersion": Int(DATA_VERSION),
            "version": Int(19133),
            "Version": Compound(
                {
                    "Id": Int(DATA_VERSION),
                    "Name": String("1.20.1"),
                    "Series": String("main"),
                    "Snapshot": Byte(0),
                }
            ),
            "LevelName": String(scene["name"]),
            "GameType": Int(3),  # spectator
            "Difficulty": Byte(0),  # peaceful: no hostile-mob nondeterminism
            "allowCommands": Byte(1),
            "DayTime": Long(scene["time"]),
            "Time": Long(0),
            "LastPlayed": Long(0),
            "raining": Byte(1 if scene.get("weather") == "rain" else 0),
            "rainTime": Int(999999999),
            "thundering": Byte(0),
            "clearWeatherTime": Int(0 if scene.get("weather") == "rain" else 999999999),
            "GameRules": gamerules,
            "SpawnX": Int(int(x)),
            "SpawnY": Int(int(y)),
            "SpawnZ": Int(int(z)),
            "SpawnAngle": Float(0.0),
            "WorldGenSettings": Compound(
                {
                    "bonus_chest": Byte(0),
                    "generate_features": Byte(1),
                    "seed": Long(scene["seed"]),
                    "dimensions": dimensions_tag(),
                }
            ),
            "Player": Compound(
                {
                    "Pos": List[Double]([Double(x), Double(y), Double(z)]),
                    "Rotation": List[Float]([Float(yaw), Float(pitch)]),
                    "Motion": List[Double]([Double(0), Double(0), Double(0)]),
                    "Dimension": String("minecraft:overworld"),
                    "playerGameType": Int(3),
                    "previousPlayerGameType": Int(1),
                    "Health": Float(20.0),
                    "foodLevel": Int(20),
                    "OnGround": Byte(0),
                    "FallFlying": Byte(0),
                    "Invulnerable": Byte(1),
                    "abilities": Compound(
                        {
                            "flying": Byte(1),
                            "mayfly": Byte(1),
                            "invulnerable": Byte(1),
                            "mayBuild": Byte(0),
                            "instabuild": Byte(0),
                            "flySpeed": Float(0.05),
                            "walkSpeed": Float(0.1),
                        }
                    ),
                }
            ),
        }
    )
    return File(Compound({"Data": data}), gzipped=True, root_name="")


def template_dir(scene_name):
    return BENCH / "worlds" / scene_name


def patch_level_dat(path, scene):
    """Patch an *existing* world's level.dat in place: our spectator
    viewpoint, frozen time/weather, determinism gamerules — and strip
    datapack entries whose packs aren't shipped with the save (ghost
    entries trigger Minecraft's blocking safe-mode prompt)."""
    import nbtlib
    from nbtlib import Compound as C

    x, y, z = scene["pos"]
    yaw, pitch = scene["rot"]
    f = nbtlib.load(str(path))
    d = f["Data"] if "Data" in f else f[""]["Data"]
    d["GameType"] = Int(3)
    d["Difficulty"] = Byte(0)
    d["allowCommands"] = Byte(1)
    d["DayTime"] = Long(scene["time"])
    d["raining"] = Byte(1 if scene.get("weather") == "rain" else 0)
    d["thundering"] = Byte(0)
    d["rainTime"] = Int(999999999)
    d["clearWeatherTime"] = Int(0 if scene.get("weather") == "rain" else 999999999)
    gr = d.get("GameRules") or C({})
    for k, v in GAMERULES.items():
        gr[k] = String(v)
    d["GameRules"] = gr
    if "DataPacks" in d:
        d["DataPacks"]["Enabled"] = List[String]([String("vanilla"), String("fabric")])
        d["DataPacks"]["Disabled"] = List[String]([])
    player = d.get("Player") or C({})
    player["Pos"] = List[Double]([Double(x), Double(y), Double(z)])
    player["Rotation"] = List[Float]([Float(yaw), Float(pitch)])
    player["Motion"] = List[Double]([Double(0)] * 3)
    player["Dimension"] = String("minecraft:overworld")
    player["playerGameType"] = Int(3)
    player["previousPlayerGameType"] = Int(1)
    player["Invulnerable"] = Byte(1)
    ab = player.get("abilities") or C({})
    ab["flying"] = Byte(1)
    ab["mayfly"] = Byte(1)
    ab["invulnerable"] = Byte(1)
    player["abilities"] = ab
    d["Player"] = player
    f.save(str(path))


def bake_template(scene, force=False):
    """Create/refresh the template save for a scene.

    Seed scenes: hand-built level.dat; region files (pregenerated chunks)
    are kept unless the seed changed or force=True.
    World scenes ({"world": "<name>"}): copy bench/worlds-src/<name>/ once,
    then patch its level.dat with the scene's viewpoint/time/gamerules."""
    tdir = template_dir(scene["name"])
    meta_path = tdir / "nbench-scene.json"
    world = scene.get("world")
    if tdir.exists():
        old = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        stale = old.get("seed") != scene.get("seed") or old.get("world") != world
        if force or stale:
            shutil.rmtree(tdir)
    if world:
        src = BENCH / "worlds-src" / world
        if not src.is_dir():
            raise SystemExit(f"world source missing: {src}")
        if not tdir.exists():
            shutil.copytree(src, tdir)
        patch_level_dat(tdir / "level.dat", scene)
    else:
        tdir.mkdir(parents=True, exist_ok=True)
        # Refresh level.dat even when chunks are kept: after a prewarm run
        # MC rewrites it with live state; re-baking restores the canonical
        # viewpoint/time while region/ stays cached.
        level_dat(scene).save(str(tdir / "level.dat"))
    meta_path.write_text(json.dumps(scene, indent=2))
    (tdir / "session.lock").unlink(missing_ok=True)
    return tdir


def install(scene, saves_dir, run_on_template=False):
    """Put the scene save into the instance saves/ dir. Returns save name."""
    tdir = bake_template(scene)
    name = f"nbench-{scene['name']}"
    dest = Path(saves_dir) / name
    if dest.is_symlink() or dest.exists():
        if dest.is_symlink():
            dest.unlink()
        else:
            shutil.rmtree(dest)
    if run_on_template:
        dest.symlink_to(tdir)  # prewarm: let MC generate chunks into template
    else:
        shutil.copytree(tdir, dest)
    return name


COUPLETIME_SAVES = (
    Path.home()
    / ".local/opt/prismlauncher/instances/CoupleTime/minecraft/saves"
)


def edit_save_dir(world):
    return COUPLETIME_SAVES / f"nbench-edit-{world}"


def open_for_editing(world):
    """Copy a worlds-src world into the CoupleTime instance's saves as
    'nbench-edit-<world>' (creative, cheats, NOT spectator-patched) so
    Robin can fly around and pick viewpoints in his own instance. Reopening
    keeps the existing copy (and thus his last position)."""
    src = BENCH / "worlds-src" / world
    if not src.is_dir():
        raise SystemExit(
            f"unknown world {world!r}; available: "
            + ", ".join(p.name for p in (BENCH / "worlds-src").iterdir())
        )
    dest = edit_save_dir(world)
    if not dest.exists():
        shutil.copytree(src, dest)
        import nbtlib
        f = nbtlib.load(str(dest / "level.dat"))
        d = f["Data"]
        d["GameType"] = Int(1)  # creative for free flight
        d["allowCommands"] = Byte(1)
        d["LevelName"] = String(f"nbench-edit-{world}")
        if "DataPacks" in d:
            d["DataPacks"]["Enabled"] = List[String](
                [String("vanilla"), String("fabric")]
            )
            d["DataPacks"]["Disabled"] = List[String]([])
        if "Player" in d:
            d["Player"]["playerGameType"] = Int(1)
        f.save(str(dest / "level.dat"))
    (dest / "session.lock").unlink(missing_ok=True)
    return dest


def read_player_view(save_dir):
    """Player position/rotation from a save's level.dat (updated whenever
    the game saves — pausing with Esc is enough)."""
    import nbtlib

    f = nbtlib.load(str(Path(save_dir) / "level.dat"))
    pl = f["Data"]["Player"]
    pos = [round(float(v), 1) for v in pl["Pos"]]
    yaw, pitch = (round(float(v), 1) for v in pl["Rotation"])
    yaw = ((yaw + 180) % 360) - 180  # normalize
    return pos, [yaw, pitch]


JUNK_DIRS = {
    "playerdata", "players", "stats", "advancements", "serverconfig",
    "ftbchunks", "ftbessentials", "ftbquests", "ftbteams", "easy_npc",
    "DIM-1", "DIM1", "dimensions", "__MACOSX",
}


def import_world(zip_path, name):
    """Unpack a downloaded map zip into worlds-src/<name>. Finds the world
    root (the dir containing level.dat) wherever it sits in the archive,
    strips per-player/mod junk, and clears ghost datapack entries."""
    import tempfile
    import zipfile

    dest = BENCH / "worlds-src" / name
    if dest.exists():
        raise SystemExit(f"worlds-src/{name} already exists")
    with tempfile.TemporaryDirectory(dir=BENCH) as tmp:
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(tmp)
        roots = [p.parent for p in Path(tmp).rglob("level.dat")]
        if not roots:
            raise SystemExit("no level.dat found in the archive")
        root = min(roots, key=lambda p: len(p.parts))
        for junk in JUNK_DIRS:
            shutil.rmtree(root / junk, ignore_errors=True)
        (root / "session.lock").unlink(missing_ok=True)
        (root / "level.dat_old").unlink(missing_ok=True)
        shutil.move(str(root), dest)

    import nbtlib
    f = nbtlib.load(str(dest / "level.dat"))
    d = f["Data"]
    info = {
        "version": str(d.get("Version", {}).get("Name", "?")),
        "spawn": [int(d["SpawnX"]), int(d["SpawnY"]), int(d["SpawnZ"])],
    }
    if "DataPacks" in d:
        d["DataPacks"]["Enabled"] = List[String](
            [String("vanilla"), String("fabric")]
        )
        d["DataPacks"]["Disabled"] = List[String]([])
        f.save(str(dest / "level.dat"))
    return dest, info
