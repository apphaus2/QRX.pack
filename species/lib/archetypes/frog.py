"""A frog: a squat body with eyes on top, a throat that swells, folded back legs and short arms.

"move" hops (the body leaves the ground as the back legs straighten), "idle" sits and breathes with its throat.
The origin is on the ground under the middle of the body. An ornament adds horns over the eyes and a ridge of
beads down the back; a glow lights them.
"""
import math
from ..builder import painter, turn, wave
from ..shapes import X, Profile, ball, box_of, ellipsoid, loft, quat, tube

HABITAT, ORIGIN, LENGTH = "ground", "ground", 0.082
SHAPE = {
    "plump": 1.0,
    "eyes": 1.0,        # how big the eyes are
    "legs": 1.0,        # how long the back legs are
    "hop": 1.0,         # how high it hops
    "beat": 0.7,        # seconds per hop
}
COLOURS = {"body": "#5FA83A", "belly": "#E6E9B8", "pattern": "#2F6B24", "trim": "#F0E36B", "eye": "#0A0A0A", "accent": "#E8A23A", "glow": "#C8FF8A"}
PATTERNS = ("plain", "bands", "stripes", "spots", "saddle", "tips")


def build(b):
    s, p = b.shape, b.shape["plump"]
    rx = Profile([(0, 0.004), (0.12, 0.013), (0.3, 0.019), (0.55, 0.020), (0.8, 0.016), (1, 0.005)])
    ry = Profile([(0, 0.003), (0.12, 0.008), (0.3, 0.012), (0.55, 0.015), (0.8, 0.012), (1, 0.004)])
    yc = Profile([(0, 0.020), (0.3, 0.020), (0.6, 0.017), (1, 0.011)])
    n = 16
    hull = loft([(0.036 - 0.070 * i / n, yc(i / n), rx(i / n) * p, ry(i / n) * p) for i in range(n + 1)], 12)
    prims = b.painted(hull, painter(b, *box_of(hull), belly=-0.3))
    lid, e = b.mat("body"), b.shape["eyes"]
    for side in (1, -1):
        prims.append((lid, ball((side * 0.011, 0.030, 0.020), 0.0065 * e, 8, 6)))
    prims += b.eyes([(side * (0.011 + 0.0022 * e), 0.0315, 0.0225) for side in (1, -1)], 0.005 * e)
    if b.has("ornament"):
        accent = b.mat("accent", rough=0.5, glow=True)
        for side in (1, -1):
            prims.append((accent, tube([(side * 0.011, 0.034, 0.018), (side * 0.014, 0.046, 0.014)], [0.003, 0.0005], 5, caps=False)))
        for z in (0.008, -0.002, -0.012, -0.022):
            prims.append((accent, ball((0, yc((0.036 - z) / 0.07) + ry((0.036 - z) / 0.07) * p, z), 0.0028, 6, 4)))
    body = b.node("Body", prims)
    throat = b.node("Throat", [(b.mat("belly"), ellipsoid((0, 0, 0), (0.011 * p, 0.006, 0.008), 8, 5))], (0, 0.011, 0.022), body)
    skin, toe = b.mat("body"), b.mat("belly")
    legs = {}
    for name, side in (("L", 1), ("R", -1)):
        long = s["legs"]
        knee = (side * 0.016, 0.006, 0.014 * long)
        thigh = b.node("Thigh" + name, [(skin, tube([(0, 0, 0), knee], [0.007, 0.005], 7))], (side * 0.013 * p, 0.012, -0.020), body)
        ankle = (side * 0.004, -0.014, -0.022 * long)
        shin = b.node("Shin" + name, [(skin, tube([(0, 0, 0), ankle], [0.005, 0.003], 6)),
                                     (toe, ellipsoid((ankle[0] + side * 0.004, ankle[1] - 0.002, ankle[2] + 0.012), (0.006, 0.002, 0.013), 8, 4))], knee, thigh)
        arm = b.node("Arm" + name, [(skin, tube([(0, 0, 0), (side * 0.006, -0.004, 0.004), (side * 0.005, -0.0095, 0.008)], [0.0045, 0.0035, 0.003], 6)),
                                   (toe, ellipsoid((side * 0.005, -0.0105, 0.011), (0.005, 0.0015, 0.006), 8, 4))], (side * 0.014 * p, 0.012, 0.016), body)
        legs[name] = (thigh, shin, arm)

    up = lambda u: max(0.0, math.sin(2 * math.pi * u))
    rot = {body: lambda u: quat(X, -12 * up(u))}
    for thigh, shin, arm in legs.values():
        rot[thigh] = lambda u: quat(X, 42 * up(u))
        rot[shin] = lambda u: quat(X, -50 * up(u))
        rot[arm] = lambda u: quat(X, -25 * up(u))
    b.clip("move", s["beat"], 14, rot=rot, pos={body: lambda u: (0, 0.018 * s["hop"] * up(u), 0)})
    swell = lambda u: 0.5 + 0.5 * math.sin(2 * math.pi * 3 * u)
    b.clip("idle", 2.4, 24, rot={body: turn(X, wave(1, 1))}, scl={throat: lambda u: (1 + 0.2 * swell(u), 1 + 0.5 * swell(u), 1 + 0.2 * swell(u))})
    return {"sockets": {"mouth": "Body", "back": "Body"}}
