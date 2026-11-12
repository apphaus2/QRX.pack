#!/usr/bin/env python3
"""Turns the species definitions into creatures: a JsonScene document and a glTF model for each, and the catalog.

    python3 species/build.py                      build everything (creatures/, models/, index.json)
    python3 species/build.py --check              validate the definitions and what is on disk; exit 1 on a fault
    python3 species/build.py --model-base <base>  how the documents name their models: the URL they are served under
                                                  (the default is species/models/ under PACK, this repository's
                                                  address, below), or "bundle:" for models shipped inside an app

Standard library only (Python 3.9 or later). README.md describes the layout and how to add to it.
"""
import argparse, hashlib, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from lib import archetypes as archetype_package          # noqa: E402
from lib.behaviour import TEMPERS, logic                  # noqa: E402
from lib.builder import FEATURES, Builder, add_motes      # noqa: E402
from lib.gltf import inspect                              # noqa: E402
from lib import mind as minds                            # noqa: E402
from lib import sounds as voices                         # noqa: E402
from lib import tricks                                   # noqa: E402

GENERATOR = "QRX species/build.py"
PACK = "https://qrx-pack.apphaus.us/"              # where this repository is served: every address the build writes starts here
DEFAULT_SOUND_BASE = PACK + "species/sounds/"
DEFAULT_MODEL_BASE = PACK + "species/models/"     # pulled by URL from this repository through GitHub Pages; nothing is bundled
MAX_MODEL_BYTES = 96 * 1024        # 80 KB until 2026-11-12: a trick is a clip, and a legendary with a signature and four others needs the room
ID = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
DEFINITION_KEYS = {"id", "name", "species", "description", "biomes", "habitat", "rarity", "archetype", "size", "shape", "colours", "pattern", "movement", "behaviour", "prompt", "speech", "temperament", "voice", "tricks", "signature", "mind"}
REQUIRED_KEYS = {"id", "name", "species", "description", "biomes", "habitat", "rarity", "archetype", "size", "prompt"}
LIFE_NAME = re.compile(r"^[A-Z][A-Za-z' -]*$")


def read_json(*path):
    with open(os.path.join(HERE, *path), encoding="utf-8") as f:
        return json.load(f)


