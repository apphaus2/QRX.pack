"""A ray: a flat body between two wings that each bend in the middle, eyes on top and a whip of a tail.

"move" rolls a wave out along each wing, "idle" a slow shallow one. The origin is at the middle of the body.
An ornament adds two lobes ahead of the mouth and a longer, finned tail; a glow lights a bead on its tip.
"""
import math
from ..builder import painter, turn, wave
from ..shapes import Y, Z, Profile, ball, fin, loft, mirrored, moved, sheet, tube

HABITAT, ORIGIN, LENGTH = "water", "centre", 0.185
SHAPE = {
    "span": 1.0,        # how far the wings reach
    "tail": 1.0,        # how long the tail is
    "beat": 1.4,        # seconds per wing beat
}
COLOURS = {"body": "#B9A679", "belly": "#F2ECDD", "pattern": "#6E5A36", "trim": "#3C3120", "eye": "#080808", "accent": "#D9B45A", "glow": "#9EE8FF"}
PATTERNS = ("plain", "spots", "saddle", "bands", "tips")


def build(b):
    s = b.shape
    hinge, tip = 0.045, 0.08 * s["span"]
    rx = Profile([(0, 0.004), (0.2, 0.016), (0.5, 0.020), (0.8, 0.012), (1, 0.004)])
    ry = Profile([(0, 0.002), (0.2, 0.007), (0.5, 0.009), (0.8, 0.006), (1, 0.003)])
    hull = loft([(0.05 - 0.09 * i / 14, 0.0, rx(i / 14), ry(i / 14)) for i in range(15)], 12)
    paint = painter(b, (-tip, -0.009, -0.04), (tip, 0.009, 0.05), belly=-0.05)
    prims = b.painted(hull, paint)
    prims += [(b.mat("body"), ball((side * 0.009, 0.0075, 0.028), 0.0042, 7, 5)) for side in (1, -1)]
    prims += b.eyes([(side * 0.0105, 0.009, 0.03) for side in (1, -1)], 0.0026)
    if b.has("ornament"):
        for side in (1, -1):
            prims.append((b.mat("accent", glow=True), tube([(side * 0.008, 0, 0.044), (side * 0.012, -0.001, 0.056), (side * 0.010, -0.002, 0.066)], [0.004, 0.003, 0.0012], 6)))
    body = b.node("Body", prims)

    front = Profile([(0, 0.046), (0.02, 0.040), (0.05, 0.018), (0.08, -0.012)])
    back = Profile([(0, -0.036), (0.02, -0.034), (0.05, -0.028), (0.08, -0.020)])
    reach = lambda x: abs(x) / s["span"]
    thick = lambda x0, x1: (lambda sp, c: 0.0065 * (1 - (x0 + (x1 - x0) * sp) / tip) * 4 * c * (1 - c) + 0.0004)
    wings = {}
    for name, side in (("L", 1), ("R", -1)):
        parent = body
        for part_name, x0, x1 in (("Wing" + name, 0.012, hinge), ("Wing" + name + "Tip", hinge, tip)):
            pieces = []
            for under in (False, True):
                part = sheet(x0, x1, lambda x: front(reach(x)), lambda x: back(reach(x)), 5, 6, thick(x0, x1), under)
                if side < 0: part = mirrored(part)
                pieces += b.painted(part, paint)
            at = (side * x0, 0, 0)
            parent = b.node(part_name, [(m, moved(p, at=(-at[0], 0, 0))) for m, p in pieces], (side * (x0 if parent == body else x0 - 0.012), 0, 0), parent)
            wings[part_name] = parent
    whip = 0.05 * s["tail"] * (1.35 if b.has("ornament") else 1.0)
    skin = b.mat("body")
    tail1 = b.node("Tail1", [(skin, tube([(0, 0, 0.004), (0, 0, -whip)], [0.0034, 0.002], 6, caps=False))], (0, 0, -0.038), body)
    end = [(skin, tube([(0, 0, 0), (0, 0, -whip)], [0.002, 0.0005], 5, caps=False))]
    if b.has("ornament"): end.append((b.mat("accent", double=True, glow=True), fin([(-0.2 * whip, 0), (-0.6 * whip, 0.007), (-whip, 0), (-0.6 * whip, -0.004)], (0, 0, 0), Z, Y)))
    if b.has("glow"): end.append((b.mat("glow", rough=0.3, glow=True), ball((0, 0, -whip), 0.003, 6, 4)))
    tail2 = b.node("Tail2", end, (0, 0, -whip), tail1)

    def clip(name, duration, flap, bend, bob):
        b.clip(name, duration, 16, rot={
            wings["WingL"]: turn(Z, wave(1, flap)), wings["WingLTip"]: turn(Z, wave(1, bend, 1.1)),
            wings["WingR"]: turn(Z, wave(1, -flap)), wings["WingRTip"]: turn(Z, wave(1, -bend, 1.1)),
            tail1: turn(Y, wave(1, 8)), tail2: turn(Y, wave(1, 12, 0.9)),
        }, pos={body: lambda u: (0, bob * math.sin(2 * math.pi * u - 1.57), 0)})
    clip("move", s["beat"], 22, 26, 0.004)
    clip("idle", s["beat"] * 2.3, 8, 10, 0.002)
    return {"sockets": {"mouth": "Body"}}
