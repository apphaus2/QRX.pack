"""A fish, after QRX.pack's reef fish: a deep lofted body, a tail and two pectoral fins of their own.

"move" sways the body and beats the tail, "idle" sways slowly with the pectoral fins paddling. The origin is at
mid-body. An ornament lengthens the tail and the dorsal fin into streamers; a glow lights a row of dots along
each flank.
"""
import math
from ..builder import painter, turn, wave
from ..builder import full_turn, lift, swing
from ..shapes import X, Y, Z, Profile, ball, box_of, fin, loft, quat

HABITAT, ORIGIN, LENGTH = "water", "centre", 0.125
SHAPE = {
    "depth": 1.0,       # how tall the body is
    "girth": 1.0,       # how wide
    "tail": "fork",     # fork, round, fan, lyre
    "dorsal": "sail",   # sail, low, tall, spines
    "fins": 1.0,        # the size of every fin
    "beat": 0.4,        # seconds per tail beat
}
CHOICES = {"tail": ("fork", "round", "fan", "lyre"), "dorsal": ("sail", "low", "tall", "spines")}
COLOURS = {"body": "#F26B0F", "belly": "#F7F1E3", "pattern": "#FFFFFF", "trim": "#111111", "fin": "#F8851F", "eye": "#080808", "accent": "#F8851F", "glow": "#9FF3FF"}
PATTERNS = ("plain", "bands", "stripes", "spots", "saddle", "tips")
TRICKS = ("jump", "spin", "flip", "roll", "dance")

TAILS = {   # (back, up) outlines round a hub at the tail's root
    "fork": [(0.008, 0), (0, -0.008), (0.012, -0.017), (0.030, -0.023), (0.024, 0), (0.030, 0.023), (0.012, 0.017), (0, 0.008), (0, -0.008)],
    "round": [(0.008, 0), (0, -0.007), (0.010, -0.016), (0.022, -0.018), (0.030, -0.010), (0.032, 0), (0.030, 0.010), (0.022, 0.018), (0.010, 0.016), (0, 0.007), (0, -0.007)],
    "fan": [(0.008, 0), (0, -0.007), (0.012, -0.024), (0.028, -0.034), (0.036, -0.018), (0.038, 0), (0.036, 0.018), (0.028, 0.034), (0.012, 0.024), (0, 0.007), (0, -0.007)],
    "lyre": [(0.010, 0), (0, -0.007), (0.014, -0.018), (0.046, -0.030), (0.022, -0.005), (0.017, 0), (0.022, 0.005), (0.046, 0.030), (0.014, 0.018), (0, 0.007), (0, -0.007)],
}
DORSALS = {  # (z, height over the back)
    "sail": [(0.024, -0.008), (0.014, 0.013), (-0.006, 0.016), (-0.030, 0.006), (-0.030, -0.010)],
    "low": [(0.022, -0.006), (0.012, 0.006), (-0.020, 0.007), (-0.034, 0.002), (-0.034, -0.008)],
    "tall": [(0.020, -0.008), (0.012, 0.022), (0.002, 0.032), (-0.012, 0.020), (-0.028, 0.008), (-0.030, -0.010)],
}


