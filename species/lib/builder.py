"""What an archetype builds with: the species' definition, its colours as materials, what its rarity grants,
a seeded random source, painted patterns and looping clips.

An archetype is a module in lib/archetypes with

    HABITAT  = "water"              the habitat it was drawn for (documentation; any habitat with the same ORIGIN works)
    ORIGIN   = "centre" | "ground"  where the model's origin is: mid-body (swimmers, fliers) or on the ground under it
    LENGTH   = 0.12                 its longest side in metres as drawn, with the default shape; `size` scales from it
    SHAPE    = {...}                shape parameters and their defaults; a definition may override any of them
    COLOURS  = {...}                colour slots and their defaults ("#rrggbb")
    PATTERNS = (...)                the pattern types it can paint
    TRICKS   = (...)                the tricks its body can do, by id from tricks.json, the ones to give first first
    def build(b): ...               adds nodes, the clips "idle" and "move" and a `b.trick(...)` clip for each trick it
                                    animates, to the Builder b; returns {"sockets": {...}}

The head is along +Z, +Y is up and +X is the creature's left.
"""
import math, random, zlib

from .gltf import Model
from .shapes import Y, add, ball, mul, norm, qmul, qrot, quat, smooth, split, sub

FEATURES = ("trim", "ornament", "glow", "motes")


def linear(hex_colour):
    """'#rrggbb' (sRGB, as a person picks it) as the linear RGB glTF wants."""
    def channel(c): return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return tuple(channel(int(hex_colour[i:i + 2], 16) / 255) for i in (1, 3, 5))


class Builder:
    def __init__(self, definition, rarity, archetype, generator, tricks=()):
        self.definition, self.rarity, self.archetype = definition, rarity, archetype
        self.wanted, self.signature, self.made = set(tricks), definition.get("signature"), {}      # tricks to animate; the clips made, in seconds
        self.shape = dict(archetype.SHAPE, **definition.get("shape", {}))
        self.colours = dict(archetype.COLOURS, **definition.get("colours", {}))
        self.pattern = dict({"type": "plain"}, **definition.get("pattern", {}))
        self.features = set(rarity.get("features", []))
        self.glow = float(rarity.get("glow", 0))
        self.rng = random.Random(zlib.crc32(definition["id"].encode()))
        self.model = Model(definition["id"], generator, definition["size"] / archetype.LENGTH)
        self.offsets, self.lo, self.hi = {}, [math.inf] * 3, [-math.inf] * 3     # where each node is, and the box of it all, as drawn

    def has(self, feature): return feature in self.features

    # ---- colours ----

    def mat(self, slot, double=False, rough=0.6, metal=0.0, glow=False):
        """The material for a colour slot. `glow` makes it emissive by the rarity's glow, when it has any."""
        lit = glow and self.has("glow") and self.glow > 0
        name = slot + ("-2" if double else "") + ("-lit" if lit else "")
        rgb = linear(self.colours[slot])
        return self.model.material(name, rgb, double, rough, metal, mul(rgb, self.glow) if lit else None)

    def painted(self, part, paint, at=(0.0, 0.0, 0.0), double=False, rough=0.6, metal=0.0, lit=("glow",)):
        """`part` cut into (material, part) pieces by `paint(centre, normal)`, which names a colour slot. `at` is
        where the part's node stands, so one painter can run over a body made of several nodes. Slots named in
        `lit` glow when the rarity does."""
        pieces = split(part, lambda centre, normal: paint(add(centre, at), normal))
        return [(self.mat(slot, double, rough, metal, glow=slot in lit), piece) for slot, piece in sorted(pieces.items())]

    # ---- nodes and clips ----

    def node(self, name, prims=(), at=(0.0, 0.0, 0.0), parent=None, turn=None):
        index = self.model.node(name, prims, at, parent, turn)
        self.offsets[index] = add(self.offsets[parent], at) if parent is not None else tuple(at)
        for _, part in prims:
            for p in part[0]:
                for i in range(3):
                    c = p[i] + self.offsets[index][i]
                    if c < self.lo[i]: self.lo[i] = c
                    if c > self.hi[i]: self.hi[i] = c
        return index

    def eyes(self, places, r, slot="eye", glow=False):
        """Shiny eyes at `places`, as a list of (material, part)."""
        return [(self.mat(slot, rough=0.25, glow=glow), ball(p, r)) for p in places]

    def clip(self, name, duration, keys, rot=None, pos=None, scl=None, wrap=True):
        """A looping clip of `keys` even steps over `duration` seconds. Each of `rot` (quaternions), `pos`
        (offsets from rest) and `scl` (scales) maps a node to a function of u, the fraction of the clip from 0
        to 1; the last key repeats the first, so write whole cycles: sin(2 * pi * 3 * u) is three of them.
        Without `wrap` the last key is the function at 1 (a full turn ends where it began, the long way round)."""
        times = [duration * i / keys for i in range(keys + 1)]
        for path, table in (("rotation", rot), ("translation", pos), ("scale", scl)):
            for node, fn in (table or {}).items():
                self.model.channel(name, node, path, times, [fn((i % keys) / keys if wrap else i / keys) for i in range(keys + 1)])

    def trick(self, name, seconds, rot=None, pos=None, scl=None, keys=16):
        """The one-shot clip of the trick `name`, made only for a species that knows it. Written like `clip`, with
        every function back where it started at u = 1 (`full_turn`, `swing`, `lean`, `lift`, `pulse`, `hold`). A
        legendary whose signature borrows this move gets it again under the signature's id, for its motes to join."""
        names = [name] if name in self.wanted else []
        if self.signature and self.signature.get("move") == name: names.append(self.signature["id"])
        for clip in names:
            self.clip(clip, seconds, keys, rot, pos, scl, wrap=False)
            self.made[clip] = seconds