def dump(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


# ---- the data ------------------------------------------------------------------------------------------------

class Data:
    """rarity.json, habitats.json, biomes.json, reserved.json, the archetypes and every definition, with the faults
    found reading them."""

    def __init__(self):
        self.faults = []
        rarity = read_json("rarity.json")
        self.visitor_share = rarity.get("visitorShare", 1.0)
        self.rarities = {level["id"]: level for level in rarity["levels"]}
        self.habitats = {h["id"]: h for h in read_json("habitats.json")["habitats"]}
        self.biomes = {b["id"]: b for b in read_json("biomes.json")["biomes"]}
        self.reserved = read_json("reserved.json")
        self.life = read_json("life.json")       # what a spawned creature's own name and age are drawn from
        names, age = self.life.get("names"), self.life.get("age", {})
        if not isinstance(names, list) or len(names) < 16 or len(set(names)) != len(names) or not all(isinstance(n, str) and n.strip() == n and n for n in names):
            raise ValueError("life.json: names must be at least 16 different, trimmed, non-empty strings")
        if not (isinstance(age.get("minDays"), int) and isinstance(age.get("maxDays"), int) and 0 <= age["minDays"] < age["maxDays"]):
            raise ValueError("life.json: age needs whole minDays < maxDays")
        natures = self.life.get("temperaments")
        if not isinstance(natures, list) or not 6 <= len(natures) <= 8 or len(set(natures)) != len(natures) or not all(isinstance(n, str) and re.match(r"^[a-z]+$", n) for n in natures):
            raise ValueError("life.json: temperaments must be six to eight different lower-case adjectives")
        self.archetypes = archetype_package.load()
        self.mind = read_json("mind.json")       # what every creature's mind shares: tokens, registers, closing lines, budget, canned rules
        self.tricks = read_json("tricks.json")   # every trick: its phrases, and what a behaviour trick does
        self.sounds = read_json("sounds.json")   # the voices: a sound for each meaning
        self.meanings = list(self.sounds.get("meanings", {}))
        self.check_tables(rarity)
        self.check_voices()
        for fault in tricks.table_faults(self.tricks, self.meanings): self.fault("tricks.json", fault)
        for fault in minds.shared_faults(self.mind, TEMPERS, self.meanings): self.fault("mind.json", fault)
        for level in rarity["levels"]:
            if level.get("speech") not in self.mind.get("registers", {}): self.fault("rarity.json %s" % level.get("id"), "speech must be a register in mind.json (%s)" % ", ".join(self.mind.get("registers", {})))
        for name in self.archetypes:
            if self.mind.get("temperaments", {}).get(name) not in self.life["temperaments"]: self.fault("mind.json", "temperaments needs one of life.json's (%s) for the archetype %s" % (", ".join(self.life["temperaments"]), name))
        for name, module in self.archetypes.items():
            unknown = [t for t in getattr(module, "TRICKS", ()) if t not in self.tricks.get("tricks", {})]
            if unknown or not getattr(module, "TRICKS", ()): self.fault("archetype %s" % name, "TRICKS must list tricks from tricks.json%s" % (" (not %s)" % ", ".join(unknown) if unknown else ""))
            if name not in self.sounds.get("voices", {}): self.fault("sounds.json", "no voice for the archetype %s" % name)
        self.tokens = minds.known_tokens(self.mind)
        self.definitions = self.read_definitions()
        self.check_life()

    def fault(self, where, message):
        self.faults.append("%s: %s" % (where, message))

    def check_tables(self, rarity):
        if len(self.rarities) != len(rarity["levels"]): self.fault("rarity.json", "two levels share an id")
        if not 0 < self.visitor_share <= 1: self.fault("rarity.json", "visitorShare must be over 0 and at most 1")
        for level in rarity["levels"]:
            where = "rarity.json %s" % level.get("id")
            if not isinstance(level.get("weight"), (int, float)) or level["weight"] <= 0: self.fault(where, "weight must be a positive number")
            if not HEX.match(str(level.get("colour", ""))): self.fault(where, "colour must be #rrggbb")
            if any(f not in FEATURES for f in level.get("features", [])): self.fault(where, "features may be %s" % ", ".join(FEATURES))
            if not 0 <= level.get("glow", 0) <= 1: self.fault(where, "glow is 0 to 1")
            if not isinstance(level.get("maxBiomes"), int) or level["maxBiomes"] < 1: self.fault(where, "maxBiomes must be 1 or more")
            if not isinstance(level.get("tricks"), int) or level["tricks"] < 1: self.fault(where, "tricks is how many of its archetype's tricks a species knows beside the basics: 1 or more")
            vary = level.get("sound", {})
            if not isinstance(vary, dict) or set(vary) - {"pitch", "length"} or any(not isinstance(v, (int, float)) or not 0.5 <= v <= 2 for v in vary.values()): self.fault(where, "sound may set pitch and length, each 0.5 to 2")
        for h in self.habitats.values():
            where = "habitats.json %s" % h.get("id")
            for key in ("bounds", "wild"):
                box = h.get(key, {})
                if len(box.get("min", [])) != 3 or len(box.get("max", [])) != 3 or any(a >= b for a, b in zip(box["min"], box["max"])): self.fault(where, "%s needs min below max on three axes" % key)
            if h.get("mode") not in ("ground", "air"): self.fault(where, "mode is ground or air (JsonScene's mobility modes)")
            if h.get("origin") not in ("ground", "centre"): self.fault(where, "origin is ground or centre")
            if not h.get("move") or h["move"] == "idle": self.fault(where, "move names the moving clip (swim, walk, fly)")
            if h.get("anchor") not in ("code", "floor", "free"): self.fault(where, "anchor is code, floor or free")
            if len(h.get("size", [])) != 2 or not 0 < h["size"][0] < h["size"][1]: self.fault(where, "size is [smallest, largest] longest side in metres")
        codes = [b.get("code") for b in self.biomes.values()]
        if len(set(codes)) != len(codes): self.fault("biomes.json", "two biomes share a land-cover code")
        for biome in self.biomes.values():
            where = "biomes.json %s" % biome.get("id")
            if not ID.match(str(biome.get("id", ""))): self.fault(where, "id must be lower-case words joined by hyphens")
            if not isinstance(biome.get("code"), int): self.fault(where, "code must be the land-cover class number")
            if not HEX.match(str(biome.get("colour", ""))): self.fault(where, "colour must be #rrggbb")
            if not biome.get("name") or not biome.get("description"): self.fault(where, "needs a name and a description")
            home = biome.get("home")
            if not isinstance(home, str) or not home.strip() or home != home.strip() or "{" in home or "}" in home or "\n" in home or len(home) > 40:
                self.fault(where, "needs a short `home` phrase that reads after \"I live in\" (what {home} becomes there)")
            if not isinstance(biome.get("roster"), int) or biome["roster"] < 0: self.fault(where, "roster is the least number of species at home here")
        for name, module in self.archetypes.items():
            missing = [k for k in ("HABITAT", "ORIGIN", "LENGTH", "SHAPE", "COLOURS", "PATTERNS", "build") if not hasattr(module, k)]
            if missing: self.fault("archetype %s" % name, "lacks %s" % ", ".join(missing))

    def check_voices(self):
        """sounds.json: every voice gives every meaning a sound, its own or another meaning's."""
        table = self.sounds
        if not isinstance(table.get("rate"), int) or not self.meanings or set(table.get("limits", {})) != {"file", "species", "seconds"}:
            self.fault("sounds.json", "needs a rate, the meanings and limits (file, species, seconds)"); return
        for voice, entry in table.get("voices", {}).items():
            where = "sounds.json %s" % voice
            if not ID.match(voice): self.fault(where, "a voice's name is lower-case words joined by hyphens")
            if not isinstance(entry, dict) or set(entry) != set(self.meanings): self.fault(where, "must give exactly %s" % ", ".join(self.meanings)); continue
            for meaning, spec in entry.items():
                if isinstance(spec, str):
                    if spec == meaning or not isinstance(entry.get(spec), dict): self.fault(where, "%s borrows %r, which must be another meaning with a sound of its own" % (meaning, spec))
                elif not isinstance(spec, dict) or spec.get("kind") not in voices.KINDS or set(spec) - {"kind", "pitch", "length", "gain"} or any(not isinstance(spec.get(k, 1.0), (int, float)) or not 0.1 <= spec.get(k, 1.0) <= 4 for k in ("pitch", "length", "gain")):
                    self.fault(where, "%s needs a kind (%s) and may set pitch, length and gain" % (meaning, ", ".join(voices.KINDS)))

    def check_life(self):
        """A living creature's name must not be mistaken for a template's, and must sit safely in a prompt."""
        taken = {str(d.get("name", "")).lower(): d.get("id") for d in self.definitions.values()}
        defaults = {str(v).lower() for v in self.mind.get("tokens", {}).values()} | {str(b.get("home", "")).lower() for b in self.biomes.values()} | set(self.life["temperaments"])
        for name in self.life["names"]:
            if not LIFE_NAME.match(name): self.fault("life.json", "the name %r must be letters, starting with a capital (it is put into prompts and spoken)" % name)
            if name.lower() in taken: self.fault("life.json", "the name %s is the template name of %s; a living creature must not look like a copy of a template" % (name, taken[name.lower()]))
            if name in self.reserved["names"]: self.fault("life.json", "the name %s belongs to a QRX.pack creature" % name)
            if name.lower() in defaults: self.fault("life.json", "the name %s is what a token reads as by default" % name)

    def read_definitions(self):
        """Every definitions/<biome>/<id>.json, by id, in id order."""
        found, root = {}, os.path.join(HERE, "definitions")
        for folder in sorted(os.listdir(root)):
            if not os.path.isdir(os.path.join(root, folder)): continue
            if folder not in self.biomes: self.fault("definitions/%s" % folder, "is not a biome in biomes.json")
            for name in sorted(os.listdir(os.path.join(root, folder))):
                if not name.endswith(".json"): continue
                where = "definitions/%s/%s" % (folder, name)
                try: definition = read_json("definitions", folder, name)
                except ValueError as error:
                    self.fault(where, "does not parse: %s" % error); continue
                if not isinstance(definition, dict): self.fault(where, "is not an object"); continue
                if definition.get("id") != name[:-5]: self.fault(where, "its id must be the file's name")
                if definition.get("id") in found: self.fault(where, "the id %s is used twice" % definition.get("id")); continue
                if isinstance(definition.get("biomes"), list) and definition["biomes"] and definition["biomes"][0] != folder:
                    self.fault(where, "is filed under %s but its home biome (the first of biomes) is %s" % (folder, definition["biomes"][0]))
                definition["_where"] = where
                found[name[:-5]] = definition
        return dict(sorted(found.items()))

    # ---- one definition ----

    def check_definition(self, d):
        """The faults in one definition; an empty list means it can be built."""
        faults = []
        bad = lambda message: faults.append("%s: %s" % (d["_where"], message))
        for key in sorted(REQUIRED_KEYS - set(d)): bad("needs \"%s\"" % key)
        for key in sorted(set(d) - DEFINITION_KEYS - {"_where"}): bad("unknown key \"%s\"" % key)
        if faults: return faults
        if not ID.match(str(d["id"])): bad("id must be lower-case words joined by hyphens")
        if d["id"] in self.reserved["ids"]: bad("the id %s is one QRX.pack uses" % d["id"])
        for key in ("name", "species", "description"):
            if not isinstance(d[key], str) or not d[key].strip() or "\n" in d[key]: bad("%s must be one line of text" % key)
        if isinstance(d["name"], str) and d["name"] in self.reserved["names"]: bad("the name %s belongs to a QRX.pack creature" % d["name"])
        if isinstance(d["description"], str) and len(d["description"]) > 160: bad("description is over 160 characters")
        prompt, limits = d["prompt"], self.mind.get("prompt", {})
        if not isinstance(prompt, str) or not prompt.strip() or "\n" in prompt or prompt != prompt.strip(): bad("prompt must be one line of text")
        else:
            if not limits.get("min", 0) <= len(prompt) <= limits.get("max", 10 ** 6): bad("prompt is %d characters; it should be %d to %d (it is sent with every turn)" % (len(prompt), limits.get("min", 0), limits.get("max", 0)))
            for fault in minds.token_faults(prompt, self.tokens): bad("prompt " + fault)
            if "name" not in minds.tokens_in(prompt): bad("prompt must use {name}")
            if not re.match(r"^I\b", prompt): bad("prompt is the creature speaking: it starts with \"I\"")
            if prompt.startswith("$") or "${" in prompt or "*" in prompt: bad("prompt must be plain text (no $, no asterisks)")
        if "temperament" in d and d["temperament"] not in self.life["temperaments"]: bad("temperament is one of life.json's: %s" % ", ".join(self.life["temperaments"]))
        if "speech" in d and d["speech"] not in self.mind.get("registers", {}): bad("speech is one of %s" % ", ".join(self.mind.get("registers", {})))
        if "voice" in d and d["voice"] not in self.sounds.get("voices", {}): bad("voice is one of the voices in sounds.json (%s)" % ", ".join(self.sounds.get("voices", {})))
        if "mind" in d and (not isinstance(d["mind"], dict) or not d["mind"] or any(key not in minds.MIND_KEYS for key in d["mind"])): bad("mind may replace %s" % ", ".join(minds.MIND_KEYS))
        rarity, habitat, archetype = self.rarities.get(d["rarity"]), self.habitats.get(d["habitat"]), self.archetypes.get(d["archetype"])
        if rarity is None: bad("unknown rarity \"%s\"" % d["rarity"])
        if habitat is None: bad("unknown habitat \"%s\"" % d["habitat"])
        if archetype is None: bad("unknown archetype \"%s\"" % d["archetype"])
        biomes = d["biomes"]
        if not isinstance(biomes, list) or not biomes or any(not isinstance(x, str) for x in biomes): bad("biomes must be a list of biome ids, home first")
        else:
            for biome in biomes:
                if biome not in self.biomes: bad("unknown biome \"%s\"" % biome)
            if len(set(biomes)) != len(biomes): bad("a biome is listed twice")
            if rarity and len(biomes) > rarity["maxBiomes"]: bad("a %s species may be found in at most %d biome(s), not %d" % (d["rarity"], rarity["maxBiomes"], len(biomes)))
        if not isinstance(d["size"], (int, float)) or isinstance(d["size"], bool) or d["size"] <= 0: bad("size must be a length in metres")
        if habitat and archetype and habitat["origin"] != archetype.ORIGIN:
            bad("a %s keeps its origin at the %s, but the %s habitat needs it at the %s" % (d["archetype"], archetype.ORIGIN, d["habitat"], habitat["origin"]))
        if archetype:
            choices = getattr(archetype, "CHOICES", {})
            for key, value in d.get("shape", {}).items():
                if key not in archetype.SHAPE: bad("the %s archetype has no shape parameter \"%s\" (it has %s)" % (d["archetype"], key, ", ".join(archetype.SHAPE))); continue
                default = archetype.SHAPE[key]
                number = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)
                if isinstance(default, bool): ok = isinstance(value, bool)
                elif number(default): ok = number(value)
                elif isinstance(default, list): ok = isinstance(value, list) and len(value) == len(default) and all(number(v) for v in value)
                else: ok = isinstance(value, str)
                if not ok: bad("shape.%s must be like %s" % (key, json.dumps(default)))
                elif key in choices and value not in choices[key]: bad("shape.%s is one of %s" % (key, ", ".join(choices[key])))
            for slot, colour in d.get("colours", {}).items():
                if slot not in archetype.COLOURS: bad("the %s archetype has no colour \"%s\" (it has %s)" % (d["archetype"], slot, ", ".join(archetype.COLOURS)))
                elif not HEX.match(str(colour)): bad("colours.%s must be #rrggbb" % slot)
            pattern = d.get("pattern", {"type": "plain"})
            if not isinstance(pattern, dict) or pattern.get("type") not in archetype.PATTERNS: bad("pattern.type is one of %s" % ", ".join(archetype.PATTERNS))
        movement = d.get("movement", {})
        for key, value in movement.items():
            if key in ("speed", "turnRate"):
                if not isinstance(value, (int, float)) or value <= 0: bad("movement.%s must be a positive number" % key)
            elif key == "pause":
                if not isinstance(value, list) or len(value) != 2 or not 0 <= value[0] <= value[1]: bad("movement.pause is [shortest, longest] seconds")
            else: bad("unknown movement key \"%s\"" % key)
        behaviour = d.get("behaviour", {})
        if behaviour.get("temper", "shy") not in TEMPERS: bad("behaviour.temper is one of %s" % ", ".join(TEMPERS))
        if archetype and rarity and not self.faults:
            for fault in tricks.species_faults(self.tricks, d, archetype, rarity): bad("tricks: " + fault)
        for key in behaviour:
            if key not in ("temper", "distance", "seconds", "watch"): bad("unknown behaviour key \"%s\"" % key)
        return faults


