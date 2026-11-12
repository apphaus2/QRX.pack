"""A butterfly, after QRX.pack's, or with `style` "moth" a moth: a body and head with feelers and two wings hinged
at the body, each a forewing and a hindwing.

"move" flaps with a bob, "idle" holds the wings up and pumps them slowly (a moth trembles them, held flat). The
origin is at the body. An ornament draws the hindwings out into tails; a glow lights the wing markings that are
painted "lit".
"""
import math
from ..shapes import X, Z, Profile, ball, ellipsoid, fin, mirrored, quat, sheet, tube

HABITAT, ORIGIN, LENGTH = "air", "centre", 0.15
SHAPE = {
    "style": "butterfly",   # butterfly or moth
    "fore": 1.0,            # the forewings' reach
    "hind": 1.0,            # the hindwings' reach
    "tails": 1.0,           # how long an ornament's tails are
    "fat": 1.0,             # how thick the body is
    "flap": [-15, 70],      # the wings' lowest and highest angle in flight, degrees above flat
    "rate": 6,              # flaps per second
}
CHOICES = {"style": ("butterfly", "moth")}
COLOURS = {"body": "#2A1D12", "wing": "#EE7A1A", "hind": "#FBB829", "pattern": "#2B1A38", "trim": "#FFFFFF", "eye": "#050505", "accent": "#F2E2B0", "glow": "#FFF2A8"}
PATTERNS = ("plain", "edged", "eyespots", "bands", "veins")


def build(b):
    s, moth = b.shape, b.shape["style"] == "moth"
    fat = s["fat"] * (1.7 if moth else 1.0)
    dark = b.mat("body", rough=0.9)
    prims = [(dark, ellipsoid((0, 0, 0), (0.006 * fat, 0.006 * fat, 0.026), 10, 7))]
    if moth: prims.append((b.mat("accent", rough=0.95), ellipsoid((0, 0.001, 0.016), (0.0085 * fat * 0.75, 0.008 * fat * 0.75, 0.009), 10, 6)))
    body = b.node("Body", prims)
    head = [(dark, ball((0, 0.001, 0.030), 0.0075, 8, 6))] + b.eyes([(side * 0.005, 0.004, 0.034) for side in (1, -1)], 0.0025)
    for side in (1, -1):
        tip = (side * 0.016, 0.024, 0.052)
        if moth:
            head.append((b.mat("accent", double=True, rough=0.9), fin([(0, 0), (0.008, 0.004), (0.02, 0.003), (0.026, 0), (0.02, -0.003), (0.008, -0.004)], (side * 0.003, 0.006, 0.034), (side * 0.6, 0.5, 0.6), (-side * 0.6, 0.0, 0.6))))
        else:
            head += [(dark, tube([(side * 0.003, 0.006, 0.034), tip], [0.0009, 0.0006], 5, caps=False)), (dark, ball(tip, 0.0016, 6, 4))]
    b.node("Head", head, parent=body)

    if moth:
        fore = (0.068 * s["fore"], Profile([(0, 0.010), (0.4, 0.024), (0.8, 0.020), (1, 0.004)]), Profile([(0, -0.004), (0.5, -0.018), (0.85, -0.024), (1, -0.010)]))
        hind = (0.040 * s["hind"], Profile([(0, -0.004), (1, -0.016)]), Profile([(0, -0.022), (0.4, -0.040), (0.8, -0.040), (1, -0.024)]))
    else:
        fore = (0.070 * s["fore"], Profile([(0, 0.008), (0.3, 0.030), (0.7, 0.040), (1, 0.030)]), Profile([(0, 0.0), (0.5, 0.002), (0.85, 0.008), (1, 0.020)]))
        hind = (0.050 * s["hind"], Profile([(0, 0.0), (0.5, -0.002), (1, -0.012)]), Profile([(0, -0.024), (0.3, -0.042), (0.6, -0.046), (1, -0.026)]))
    kind, p = b.pattern["type"], b.pattern
    mark = "glow" if p.get("lit") and b.has("glow") else "pattern"
    trim = b.has("trim")

    def painted(span, front, back, base, side):
        part = sheet(0.0, span, lambda x: front(x / span), lambda x: back(x / span), 8, 5)

        def paint(c, n):
            sp = c[0] / span
            lo, hi = back(sp), front(sp)
            ch = (c[2] - lo) / (hi - lo) if hi > lo else 0.5
            if kind == "edged":
                if sp > 0.8 or ch < 0.14 and sp > 0.3: return mark
                if trim and sp > 0.68: return "trim"
            elif kind == "eyespots":
                d = math.hypot((sp - 0.62) * 1.3, ch - 0.5)
                if d < float(p.get("size", 0.2)): return mark
                if trim and d < float(p.get("size", 0.2)) * 1.6: return "trim"
            elif kind == "bands":
                f = (sp * int(p.get("count", 3))) % 1.0
                if f > 1 - float(p.get("width", 0.4)): return mark
                if trim and f > 1 - float(p.get("width", 0.4)) - 0.12: return "trim"
            elif kind == "veins":
                if abs((ch * 4) % 1.0 - 0.5) < 0.16 or sp > 0.9: return mark
            return base
        pieces = b.painted(part, paint, double=True, rough=0.8)
        return [(m, mirrored(piece)) for m, piece in pieces] if side < 0 else pieces

    wings = {}
    for name, side in (("WingL", 1), ("WingR", -1)):
        prims = painted(*fore, "wing", side) + painted(*hind, "hind", side)
        if b.has("ornament") and not moth:
            span, long = hind[0], 0.034 * s["tails"]
            prims.append((b.mat("accent", double=True, rough=0.8, glow=True), fin([(0.45 * span * side, -0.040), (0.62 * span * side, -0.046 - long), (0.70 * span * side, -0.046 - long * 0.95), (0.74 * span * side, -0.040)], (0, 0, 0), X, Z)))
        wings[name] = b.node(name, prims, (side * 0.004 * fat, 0.004, 0.0), body)

    lo, hi = s["flap"]
    rate = int(s["rate"])
    angle = lambda u: (lo + hi) / 2 + (hi - lo) / 2 * math.cos(2 * math.pi * rate * u)
    b.clip("move", 1.0, rate * 6, rot={wings["WingL"]: lambda u: quat(Z, angle(u)), wings["WingR"]: lambda u: quat(Z, -angle(u))},
           pos={body: lambda u: (0, 0.004 * math.sin(2 * math.pi * max(1, rate // 2) * u), 0)})
    rest = (lambda u: 8 + 5 * math.cos(2 * math.pi * 6 * u)) if moth else (lambda u: 45 + 25 * math.cos(2 * math.pi * u))
    b.clip("idle", 3.0, 36 if moth else 24, rot={wings["WingL"]: lambda u: quat(Z, rest(u)), wings["WingR"]: lambda u: quat(Z, -rest(u))})
    return {"sockets": {"mouth": "Head"}}
