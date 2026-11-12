"""A seahorse: upright, a snouted head, a ridged body, a tail that curls forward and a fluttering back fin.

"move" leans it forward with the back fin beating, "idle" bobs it upright with the tail curling. The origin is at
mid-body. An ornament adds a tall coronet and spines down the back; a glow lights them.
"""
import math
from ..builder import painter, turn, wave
from ..builder import full_turn, lean, swing
from ..shapes import X, Y, Z, ball, ellipsoid, fin, tube

HABITAT, ORIGIN, LENGTH = "water", "centre", 0.115
SHAPE = {
    "girth": 1.0,
    "snout": 1.0,       # how long the snout is
    "flutter": 8,       # back fin beats per second
}
COLOURS = {"body": "#C7A93C", "belly": "#E7D48A", "pattern": "#8A6F1E", "trim": "#5B4712", "fin": "#E6D27A", "eye": "#080808", "accent": "#E86A5C", "glow": "#FFD27A"}
PATTERNS = ("plain", "bands", "spots", "tips")
TRICKS = ("spin", "bow", "dance")


def build(b):
    s, g = b.shape, b.shape["girth"]
    trunk = tube([(0, 0.038, 0.004), (0, 0.022, 0.008), (0, 0.002, 0.006), (0, -0.016, 0.001), (0, -0.030, -0.004)], [0.0065 * g, 0.0105 * g, 0.0125 * g, 0.009 * g, 0.006 * g], 10)
    paint = painter(b, (-0.013, -0.058, -0.012), (0.013, 0.058, 0.02), axes=(1, 2, 0), belly=None)
    prims = b.painted(trunk, paint)
    prims.append((b.mat("belly"), ellipsoid((0, 0.0, 0.0125), (0.0085 * g, 0.014, 0.008 * g), 10, 6)))
    accent = b.mat("accent", double=True, rough=0.6, glow=True)
    if b.has("ornament"):
        for y, z in ((0.03, -0.004), (0.02, -0.004), (0.008, -0.007), (-0.006, -0.008), (-0.02, -0.006)):
            prims.append((accent, tube([(0, y, z), (0, y + 0.002, z - 0.009)], [0.0022, 0.0003], 5, caps=False)))
    body = b.node("Body", prims)

    head = b.painted(ellipsoid((0, 0.007, 0.004), (0.008 * g, 0.009, 0.011), 10, 7), paint, at=(0, 0.04, 0.004))
    reach = 0.022 * s["snout"]
    head.append((b.mat("body"), tube([(0, 0.006, 0.011), (0, 0.003, 0.011 + reach * 0.6), (0, 0.002, 0.011 + reach)], [0.0045, 0.003, 0.0036], 7)))
    head += b.eyes([(side * 0.0072 * g, 0.009, 0.008) for side in (1, -1)], 0.0027)
    crown = 0.018 if b.has("ornament") else 0.008
    for dx, dz, h in ((0, 0, 1.0), (0.003, -0.003, 0.7), (-0.003, -0.003, 0.7)) if b.has("ornament") else ((0, 0, 1.0),):
        head.append((accent if b.has("ornament") else b.mat("body"), tube([(dx, 0.014, dz), (dx * 1.6, 0.014 + crown * h, dz * 1.6 - 0.002)], [0.0034, 0.0006], 5, caps=False)))
    head_node = b.node("Head", head, (0, 0.04, 0.004), body)

    curl, parent, at = [], body, (0, -0.030, -0.004)
    for k, (points, radii) in enumerate((
            ([(0, 0, 0), (0, -0.012, 0.002), (0, -0.021, 0.009)], [0.006 * g, 0.0048 * g, 0.0038 * g]),
            ([(0, 0, 0), (0, -0.006, 0.008), (0, -0.002, 0.016)], [0.0038 * g, 0.003 * g, 0.0024 * g]),
            ([(0, 0, 0), (0, 0.007, 0.003), (0, 0.009, -0.004), (0, 0.004, -0.008)], [0.0024 * g, 0.0018 * g, 0.0012 * g, 0.0006]))):
        parent = b.node("Tail%d" % (k + 1), b.painted(tube(points, radii, 7, caps=False), paint, at=(0, -0.03 - 0.012 * k, 0)) + [(b.mat("body"), ball((0, 0, 0), radii[0], 7, 5))], at, parent)
        curl.append(parent)
        at = points[-1]
    fins = b.mat("fin", double=True, rough=0.8)
    dorsal = b.node("Dorsal", [(fins, fin([(0, -0.011), (0.011, -0.009), (0.016, 0.001), (0.012, 0.012), (0, 0.011)], (0, 0, 0), (0, 0, -1), Y))], (0, 0.006, -0.0045 - 0.0045 * g), body)
    pecs = [b.node(name, [(fins, fin([(0, -0.004), (0.008, -0.005), (0.011, 0.001), (0.007, 0.006), (0, 0.004)], (0, 0, 0), (side, 0, -0.5), Y))], (side * 0.007 * g, 0.031, 0.002), body)
            for name, side in (("PecL", 1), ("PecR", -1))]

    def clip(name, duration, keys, lean, beats, flutter, tail, nod, bob):
        rot = {body: turn(X, wave(1, 2.5, 0, lean)), head_node: turn(X, wave(1, nod, 0.6)), dorsal: turn(Y, wave(beats, flutter))}
        for k, joint in enumerate(curl): rot[joint] = turn(X, wave(1, tail * (1 + 0.3 * k), 0.8 * k))
        for i, pec in enumerate(pecs): rot[pec] = turn(Y, wave(beats, flutter * 0.8 * (1 if i == 0 else -1), 0.5))
        b.clip(name, duration, keys, rot=rot, pos={body: lambda u: (0, bob * math.sin(2 * math.pi * u), 0)})
    beats = int(s["flutter"])
    clip("move", 1.0, beats * 4, 11, beats, 25, 6, 2, 0.001)
    clip("idle", 3.0, 48, 0, 12, 14, 9, 5, 0.003)
    # Tricks: a twirl, a bow and a sway.
    b.trick("spin", 1.2, rot={body: full_turn(Y)})
    b.trick("bow", 1.2, rot={body: lean(X, 32), head_node: lean(X, 18)})
    b.trick("dance", 1.5, rot={body: swing(Z, 18, 3), curl[0]: swing(X, 14, 3, 1.0)})
    return {"sockets": {"mouth": "Head"}}
