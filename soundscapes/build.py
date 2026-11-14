#!/usr/bin/python3 -I
"""Builds the biome soundscapes: two looping beds and a handful of cues per biome, from recipes/<biome>.py.

    python3 -I soundscapes/build.py                  build every biome that has a recipe, then write index.json
    python3 -I soundscapes/build.py forest town      build only these: their beds/, cues/ and index/<biome>.json
    python3 -I soundscapes/build.py --index          write index.json from the index/ fragments, build nothing
    python3 -I soundscapes/build.py --check [biome]  measure what is on disk and check it; write nothing; exit 1 on
                                                     a fault (with no biome named, also index.json and every recipe)
    --wav                                            also write wav/<biome>-<name>.wav (16-bit) to listen to

Standard library only (Python 3.9), macOS for afconvert. A named build writes only its own biomes' files, so
several can run at once; only a build with no biome named (or --index) writes index.json. README.md says the rest.
"""
import argparse, glob, hashlib, importlib.util, json, os, sys, tempfile, time

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
PACK_ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from lib import core, finish, measure, opus       # noqa: E402

BASE = "https://qrx-pack.apphaus.us/soundscapes/"
VERSION = 1
BED_LADDER = (40000, 64000, 96000, 128000)   # afconvert's targets, bits a second, tried in turn until the decoded
                                             # seam passes with SEAM_MARGIN; at 40 kbps a 30 s bed is about 150 KB
