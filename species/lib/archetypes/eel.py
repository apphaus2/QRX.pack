"""An eel: a head and a chain of body pieces, each hanging off the one before, with a ribbon fin down the back.

"move" sends a wave down the chain, "idle" a slow shallow one. The origin is at mid-body. An ornament adds two
fluttering frills behind the head and a taller ribbon; a glow lights a dot on each flank of every piece.
"""
from ..builder import painter, turn, wave
from ..shapes import Y, Z, Profile, ball, ellipsoid, fin, moved, tube

HABITAT, ORIGIN, LENGTH = "water", "centre", 0.22
SHAPE = {
    "segments": 7,      # pieces behind the head
    "girth": 1.0,
    "crest": 1.0,       # the height of the ribbon fin
    "sway": 18,         # degrees each joint bends
    "beat": 0.9,        # seconds per wave
}
COLOURS = {"body": "#C9B27A", "belly": "#EFE6C8", "pattern": "#5E4B2B", "trim": "#2A2114", "fin": "#A8905A", "eye": "#080808", "accent": "#E08A3C", "glow": "#8CF5E1"}
PATTERNS = ("plain", "bands", "stripes", "spots", "saddle", "tips")


def build(b):
    s = b.shape
    count, neck, end = int(s["segments"]), 0.075, -0.11
    piece = (neck - end) / count
    radius = Profile([(0, 0.0105), (0.15, 0.011), (0.6, 0.0085), (0.9, 0.004), (1, 0.0015)])
    r = lambda z: radius((0.11 - z) / 0.22) * s["girth"]
    flat = (0.72, 1.0, 1.0)
    paint = painter(b, (-0.011, -0.011, end), (0.011, 0.011, 0.11), belly=-0.45)
    fins = b.mat("fin", double=True, rough=0.8)
    crest = 0.007 * s["crest"] * (1.6 if b.has("ornament") else 1.0)

    head = moved(ellipsoid((0, 0, 0.017), (0.0105 * s["girth"], 0.0105 * s["girth"], 0.019), 12, 8), scale=flat)
    prims = b.painted(head, paint, at=(0, 0, neck))
    prims += b.eyes([(side * 0.0058 * s["girth"], 0.004, 0.024) for side in (1, -1)], 0.0026)
    body = b.node("Body", prims, (0, 0, neck))
    joints, parent = [], body
    dots = b.mat("glow", rough=0.3, glow=True) if b.has("glow") else None
    for k in range(count):
        z0, z1 = neck - k * piece, neck - (k + 1) * piece
        part = moved(tube([(0, 0, 0), (0, 0, -piece)], [r(z0), r(z1)], 8, caps=False), scale=flat)
        prims = b.painted(part, paint, at=(0, 0, z0)) + b.painted(moved(ellipsoid((0, 0, 0), (r(z0),) * 3, 8, 4), scale=flat), paint, at=(0, 0, z0))
        prims.append((fins, fin([(0, r(z0) - 0.002), (0, r(z0) + crest), (-piece, r(z1) + crest * (0.4 if k == count - 1 else 1)), (-piece, r(z1) - 0.002)], (0, 0, 0), Z, Y)))
        if k >= count // 2:
            prims.append((fins, fin([(0, -r(z0) + 0.002), (0, -r(z0) - crest * 0.6), (-piece, -r(z1) - crest * 0.3), (-piece, -r(z1) + 0.002)], (0, 0, 0), Z, Y)))
        if dots is not None:
            prims += [(dots, ball((side * r(z0) * 0.74, 0.001, -piece / 2), 0.0021, 5, 3)) for side in (1, -1)]
        parent = b.node("Seg%d" % (k + 1), prims, (0, 0, 0 if k == 0 else -piece), parent)
        joints.append(parent)
    frills = {}
    if b.has("ornament"):
        accent = b.mat("accent", double=True, rough=0.7, glow=True)
        for name, side in (("FrillL", 1), ("FrillR", -1)):
            shape = [(0, 0), (0.006, 0.012), (0.016, 0.016), (0.024, 0.008), (0.022, -0.004), (0.010, -0.008)]
            frills[name] = b.node(name, [(accent, fin(shape, (0, 0, 0), (side * 0.8, 0, -0.6), Y))], (side * 0.0068, 0, 0.006), body)

    def clip(name, duration, sway, flutter):
        rot = {body: turn(Y, wave(1, sway * 0.5, -0.9))}
        for k, joint in enumerate(joints):
            rot[joint] = turn(Y, wave(1, sway * (0.7 + 0.5 * k / count), 0.9 * k))
        for name_, side in (("FrillL", 1), ("FrillR", -1)):
            if name_ in frills: rot[frills[name_]] = turn(Y, wave(3, side * flutter))
        b.clip(name, duration, 14, rot=rot)
    clip("move", s["beat"], s["sway"], 18)
    clip("idle", s["beat"] * 4, s["sway"] * 0.3, 10)
    return {"sockets": {"mouth": "Body"}}