# ---- building --------------------------------------------------------------------------------------------------

def model_reference(base, species_id):
    """How a document names a species' model under `base`."""
    if base.endswith(":") or base.endswith("/") or base == "": return "%s%s.glb" % (base, species_id)
    return "%s/%s.glb" % (base, species_id)


def sound_base_for(model_base):
    """Where the sounds are, beside the models: the same address with sounds/ for models/."""
    if model_base.endswith("models/"): return model_base[:-len("models/")] + "sounds/"
    return model_base if model_base.endswith(":") else DEFAULT_SOUND_BASE


def species_sounds(data, d):
    """{meaning: (file name, spec, pitch, length)} for a species: its voice (its definition's, or its archetype's)
    with its rarity's variation. A meaning that borrows another's sound gets that one's file."""
    voice, vary = d.get("voice", d["archetype"]), data.rarities[d["rarity"]].get("sound", {})
    pitch, length = vary.get("pitch", 1.0), vary.get("length", 1.0)
    specs, out = voices.resolve(data.sounds["voices"], voice), {}
    for meaning in data.meanings:
        out[meaning] = (voices.file_name(voice, voices.source(data.sounds["voices"], voice, meaning), pitch, length), specs[meaning], pitch, length)
    return out


def build_model(data, d):
    """The .glb for one definition, and what was made: the archetype's sockets and each trick clip's seconds."""
    archetype, rarity, habitat = data.archetypes[d["archetype"]], data.rarities[d["rarity"]], data.habitats[d["habitat"]]
    known = tricks.known(data.tricks, d, archetype, rarity)
    b = Builder(d, rarity, archetype, GENERATOR, known)
    made = dict(archetype.build(b) or {})
    if rarity.get("motes") and b.has("motes"): add_motes(b, int(rarity["motes"]))
    if set(b.model.clips) != {"idle", "move"} | set(b.made): raise ValueError("the %s archetype made the clips %s, not idle, move and its tricks" % (d["archetype"], sorted(b.model.clips)))
    clash = set(b.made) & {"idle", "move", habitat["move"]}
    if clash: raise ValueError("a trick is named like a clip the habitat plays: %s" % ", ".join(sorted(clash)))
    for trick_id in known:
        if tricks.handler(data.tricks, d, trick_id, b.made) is None: raise ValueError("the %s archetype animates no %s and tricks.json gives it nothing to do" % (d["archetype"], trick_id))
    b.model.rename_clip("move", habitat["move"])
    made["tricks"] = {trick_id: b.made[trick_id] for trick_id in known if trick_id in b.made}
    return b.model.to_bytes(), made