SEAM_MARGIN = 0.8          # a bed's decoded seam and slope must be at most this (the limit is 1.0) to stop the ladder
CUE_BITRATE = 24000
CUES_PER_BED = (4, 6)


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    part = path + ".part%d" % os.getpid()
    with open(part, "w", encoding="utf-8") as f:
        f.write(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    os.replace(part, path)


def biomes():
    return read_json(os.path.join(PACK_ROOT, "species", "biomes.json"))["biomes"]


def calls(biome_id):
    """The `call` sounds of the species at home in this biome, as paths from the pack root."""
    catalog = read_json(os.path.join(PACK_ROOT, "species", "index.json"))
    return sorted({"species/" + s["sounds"]["call"] for s in catalog["species"]
                   if s.get("biome") == biome_id and s.get("sounds", {}).get("call")})


def sha(*paths):
    h = hashlib.sha256()
    for p in sorted(paths):
        with open(p, "rb") as f:
            h.update(os.path.relpath(p, HERE).encode() + b"\0" + f.read())
    return h.hexdigest()[:16]


def toolkit_sha():
    return sha(*glob.glob(os.path.join(HERE, "lib", "*.py")))


def recipe_path(b):
    return os.path.join(HERE, "recipes", b + ".py")


def load_recipe(b):
    spec = importlib.util.spec_from_file_location("recipe_" + b, recipe_path(b))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in ("day", "night", "cues"):
        if not callable(getattr(module, name, None)):
            raise ValueError("recipes/%s.py has no %s(s)" % (b, name))
    return module


# ---- the table ------------------------------------------------------------------------------------------------

def bed_row(name, m, faults):
    bands = " ".join("%4.1f" % m["bands"][k] for k, _, _ in measure.BANDS)
    above2, above8 = measure.brightness(m["bands"])
    return ("  %-24s peak %6.1f  rms %6.1f  lufs %6.1f  >2k %4.1f%%  >8k %4.1f%%  dc %5.0f  corr %4.2f  seam %4.2f/%4.2f  "
            "spread %4.1f  stand %4.1f (%s)  bands %s  %s" % (
                name, m["peak"], m["rms"], m["lufs"], above2, above8, m["dc"], m["corr"], m["seam"], m["slope"],
                m["spread"], m["stand"], m["standBand"], bands, "ok" if not faults else "FAULT"))


def cue_row(name, m, faults, cue, bed_rms):
    """One cue's line; `bed_rms` is {part: the decoded bed's RMS} for the `over bed` figures."""
    over = "/".join("%+.1f" % (m["loud"] + cue["level"] - bed_rms[p]) for p in cue["beds"] if p in bed_rms) or "?"
    return ("  %-24s peak %6.1f  %5.2f s  edges -%3.0f dB  snap %4.1f  loud %6.1f  level %+4.0f  over bed %s dB  "
            "every %3.0f-%3.0f s  %s  %s" % (name, m["peak"], m["seconds"], m["edges"], m["snap"], m["loud"],
                                            cue["level"], over, cue["every"][0], cue["every"][1], "+".join(cue["beds"]),
                                            "ok" if not faults else "FAULT"))


def schedule(cues, measures, b):
    """(rows, faults) for how each bed's cues are spaced and placed."""
    rows, faults = [], []
    entries = [dict(c, snap=(measures.get(c["id"]) or {}).get("snap")) for c in cues]
    for part in ("day", "night"):
        rows.append("  %-24s %.2f events a minute expected (aim at about 1 or fewer)" % (part + " cues", measure.per_minute(entries, part)))
        faults += ["%s: %s" % (b, x) for x in measure.schedule_faults(entries, part)]
        count = sum(1 for c in entries if part in c["beds"])
        if not CUES_PER_BED[0] <= count <= CUES_PER_BED[1]:
            faults.append("%s: the %s bed has %d cues; it needs %d to %d" % (b, part, count, *CUES_PER_BED))
    return rows, list(dict.fromkeys(faults))      # a cue in both beds is named once


def check_file(path, kind, expect_frames, channels, tmp, bytes_expected=None, part=None):
    """(measures, faults) for one encoded file, decoded back with afconvert."""
    faults = []
    if not os.path.exists(path):
        return None, ["missing"]
    if bytes_expected is not None and os.path.getsize(path) != bytes_expected:
        faults.append("%d bytes on disk, %d in the index" % (os.path.getsize(path), bytes_expected))
    try:
        rate, ch = opus.decode(path, tmp)
    except Exception as e:      # noqa: BLE001
        return None, ["does not decode: %s" % e]
    if rate != core.RATE:
        faults.append("decodes at %d Hz" % rate)
    if len(ch) != channels:
        faults.append("decodes to %d channels" % len(ch))
    if expect_frames is not None and len(ch[0]) != expect_frames:
        faults.append("decodes to %d frames, not %d" % (len(ch[0]), expect_frames))
    if kind == "bed":
        m = measure.bed(ch[0], ch[-1])
        faults += measure.bed_faults(m, part)
        if m["rms"] < -70:
            faults.append("decodes to silence")
    else:
        m = measure.cue(ch[0])
        faults += measure.cue_faults(m)
    return m, faults


# ---- building --------------------------------------------------------------------------------------------------

def build_biome(b, info, tmp, wav):
    t0 = time.time()
    recipe = load_recipe(b)
    level = getattr(recipe, "LEVEL", {}) or {}
    entry = {"id": b, "code": info["code"], "name": info["name"], "beds": {}, "cues": [], "calls": calls(b)}
    faults, timing, rows, measures = [], {}, [], {}
    os.makedirs(os.path.join(HERE, "beds"), exist_ok=True)
    os.makedirs(os.path.join(HERE, "cues"), exist_ok=True)
    bitrates, softened = {}, {}
    for part in ("day", "night"):
        t = time.time()
        s = core.Studio(b, part)
        with core.looping():
            left, right, notes = finish.bed(getattr(recipe, part)(s), s.n, "%s.%s" % (b, part), part)
        softened[part] = notes
        timing[part] = round(time.time() - t, 1)
        exact = max(measure.seam(left)[0], measure.seam(right)[0]), max(measure.seam(left)[1], measure.seam(right)[1])
        rel = "beds/%s-%s.ogg" % (b, part)
        tried = []
        for bitrate in BED_LADDER:
            size = opus.encode([left, right], os.path.join(HERE, rel), bitrate, core.seed(b, rel), tmp, loop=True)
            # The codec moves the loudness a little (most of it above 12 kHz), so the decoded file is measured and
            # the bed encoded once more with the difference when it is over 0.25 dB.
            _, back = opus.decode(os.path.join(HERE, rel), tmp)
            short = core.BED_LUFS - measure.loudness(back[0], back[1])
            if abs(short) > 0.25:
                left, right = finish.regain(left, right, short)
                size = opus.encode([left, right], os.path.join(HERE, rel), bitrate, core.seed(b, rel), tmp, loop=True)
            m, f = check_file(os.path.join(HERE, rel), "bed", s.n, 2, tmp, part=part)
            if m is None:
                break
            above2, above8 = measure.brightness(m["bands"])
            if above2 > core.BRIGHTNESS[part][0] or above8 > core.BRIGHTNESS[part][1]:
                # The codec can leave more on top than the bed had (its noise is broadband, and loud beside a
                # quiet top); soften once more from the decoded file's shares and encode again.
                left, right, c2, c8 = finish.soften(left, right, part, notes["softened2k"], notes["softened8k"], m["bands"])
                notes = {"softened2k": round(c2, 1), "softened8k": round(c8, 1)}
                softened[part] = notes
                left, right = finish.level(left, right)
                size = opus.encode([left, right], os.path.join(HERE, rel), bitrate, core.seed(b, rel), tmp, loop=True)
                m, f = check_file(os.path.join(HERE, rel), "bed", s.n, 2, tmp, part=part)
                if m is None:
                    break
            tried.append("%d kbps %.2f/%.2f" % (bitrate // 1000, m["seam"], m["slope"]))
            if max(m["seam"], m["slope"]) <= SEAM_MARGIN:
                break
        bitrates[part] = bitrate
        if wav:
            os.makedirs(os.path.join(HERE, "wav"), exist_ok=True)
            opus.write_wav(os.path.join(HERE, "wav", "%s-%s.wav" % (b, part)), [left, right])
        if m is None:
            faults += ["%s: %s" % (rel, x) for x in f]
            continue
        if exact[0] > 1.0 or exact[1] > 1.0:
            f.append("the synthesized loop's seam moves more than the file does (step %.2f, slope %.2f)" % exact)
        m["sourceSeam"] = [round(exact[0], 3), round(exact[1], 3)]
        measures[part] = m
        rows.append(bed_row(part, m, f) + "  (source seam %.2f/%.2f; %s; softened %+.1f dB over 2k, %+.1f over 8k)" % (
            exact[0], exact[1], ", then ".join(tried), notes["softened2k"], notes["softened8k"]))
        faults += ["%s: %s" % (rel, x) for x in f]
        entry["beds"][part] = {"file": rel, "bytes": size, "level": float(level.get(part, 0.0))}
    t = time.time()
    s = core.Studio(b, "cues")
    with core.one_shot():
        made = list(recipe.cues(s))
    seen, frames = set(), {}
    for c in made:
        if c.id in seen:
            raise ValueError("%s: two cues are called %s" % (b, c.id))
        seen.add(c.id)
        x = finish.cue(c, b)
        frames[c.id] = len(x)
        rel = "cues/%s-%s.ogg" % (b, c.id)
        size = opus.encode([x], os.path.join(HERE, rel), CUE_BITRATE, core.seed(b, rel), tmp)
        m, f = check_file(os.path.join(HERE, rel), "cue", len(x), 1, tmp)
        if m and m["peak"] > core.BED_PEAK_DB - 1.0:
            # the codec overshot a sharp peak; take the whole cue down by as much and encode it again
            x = [v * core.undb(core.BED_PEAK_DB - 1.5 - m["peak"]) for v in x]
            size = opus.encode([x], os.path.join(HERE, rel), CUE_BITRATE, core.seed(b, rel), tmp)
            m, f = check_file(os.path.join(HERE, rel), "cue", len(x), 1, tmp)
        if wav:
            opus.write_wav(os.path.join(HERE, "wav", "%s-%s.wav" % (b, c.id)), [x])
        measures[c.id] = m
        item = {"id": c.id, "file": rel, "bytes": size, "seconds": round(len(x) / core.RATE, 3),
                "beds": list(c.beds), "every": list(c.every), "level": c.level, "spread": c.spread}
        bed_rms = {p: measures[p]["rms"] for p in ("day", "night") if p in measures}
        rows.append(cue_row(c.id, m, f, item, bed_rms) if m else "  %-24s %s" % (c.id, "; ".join(f)))
        faults += ["%s: %s" % (rel, x) for x in f]
        entry["cues"].append(item)
    timing["cues"] = round(time.time() - t, 1)
    srows, sfaults = schedule(entry["cues"], measures, b)
    rows += srows
    faults += sfaults
    for old in glob.glob(os.path.join(HERE, "cues", b + "-*.ogg")):
        if os.path.basename(old)[len(b) + 1:-4] not in seen:
            os.remove(old)
    timing["total"] = round(time.time() - t0, 1)
    fragment = dict(entry)
    fragment["build"] = {"recipe": sha(recipe_path(b)), "toolkit": toolkit_sha(), "seconds": timing,
                         "frames": frames, "bitrate": bitrates, "softened": softened, "measures": measures}
    write_json(os.path.join(HERE, "index", b + ".json"), fragment)
    total_bytes = sum(v["bytes"] for v in entry["beds"].values()) + sum(c["bytes"] for c in entry["cues"])
    print("%s: built in %.0f s (day %.0f s, night %.0f s, cues %.0f s), %d bytes" % (
        b, timing["total"], timing["day"], timing["night"], timing["cues"], total_bytes))
    for r in rows:
        print(r)
    return faults


def assemble():
    """index.json from the fragments in index/, in biomes.json's order."""
    out = {"version": VERSION, "base": BASE,
           "format": {"codec": "opus", "container": "ogg", "rate": core.RATE, "bedSeconds": core.BED_SECONDS,
                      "bedChannels": 2, "cueChannels": 1, "bedRmsDb": core.BED_RMS_DB, "cueLoudDb": core.CUE_LOUD_DB,
                      "bedLufs": core.BED_LUFS,
                      "level": "dB of gain to play a file at; a cue's is relative to its bed played at 0"},
           "biomes": []}
    for info in biomes():
        p = os.path.join(HERE, "index", info["id"] + ".json")
        if os.path.exists(p):
            frag = read_json(p)
            frag.pop("build", None)
            out["biomes"].append(frag)
    return out


# ---- checking --------------------------------------------------------------------------------------------------

def check(names, tmp):
    faults = []
    known = {b["id"]: b for b in biomes()}
    targets = names or [b for b in known]
    tk = toolkit_sha()
    for b in targets:
        frag_path = os.path.join(HERE, "index", b + ".json")
        has_recipe = os.path.exists(recipe_path(b))
        if not os.path.exists(frag_path):
            if has_recipe:
                faults.append("%s: has a recipe and has not been built" % b)
            print("%s: not built" % b)
            continue
        frag = read_json(frag_path)
        build = frag.get("build", {})
        print("%s:" % b)
        if not has_recipe:
            faults.append("%s: built, but recipes/%s.py is gone" % (b, b))
        elif build.get("recipe") != sha(recipe_path(b)):
            faults.append("%s: recipes/%s.py changed since it was built; build it again" % (b, b))
        if build.get("toolkit") != tk:
            print("  note: built with another version of lib/ (%s, now %s)" % (build.get("toolkit"), tk))
        if frag.get("calls") != calls(b):
            faults.append("%s: its calls differ from species/index.json's; build it again" % b)
        measured = {}
        for part in ("day", "night"):
            bed = frag.get("beds", {}).get(part)
            if not bed:
                faults.append("%s: no %s bed" % (b, part))
                continue
            m, f = check_file(os.path.join(HERE, bed["file"]), "bed", core.RATE * core.BED_SECONDS, 2, tmp, bed["bytes"],
                              part=part)
            if m:
                measured[part] = m
            kbps = build.get("bitrate", {}).get(part)
            print((bed_row(part, m, f) if m else "  %-24s %s" % (part, "; ".join(f)))
                  + ("  (%d kbps)" % (kbps // 1000) if kbps else ""))
            faults += ["%s: %s" % (bed["file"], x) for x in f]
        listed = set()
        bed_rms = {p: measured[p]["rms"] for p in measured}
        for c in frag.get("cues", []):
            listed.add(os.path.basename(c["file"]))
            frames = build.get("frames", {}).get(c["id"], int(round(c["seconds"] * core.RATE)))
            m, f = check_file(os.path.join(HERE, c["file"]), "cue", frames, 1, tmp, c["bytes"])
            if m:
                measured[c["id"]] = m
            print(cue_row(c["id"], m, f, c, bed_rms) if m else "  %-24s %s" % (c["id"], "; ".join(f)))
            faults += ["%s: %s" % (c["file"], x) for x in f]
        srows, sfaults = schedule(frag.get("cues", []), measured, b)
        for r in srows:
            print(r)
        faults += sfaults
        for p in glob.glob(os.path.join(HERE, "cues", b + "-*.ogg")):
            if os.path.basename(p) not in listed:
                faults.append("cues/%s is not in its index fragment" % os.path.basename(p))
        for p in frag.get("calls", []):
            if not os.path.exists(os.path.join(PACK_ROOT, p)):
                faults.append("%s: call %s does not exist" % (b, p))
    if not names:
        for p in glob.glob(os.path.join(HERE, "recipes", "*.py")):
            if os.path.basename(p)[:-3] not in known:
                faults.append("recipes/%s is not a biome in species/biomes.json" % os.path.basename(p))
        index_path = os.path.join(HERE, "index.json")
        if not os.path.exists(index_path):
            faults.append("index.json is missing; run build.py --index")
        elif read_json(index_path) != assemble():
            faults.append("index.json is not what the fragments in index/ make; run build.py --index")
    return faults


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("biomes", nargs="*")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--index", action="store_true")
    ap.add_argument("--wav", action="store_true")
    a = ap.parse_args()
    known = {b["id"]: b for b in biomes()}
    for b in a.biomes:
        if b not in known:
            ap.error("%s is not a biome (%s)" % (b, ", ".join(known)))
    with tempfile.TemporaryDirectory(prefix="qrx-soundscapes-") as tmp:
        if a.check:
            faults = check(a.biomes, tmp)
        elif a.index:
            write_json(os.path.join(HERE, "index.json"), assemble())
            print("index.json: %d biomes" % len(assemble()["biomes"]))
            faults = []
        else:
            names = a.biomes or [b for b in known if os.path.exists(recipe_path(b))]
            faults = []
            for b in names:
                if not os.path.exists(recipe_path(b)):
                    faults.append("%s: there is no recipes/%s.py" % (b, b))
                    continue
                faults += build_biome(b, known[b], tmp, a.wav)
            if not a.biomes:
                write_json(os.path.join(HERE, "index.json"), assemble())
                print("index.json: %d biomes" % len(assemble()["biomes"]))
    for f in faults:
        print("FAULT " + f)
    print("%d fault%s" % (len(faults), "" if len(faults) == 1 else "s"))
    sys.exit(1 if faults else 0)


if __name__ == "__main__":
    main()
