"""A spider: a round abdomen, a small front body with a cluster of eyes and eight arched legs.

"move" walks on alternating sets of four legs, "idle" stands and feels the air with its front pair. The origin is
on the ground under the middle of the body. An ornament sets horns on the abdomen; a glow lights them.
"""
import math
from ..builder import painter, turn, wave
from ..shapes import X, Y, box_of, cross, ellipsoid, norm, qmul, quat, tube

HABITAT, ORIGIN, LENGTH = "ground", "ground", 0.085
SHAPE = {
    "abdomen": 1.0,     # how big the abdomen is
    "legs": 1.0,        # how far the legs reach
    "beat": 0.4,        # seconds per stride
}
COLOURS = {"body": "#6B4A2E", "belly": "#3A2A1C", "pattern": "#E8C56A", "trim": "#2A1C10", "head": "#3E2C1E", "eye": "#050505", "accent": "#D94F3A", "glow": "#FFB37A"}
PATTERNS = ("plain", "bands", "stripes", "spots", "saddle", "tips")


def build(b):
    s, a = b.shape, b.shape["abdomen"]
    height = 0.014
    bulb = ellipsoid((0, height + 0.003, -0.006 - 0.012 * a), (0.011 * a, 0.010 * a, 0.014 * a), 12, 8)
    prims = b.painted(bulb, painter(b, *box_of(bulb), belly=-0.5))
    dark = b.mat("head")
    prims.append((dark, ellipsoid((0, height, 0.006), (0.0075, 0.006, 0.0085), 10, 6)))
    prims += b.eyes([(side * 0.0026, height + 0.004, 0.0125) for side in (1, -1)], 0.0018)
    prims += b.eyes([(side * 0.0052, height + 0.0035, 0.0105) for side in (1, -1)], 0.0012)
    for side in (1, -1):
        prims.append((dark, tube([(side * 0.002, height - 0.002, 0.012), (side * 0.0025, height - 0.007, 0.015)], [0.0016, 0.0005], 5)))
    if b.has("ornament"):
        accent = b.mat("accent", rough=0.5, glow=True)
        for side, z in ((1, -0.004), (-1, -0.004), (1, -0.016), (-1, -0.016)):
            root = (side * 0.006 * a, height + 0.003 + 0.008 * a, -0.006 - 0.012 * a + (z + 0.01) * a)
            prims.append((accent, tube([root, (root[0] * 1.9, root[1] + 0.010, root[2] - 0.003)], [0.003, 0.0004], 5, caps=False)))
    body = b.node("Body", prims)
    legs, reach = [], 0.034 * s["legs"]
    for i, degrees in enumerate((32, 68, 104, 142)):
        for name, side in (("L", 1), ("R", -1)):
            angle = math.radians(degrees)
            out = (side * math.sin(angle), 0.0, math.cos(angle))
            hip = (side * 0.006, height, 0.011 - 0.004 * i)
            part = tube([(0, 0, 0), (out[0] * reach * 0.45, 0.014, out[2] * reach * 0.45), (out[0] * reach, -height + 0.0008, out[2] * reach)], [0.0017, 0.0015, 0.0007], 5, caps=False)
            legs.append((b.node("Leg%s%d" % (name, i + 1), [(dark, part)], hip, body), side, norm(cross(out, Y)), (i + (0 if side > 0 else 1)) % 2, i))

    def stride(side, axis, half, swing, lift):
        def at(u):
            phase = 2 * math.pi * u + math.pi * half
            return qmul(quat(Y, -side * swing * math.sin(phase)), quat(axis, lift * max(0.0, math.cos(phase))))
        return at
    rot = {node: stride(side, axis, half, 15, 12) for node, side, axis, half, i in legs}
    b.clip("move", s["beat"], 12, rot=rot, pos={body: lambda u: (0, 0.0008 * math.sin(4 * math.pi * u), 0)})
    rot = {body: turn(X, wave(1, 2.5))}
    for node, side, axis, half, i in legs:
        if i == 0: rot[node] = lambda u, axis=axis, side=side: quat(axis, 12 * (0.5 + 0.5 * math.sin(4 * math.pi * u + side)))
    b.clip("idle", 3.0, 24, rot=rot)
    return {"sockets": {"mouth": "Body", "back": "Body"}}
