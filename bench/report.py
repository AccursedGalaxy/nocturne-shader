#!/usr/bin/env python3
"""Report generator for nocturne bench runs.

Walks bench/runs/<run>/<shader>/<scene>/, parses MangoHud CSVs (trimmed to
the measurement window recorded in meta.json), and emits:
  - stats.json per scene dir
  - REPORT.md at the run root: per-scene table + shader-vs-shader deltas
    with chunked-bootstrap significance (same method as perflogs/perfbench)
  - gallery.html at the run root with the screenshots

Usage:
  report.py <run-dir> [--baseline <shader-dirname>]
"""

import csv
import json
import random
import statistics
import sys
from pathlib import Path


def load_frametimes(csv_path, t_from=None, t_to=None):
    """MangoHud CSV -> frametimes (ms), sliced by seconds since log start."""
    rows = list(csv.reader(open(csv_path)))
    header_i = next(
        (i for i, r in enumerate(rows) if any("frametime" in c.lower() for c in r)),
        None,
    )
    if header_i is None:
        return []
    header = [c.strip().lower() for c in rows[header_i]]
    ft_i = header.index("frametime")
    el_i = header.index("elapsed") if "elapsed" in header else None
    out = []
    for r in rows[header_i + 1 :]:
        if len(r) <= ft_i:
            continue
        try:
            ft = float(r[ft_i])
            el = float(r[el_i]) / 1e9 if el_i is not None else None
        except ValueError:
            continue
        if t_from is not None and el is not None and el < t_from:
            continue
        if t_to is not None and el is not None and el > t_to:
            continue
        out.append(ft)
    return out


def stats(ft):
    if len(ft) < 100:
        return None
    s = sorted(ft)
    n = len(s)
    total = sum(s)
    worst = s[int(n * 0.99) :]
    return {
        "frames": n,
        "seconds": round(total / 1000, 1),
        "avg_fps": round(1000 * n / total, 1),
        "median_ms": round(statistics.median(s), 3),
        "p95_ms": round(s[int(n * 0.95)], 3),
        "p99_ms": round(s[int(n * 0.99)], 3),
        "low1_fps": round(1000 / (sum(worst) / len(worst)), 1),
    }


def bootstrap_delta(a, b, iters=2000, chunk=250):
    """Chunked bootstrap CI on median difference (b-a)/a. Chunking respects
    frame-time autocorrelation. Returns (delta_pct, lo_pct, hi_pct)."""
    rng = random.Random(42)

    def chunks(x):
        return [x[i : i + chunk] for i in range(0, len(x) - chunk + 1, chunk)]

    ca, cb = chunks(a), chunks(b)
    deltas = []
    for _ in range(iters):
        ma = statistics.median([v for c in rng.choices(ca, k=len(ca)) for v in c])
        mb = statistics.median([v for c in rng.choices(cb, k=len(cb)) for v in c])
        deltas.append((mb - ma) / ma * 100)
    deltas.sort()
    return (
        round(statistics.median(deltas), 2),
        round(deltas[int(iters * 0.025)], 2),
        round(deltas[int(iters * 0.975)], 2),
    )


def scene_stats(scene_dir):
    meta_p = scene_dir / "meta.json"
    if not meta_p.exists():
        return None
    meta = json.loads(meta_p.read_text())
    csvs = [p for p in scene_dir.glob("*.csv")]
    result = {"meta": meta, "stats": None}
    if csvs:
        csv_path = max(csvs, key=lambda p: p.stat().st_mtime)
        # trim: MangoHud's elapsed==0 at autostart_log seconds after app
        # init; the measure window is recorded as wall-clock in meta.
        t0 = meta.get("t_java", meta["t_launch"]) + (
            meta.get("mangohud_autostart") or 1
        )
        t_from = meta.get("t_measure_start", t0) - t0
        t_to = meta.get("t_measure_end")
        t_to = (t_to - t0) if t_to else None
        ft = load_frametimes(csv_path, max(t_from, 0), t_to)
        result["stats"] = stats(ft)
        result["_frametimes"] = ft
    (scene_dir / "stats.json").write_text(
        json.dumps({k: v for k, v in result.items() if k != "_frametimes"}, indent=2)
    )
    return result


