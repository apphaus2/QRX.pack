"""A lizard, after QRX.pack's: a flattened body and head, a tail in three jointed pieces and four bent legs.

"move" swings the legs in diagonal pairs while the body and the tail snake, "idle" breathes with a slow curl of
the tail. The origin is on the ground under the middle of the body. An ornament raises a crest (`crest`: spikes,
a sail or a neck frill); a glow lights it.
"""
import math
from ..builder import painter, turn, wave
from ..builder import full_turn, hold, lean, lift, swing
from ..shapes import X, Y, Z, ellipsoid, fin, tube

HABITAT, ORIGIN, LENGTH = "ground", "ground", 0.29
SHAPE = {
    "girth": 1.0,
    "tail": 1.0,        # how long the tail is
    "legs": 1.0,        # how far the feet reach
    "flat": 0.72,       # how flattened the body is (1 is round)
    "crest": "spikes",  # what an ornament adds: spikes, sail or frill
    "beat": 0.6,        # seconds per stride
}
CHOICES = {"crest": ("spikes", "sail", "frill")}
COLOURS = {"body": "#80C23D", "belly": "#D9E8A0", "pattern": "#2B6B33", "trim": "#173D1E", "toe": "#A9D15C", "eye": "#080808", "accent": "#E8B33A", "glow": "#FFD86B"}
PATTERNS = ("plain", "bands", "stripes", "spots", "saddle", "tips")
TRICKS = ("spin", "pushup", "roll", "dead", "dance")


def build(b):
    s, g = b.shape, b.shape["girth"]
    height = 0.024
    spine = [(0, 0, -0.05), (0, 0.001, -0.03), (0, 0.002, 0.0), (0, 0.002, 0.03), (0, 0.003, 0.05), (0, 0.005, 0.066), (0, 0.004, 0.086), (0, 0.002, 0.102)]
    trunk = tube(spine, [r * g for r in (0.011, 0.017, 0.02, 0.018, 0.012, 0.016, 0.012, 0.004)], 10, squash=s["flat"])
    paint = painter(b, (-0.02 * g, height - 0.02 * g * s["flat"], -0.05), (0.02 * g, height + 0.02 * g * s["flat"], 0.102), belly=-0.45)
    prims = b.painted(trunk, paint, at=(0, height, 0))
    prims += b.eyes([(side * 0.0125 * g, 0.011 * g, 0.078) for side in (1, -1)], 0.004)
    accent = b.mat("accent", double=True, rough=0.6, glow=True)
    if b.has("ornament"):
        top = lambda z: 0.019 * g * s["flat"] * (1 - 0.35 * abs(z) / 0.05)
        if s["crest"] == "sail":
            prims.append((accent, fin([(0.05, top(0.05) - 0.004), (0.036, top(0.036) + 0.02), (0.0, top(0) + 0.03), (-0.03, top(-0.03) + 0.018), (-0.048, top(-0.048) - 0.004)], (0, 0, 0), Z, Y)))
        elif s["crest"] == "frill":
            fan = [(0.0, 0.0)] + [(0.034 * math.cos(a), 0.034 * math.sin(a)) for a in [math.radians(-25 + 230 * k / 10) for k in range(11)]]
            prims.append((accent, fin(fan, (0, 0.004, 0.058), X, (0, 1, -0.35))))
        else:
            for z in (0.046, 0.03, 0.014, -0.002, -0.018, -0.034):
                prims.append((accent, fin([(z + 0.007, top(z + 0.007) - 0.003), (z - 0.002, top(z) + 0.014), (z - 0.007, top(z - 0.007) - 0.003)], (0, 0, 0), Z, Y)))
    body = b.node("Body", prims, (0, height, 0))

    tail, parent, z = [], body, -0.05
    for i, (r0, r1, piece) in enumerate(((0.011, 0.008, 0.045), (0.008, 0.005, 0.045), (0.005, 0.0008, 0.05))):
        piece *= s["tail"]
        part = tube([(0, 0, 0), (0, -0.002, -piece)], [r0 * g, r1 * g], 8, squash=0.8, caps=False)
        prims = b.painted(part, paint, at=(0, height, z))
        if b.has("ornament") and s["crest"] == "spikes" and i < 2:
            prims.append((accent, fin([(-0.004, r0 * g * 0.6), (-piece / 2, r0 * g + 0.008), (-piece + 0.006, r1 * g * 0.6)], (0, 0, 0), Z, Y)))
        parent = b.node("Tail%d" % (i + 1), prims, (0, 0.0 if i == 0 else -0.002, -0.05 if i == 0 else -last), parent)
        tail.append(parent)
        z, last = z - piece, piece

    legs = {}
    skin, toe = b.mat("body"), b.mat("toe")
    for name, side, at, reach in (("LegFL", 1, 0.04, 0.012), ("LegFR", -1, 0.04, 0.012), ("LegBL", 1, -0.034, -0.008), ("LegBR", -1, -0.034, -0.008)):
        hip_y, out = -0.004, 0.036 * s["legs"]
        foot = (side * out, -(height + hip_y) + 0.003, reach)
        limb = tube([(0, 0, 0), (side * out * 0.6, 0.006, reach * 0.4), foot], [0.0055 * g, 0.0045 * g, 0.003], 6, caps=False)
        pad = ellipsoid((foot[0] + side * 0.003, foot[1], foot[2] + 0.004), (0.008, 0.003, 0.011), 8, 4)
        legs[name] = b.node(name, [(skin, limb), (toe, pad)], (side * 0.014 * g, hip_y, at), body)

    stride = 30
    b.clip("move", s["beat"], 12, rot={
        body: turn(Y, wave(1, 6)),
        tail[0]: turn(Y, wave(1, -12, 0.7)), tail[1]: turn(Y, wave(1, -16, 1.4)), tail[2]: turn(Y, wave(1, -18, 2.1)),
        # A leg on +x swings forward with a negative turn about y, one on -x with a positive one; diagonal pairs together.
        legs["LegFL"]: turn(Y, wave(1, -stride)), legs["LegBR"]: turn(Y, wave(1, stride)),
        legs["LegFR"]: turn(Y, wave(1, -stride)), legs["LegBL"]: turn(Y, wave(1, stride)),
    })
    b.clip("idle", 4.0, 24, rot={
        body: turn(X, wave(1, 1.5, 0, -1.5)),
        tail[0]: turn(Y, wave(1, 5)), tail[1]: turn(Y, wave(1, 8, 0.8)), tail[2]: turn(Y, wave(1, 10, 1.6)),
    })
    # Tricks: push-ups, a turn after its own tail, a roll, playing dead on its back and a wriggle.
    b.trick("pushup", 1.5, pos={body: lift(0.012, 3)}, rot={body: swing(X, -6, 3)})
    b.trick("spin", 1.1, rot={body: full_turn(Y), tail[0]: lean(Y, 30)})
    b.trick("roll", 1.2, rot={body: full_turn(Z)}, pos={body: lift(0.01)})
    b.trick("dead", 2.6, rot={body: hold(Z, 180)}, pos={body: lift(0.006)}, keys=20)
    b.trick("dance", 1.4, rot={body: swing(Y, 18, 3), tail[0]: swing(Y, 26, 3, 1.0), tail[1]: swing(Y, 30, 3, 2.0)})
    return {"sockets": {"mouth": "Body", "back": "Body"}}
