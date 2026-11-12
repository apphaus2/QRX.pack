"""A beetle: a domed shell with a seam down the middle, a shield and a head in front, two feelers and six legs.

"move" walks on alternating tripods of legs, "idle" stands with the feelers searching. The origin is on the ground
under the middle of the body. An ornament grows a horn (`horn`: rhino, stag); a glow lights it.
"""
import math
from ..builder import painter, turn, wave
from ..shapes import X, Y, Z, cross, ellipsoid, norm, qmul, quat, tube

HABITAT, ORIGIN, LENGTH = "ground", "ground", 0.092
SHAPE = {
    "dome": 1.0,        # how tall the shell is
    "width": 1.0,       # how wide
    "sheen": 0.0,       # how metallic the shell is, 0 to 1
    "horn": "rhino",    # what an ornament adds: rhino or stag
    "beat": 0.4,        # seconds per stride
}
CHOICES = {"horn": ("rhino", "stag")}
COLOURS = {"body": "#C0392B", "belly": "#2B2B2B", "pattern": "#151515", "trim": "#151515", "head": "#1C1C1C", "eye": "#050505", "accent": "#E0A030", "glow": "#FFE08A"}
PATTERNS = ("plain", "bands", "stripes", "spots", "saddle", "tips")


def build(b):
    s = b.shape
    rx, ry = 0.022 * s["width"], 0.016 * s["dome"]
    shell = ellipsoid((0, 0.018, -0.008), (rx, ry, 0.028), 14, 8)
    inner = painter(b, (-rx, 0.018 - ry, -0.036), (rx, 0.018 + ry, 0.020), belly=-0.45)
    paint = lambda c, n: "trim" if abs(c[0]) < 0.0016 and n[1] > 0.2 else inner(c, n)
    prims = b.painted(shell, paint, rough=0.6 - 0.35 * s["sheen"], metal=0.8 * s["sheen"])
    dark = b.mat("head", rough=0.5 - 0.2 * s["sheen"], metal=0.5 * s["sheen"])
    prims += [(dark, ellipsoid((0, 0.017, 0.024), (0.016 * s["width"], 0.011, 0.011), 10, 6)), (dark, ellipsoid((0, 0.014, 0.037), (0.009, 0.007, 0.008), 8, 5))]
    prims += b.eyes([(side * 0.0072, 0.016, 0.040) for side in (1, -1)], 0.0024)
    if b.has("ornament"):
        accent = b.mat("accent", rough=0.4, metal=0.3, glow=True)
        if s["horn"] == "stag":
            for side in (1, -1):
                prims.append((accent, tube([(side * 0.004, 0.013, 0.042), (side * 0.015, 0.015, 0.056), (side * 0.012, 0.016, 0.070), (side * 0.004, 0.016, 0.076)], [0.003, 0.0028, 0.002, 0.0006], 6)))
        else:
            prims.append((accent, tube([(0, 0.016, 0.040), (0, 0.027, 0.054), (0, 0.041, 0.057)], [0.0042, 0.0032, 0.0008], 6)))
            prims.append((accent, tube([(0, 0.026, 0.026), (0, 0.036, 0.032)], [0.003, 0.0008], 6)))
    body = b.node("Body", prims)
    feelers = []
    for name, side in (("FeelerL", 1), ("FeelerR", -1)):
        part = tube([(0, 0, 0), (side * 0.008, 0.006, 0.010), (side * 0.016, 0.004, 0.016)], [0.0012, 0.001, 0.0015], 5)
        feelers.append((side, b.node(name, [(dark, part)], (side * 0.005, 0.017, 0.042), body)))
    legs = []
    for i, (z, reach) in enumerate(((0.022, 0.014), (0.004, 0.0), (-0.014, -0.016))):
        for name, side in (("L", 1), ("R", -1)):
            hip = (side * 0.012 * s["width"], 0.012, z)
            foot = (side * (0.036 * s["width"] - hip[0] * side), -0.012, reach)
            part = tube([(0, 0, 0), (foot[0] * 0.55, 0.010, reach * 0.5), foot], [0.0028, 0.0022, 0.001], 5, caps=False)
            direction = norm((foot[0], 0.0, foot[2]))
            legs.append((b.node("Leg%s%d" % (name, i + 1), [(dark, part)], hip, body), side, norm(cross(direction, Y)), (i + (0 if side > 0 else 1)) % 2))

    def stride(side, axis, half, swing, lift):
        def at(u):
            phase = 2 * math.pi * u + math.pi * half
            return qmul(quat(Y, -side * swing * math.sin(phase)), quat(axis, lift * max(0.0, math.cos(phase))))
        return at
    rot = {node: stride(side, axis, half, 22, 14) for node, side, axis, half in legs}
    rot[body] = turn(Z, wave(1, 2))
    for side, node in feelers: rot[node] = turn(Y, wave(2, 8 * side))
    b.clip("move", s["beat"], 12, rot=rot)
    rot = {body: turn(X, wave(1, 1.2))}
    for side, node in feelers: rot[node] = lambda u, side=side: qmul(quat(Y, side * 10 * math.sin(2 * math.pi * u)), quat(X, 8 * math.sin(4 * math.pi * u + side)))
    b.clip("idle", 3.0, 24, rot=rot)
    return {"sockets": {"mouth": "Body", "back": "Body"}}
