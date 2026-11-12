"""A small bird: a plump body, a head with a beak, a fanned tail and two wings that bend at the wrist. With
`style` "owl" the head is big and round with a face and the eyes look ahead.

"move" flaps with the wing tips following and the body bobbing, "idle" hovers with quick shallow beats. The
origin is at the body. An ornament raises a crest and trails two tail streamers (an owl gets ear tufts); a glow lights them.
"""
import math
from ..builder import painter, turn, wave
from ..builder import full_turn, lean, lift, swing
from ..shapes import X, Y, Z, Profile, ball, box_of, ellipsoid, fin, loft, mirrored, quat, sheet, tube

HABITAT, ORIGIN, LENGTH = "air", "centre", 0.165
SHAPE = {
    "style": "song",    # song or owl
    "plump": 1.0,
    "head": 1.0,        # how big the head is
    "beak": 1.0,        # how long the beak is
    "wings": 1.0,       # how long the wings are
    "chord": 1.0,       # how broad the wings are
    "tail": 1.0,        # how long the tail is
    "fork": 0.0,        # how deeply the tail is forked, 0 to 1
    "streamers": 1.0,   # how long an ornament's streamers are
    "beat": 0.3,        # seconds per wing beat
}
CHOICES = {"style": ("song", "owl")}
COLOURS = {"body": "#8A6B4A", "belly": "#EAD9BE", "head": "#6E5238", "wing": "#6E5238", "pattern": "#3E2E20", "trim": "#F2E8D5", "beak": "#E0A030", "eye": "#050505", "accent": "#F25C54", "glow": "#FFE9A8"}
PATTERNS = ("plain", "bands", "stripes", "spots", "saddle", "tips")
TRICKS = ("jump", "spin", "flip", "bow", "dance", "shake", "headturn")


