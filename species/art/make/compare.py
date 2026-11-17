"""A page that sets a creature's variants side by side, for the owner to choose between: art/<id>/work/compare.html.

    python3 species/art/make/compare.py <id> [--embed]

Each column is one work/<mesher>-<rigger>/ folder: its pictures (clean, rigged, each clip mid-way), its check, and the
time and peak VRAM of each step from work/log.json. The master copy (mesh.glb as filed) is described in the first row."""
import html, json, os, sys

ART = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
creature = sys.argv[1]
EMBED = "--embed" in sys.argv          # the pictures inside the page, so it can be sent on its own
work = os.path.join(ART, creature, "work")
variants = sorted(d for d in os.listdir(work) if os.path.isfile(os.path.join(work, d, "check.json")))
log = json.load(open(os.path.join(work, "log.json"))) if os.path.exists(os.path.join(work, "log.json")) else []


def latest(step, variant):
    rows = [r for r in log if r.get("step") == step and (r.get("variant") == variant or step in ("mesh", "cutout", "render"))]
    if step == "mesh": rows = [r for r in rows if variant.split("-")[0] in json.dumps(r.get("pins", {}))]
    return rows[-1] if rows else None


pictures = ["look-clean-side", "look-clean-front34", "look-rigged-back34", "look-rigged-top"] + \
           ["pose-%s-%d-front34" % (c, k) for c in ("idle", "walk", "shake", "roll", "bow", "jump", "spin", "dead", "wave", "dance") for k in (1, 2)]
cells = {v: [] for v in variants}
for v in variants:
    check = json.load(open(os.path.join(work, v, "check.json")))
    facts = check["mesh.glb"]["facts"]; quest = check["mesh.quest.glb"]["facts"]
    faults = check["mesh.glb"]["faults"] + check["mesh.quest.glb"]["faults"]
    times = []
    for step in ("mesh", "clean", "rig", "clips", "pack"):
        r = latest(step, v)
        if r: times.append("%s %.0f s, %s MiB" % (step, r.get("seconds", 0), r.get("vram_peak_mib")))
    cells[v] = ["<b>%s</b>" % html.escape(v),
                "%s<br>%d triangles, %s m<br>phones %d KB, Quest %d KB<br>texture %s" % (
                    "ok" if not faults else "<span class=f>%s</span>" % html.escape("; ".join(faults)), facts["triangles"],
                    " x ".join("%.3f" % s for s in facts["size"]), facts["bytes"] // 1024, quest["bytes"] // 1024,
                    ", ".join("%s %dx%d" % (t["format"], *t["size"]) for t in facts["textures"])),
                "<br>".join(times)]
    for p in pictures:
        f = os.path.join(v, p + ".png")
        if not os.path.exists(os.path.join(work, f)): cells[v].append(""); continue
        if EMBED:
            import base64
            f = "data:image/png;base64," + base64.b64encode(open(os.path.join(work, f), "rb").read()).decode()
        cells[v].append('<img src="%s">' % f)
rows = list(zip(*[cells[v] for v in variants])) if variants else []
labels = ["", "check", "time and peak VRAM (whole GPU)"] + pictures
page = ["<!doctype html><meta charset=utf-8><title>%s variants</title>" % creature,
        "<style>body{font:13px system-ui;background:#f4f4f5;margin:16px}td{vertical-align:top;padding:6px;background:#fff}"
        "img{width:300px}th{text-align:left;font-weight:normal;color:#666;width:120px}.f{color:#b00}</style>",
        "<h1>%s</h1><table>" % creature]
for label, row in zip(labels, rows):
    if not any(row): continue
    page.append("<tr><th>%s</th>%s</tr>" % (html.escape(label), "".join("<td>%s</td>" % c for c in row)))
page.append("</table>")
out = os.path.join(work, "compare-embedded.html" if EMBED else "compare.html")
with open(out, "w", encoding="utf-8") as f: f.write("\n".join(page))
print(out)