def build_document(data, d, made, model_base, sound_base):
    """The creature's scene, in the shape of QRX.pack's creature-*.json with the body inlined."""
    habitat, rarity, archetype = data.habitats[d["habitat"]], data.rarities[d["rarity"]], data.archetypes[d["archetype"]]
    movement, wild = d.get("movement", {}), habitat["wild"]
    behaviour = d.get("behaviour", {})
    temper = behaviour.get("temper", "shy")
    state, behaviors, on = logic(behaviour, movement.get("pause", habitat["pause"]))
    mobility = {"mode": habitat["mode"], "speed": movement.get("speed", habitat["speed"]), "turnRate": movement.get("turnRate", habitat["turnRate"])}
    if habitat["mode"] == "air": mobility["altitude"] = [wild["min"][1], wild["max"][1]]
    mobility.update(idle="idle", move=habitat["move"])
    known = tricks.known(data.tricks, d, archetype, rarity)
    animations = {"idle": {"clip": "idle", "loop": True}, habitat["move"]: {"clip": habitat["move"], "loop": True}}
    for trick_id in made["tricks"]: animations[trick_id] = {"clip": trick_id, "loop": False}
    # What the actor does by itself, whoever is or is not listening: its sounds when tapped or approached, and its tricks.
    on["tap"] = [{"sound": data.mind["on"]["tap"][temper]}] + on["tap"]
    on["near"] = ([] if temper == "shy" else [{"lookAt": "user"}]) + [{"sound": data.mind["on"]["near"][temper]}]
    for trick_id in known: on[trick_id] = tricks.handler(data.tricks, d, trick_id, made["tricks"])
    return {
        "_ui": {"version": 1, "habitat": d["habitat"], "species": d["id"], "rarity": d["rarity"], "biome": d["biomes"][0], "biomes": list(d["biomes"]),
                "tokens": minds.header_tokens(data.mind, d, data.biomes), "homes": minds.homes(d, data.biomes),
                "tricks": tricks.header(data.tricks, d, known), "state": state},
        "type": "Scene",
        "anchor": habitat["anchor"],
        "bounds": {"min": list(wild["min"]), "max": list(wild["max"])},
        "actors": [{
            "id": actor_id(d),
            "name": d["name"],
            "transform": {"position": list(habitat["start"]), "rotation": [0, 90, 0]},
            "body": {
                "model": model_reference(model_base, d["id"]),
                "scale": 1,
                "animations": animations,
                "sounds": {meaning: sound_base + name for meaning, (name, _, _, _) in species_sounds(data, d).items()},
                "sockets": dict(made.get("sockets", {})),
            },
            "mobility": mobility,
            "behaviors": behaviors,
            "mind": minds.build(data.mind, d, minds.register(d, rarity), tricks.canned(data.tricks, d, known)),
            "on": on,
        }],
    }


def actor_id(d):
    return re.sub(r"[^a-z0-9]+", "_", d["name"].lower()).strip("_")


def spawn_weight(data, rarity, home):
    """A species' weight in a biome: its rarity's, or `visitorShare` of it away from home."""
    weight = data.rarities[rarity]["weight"] * (1 if home else data.visitor_share)
    return int(weight) if float(weight).is_integer() else round(weight, 4)


def spawn_tables(data, definitions):
    """For each biome, what can spawn there and how likely: the species at home in it at their rarity's weight,
    and the visitors from other biomes at `visitorShare` of theirs."""
    tables = {}
    for biome in data.biomes:
        rows = []
        for d in definitions:
            if biome not in d["biomes"]: continue
            home = d["biomes"][0] == biome
            rows.append({"species": d["id"], "rarity": d["rarity"], "weight": spawn_weight(data, d["rarity"], home), "home": home})
        order = list(data.rarities)
        rows.sort(key=lambda r: (not r["home"], order.index(r["rarity"]), r["species"]))
        tables[biome] = rows
    return tables


def total_weight(rows):
    total = sum(row["weight"] for row in rows)
    return int(total) if float(total).is_integer() else round(total, 4)


