"""A small furry four-legged animal, shaped by its parameters into a mouse, a vole, a hare, a jerboa, a hedgehog
or a fox: a body, a head with a snout and ears, four legs and a tail.

"move" scurries on diagonal pairs of legs or, with `gait` "hop", bounds off both hind legs; "idle" looks about and
sniffs. The origin is on the ground under the middle of the body. An ornament adds a ruff at the neck and tufts
on the ears; a glow lights them and the tip of the tail.
"""
import math
from ..builder import painter, turn, wave
from ..shapes import X, Y, Profile, ball, box_of, ellipsoid, fin, loft, moved, qmul, quat, tube

HABITAT, ORIGIN, LENGTH = "ground", "ground", 0.125
SHAPE = {
    "plump": 1.0,       # how round the body is
    "long": 1.0,        # how long the body is
    "snout": 1.0,       # how long the snout is
    "ears": "round",    # round, long, point or none
    "earsize": 1.0,
    "tail": "thin",     # thin, stub, bushy, tuft or none
    "taillen": 1.0,
    "legs": 1.0,        # how long the legs are
    "hindfeet": 1.0,    # how long the hind feet are (a hare's, a jerboa's)
    "spines": False,    # a hedgehog's coat
    "gait": "scurry",   # scurry or hop
    "beat": 0.4,        # seconds per stride
}
CHOICES = {"ears": ("round", "long", "point", "none"), "tail": ("thin", "stub", "bushy", "tuft", "none"), "gait": ("scurry", "hop")}
COLOURS = {"body": "#9A7B5A", "belly": "#E9DCC6", "pattern": "#5E4630", "trim": "#F3E9D8", "ear": "#D9A99A", "nose": "#3A2A2A", "eye": "#080808", "accent": "#F0E6D0", "glow": "#FFE2B0"}
PATTERNS = ("plain", "bands", "stripes", "spots", "saddle", "tips")


