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


def bake_template(scene, force=False):
    """Create/refresh the template save for a scene. Keeps existing region
    files (pregenerated chunks) unless the seed changed or force=True."""
    tdir = template_dir(scene["name"])
    meta_path = tdir / "nbench-scene.json"
    if tdir.exists():
        old = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        if force or old.get("seed") != scene["seed"]:
            shutil.rmtree(tdir)  # seed changed: cached chunks are invalid
    tdir.mkdir(parents=True, exist_ok=True)
    level_dat(scene).save(str(tdir / "level.dat"))
    # Also refresh the player inside level.dat even when chunks are kept:
    # after a prewarm run MC rewrites level.dat with live state, so re-baking
    # restores the canonical viewpoint/time while region/ stays cached.
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