def build(b):
    s = b.shape
    nose, tail, n = 0.052, -0.040, 26
    rx = Profile([(0, 0.0025), (0.15, 0.009), (0.4, 0.013), (0.7, 0.010), (1, 0.0045)])
    ry = Profile([(0, 0.004), (0.1, 0.018), (0.3, 0.029), (0.5, 0.030), (0.75, 0.021), (0.9, 0.012), (1, 0.008)])
    width, height = (lambda t: rx(t) * s["girth"]), (lambda t: ry(t) * s["depth"])
    hull = loft([(nose + (tail - nose) * i / n, 0.0, width(i / n), height(i / n)) for i in range(n + 1)], 14)
    prims = b.painted(hull, painter(b, *box_of(hull)))
    prims += b.eyes([(side * width(0.17) * 0.85, height(0.17) * 0.25, nose + (tail - nose) * 0.17) for side in (1, -1)], 0.0032)

    fins, grand = b.mat("fin", double=True, rough=0.8), (1.35 if b.has("ornament") else 1.0) * s["fins"]
    top = lambda z: height((nose - z) / (nose - tail))
    if s["dorsal"] == "spines":
        for z in (0.020, 0.008, -0.004, -0.016):
            prims.append((fins, fin([(z + 0.005, top(z + 0.005) - 0.006), (z - 0.004, top(z) + 0.016 * grand), (z - 0.007, top(z - 0.007) - 0.006)], (0, 0, 0), Z, Y)))
    else:
        prims.append((fins, fin([(z, top(z) + (h * grand if h > 0 else h)) for z, h in DORSALS[s["dorsal"]]], (0, 0, 0), Z, Y)))
    prims.append((fins, fin([(z, -top(z) - (h * s["fins"] if h > 0 else h)) for z, h in ((-0.004, -0.006), (-0.012, 0.010), (-0.028, 0.006), (-0.030, -0.008))], (0, 0, 0), Z, Y)))
    for side in (1, -1):
        prims.append((fins, fin([(0, 0), (0.010, 0.003), (0.014, 0.010), (0.009, 0.015), (0, 0.010)], (side * 0.007 * s["girth"], -0.014 * s["depth"], 0.012), (side, -0.7, 0), (0, 0, -1))))
    if b.has("glow"):
        dots = b.mat("glow", rough=0.3, glow=True)
        for side in (1, -1):
            for k in range(5):
                t = 0.28 + 0.13 * k
                prims.append((dots, ball((side * width(t) * 0.97, 0.002, nose + (tail - nose) * t), 0.0022, 6, 4)))
    body = b.node("Body", prims)

    stretch = 1.5 if b.has("ornament") else 1.0
    outline = [(x * stretch * s["fins"], y * s["fins"] * max(1.0, 0.6 + 0.4 * s["depth"])) for x, y in TAILS[s["tail"]]]
    tail_node = b.node("Tail", [(fins, fin(outline, (0, 0, 0), (0, 0, -1), Y))], (0, 0, tail), body)
    pecs = {}
    for name, side in (("PecL", 1), ("PecR", -1)):
        shape = [(x * s["fins"], y * s["fins"]) for x, y in ((0, 0), (0.012, 0.003), (0.018, 0.011), (0.012, 0.017), (0, 0.011))]
        pecs[name] = b.node(name, [(fins, fin(shape, (0, 0, 0), (side, -0.35, 0), (0, 0, -1)))], (side * 0.011 * s["girth"], -0.004, 0.024), body)

    def clip(name, duration, sway, beat, paddle):
        b.clip(name, duration, 24, rot={
            body: turn(Y, wave(2, sway)),
            tail_node: turn(Y, wave(2, beat, 1.3)),
            pecs["PecL"]: lambda u: quat(Z, paddle * (0.5 + 0.5 * math.sin(4 * math.pi * u))),
            pecs["PecR"]: lambda u: quat(Z, -paddle * (0.5 + 0.5 * math.sin(4 * math.pi * u))),
        })
    clip("move", s["beat"] * 2, 3, 25, 6)
    clip("idle", s["beat"] * 8, 1, 8, 25)
    # Tricks: a leap, a turn on the spot, a somersault, a barrel roll and a wiggle.
    b.trick("jump", 0.9, rot={body: swing(X, -28, 1)}, pos={body: lift(0.05)})
    b.trick("spin", 1.0, rot={body: full_turn(Y)})
    b.trick("flip", 1.1, rot={body: full_turn(X, -1)}, pos={body: lift(0.03)})
    b.trick("roll", 1.0, rot={body: full_turn(Z)})
    b.trick("dance", 1.4, rot={body: swing(Y, 24, 3), tail_node: swing(Y, 38, 3, 1.0)})
    return {"sockets": {"mouth": "Body"}}