def build_all(data, model_base, sound_base):
    """Every output file as {relative path: bytes}, with the faults met on the way. Definitions with faults are
    left out, so one bad file does not hide the rest."""
    outputs, faults, entries, good = {}, [], [], []
    for d in data.definitions.values():
        found = data.check_definition(d)
        if found: faults += found; continue
        try:
            glb, made = build_model(data, d)
            document = build_document(data, d, made, model_base, sound_base)
            sounds = species_sounds(data, d)
            actor = document["actors"][0]
            cost = minds.turn_estimate(d["name"], actor["mind"], actor["body"]["animations"], actor["body"]["sounds"], [b["type"] for b in actor["behaviors"]])
            if cost > actor["mind"]["budget"]["perTurn"]: raise ValueError("a turn with a full history is about %d tokens, over its mind's perTurn of %d: JsonMind would stop asking the model" % (cost, actor["mind"]["budget"]["perTurn"]))
            for name, spec, pitch, length in sounds.values():
                if "sounds/" + name not in outputs: outputs["sounds/" + name] = voices.synthesize(spec, data.sounds["rate"], pitch, length)
        except Exception as error:      # an archetype's own fault, reported against the definition that met it
            faults.append("%s: could not be built: %s: %s" % (d["_where"], type(error).__name__, error)); continue
        model_faults, facts = inspect(glb)
        if model_faults: faults += ["%s: the model it builds: %s" % (d["_where"], f) for f in model_faults]; continue
        outputs["models/%s.glb" % d["id"]] = glb
        outputs["creatures/%s.json" % d["id"]] = dump(document)
        box = facts["box"]
        good.append(d)
        entries.append({
            "id": d["id"], "name": d["name"], "species": d["species"], "description": d["description"],
            "biome": d["biomes"][0], "biomes": list(d["biomes"]), "habitat": d["habitat"], "rarity": d["rarity"],
            "weight": data.rarities[d["rarity"]]["weight"], "archetype": d["archetype"],
            "document": "creatures/%s.json" % d["id"], "model": "models/%s.glb" % d["id"], "modelRef": model_reference(model_base, d["id"]),
            "size": [round(box[1][i] - box[0][i], 4) for i in range(3)], "bytes": len(glb), "triangles": facts["triangles"],
            "speech": minds.register(d, data.rarities[d["rarity"]]), "sounds": {meaning: "sounds/" + name for meaning, (name, _, _, _) in sounds.items()},
        })
    tables = spawn_tables(data, good)
    index = {
        "version": 1,
        "modelBase": model_base,
        "soundBase": sound_base,
        "visitorShare": data.visitor_share,
        "life": {"names": list(data.life["names"]), "age": {"minDays": data.life["age"]["minDays"], "maxDays": data.life["age"]["maxDays"]}, "temperaments": list(data.life["temperaments"])},
        "rarities": [{"id": r["id"], "name": r["name"], "weight": r["weight"], "colour": r["colour"]} for r in data.rarities.values()],
        "habitats": [{"id": h["id"], "name": h["name"]} for h in data.habitats.values()],
        "codes": {str(b["code"]): b["id"] for b in sorted(data.biomes.values(), key=lambda b: b["code"])},
        "biomes": [{"id": b["id"], "code": b["code"], "name": b["name"], "worldcover": b.get("worldcover", b["name"]), "colour": b["colour"], "home": b.get("home", ""), "description": b["description"],
                    "weight": total_weight(tables[b["id"]]), "spawns": tables[b["id"]]}
                   for b in sorted(data.biomes.values(), key=lambda b: b["code"])],
        "species": entries,
    }
    outputs["index.json"] = dump(index)
    outputs["ROSTER.md"] = roster(data, index).encode("utf-8")
    return outputs, faults


