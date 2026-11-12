"""A bat: a furry body, a head with tall ears, and two skin wings that fold at the wrist, with finger bones
showing through the scalloped membrane.

"move" flaps with the hands following the arms, "idle" beats more gently, hanging in the air. The origin is at
the body. An ornament grows the ears and adds a tail membrane; a glow lights the eyes and the finger bones.
"""
import math
from ..builder import turn, wave
from ..shapes import X, Z, ball, ellipsoid, fin, mirrored, sheet, tube

HABITAT, ORIGIN, LENGTH = "air", "centre", 0.178
SHAPE = {
    "span": 1.0,        # how long the wings are
    "ears": 1.0,
    "plump": 1.0,
    "beats": 4,         # wing beats in the one-second flying clip
}
COLOURS = {"body": "#4A3B36", "belly": "#7A655B", "membrane": "#2E2422", "bone": "#5A4740", "skin": "#8A6B62", "eye": "#0A0A0A", "accent": "#C9A0DC", "glow": "#E0B0FF"}
PATTERNS = ("plain", "veins")


def build(b):
    s, p = b.shape, b.shape["plump"]
    fur = b.mat("body", rough=0.95)
    prims = [(fur, ellipsoid((0, 0, 0), (0.011 * p, 0.011 * p, 0.020), 10, 7)), (b.mat("belly", rough=0.95), ellipsoid((0, -0.004, 0.006), (0.008 * p, 0.007 * p, 0.010), 8, 5))]
    skin = b.mat("skin", double=True, rough=0.7)
    for side in (1, -1):
        prims.append((b.mat("skin", rough=0.7), tube([(side * 0.004, -0.004, -0.016), (side * 0.006, -0.008, -0.026)], [0.0014, 0.0008], 4)))
    if b.has("ornament"):
        prims.append((b.mat("accent", double=True, rough=0.7, glow=True), fin([(0, 0.016), (0.007, 0.03), (0, 0.04), (-0.007, 0.03)], (0, -0.004, 0), X, (0, 0, -1))))
    body = b.node("Body", prims)
    ears = s["ears"] * (1.45 if b.has("ornament") else 1.0)
    head = [(fur, ball((0, 0.002, 0.006), 0.0105, 9, 6)), (b.mat("skin", rough=0.7), ellipsoid((0, -0.001, 0.015), (0.004, 0.0035, 0.004), 7, 5))]
    head += b.eyes([(side * 0.0055, 0.004, 0.0135) for side in (1, -1)], 0.0019, glow=True)
    for side in (1, -1):
        head.append((skin, fin([(-0.005, 0), (0.002 * side, 0.02 * ears), (0.005, 0.002)], (side * 0.0065, 0.009, 0.004), X, (0.2 * side, 1, -0.1))))
    head_node = b.node("Head", head, (0, 0.004, 0.019), body)

    arm, hand = 0.035 * s["span"], 0.046 * s["span"]
    scallop = lambda x, span, n: 0.006 * abs(math.sin(math.pi * n * x / span))
    front_arm, back_arm = (lambda x: 0.010 + 0.010 * x / arm), (lambda x: -0.032 + scallop(x, arm, 1))
    front_hand, back_hand = (lambda x: 0.020 - 0.032 * (x / hand) ** 1.5), (lambda x: -0.032 + 0.020 * (x / hand) + scallop(x, hand, 2) * (1 - 0.5 * x / hand))
    bone = "glow" if b.has("glow") and (b.pattern["type"] == "veins" or b.pattern.get("lit")) else "bone"

    def membrane(span, front, back, fingers):
        part = sheet(0.0, span, front, back, 8, 6)

        def paint(c, n):
            lo, hi = back(c[0]), front(c[0])
            ch = (c[2] - lo) / (hi - lo) if hi > lo else 1.0
            if ch > 0.84: return bone
            if fingers and (abs(ch - 0.5) < 0.06 or abs(c[0] / span - 0.5) < 0.05 and ch < 0.5): return bone
            return "membrane"
        return b.painted(part, paint, double=True, rough=0.75)
    wings = {}
    for name, side in (("L", 1), ("R", -1)):
        flip = (lambda pieces: [(m, mirrored(q)) for m, q in pieces]) if side < 0 else (lambda pieces: pieces)
        upper = b.node("Wing" + name, flip(membrane(arm, front_arm, back_arm, False)), (side * 0.008 * p, 0.004, 0.004), body)
        wings[name] = (upper, b.node("Wing" + name + "Tip", flip(membrane(hand, front_hand, back_hand, True)), (side * arm, 0, 0), upper))

    def clip(name, duration, beats, keys, flap, bend, tilt, bob):
        rot = {head_node: turn(X, wave(beats, 3, 0, -tilt * 0.5)), body: turn(X, wave(1, 0.5, 0, tilt))}
        for side, (upper, tip) in ((1, wings["L"]), (-1, wings["R"])):
            rot[upper] = turn(Z, wave(beats, side * flap, 0, side * 5))
            rot[tip] = turn(Z, wave(beats, side * bend, 1.0, -side * 8))
        b.clip(name, duration, keys, rot=rot, pos={body: lambda u: (0, bob * math.sin(2 * math.pi * beats * u - 1.9), 0)})
    beats = int(s["beats"])
    clip("move", 1.0, beats, beats * 8, 35, 30, 0, 0.005)
    clip("idle", 1.2, 3, 24, 25, 20, -10, 0.004)
    return {"sockets": {"mouth": "Head"}}
