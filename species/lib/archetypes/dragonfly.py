"""A dragonfly: a big-eyed head, a thorax, a long banded abdomen in two pieces and four narrow wings.

"move" beats the two pairs of wings out of step, "idle" hovers with the abdomen dipping. The origin is at the
thorax. An ornament ends the abdomen in a club and marks the wing tips; a glow lights the club.
"""
import math
from ..builder import painter, turn, wave
from ..builder import full_turn, lift, swing
from ..shapes import X, Y, Z, Profile, ball, ellipsoid, mirrored, moved, quat, sheet, tube

HABITAT, ORIGIN, LENGTH = "air", "centre", 0.14
SHAPE = {
    "span": 1.0,        # how long the wings are
    "tail": 1.0,        # how long the abdomen is
    "girth": 1.0,
    "beats": 5,         # wing beats in the half-second flying clip
}
COLOURS = {"body": "#2E86C1", "belly": "#2E86C1", "pattern": "#12344D", "trim": "#9FD3F5", "wing": "#DCEBF5", "eye": "#3A7D44", "accent": "#F25C54", "glow": "#9FF5FF"}
PATTERNS = ("plain", "bands", "stripes", "tips", "saddle")
TRICKS = ("spin", "flip", "dance")


def build(b):
    s, g = b.shape, b.shape["girth"]
    skin = b.mat("body", rough=0.4)
    prims = [(skin, ellipsoid((0, 0, 0.012), (0.008 * g, 0.008 * g, 0.014), 10, 7)), (skin, ball((0, 0.001, 0.030), 0.0072, 8, 6))]
    prims += [(b.mat("eye", rough=0.2), ellipsoid((side * 0.0052, 0.003, 0.0325), (0.005, 0.0055, 0.006), 8, 6)) for side in (1, -1)]
    for side in (1, -1):
        for z in (0.020, 0.014, 0.008):
            prims.append((b.mat("pattern"), tube([(side * 0.004, -0.006, z), (side * 0.008, -0.012, z + 0.004), (side * 0.006, -0.015, z + 0.009)], [0.0009, 0.0007, 0.0005], 4, caps=False)))
    body = b.node("Body", prims)
    piece = 0.04 * s["tail"]
    paint = painter(b, (-0.005, -0.005, -2 * piece), (0.005, 0.005, 0.0), belly=None)
    abd1 = b.node("Abd1", b.painted(tube([(0, 0, 0.002), (0, 0, -piece)], [0.0046 * g, 0.0034 * g], 8, caps=False), paint, rough=0.4), (0, 0, 0), body)
    end = b.painted(tube([(0, 0, 0), (0, 0, -piece)], [0.0034 * g, 0.0028 * g], 8), paint, at=(0, 0, -piece), rough=0.4)
    if b.has("ornament"): end.append((b.mat("accent", rough=0.3, glow=True), ellipsoid((0, 0, -piece), (0.0058, 0.0046, 0.009), 8, 5)))
    abd2 = b.node("Abd2", end, (0, 0, -piece), abd1)

    span = 0.064 * s["span"]
    chord = Profile([(0, 0.003), (0.15, 0.006), (0.7, 0.008), (0.95, 0.006), (1, 0.002)])
    wings = {}
    for pair, z, sweep, wide in (("F", 0.018, -8, 1.0), ("B", 0.006, 10, 1.15)):
        for name, side in (("L", 1), ("R", -1)):
            part = sheet(0.0, span, lambda x: chord(x / span) * wide, lambda x: -chord(x / span) * wide, 8, 2)
            pieces = b.painted(part, lambda c, n: "pattern" if b.has("ornament") and c[0] > 0.8 * span and c[2] > 0 else ("trim" if b.has("trim") and c[0] < 0.12 * span else "wing"), double=True, rough=0.3)
            pieces = [(m, moved(piece_, turn=quat(Y, sweep))) for m, piece_ in pieces]
            if side < 0: pieces = [(m, mirrored(piece_)) for m, piece_ in pieces]
            wings[pair + name] = b.node("Wing" + pair + name, pieces, (side * 0.005 * g, 0.006 * g, z), body)

    def clip(name, duration, beats, keys, flap, dip, yaw):
        b.clip(name, duration, keys, rot={
            wings["FL"]: turn(Z, wave(beats, flap, 0, 8)), wings["FR"]: turn(Z, wave(beats, -flap, 0, -8)),
            wings["BL"]: turn(Z, wave(beats, flap, 1.57, 4)), wings["BR"]: turn(Z, wave(beats, -flap, 1.57, -4)),
            abd1: turn(X, wave(1, dip)), abd2: turn(X, wave(1, dip * 1.3, 0.8)), body: turn(Y, wave(1, yaw)),
        }, pos={body: lambda u: (0, 0.002 * math.sin(2 * math.pi * u), 0)})
    beats = int(s["beats"])
    clip("move", 0.5, beats, beats * 6, 28, 3, 0)
    clip("idle", 1.0, 8, 40, 22, 5, 4)
    # Tricks: a loop, a turn and a zigzag, the wings beating through each.
    beat = lambda side, phase: (lambda u: quat(Z, side * (8 + 28 * math.sin(2 * math.pi * 6 * u - phase))))
    flap = {wings["FL"]: beat(1, 0), wings["FR"]: beat(-1, 0), wings["BL"]: beat(1, 1.57), wings["BR"]: beat(-1, 1.57)}
    b.trick("flip", 1.0, rot={**flap, body: full_turn(X, -1)}, pos={body: lift(0.04)}, keys=24)
    b.trick("spin", 1.0, rot={**flap, body: full_turn(Y)}, keys=24)
    b.trick("dance", 1.0, rot={**flap, body: swing(Y, 30, 3)}, pos={body: lambda u: (0.03 * math.sin(math.pi * u) * math.sin(6 * math.pi * u), 0.0, 0.0)}, keys=24)
    return {"sockets": {"mouth": "Body"}}