def build(b):
    s, p, owl = b.shape, b.shape["plump"], b.shape["style"] == "owl"
    rx = Profile([(0, 0.006), (0.25, 0.018), (0.55, 0.019), (0.85, 0.012), (1, 0.005)])
    ry = Profile([(0, 0.007), (0.25, 0.019), (0.55, 0.020), (0.85, 0.012), (1, 0.005)])
    yc = Profile([(0, 0.004), (0.5, 0.0), (1, 0.002)])
    n = 14
    hull = loft([(0.030 - 0.070 * i / n, yc(i / n), rx(i / n) * p, ry(i / n) * p) for i in range(n + 1)], 12)
    prims = b.painted(hull, painter(b, *box_of(hull), belly=-0.15), rough=0.85)
    horn = b.mat("beak", rough=0.5)
    for side in (1, -1):
        prims.append((horn, tube([(side * 0.006, -0.016 * p, -0.006), (side * 0.006, -0.022 * p, -0.016)], [0.0014, 0.0008], 4)))
    body = b.node("Body", prims)

    h = s["head"] * (1.3 if owl else 1.0)
    accent = b.mat("accent", double=True, rough=0.8, glow=True)
    head = [(b.mat("head", rough=0.85), ball((0, 0.002, 0.004), 0.0135 * h, 10, 7))]
    if owl:
        head.append((b.mat("belly", rough=0.9), ellipsoid((0, 0.002, 0.004 + 0.008 * h), (0.0115 * h, 0.0105 * h, 0.007 * h), 10, 6)))
        head += b.eyes([(side * 0.0052 * h, 0.004, 0.004 + 0.0135 * h) for side in (1, -1)], 0.003 * h, glow=True)
        head.append((horn, tube([(0, 0.0005, 0.004 + 0.013 * h), (0, -0.004, 0.004 + 0.0165 * h)], [0.0022, 0.0004], 5)))
    else:
        head += b.eyes([(side * 0.0088 * h, 0.005, 0.011) for side in (1, -1)], 0.0024)
        head.append((horn, tube([(0, 0, 0.004 + 0.011 * h), (0, -0.001, 0.004 + 0.012 * h + 0.014 * s["beak"])], [0.004, 0.0005], 6)))
    if b.has("ornament"):
        if owl:
            for side in (1, -1):
                head.append((accent, fin([(-0.004, 0), (0.001 * side, 0.016), (0.004, 0)], (side * 0.008 * h, 0.002 + 0.011 * h, 0.004), X, (0.25 * side, 1, -0.2))))
        else:
            head.append((accent, fin([(0.006, 0.010 * h), (-0.002, 0.034), (-0.014, 0.032), (-0.008, 0.010 * h)], (0, 0, 0), Z, Y)))
    head_node = b.node("Head", head, (0, 0.012 * p + (0.004 if owl else 0.002), 0.026 if owl else 0.030), body)

    feather = b.mat("wing", double=True, rough=0.85)
    long, half = 0.034 * s["tail"], 0.013
    fan = sheet(-half, half, lambda x: 0.004, lambda x: -long * (1 - s["fork"] * 0.6 * (1 - abs(x) / half)) + 0.25 * abs(x), 6, 3)
    tail = b.painted(fan, lambda c, n: "pattern" if c[2] < -long * 0.62 else "wing", double=True, rough=0.85)
    if b.has("ornament") and not owl:
        reach = 0.07 * s["streamers"]
        for side in (1, -1):
            tail.append((accent, fin([(-0.002, 0), (0.002, 0), (0.003, reach * 0.8), (0.0, reach)], (side * 0.005, 0, -long * 0.6), (side, 0, 0), (0.12 * side, 0, -1))))
    tail_node = b.node("Tail", tail, (0, 0.003, -0.036), body)

    inner, outer, c = 0.030 * s["wings"], 0.036 * s["wings"], s["chord"]
    front_in, back_in = Profile([(0, 0.016), (1, 0.014)]), Profile([(0, -0.020), (1, -0.022)])
    front_out, back_out = Profile([(0, 0.014), (0.6, 0.008), (1, -0.004)]), Profile([(0, -0.022), (0.6, -0.019), (1, -0.011)])
    camber = lambda sp, ch: 0.0025 * 4 * ch * (1 - ch)

    def feathers(span, front, back):
        part = sheet(0.0, span, lambda x: front(x / span) * c, lambda x: back(x / span) * c, 5, 5, camber)

        def paint(pt, n):
            lo, hi = back(pt[0] / span) * c, front(pt[0] / span) * c
            ch = (pt[2] - lo) / (hi - lo)
            if ch < 0.36: return "pattern"
            if b.has("trim") and ch < 0.5: return "trim"
            return "wing"
        return b.painted(part, paint, double=True, rough=0.85)
    wings = {}
    for name, side in (("L", 1), ("R", -1)):
        flip = (lambda pieces: [(m, mirrored(q)) for m, q in pieces]) if side < 0 else (lambda pieces: pieces)
        arm = b.node("Wing" + name, flip(feathers(inner, front_in, back_in)), (side * 0.013 * p, 0.008 * p, 0.006), body)
        wings[name] = (arm, b.node("Wing" + name + "Tip", flip(feathers(outer, front_out, back_out)), (side * inner, 0, 0), arm))

    def clip(name, duration, beats, keys, flap, bend, tilt, bob):
        rot = {tail_node: turn(X, wave(beats, 5, 0.5)), head_node: turn(X, wave(beats, 2, 0, -tilt * 0.6)), body: turn(X, wave(1, 0.5, 0, tilt))}
        for side, (arm, tip) in ((1, wings["L"]), (-1, wings["R"])):
            rot[arm] = turn(Z, wave(beats, side * flap, 0, side * 8))
            rot[tip] = turn(Z, wave(beats, side * bend, 1.0))
        b.clip(name, duration, keys, rot=rot, pos={body: lambda u: (0, bob * math.sin(2 * math.pi * beats * u - 1.9), 0)})
    clip("move", s["beat"] * 2, 2, 24, 38, 24, 0, 0.004)
    clip("idle", s["beat"] * 2, 4, 32, 30, 16, -14, 0.002)
    # Tricks: a hop in the air, a twirl, a loop, a bow, a rocking dance, a shake of the feathers and (for an owl)
    # turning the head right round; the wings beat through each.
    beat = lambda side, sweep, phase=0.0: (lambda u: quat(Z, side * (8 + sweep * math.sin(2 * math.pi * 3 * u - phase))))
    flap = {}
    for side, (arm, tip) in ((1, wings["L"]), (-1, wings["R"])):
        flap[arm], flap[tip] = beat(side, 30), (lambda u, side=side: quat(Z, side * 18 * math.sin(2 * math.pi * 3 * u - 1.0)))
    b.trick("jump", 0.9, rot=dict(flap), pos={body: lift(0.04, 2)}, keys=18)
    b.trick("spin", 0.9, rot={**flap, body: full_turn(Y)}, keys=18)
    b.trick("flip", 1.0, rot={**flap, body: full_turn(X, -1)}, pos={body: lift(0.04)}, keys=18)
    b.trick("bow", 1.0, rot={**flap, body: lean(X, 32), head_node: lean(X, 14), tail_node: lean(X, -18)}, keys=18)
    b.trick("dance", 1.0, rot={**flap, body: swing(Z, 20, 3)}, pos={body: lift(0.01, 3)}, keys=18)
    b.trick("shake", 0.9, rot={**flap, body: swing(Z, 14, 5), tail_node: swing(Y, 20, 5, 1.0)}, keys=18)
    b.trick("headturn", 1.8, rot={**flap, head_node: full_turn(Y)}, keys=18)
    return {"sockets": {"mouth": "Head", "back": "Body"}}