def build(run_dir, baseline=None):
    run_dir = Path(run_dir)
    shaders = sorted([d for d in run_dir.iterdir() if d.is_dir()])
    data = {}  # shader -> scene -> result
    for sh in shaders:
        for sc in sorted(d for d in sh.iterdir() if d.is_dir()):
            r = scene_stats(sc)
            if r:
                data.setdefault(sh.name, {})[sc.name] = r

    lines = [f"# nocturne bench report — {run_dir.name}", ""]
    for sh, scenes in data.items():
        have = [s for s in scenes.values() if s["stats"]]
        lines += [f"## {sh}", ""]
        if have:
            lines += [
                "| scene | frames | avg fps | median ms | p95 | p99 | 1% low fps |",
                "|---|---|---|---|---|---|---|",
            ]
            for name, r in scenes.items():
                st = r["stats"]
                if st:
                    lines.append(
                        f"| {name} | {st['frames']} | {st['avg_fps']} | "
                        f"{st['median_ms']} | {st['p95_ms']} | {st['p99_ms']} | "
                        f"{st['low1_fps']} |"
                    )
            lines.append("")
        else:
            lines += ["(screenshot-only run — no frame logs)", ""]

    base = baseline or (shaders[0].name if shaders else None)
    others = [s for s in data if s != base]
    if base in data and others:
        lines += [
            f"## Deltas vs baseline `{base}` (median frametime, "
            "chunked bootstrap 95% CI)",
            "",
        ]
        lines += [
            "| scene | shader | Δ median | 95% CI | verdict |",
            "|---|---|---|---|---|",
        ]
        for other in others:
            for name in data[base]:
                a = data[base][name].get("_frametimes")
                b = data.get(other, {}).get(name, {}).get("_frametimes")
                if not a or not b or len(a) < 500 or len(b) < 500:
                    continue
                d, lo, hi = bootstrap_delta(a, b)
                verdict = "NOISE" if lo <= 0 <= hi else "SIGNIFICANT"
                lines.append(
                    f"| {name} | {other} | {d:+.2f}% | "
                    f"[{lo:+.2f}, {hi:+.2f}] | {verdict} |"
                )
        lines.append("")

    (run_dir / "REPORT.md").write_text("\n".join(lines) + "\n")

    # gallery: one row per scene, shaders side by side for A/B eyeballing
    by_scene = {}
    for sh in shaders:
        for shot in sorted(sh.glob("*/shot-*.png")):
            by_scene.setdefault(shot.parent.name, []).append(
                (sh.name, shot.relative_to(run_dir))
            )
    n_shaders = max((len(v) for v in by_scene.values()), default=1)
    html = [
        "<!doctype html><meta charset=utf-8>",
        f"<title>nocturne bench — {run_dir.name}</title>",
        "<style>body{font-family:sans-serif;background:#111;color:#eee;"
        "margin:2em}img{width:100%;border-radius:6px}"
        f".row{{display:grid;grid-template-columns:repeat({n_shaders},1fr);"
        "gap:12px;margin:0 0 2.5em}"
        "figure{margin:0}figcaption{margin:.4em 0;opacity:.8;"
        "font-size:.9em}h2{margin:.2em 0 .6em}</style>",
        f"<h1>{run_dir.name}</h1>",
    ]
    for scene in sorted(by_scene):
        html.append(f"<h2>{scene}</h2><div class=row>")
        for sh, rel in by_scene[scene]:
            html.append(
                f"<figure><figcaption>{sh}</figcaption>"
                f"<a href='{rel}'><img src='{rel}' loading=lazy></a></figure>"
            )
        html.append("</div>")
    (run_dir / "gallery.html").write_text("\n".join(html))
    print(run_dir / "REPORT.md")
    print(run_dir / "gallery.html")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    base = None
    if "--baseline" in sys.argv:
        base = sys.argv[sys.argv.index("--baseline") + 1]
    if not args:
        sys.exit(__doc__)
    build(args[0], base)