def roster(data, index):
    """ROSTER.md: every species by the biome it is at home in, written from the catalog."""
    species = {entry["id"]: entry for entry in index["species"]}
    lines = ["# The roster", "", "**Spoilers.** This lists every creature's tricks, which players are meant to find out for themselves. The apps never show it.", "",
             "Written by `build.py` from the definitions; do not edit. %d species in %d biomes." % (len(species), len(index["biomes"])), ""]
    lines += ["| biome | WorldCover | at home | " + " | ".join(data.rarities) + " | " + " | ".join(data.habitats) + " | visiting |",
              "| --- | --- | --- |" + " --- |" * (len(data.rarities) + len(data.habitats) + 1)]
    for biome in index["biomes"]:
        home = [species[row["species"]] for row in biome["spawns"] if row["home"]]
        lines.append("| %s (`%s`) | %d %s | %d | %s | %s | %d |" % (
            biome["name"], biome["id"], biome["code"], biome["worldcover"], len(home),
            " | ".join(str(sum(1 for e in home if e["rarity"] == r)) for r in data.rarities),
            " | ".join(str(sum(1 for e in home if e["habitat"] == h)) for h in data.habitats), len(biome["spawns"]) - len(home)))
    for biome in index["biomes"]:
        lines += ["", "## %s (`%s`, WorldCover %d: %s)" % (biome["name"], biome["id"], biome["code"], biome["worldcover"]), "", biome["description"], "",
                  "| creature | species | rarity | habitat | archetype | speaks | tricks | chance here | also found in |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        for row in biome["spawns"]:
            entry = species[row["species"]]
            if not row["home"]: continue
            d = data.definitions[entry["id"]]
            known = tricks.known(data.tricks, d, data.archetypes[d["archetype"]], data.rarities[d["rarity"]])
            sign = (d.get("signature") or {}).get("id")
            lines.append("| %s | %s (`%s`) | %s | %s | %s | %s | %s | %.2f%% | %s |" % (entry["name"], entry["species"], entry["id"], entry["rarity"], entry["habitat"], entry["archetype"], entry["speech"],
                                                                                   ", ".join("**%s**" % t if t == sign else t for t in known), 100.0 * row["weight"] / biome["weight"], ", ".join(entry["biomes"][1:])))
        visitors = ["%s (%s, %.2f%%)" % (species[row["species"]]["name"], species[row["species"]]["biome"], 100.0 * row["weight"] / biome["weight"]) for row in biome["spawns"] if not row["home"]]
        if visitors: lines += ["", "Visiting from other biomes: %s." % ", ".join(visitors)]
    lines += ["", "## What to say", "", "Each trick answers to any of its phrases, said on their own or inside a sentence.", "", "| trick | phrases |", "| --- | --- |"]
    for trick_id, entry in data.tricks["tricks"].items(): lines.append("| %s | %s |" % (trick_id, ", ".join(entry["phrases"])))
    for d in data.definitions.values():
        if isinstance(d.get("signature"), dict): lines.append("| **%s** (%s only) | %s |" % (d["signature"]["id"], d["name"], ", ".join(d["signature"]["phrases"])))
    return "\n".join(lines) + "\n"


def write_all(outputs):
    """Writes the outputs and removes creatures, models and sounds no definition makes any more."""
    for folder in ("creatures", "models", "sounds"):
        os.makedirs(os.path.join(HERE, folder), exist_ok=True)
        for name in os.listdir(os.path.join(HERE, folder)):
            if "%s/%s" % (folder, name) not in outputs and name.endswith((".json", ".glb", ".wav")): os.remove(os.path.join(HERE, folder, name))
    for path, content in outputs.items():
        with open(os.path.join(HERE, path), "wb") as f: f.write(content)


# ---- checking --------------------------------------------------------------------------------------------------

def check_model(data, d, glb, where):
    """(faults, facts) for one species' .glb: it parses, has the clips its habitat plays, fits the habitat and
    stands where its habitat expects. No facts means it could not be read."""
    habitat, faults = data.habitats[d["habitat"]], []
    model_faults, facts = inspect(glb)
    if model_faults: return ["%s: %s" % (where, f) for f in model_faults], {}
    if len(glb) > MAX_MODEL_BYTES: faults.append("%s: %d bytes, over the %d allowed" % (where, len(glb), MAX_MODEL_BYTES))
    for clip in ("idle", habitat["move"]):
        if clip not in facts["clips"]: faults.append("%s: no clip named %s" % (where, clip))
    known = tricks.known(data.tricks, d, data.archetypes[d["archetype"]], data.rarities[d["rarity"]])
    extra = sorted(set(facts["clips"]) - {"idle", habitat["move"]} - set(known))
    if extra: faults.append("%s: clips nothing plays: %s" % (where, ", ".join(extra)))
    lo, hi = facts["box"]
    longest = max(hi[i] - lo[i] for i in range(3))
    if not habitat["size"][0] <= longest <= habitat["size"][1]:
        faults.append("%s: its longest side is %.3f m; a %s creature is %.2f to %.2f m" % (where, longest, d["habitat"], habitat["size"][0], habitat["size"][1]))
    # The clips that loop (idle and the moving one) must keep the creature compact; a trick may fling it about,
    # but not out of the habitat.
    looping = [facts["clips"][clip]["swept"] for clip in ("idle", habitat["move"]) if clip in facts["clips"]]
    swept = [[min([lo[i]] + [box[0][i] for box in looping]) for i in range(3)], [max([hi[i]] + [box[1][i] for box in looping]) for i in range(3)]]
    for axis, i in (("wide", 0), ("tall", 1), ("long", 2)):
        room = habitat["bounds"]["max"][i] - habitat["bounds"]["min"][i]
        if swept[1][i] - swept[0][i] > room / 2: faults.append("%s: %.3f m %s in motion, over half the %s's %.2f m" % (where, swept[1][i] - swept[0][i], axis, habitat["name"], room))
        for clip, measured in facts["clips"].items():
            reach = measured["swept"][1][i] - measured["swept"][0][i]
            if clip not in ("idle", habitat["move"]) and reach > room: faults.append("%s: the trick %s takes it %.3f m %s, more than the %s's %.2f m" % (where, clip, reach, axis, habitat["name"], room))
    if habitat["origin"] == "ground":
        if not -0.004 <= lo[1] <= 0.004: faults.append("%s: stands %.4f m off the ground (its lowest point should be at 0)" % (where, lo[1]))
    elif not all(lo[i] < 0 < hi[i] for i in range(3)): faults.append("%s: the origin is outside the body; a swimmer's or flier's is at mid-body" % where)
    if any(swept[0][i] < lo[i] - 0.5 * longest or swept[1][i] > hi[i] + 0.5 * longest for i in range(3)):
        faults.append("%s: a clip throws part of it more than half its length outside its resting box" % where)
    eyes = facts.get("eyes")
    if eyes is not None and eyes < lo[2] + (hi[2] - lo[2]) / 3: faults.append("%s: its eyes are in the rear third; the head goes along +Z" % where)
    return faults, facts


def check_outputs(data, outputs, model_base, sound_base):
    """Faults in what is on disk: against what the definitions build now, and each file on its own terms."""
    faults = []
    on_disk = {}
    for path in outputs:
        try:
            with open(os.path.join(HERE, path), "rb") as f: on_disk[path] = f.read()
        except OSError:
            faults.append("%s: missing; run build.py" % path)
    for folder in ("creatures", "models", "sounds"):
        for name in sorted(os.listdir(os.path.join(HERE, folder))) if os.path.isdir(os.path.join(HERE, folder)) else []:
            if "%s/%s" % (folder, name) not in outputs: faults.append("%s/%s: no definition makes this file" % (folder, name))
    for path, content in on_disk.items():
        if content != outputs[path]: faults.append("%s: differs from what the definitions build now (edited by hand, or stale); run build.py" % path)

    try: index = json.loads(on_disk.get("index.json", b"{}"))
    except ValueError as error: return faults + ["index.json: does not parse: %s" % error]
    listed = {entry.get("id"): entry for entry in index.get("species", [])}
    if len(listed) != len(index.get("species", [])): faults.append("index.json: a species is listed twice")
    names = {}
    for d in data.definitions.values():
        if not isinstance(d.get("name"), str): continue
        if actor_id(d) in names: faults.append("%s: the name %s is also %s's; names are how a player tells creatures apart" % (d["_where"], d["name"], names[actor_id(d)]))
        names[actor_id(d)] = d["id"]

    for d in data.definitions.values():
        if data.check_definition(d): continue
        sid, where = d["id"], "models/%s.glb" % d["id"]
        habitat = data.habitats[d["habitat"]]
        if sid not in listed: faults.append("index.json: %s is not listed" % sid)
        if where not in on_disk or "creatures/%s.json" % sid not in on_disk: continue

        # The model, read back from disk by the reader; and, when the disk is stale, the one the definition builds now.
        glb = on_disk[where]
        model_faults, facts = check_model(data, d, glb, where)
        faults += model_faults
        if glb != outputs[where]: faults += check_model(data, d, outputs[where], "%s: the model it builds now" % d["_where"])[0]
        if not facts: continue

        # The document.
        path = "creatures/%s.json" % sid
        try: doc = json.loads(on_disk[path])
        except ValueError as error:
            faults.append("%s: does not parse: %s" % (path, error)); continue
        bad = lambda message: faults.append("%s: %s" % (path, message))
        header = doc.get("_ui", {})
        if header.get("version") != 1: bad("_ui.version is not 1")
        archetype, rarity = data.archetypes[d["archetype"]], data.rarities[d["rarity"]]
        known = tricks.known(data.tricks, d, archetype, rarity)
        expected = {"habitat": d["habitat"], "species": sid, "rarity": d["rarity"], "biome": d["biomes"][0], "biomes": d["biomes"],
                    "tokens": minds.header_tokens(data.mind, d, data.biomes), "homes": minds.homes(d, data.biomes), "tricks": tricks.header(data.tricks, d, known)}
        for key, value in expected.items():
            if header.get(key) != value: bad("_ui.%s is %r, not %r" % (key, header.get(key), value))
        if doc.get("type") != "Scene": bad("type is not Scene")
        if doc.get("anchor") != habitat["anchor"]: bad("anchor is not %s" % habitat["anchor"])
        if doc.get("bounds") != {"min": habitat["wild"]["min"], "max": habitat["wild"]["max"]}: bad("bounds are not the %s habitat's" % d["habitat"])
        actors = doc.get("actors", [])
        if len(actors) != 1: bad("has %d actors, not 1" % len(actors)); continue
        actor = actors[0]
        if actor.get("name") != d["name"] or not re.match(r"^[a-z0-9_]+$", str(actor.get("id", ""))): bad("the actor's id or name is wrong")
        body, mobility = actor.get("body", {}), actor.get("mobility")
        if not isinstance(mobility, dict): bad("the actor has no mobility, so it is not a creature"); continue
        if body.get("model") != model_reference(model_base, sid): bad("body.model is %r, not %r" % (body.get("model"), model_reference(model_base, sid)))
        for role in ("idle", "move"):
            name = mobility.get(role)
            clip = body.get("animations", {}).get(name, {}).get("clip")
            if clip is None: bad("mobility.%s names the animation %r, which the body lacks" % (role, name))
            elif clip not in facts["clips"]: bad("the animation %s plays the clip %r, which the model lacks" % (name, clip))
        for socket, node in body.get("sockets", {}).items():
            if node not in facts["nodes"]: bad("the socket %s names the node %r, which the model lacks" % (socket, node))
        if mobility.get("mode") != habitat["mode"]: bad("mobility.mode is not %s" % habitat["mode"])
        if habitat["mode"] == "air":
            low, high = mobility.get("altitude", [None, None])
            if low is None or not doc["bounds"]["min"][1] <= low < high <= doc["bounds"]["max"][1]: bad("mobility.altitude is outside the bounds")
        keys = set(header.get("state", {}))
        used = set(re.findall(r"\"\$([A-Za-z_][A-Za-z0-9_]*)\"", json.dumps(actor)))
        for behaviour in actor.get("behaviors", []):
            if behaviour.get("type") not in ("idle", "wander", "approach", "flee", "follow", "patrol", "lookAt", "perchOn", "flyTo", "goTo"): bad("unknown behavior type %r" % behaviour.get("type"))
        if used - keys: bad("binds state it does not declare: %s" % ", ".join(sorted(used - keys)))

        # The sounds: one for each meaning, each a small quiet WAV on disk.
        sounds, heard, total = species_sounds(data, d), body.get("sounds", {}), 0
        if list(heard) != data.meanings: bad("body.sounds must name exactly %s" % ", ".join(data.meanings))
        for name in sorted({name for name, _, _, _ in sounds.values()}):
            if "sounds/" + name not in on_disk: bad("its sound %s is missing" % name); continue
            found, measured = voices.inspect(on_disk["sounds/" + name], data.sounds["rate"], data.sounds["limits"])
            faults += ["sounds/%s: %s" % (name, f) for f in found]
            total += len(on_disk["sounds/" + name])
        for meaning, (name, _, _, _) in sounds.items():
            if heard.get(meaning) != sound_base + name: bad("body.sounds.%s is %r, not %r" % (meaning, heard.get(meaning), sound_base + name))
        if total > data.sounds["limits"]["species"]: bad("its sounds are %d bytes together, over the %d allowed" % (total, data.sounds["limits"]["species"]))

        # The tricks: listed in the header, each an event the actor's own handler answers, each clip a one-shot.
        handlers, listed_tricks = actor.get("on", {}), header.get("tricks", [])
        if not listed_tricks: bad("knows no tricks")
        for trick in listed_tricks if isinstance(listed_tricks, list) else []:
            tid = trick.get("id")
            faults += ["%s: %s" % (path, f) for f in tricks.phrase_faults("the trick %s" % tid, trick.get("phrases")) + tricks.command_faults("the trick %s" % tid, trick.get("do"), data.meanings)]
            steps = handlers.get(tid)
            if trick.get("do") != [{"emit": tid}] or not steps: bad("the trick %s must emit its own event, and the actor must have an on.%s handler" % (tid, tid)); continue
            faults += ["%s: %s" % (path, f) for f in tricks.command_faults("on.%s" % tid, steps, data.meanings)]
            for step in steps:
                if "play" not in step: continue
                animation = body.get("animations", {}).get(step["play"])
                if animation is None or animation.get("clip") not in facts["clips"]: bad("the trick %s plays %r, which the body or the model lacks" % (tid, step["play"]))
                elif animation.get("loop") is not False: bad("the trick %s plays %r, which loops; a trick is done once" % (tid, step["play"]))
        declared = {a.get("clip") for a in body.get("animations", {}).values()}
        if set(facts["clips"]) - declared: bad("the model has clips the body does not declare: %s" % ", ".join(sorted(set(facts["clips"]) - declared)))
        for event in ("tap", "near"):
            if not any("sound" in step for step in handlers.get(event, [])): bad("on.%s makes no sound" % event)
        if "spoken" in handlers: bad("an on.spoken handler would answer beside the mind; being spoken to is the mind's")

        # The mind: the definition's prompt as its persona, tokens the header can fill, parts JsonMind will act on.
        mind = actor.get("mind")
        if not isinstance(mind, dict) or not isinstance(mind.get("persona"), str): bad("the actor has no mind, so it cannot be talked to"); continue
        if mind != minds.build(data.mind, d, minds.register(d, rarity), tricks.canned(data.tricks, d, known)): bad("the mind is not the one its definition, mind.json and tricks.json make")
        if not mind["persona"].startswith(d["prompt"]): bad("the mind's persona does not begin with the definition's prompt")
        if data.mind["secret"] not in mind["persona"]: bad("the persona does not tell the creature to keep its tricks secret")
        tokens = header.get("tokens", {})
        for fault in minds.token_faults(mind["persona"], list(tokens)): bad("the persona " + fault)
        if list(tokens) != data.tokens: bad("_ui.tokens has %s, the known tokens are %s" % (", ".join(tokens), ", ".join(data.tokens)))
        if "name" not in minds.tokens_in(mind["persona"]): bad("the persona does not use {name}")
        if set(header.get("homes", {})) != set(d["biomes"]): bad("_ui.homes does not cover exactly the species' biomes")
        elif tokens.get("home") != header["homes"].get(d["biomes"][0]): bad("_ui.tokens.home is not the home biome's phrase")
        for fault in minds.mind_faults(mind, data.meanings, set(handlers)): bad("mind: " + fault)
        for trick in listed_tricks if isinstance(listed_tricks, list) else []:
            said = "spoken can you %s please" % (trick.get("phrases") or [""])[0]
            first = next((rule for rule in mind.get("canned", []) if re.search(rule["match"], said, re.IGNORECASE)), None)
            if first is None or first.get("do") != [{"emit": trick.get("id")}]: bad("with no model, saying %r would not do the trick %s" % (said[7:], trick.get("id")))
        if isinstance(mind.get("budget"), dict) and isinstance(mind["budget"].get("perTurn"), int):
            cost = minds.turn_estimate(d["name"], mind, body.get("animations", {}), heard, [b.get("type") for b in actor.get("behaviors", [])])
            if cost > mind["budget"]["perTurn"]: bad("a turn with a full history is about %d tokens, over the mind's perTurn of %d: JsonMind would stop asking the model and fall back to the canned rules" % (cost, mind["budget"]["perTurn"]))

        entry = listed.get(sid, {})
        for key, value in (("biome", d["biomes"][0]), ("biomes", d["biomes"]), ("habitat", d["habitat"]), ("rarity", d["rarity"]), ("weight", data.rarities[d["rarity"]]["weight"]),
                           ("bytes", len(glb)), ("document", path), ("model", where), ("speech", minds.register(d, rarity))):
            if sid in listed and entry.get(key) != value: faults.append("index.json: %s.%s is %r, not %r" % (sid, key, entry.get(key), value))

    # Tricks are for the player to find: the catalog must not list them. Signature tricks are one species' alone.
    if b'"tricks"' in on_disk.get("index.json", b"") or b'"phrases"' in on_disk.get("index.json", b""): faults.append("index.json: lists tricks; they belong only in each creature's document")
    signed, spoken_for = {}, {}
    for d in data.definitions.values():
        signature = d.get("signature")
        if data.check_definition(d) or not isinstance(signature, dict): continue
        if signature["id"] in signed: faults.append("%s: the signature trick %s is also %s's" % (d["_where"], signature["id"], signed[signature["id"]]))
        signed[signature["id"]] = d["id"]
        for phrase in signature["phrases"]:
            if phrase in spoken_for: faults.append("%s: the signature phrase %r is also %s's" % (d["_where"], phrase, spoken_for[phrase]))
            spoken_for[phrase] = d["id"]

    # The biomes: rosters, rarities, and the spawn tables against the definitions.
    valid = [d for d in data.definitions.values() if not data.check_definition(d)]
    tables = {b.get("id"): b for b in index.get("biomes", [])}
    codes = index.get("codes", {})
    for biome in data.biomes.values():
        bid, home = biome["id"], [d for d in valid if d["biomes"][0] == biome["id"]]
        if len(home) < biome["roster"]: faults.append("biome %s: %d species at home, its roster needs %d" % (bid, len(home), biome["roster"]))
        missing = [r for r in data.rarities if not any(d["rarity"] == r for d in home)]
        if missing: faults.append("biome %s: no %s species at home" % (bid, ", ".join(missing)))
        if codes.get(str(biome["code"])) != bid: faults.append("index.json: codes does not map %d to %s" % (biome["code"], bid))
        table = tables.get(bid)
        if table is None: faults.append("index.json: no table for the biome %s" % bid); continue
        want = {d["id"]: (d["rarity"], d["biomes"][0] == bid) for d in valid if bid in d["biomes"]}
        got = {row.get("species"): row for row in table.get("spawns", [])}
        if set(want) != set(got): faults.append("index.json: the %s table lists %s, the definitions say %s" % (bid, sorted(got), sorted(want)))
        for sid, (rarity, at_home) in want.items():
            row = got.get(sid)
            if row is None: continue
            weight = spawn_weight(data, rarity, at_home)
            if row.get("rarity") != rarity or row.get("home") != at_home or abs(row.get("weight", 0) - weight) > 1e-6:
                faults.append("index.json: the %s table has %s as %r, not a %s %s at weight %g" % (bid, sid, row, rarity, "resident" if at_home else "visitor", weight))
        if abs(table.get("weight", 0) - sum(row.get("weight", 0) for row in table.get("spawns", []))) > 1e-6: faults.append("index.json: the %s table's weight is not the sum of its rows" % bid)
    return faults


def summary(data):
    """The roster as text: by biome, then what the whole set holds."""
    lines = []
    valid = [d for d in data.definitions.values() if not data.check_definition(d)]
    for biome in sorted(data.biomes.values(), key=lambda b: b["code"]):
        home = [d for d in valid if d["biomes"][0] == biome["id"]]
        counts = ", ".join("%d %s" % (sum(1 for d in home if d["rarity"] == r), r) for r in data.rarities)
        habitats = ", ".join("%d %s" % (sum(1 for d in home if d["habitat"] == h), h) for h in data.habitats)
        lines.append("  %3d %-9s %2d at home (%s; %s), %d visiting" % (biome["code"], biome["id"], len(home), counts, habitats, sum(1 for d in valid if biome["id"] in d["biomes"][1:])))
    lines.append("  %d species: %s; %s" % (len(valid), ", ".join("%d %s" % (sum(1 for d in valid if d["habitat"] == h), h) for h in data.habitats),
                                           ", ".join("%d %s" % (sum(1 for d in valid if d["archetype"] == a), a) for a in data.archetypes)))
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true", help="validate the definitions and the files on disk, write nothing")
    parser.add_argument("--model-base", help="how documents name their models: a URL prefix (default %s) or bundle:" % DEFAULT_MODEL_BASE)
    parser.add_argument("--sound-base", help="how documents name their sounds: a URL prefix (default: beside the models, sounds/ for models/)")
    args = parser.parse_args()
    data = Data()
    model_base = args.model_base
    if model_base is None:
        try: model_base = read_json("index.json").get("modelBase", DEFAULT_MODEL_BASE) if args.check else DEFAULT_MODEL_BASE
        except (OSError, ValueError): model_base = DEFAULT_MODEL_BASE
    sound_base = args.sound_base
    if sound_base is None:
        try: recorded = read_json("index.json") if args.check else {}
        except (OSError, ValueError): recorded = {}
        sound_base = recorded["soundBase"] if recorded.get("modelBase") == model_base and "soundBase" in recorded else sound_base_for(model_base)
    outputs, faults = build_all(data, model_base, sound_base)
    faults = data.faults + faults
    if not args.check and not faults: write_all(outputs)
    if args.check or not faults: faults += check_outputs(data, outputs, model_base, sound_base)       # a build checks what it wrote
    print(summary(data))
    digest = hashlib.sha256()
    for path in sorted(outputs): digest.update(path.encode() + b"\0" + outputs[path])
    print("  %d files, %d bytes, model base %s, sha256 %s" % (len(outputs), sum(len(c) for c in outputs.values()), model_base, digest.hexdigest()[:16]))
    if faults:
        print("\n%d fault%s:" % (len(faults), "" if len(faults) == 1 else "s"))
        for fault in faults: print("  " + fault)
        return 1
    print("checked: no faults" if args.check else "built")
    return 0


if __name__ == "__main__":
    sys.exit(main())