def build(b):
    s, p = b.shape, b.shape["plump"]
    leg = 0.014 * s["legs"]
    cy = leg + 0.015 * p
    front, rear = 0.022 * s["long"], -0.038 * s["long"]
    rx = Profile([(0, 0.010), (0.3, 0.017), (0.7, 0.018), (1, 0.008)])
    ry = Profile([(0, 0.010), (0.3, 0.016), (0.7, 0.017), (1, 0.008)])
    n = 14
    hull = loft([(front + (rear - front) * i / n, cy, rx(i / n) * p, ry(i / n) * p) for i in range(n + 1)], 12)
    paint = painter(b, *box_of(hull), belly=-0.3)
    prims = b.painted(hull, paint, rough=0.85)
    accent = b.mat("accent", rough=0.8, glow=True)
    if s["spines"]:
        quill = b.mat("pattern", rough=0.7)
        for i in range(1, 7):
            t = i / 7.5
            z = front + (rear - front) * t
            for k in range(-3, 4):
                a = math.radians(90 + k * 24 + (12 if i % 2 else 0))
                root = (rx(t) * p * math.cos(a) * 0.9, cy + ry(t) * p * math.sin(a) * 0.9, z)
                tip = (rx(t) * p * math.cos(a) * 1.55, cy + (ry(t) * p + 0.009) * math.sin(a) * 1.25, z - 0.006)
                prims.append((quill, tube([root, tip], [0.0026, 0.0003], 4, caps=False)))
    if b.has("ornament"):
        prims.append((accent, ellipsoid((0, cy + 0.001, front - 0.003), (rx(0.1) * p + 0.003, ry(0.1) * p + 0.003, 0.0045), 12, 5)))
    body = b.node("Body", prims)

    fur, nose = b.mat("body", rough=0.85), b.mat("nose", rough=0.4)
    head = b.painted(ellipsoid((0, 0, 0.008), (0.012, 0.011, 0.013), 10, 7), lambda c, n: "belly" if c[1] < -0.004 else "body", rough=0.85)
    reach = 0.012 * s["snout"]
    head.append((b.mat("belly", rough=0.85), ellipsoid((0, -0.003, 0.013 + reach * 0.5), (0.0066, 0.0056, 0.006 + reach * 0.55), 8, 6)))
    head.append((nose, ball((0, -0.0035, 0.017 + reach), 0.0023, 6, 4)))
    head += b.eyes([(side * 0.0085, 0.004, 0.014) for side in (1, -1)], 0.0024, glow=True)
    ear, e = b.mat("ear", double=True, rough=0.8), s["earsize"]
    for side in (1, -1):
        if s["ears"] == "round":
            head.append((ear, ellipsoid((side * 0.009, 0.011, 0.002), (0.006 * e, 0.007 * e, 0.002), 8, 5)))
        elif s["ears"] == "long":
            head.append((fur, moved(ellipsoid((0, 0.019 * e, 0), (0.004, 0.02 * e, 0.0026), 8, 6), at=(side * 0.006, 0.008, -0.001), turn=quat(X, -18))))
            head.append((ear, moved(ellipsoid((0, 0.019 * e, 0.002), (0.0024, 0.015 * e, 0.0012), 6, 4), at=(side * 0.006, 0.008, -0.001), turn=quat(X, -18))))
        elif s["ears"] == "point":
            head.append((fur, fin([(-0.006, 0.0), (0.001 * side, 0.017 * e), (0.006, 0.0)], (side * 0.007, 0.008, 0.001), X, (0, 1, -0.15))))
            head.append((ear, fin([(-0.0035, 0.001), (0.0008 * side, 0.012 * e), (0.0035, 0.001)], (side * 0.007, 0.008, 0.0016), X, (0, 1, -0.15))))
        if b.has("ornament") and s["ears"] != "none":
            tall = {"round": 0.017 * e, "long": 0.044 * e, "point": 0.024 * e}[s["ears"]]
            lean = -0.012 * e if s["ears"] == "long" else 0.0
            head.append((accent, tube([(side * 0.0075, tall - 0.004, 0.001 + lean), (side * 0.009, tall + 0.008, lean - 0.001)], [0.0022, 0.0003], 5, caps=False)))
    head_node = b.node("Head", head, (0, cy + 0.004, front + 0.002), body)

    tail_node, long = None, s["taillen"]
    if s["tail"] != "none":
        if s["tail"] == "stub":
            parts = [(b.mat("trim", rough=0.9), ball((0, 0.003, -0.004), 0.0065 * long, 8, 5))]
        elif s["tail"] == "bushy":
            brush = tube([(0, 0, 0), (0, 0.008 * long, -0.016 * long), (0, 0.02 * long, -0.034 * long), (0, 0.03 * long, -0.05 * long)], [0.004, 0.0105, 0.0115, 0.003], 9)
            parts = b.painted(brush, lambda c, n: "accent" if c[2] < -0.036 * long else "body", rough=0.9)
        else:
            parts = [(b.mat("ear", rough=0.7), tube([(0, 0, 0), (0, -0.004, -0.02 * long), (0, 0.0, -0.05 * long)], [0.0022, 0.0016, 0.0008], 5))]
            if s["tail"] == "tuft": parts.append((accent, ellipsoid((0, 0.001, -0.052 * long), (0.004, 0.004, 0.008), 7, 5)))
        tail_node = b.node("Tail", parts, (0, cy, rear + 0.004), body)

    legs = {}
    for name, side, z, hind in (("LegFL", 1, front - 0.008, False), ("LegFR", -1, front - 0.008, False), ("LegBL", 1, rear + 0.012, True), ("LegBR", -1, rear + 0.012, True)):
        drop = cy - 0.006 - 0.002
        foot = 0.006 * (s["hindfeet"] if hind else 1.0)
        parts = [(fur, tube([(0, 0, 0), (0, -drop, 0.001)], [0.0055 if hind else 0.0045, 0.003], 6, caps=False)),
                 (b.mat("ear", rough=0.7), ellipsoid((0, -drop, foot * 0.6), (0.0038, 0.002, foot), 7, 4))]
        legs[name] = b.node(name, parts, (side * 0.009 * p, cy - 0.006, z), body)

    up = lambda u: max(0.0, math.sin(2 * math.pi * u))
    rot = {head_node: turn(X, wave(2, 3))}
    if tail_node is not None: rot[tail_node] = turn(Y, wave(1, 12))
    if s["gait"] == "hop":
        rot.update({body: lambda u: quat(X, -9 * up(u)), legs["LegBL"]: turn(X, wave(1, 38)), legs["LegBR"]: turn(X, wave(1, 38)),
                    legs["LegFL"]: turn(X, wave(1, -26)), legs["LegFR"]: turn(X, wave(1, -26))})
        b.clip("move", s["beat"], 12, rot=rot, pos={body: lambda u: (0, 0.013 * up(u), 0)})
    else:
        rot.update({legs["LegFL"]: turn(X, wave(1, 28)), legs["LegBR"]: turn(X, wave(1, 28)), legs["LegFR"]: turn(X, wave(1, -28)), legs["LegBL"]: turn(X, wave(1, -28))})
        b.clip("move", s["beat"], 12, rot=rot, pos={body: lambda u: (0, 0.001 * math.sin(4 * math.pi * u), 0)})
    rot = {head_node: lambda u: qmul(quat(Y, 12 * math.sin(2 * math.pi * u)), quat(X, 3 * math.sin(8 * math.pi * u)))}     # looks about, sniffing
    if tail_node is not None: rot[tail_node] = turn(Y, wave(1, 8, 0.7))
    b.clip("idle", 3.0, 24, rot=rot)
    return {"sockets": {"mouth": "Head", "back": "Body"}}