def wave(cycles, amplitude, phase=0.0, offset=0.0):
    """u -> offset + amplitude * sin(2 pi cycles u - phase)."""
    return lambda u: offset + amplitude * math.sin(2 * math.pi * cycles * u - phase)


# ---- trick moves: functions of u from 0 to 1 that end where they began ---------------------------------------

def full_turn(axis, turns=1.0):
    """A whole turn (or `turns` of them, negative for the other way) about `axis`, easing in and out."""
    return lambda u: quat(axis, 360.0 * turns * smooth(u))


def swing(axis, degrees, cycles=1, phase=0.0):
    """Back and forth `cycles` times about `axis`, growing from rest and dying back to it."""
    return lambda u: quat(axis, degrees * math.sin(math.pi * u) * math.sin(2 * math.pi * cycles * u + phase))


def lean(axis, degrees):
    """Over by `degrees` about `axis` and back."""
    return lambda u: quat(axis, degrees * math.sin(math.pi * u) ** 2)


def hold(axis, degrees, edge=0.2):
    """Over by `degrees`, held there, and back: `edge` is the share of the clip spent going and returning."""
    return lambda u: quat(axis, degrees * smooth(u / edge) * smooth((1 - u) / edge))


def lift(height, hops=1):
    """Up by `height` and down again, `hops` times."""
    return lambda u: (0.0, height * math.sin(math.pi * ((u * hops) % 1.0 if u < 1 else 0.0)), 0.0)


def pulse(amount, beats=1, axes=(1.0, 1.0, 1.0)):
    """Bigger by `amount` (smaller if negative) and back, `beats` times; `axes` weights x, y and z."""
    return lambda u: tuple(1 + amount * a * math.sin(math.pi * beats * u) ** 2 for a in axes)


def shrink(amount, edge=0.2, axes=(1.0, 1.0, 1.0)):
    """Smaller by `amount`, held, and back: tucking something in."""
    return lambda u: tuple(1 - amount * a * smooth(u / edge) * smooth((1 - u) / edge) for a in axes)


def about(pivot, rotation, also=None):
    """The offset that makes `rotation` (a function of u) turn a node about `pivot` (in the node's own space)
    instead of about its origin, plus the offset `also` when given."""
    def at(u):
        offset = sub(pivot, qrot(rotation(u), pivot))
        return add(offset, also(u)) if also else offset
    return at


def both(first, then):
    """Two rotations at once: `first` applied, then `then`."""
    return lambda u: qmul(then(u), first(u))


def turn(axis, fn):
    """u -> a rotation about `axis` by fn(u) degrees."""
    return lambda u: quat(axis, fn(u))


# ---- patterns ---------------------------------------------------------------------------------------------

