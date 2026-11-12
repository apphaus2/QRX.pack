"""A bee: a fuzzy thorax, a head with feelers, a striped abdomen that wags, dangling legs and two blurred wings.

"move" flies with the wings whirring, "idle" hovers and turns. The origin is at the thorax. An ornament adds a
fluffy collar and bobbles on the feelers; a glow lights them.
"""
import math
from ..builder import painter, turn, wave
from ..builder import full_turn, lift, swing
from ..shapes import X, Y, Z, Profile, ball, box_of, ellipsoid, mirrored, moved, quat, sheet, tube

HABITAT, ORIGIN, LENGTH = "air", "centre", 0.066
SHAPE = {
    "fat": 1.0,         # how round it is (a bumblebee is fat)
    "long": 1.0,        # how long the abdomen is (a wasp's is long)
    "wings": 1.0,
    "beats": 9,         # wing beats in the half-second flying clip
}
COLOURS = {"body": "#F2C12E", "belly": "#F2C12E", "pattern": "#1B1B1B", "trim": "#FFF3C4", "fuzz": "#D9A521", "head": "#1B1B1B", "wing": "#E8F1F7", "eye": "#050505", "accent": "#FFF3C4", "glow": "#FFE680"}
PATTERNS = ("plain", "bands", "tips", "saddle", "spots")
TRICKS = ("dance", "spin", "flip")


def build(b):
    s, f = b.shape, b.shape["fat"]
    dark = b.mat("head", rough=0.5)
    prims = [(b.mat("fuzz", rough=0.95), ball((0, 0, 0.004), 0.0095 * f, 10, 7)), (dark, ellipsoid((0, -0.001, 0.017), (0.007, 0.007, 0.006), 8, 6))]
    prims += [(b.mat("eye", rough=0.2), ellipsoid((side * 0.0055, 0.0, 0.019), (0.003, 0.0042, 0.0035), 7, 5)) for side in (1, -1)]
    accent = b.mat("accent", rough=0.9, glow=True)
    for side in (1, -1):
        tip = (side * 0.007, 0.010, 0.032)
        prims.append((dark, tube([(side * 0.002, 0.005, 0.020), (side * 0.005, 0.011, 0.026), tip], [0.0008, 0.0007, 0.0006], 4, caps=False)))
        if b.has("ornament"): prims.append((accent, ball(tip, 0.0019, 6, 4)))
        for z in (0.010, 0.004, -0.002):
            prims.append((dark, tube([(side * 0.004, -0.007 * f, z), (side * 0.008, -0.014 * f, z - 0.002), (side * 0.007, -0.020 * f, z - 0.006)], [0.0011, 0.0009, 0.0006], 4, caps=False)))
    if b.has("ornament"):
        for k in range(9):
            a = 2 * math.pi * k / 9
            prims.append((accent, ball((0.0085 * f * math.cos(a), 0.0085 * f * math.sin(a), 0.011), 0.003, 6, 4)))
    body = b.node("Body", prims)
    bulb = ellipsoid((0, -0.001, -0.016 * s["long"]), (0.0105 * f, 0.0105 * f, 0.017 * s["long"]), 12, 10)
    tail = b.painted(bulb, painter(b, *box_of(bulb), belly=None), rough=0.8)
    tail.append((dark, tube([(0, -0.001, -0.031 * s["long"]), (0, -0.002, -0.038 * s["long"])], [0.002, 0.0003], 5, caps=False)))
    abdomen = b.node("Abdomen", tail, (0, 0, -0.004), body)
    chord = Profile([(0, 0.002), (0.5, 0.0065), (1, 0.003)])
    wings = {}
    for name, side in (("WingL", 1), ("WingR", -1)):
        pieces = []
        for span, sweep, wide in ((0.026 * s["wings"], 20, 1.0), (0.017 * s["wings"], 50, 0.8)):
            part = sheet(0.0, span, lambda x: chord(x / span) * wide, lambda x: -chord(x / span) * wide, 5, 2)
            part = moved(part, turn=quat(Y, sweep))
            pieces.append((b.mat("wing", double=True, rough=0.3), mirrored(part) if side < 0 else part))
        wings[name] = b.node(name, pieces, (side * 0.004, 0.008 * f, 0.006), body)

    def clip(name, duration, beats, keys, flap, wag, yaw, bob):
        b.clip(name, duration, keys, rot={
            wings["WingL"]: turn(Z, wave(beats, flap, 0, 20)), wings["WingR"]: turn(Z, wave(beats, -flap, 0, -20)),
            abdomen: turn(X, wave(1, wag)), body: turn(Y, wave(1, yaw)),
        }, pos={body: lambda u: (0, bob * math.sin(4 * math.pi * u), 0)})
    beats = int(s["beats"])
    clip("move", 0.5, beats, beats * 4, 35, 4, 0, 0.002)
    clip("idle", 1.0, 12, 48, 26, 6, 5, 0.003)
    # Tricks: a waggle dance, a turn and a loop, the wings beating through each.
    beat = lambda side: (lambda u: quat(Z, side * (20 + 30 * math.sin(2 * math.pi * 6 * u))))
    flap = {wings["WingL"]: beat(1), wings["WingR"]: beat(-1)}
    b.trick("dance", 1.0, rot={**flap, body: swing(Y, 26, 4), abdomen: swing(Y, 24, 6, 1.0)}, pos={body: lift(0.008, 2)}, keys=24)
    b.trick("spin", 1.0, rot={**flap, body: full_turn(Y)}, keys=24)
    b.trick("flip", 1.0, rot={**flap, body: full_turn(X, -1)}, pos={body: lift(0.03)}, keys=24)
    return {"sockets": {"mouth": "Body"}}
