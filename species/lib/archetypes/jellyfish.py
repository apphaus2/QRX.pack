"""A jellyfish: a bell that pulses, oral arms under it and a ring of two-jointed tentacles.

"move" pulses the bell and trails the tentacles, "idle" does the same gently. The origin is in the middle of the
whole animal. An ornament lengthens the tentacles and beads their tips; a glow lights the rim and the beads.
"""
import math
from ..builder import painter
from ..shapes import ball, box_of, ellipsoid, quat, tube

HABITAT, ORIGIN, LENGTH = "water", "centre", 0.115
SHAPE = {
    "tentacles": 8,
    "dome": 1.0,        # how tall the bell is
    "trail": 1.0,       # how long the tentacles are
    "beat": 1.2,        # seconds per pulse
}
COLOURS = {"body": "#BFD9F2", "belly": "#EAF4FF", "pattern": "#7FA8D9", "trim": "#5E86C4", "tentacle": "#D7E6F7", "accent": "#F2A6C9", "glow": "#A8F0FF"}
PATTERNS = ("plain", "bands", "stripes", "spots", "saddle")


def build(b):
    s = b.shape
    lift = 0.02
    dome = ellipsoid((0, 0, 0), (0.045, 0.035 * s["dome"], 0.045), 16, 7, 0.0, 0.55)
    if b.pattern["type"] == "stripes":
        count, mark = int(b.pattern.get("count", 4)), "glow" if b.pattern.get("lit") and b.has("glow") else "pattern"
        paint = lambda c, n: mark if int(((math.atan2(c[0], c[2]) / (2 * math.pi)) % 1.0) * count * 2) % 2 == 0 else "body"
    else:
        paint = painter(b, *box_of(dome), axes=(1, 2, 0), belly=None)
    rim_y, rim_r = 0.035 * s["dome"] * math.cos(0.55 * math.pi), 0.045 * math.sin(0.55 * math.pi)
    ring = [(rim_r * math.cos(2 * math.pi * k / 16), rim_y, rim_r * math.sin(2 * math.pi * k / 16)) for k in range(17)]
    root = b.node("Body")
    bell = b.node("Bell", b.painted(dome, paint, rough=0.35)
                  + [(b.mat("trim" if b.has("trim") else "body", rough=0.35, glow=True), tube(ring, [0.004] * 17, 6, caps=False)),
                     (b.mat("belly", rough=0.4), ellipsoid((0, rim_y, 0), (0.042, 0.012, 0.042), 16, 4, 0.5, 1.0))], (0, lift, 0), root)
    arms = []
    for k in range(4):
        dx, dz = math.cos(math.pi / 4 + k * math.pi / 2), math.sin(math.pi / 4 + k * math.pi / 2)
        arms.append((b.mat("belly", rough=0.5), tube([(dx * 0.008, 0, dz * 0.008), (dx * 0.015, -0.022, dz * 0.015), (dx * 0.008, -0.046, dz * 0.008)], [0.006, 0.005, 0.002], 6)))
    arm_node = b.node("Arms", arms, (0, lift + rim_y - 0.006, 0), root)
    count = int(s["tentacles"])
    upper, lower = 0.034 * s["trail"], 0.034 * s["trail"] * (1.7 if b.has("ornament") else 1.0)
    strand, bead = b.mat("tentacle", rough=0.5), b.mat("accent" if b.has("ornament") else "tentacle", rough=0.4, glow=True)
    tentacles = []
    for k in range(count):
        a = 2 * math.pi * (k + 0.5) / count
        axis = (-math.sin(a), 0.0, math.cos(a))             # a positive turn about it swings the tentacle outwards
        top = b.node("Tent%d" % (k + 1), [(strand, tube([(0, 0, 0), (0, -upper, 0)], [0.0019, 0.0015], 4, caps=False))], (0.04 * math.cos(a), lift + rim_y, 0.04 * math.sin(a)), root)
        tip = [(strand, tube([(0, 0, 0), (0, -lower, 0)], [0.0015, 0.0007], 4, caps=False))]
        if b.has("ornament"): tip.append((bead, ball((0, -lower, 0), 0.0028, 5, 3)))
        tentacles.append((axis, top, b.node("Tent%db" % (k + 1), tip, (0, -upper, 0), top), k))

    def clip(name, duration, pulse, swing, bob):
        rot, cycle = {}, lambda u: math.sin(2 * math.pi * u)
        for axis, top, tip, k in tentacles:
            rot[top] = (lambda u, axis=axis, k=k: quat(axis, swing * (0.5 + math.sin(2 * math.pi * u - 0.6 - 0.3 * (k % 2)))))
            rot[tip] = (lambda u, axis=axis, k=k: quat(axis, swing * 0.8 * math.sin(2 * math.pi * u - 1.6 - 0.3 * (k % 2))))
        b.clip(name, duration, 16, rot=rot,
               pos={root: lambda u: (0, bob * math.sin(2 * math.pi * u - 1.2), 0)},
               scl={bell: lambda u: (1 + pulse * cycle(u), 1 - 1.2 * pulse * cycle(u), 1 + pulse * cycle(u)),
                    arm_node: lambda u: (1, 1 + pulse * math.sin(2 * math.pi * u - 1.0), 1)})
    clip("move", s["beat"], 0.10, 14, 0.006)
    clip("idle", s["beat"] * 2.5, 0.04, 6, 0.003)
    return {"sockets": {"mouth": "Bell"}}