def painter(b, lo, hi, axes=(2, 1, 0), belly=-0.35, base="body"):
    """paint(centre, normal) for a body in the box lo..hi, by the definition's `pattern`. `axes` are the indices
    of the body's long axis (the nose at its high end), its up axis and its side axis. The names it returns are
    colour slots: `base`, "belly" (the underside, below `belly` on the up axis from -1 to 1; None for no belly),
    "pattern" and, with the rarity's trim, "trim" edging the pattern. Rarity's glow lights "glow" slots, so a
    pattern with "lit": true paints "glow" in place of "pattern".

        {"type": "plain"}
        {"type": "bands",   "count": 3, "width": 0.4}      rings around the long axis; width is the painted share
        {"type": "stripes", "count": 3, "width": 0.4}      lines along the body
        {"type": "spots",   "count": 9, "size": 0.2, "top": true}
        {"type": "saddle",  "level": 0.2}                  everything above `level` (-1 to 1) on the up axis
        {"type": "tips",    "share": 0.2}                  the nose and the tail end
    """
    p, kind = b.pattern, b.pattern["type"]
    li, ui, si = axes
    mark = "glow" if p.get("lit") and b.has("glow") else "pattern"
    trim = "trim" if b.has("trim") else None
    half = [(hi[i] - lo[i]) / 2 or 1.0 for i in range(3)]
    mid = [(hi[i] + lo[i]) / 2 for i in range(3)]
    spots = []
    if kind == "spots":
        for _ in range(int(p.get("count", 8))):
            theta, y = b.rng.uniform(0, 2 * math.pi), b.rng.uniform(0.15 if p.get("top", True) else -1.0, 0.95)
            r = math.sqrt(1 - y * y)
            spots.append(((r * math.cos(theta), y, r * math.sin(theta)), float(p.get("size", 0.2)) * b.rng.uniform(0.75, 1.15)))

    def paint(centre, normal):
        along = (centre[li] - mid[li]) / half[li]           # -1 at the tail, 1 at the nose
        up = (centre[ui] - mid[ui]) / half[ui]
        side = (centre[si] - mid[si]) / half[si]
        t = (1 - along) / 2
        if kind == "bands":
            count, width = int(p.get("count", 3)), float(p.get("width", 0.4))
            f = (t * count) % 1.0
            d = abs(f - 0.5)
            if d < width / 2: return mark
            if trim and d < width / 2 + 0.09: return trim
        elif kind == "stripes":
            count, width = int(p.get("count", 3)), float(p.get("width", 0.4))
            angle = math.atan2(side, up) / math.pi           # 0 on the back, +-1 under the belly
            f = (abs(angle) * count) % 1.0
            d = abs(f - 0.5) if count > 1 else abs(angle)
            if d < width / 2: return mark
            if trim and d < width / 2 + 0.1: return trim
        elif kind == "spots":
            direction = norm((side, up, along))
            for where, size in spots:
                d = math.acos(max(-1.0, min(1.0, direction[0] * where[0] + direction[1] * where[1] + direction[2] * where[2])))
                if d < size: return mark
                if trim and d < size * 1.45: return trim
        elif kind == "saddle":
            level = float(p.get("level", 0.2))
            if up > level: return mark
            if trim and up > level - 0.22: return trim
        elif kind == "tips":
            share = float(p.get("share", 0.2))
            if t < share or t > 1 - share: return mark
            if trim and (t < share + 0.07 or t > 1 - share - 0.07): return trim
        if belly is not None and up < belly: return "belly"
        return base
    return paint


# ---- the legendary's motes --------------------------------------------------------------------------------

def add_motes(b, count):
    """A tilted ring of small glowing motes around the creature, swaying and pulsing in every clip: the rarest
    creatures carry their own lights. Any archetype gets them; the driver adds them after `build`."""
    lo, hi = b.lo, b.hi
    centre = tuple((lo[i] + hi[i]) / 2 for i in range(3))
    radius = 0.62 * max(hi[0] - lo[0], hi[2] - lo[2]) / 2 + 0.25 * (hi[1] - lo[1])
    size = 0.03 * max(hi[i] - lo[i] for i in range(3))
    material = b.mat("glow", rough=0.3, glow=True)
    prims = []
    for k in range(count):
        a = 2 * math.pi * k / count
        prims.append((material, ball((radius * math.cos(a), 0.3 * radius * math.sin(2 * a), radius * math.sin(a)), size, 6, 4)))
    tilt = quat(norm((1.0, 0.0, 0.4)), 14)
    at = add(centre, (0.0, (hi[1] - lo[1]) * 0.25, 0.0))
    if b.archetype.ORIGIN == "ground":      # a walker's motes stay above the ground it stands on
        lowest = min(qrot(tilt, p)[1] for _, part in prims for p in part[0])
        at = (at[0], max(at[1], lo[1] + size - lowest), at[2])
    node = b.model.node("Motes", prims, at, turn=tilt)
    sway, keys = 180.0 / count, 24
    flourish = (b.signature or {}).get("motes")
    span, tall = max(hi[0] - lo[0], hi[2] - lo[2]), hi[1] - lo[1]
    for name, channels in list(b.model.clips.items()):
        duration = max(times[-1] for _, _, times, _ in channels)
        times = [duration * i / keys for i in range(keys + 1)]
        if b.signature and name == b.signature["id"]:
            # The signature trick: the motes leave their ring and come back, each legendary's in its own way.
            u = [i / keys for i in range(keys + 1)]
            turns, grow, rise = {"burst": (1, 1.6, 0.0), "swirl": (2, 0.5, 0.0), "gather": (1, -0.6, 0.35), "rise": (1, 0.3, 0.9), "fall": (1, 0.3, -0.7)}[flourish]
            b.model.channel(name, node, "rotation", times, [qmul(tilt, quat(Y, 360.0 * turns * smooth(x))) for x in u])
            b.model.channel(name, node, "scale", times, [(1 + grow * math.sin(math.pi * x) ** 2,) * 3 for x in u])
            if rise: b.model.channel(name, node, "translation", times, [(0.0, rise * max(tall, 0.3 * span) * math.sin(math.pi * x) ** 2, 0.0) for x in u])
            continue
        phase = [2 * math.pi * (i % keys) / keys for i in range(keys + 1)]
        b.model.channel(name, node, "rotation", times, [qmul(tilt, quat(Y, sway * math.sin(p))) for p in phase])
        b.model.channel(name, node, "scale", times, [(1 + 0.25 * math.sin(2 * p),) * 3 for p in phase])
    return node
