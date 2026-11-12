"""A snail: a soft foot with its head raised, two eyes on stalks and a coiled shell on its back.

"move" stretches and gathers the foot while the shell rocks, "idle" draws the eye stalks in and out. The origin is
on the ground under the middle of the foot. An ornament sets spikes round the shell's outer whorl; a glow lights
them and a lit band.
"""
import math
from ..builder import turn, wave
from ..shapes import X, Z, norm, tube

HABITAT, ORIGIN, LENGTH = "ground", "ground", 0.088
SHAPE = {
    "shell": 1.0,       # how big the shell is
    "turns": 2.4,       # how many times it coils
    "lean": 0.5,        # how far the coil's point sticks out to the side
    "beat": 2.0,        # seconds per stretch
}
COLOURS = {"body": "#C8A46A", "skin": "#B9B08E", "pattern": "#7A5630", "trim": "#F0DFB8", "eye": "#080808", "accent": "#E8C860", "glow": "#FFE9A0"}
PATTERNS = ("plain", "bands", "stripes")


def build(b):
    s = b.shape
    skin = b.mat("skin", rough=0.45)
    foot = tube([(0, 0.004, -0.04), (0, 0.006, -0.025), (0, 0.007, 0.0), (0, 0.008, 0.02), (0, 0.014, 0.032), (0, 0.022, 0.038)], [0.002, 0.008, 0.011, 0.010, 0.008, 0.007], 10, squash=0.6)
    prims = [(skin, foot)]
    for side in (1, -1):
        prims.append((skin, tube([(side * 0.004, 0.017, 0.042), (side * 0.007, 0.013, 0.050)], [0.0014, 0.001], 5)))
    body = b.node("Body", prims)

    # The shell: a tube wound in a shrinking spiral in the plane of the body, its point leaning out to one side.
    outer = 0.016 * s["shell"]
    centre = (0.0, 0.018 + outer * 0.45, 0.002)
    steps = int(14 * s["turns"])
    path, radii = [], []
    for k in range(steps + 1):
        a = 2 * math.pi * s["turns"] * k / steps
        r = outer * math.exp(-0.22 * a)
        psi = math.radians(-60) + a
        path.append((s["lean"] * (outer - r), centre[1] + r * math.sin(psi), centre[2] + r * math.cos(psi)))
        radii.append(0.45 * r + 0.0006)
    kind, mark = b.pattern["type"], "glow" if b.pattern.get("lit") and b.has("glow") else "pattern"

    def paint(c, n):
        out = norm((0.0, c[1] - centre[1], c[2] - centre[2]))
        if kind == "bands" and n[1] * out[1] + n[2] * out[2] > 0.75: return mark
        if kind == "bands" and b.has("trim") and n[1] * out[1] + n[2] * out[2] > 0.5: return "trim"
        if kind == "stripes" and int((math.atan2(out[1], out[2]) / (2 * math.pi) % 1.0) * 2 * int(b.pattern.get("count", 7))) % 2 == 0: return mark
        return "body"
    prims = b.painted(tube(path, radii, 9), paint, rough=0.4)
    if b.has("ornament"):
        accent = b.mat("accent", rough=0.4, glow=True)
        for k in range(1, 8):
            psi = math.radians(-60) + 2 * math.pi * k / 9
            r = outer * math.exp(-0.22 * 2 * math.pi * k / 9)
            root = (s["lean"] * (outer - r), centre[1] + 1.35 * r * math.sin(psi), centre[2] + 1.35 * r * math.cos(psi))
            tip = (root[0], centre[1] + (1.45 * r + 0.011) * math.sin(psi), centre[2] + (1.45 * r + 0.011) * math.cos(psi))
            prims.append((accent, tube([root, tip], [0.0032, 0.0004], 5, caps=False)))
    shell = b.node("Shell", prims, (0, 0.012, -0.006))
    stalks = []
    for name, side in (("StalkL", 1), ("StalkR", -1)):
        part = tube([(0, 0, 0), (side * 0.004, 0.012, 0.004), (side * 0.006, 0.022, 0.006)], [0.0018, 0.0014, 0.0012], 5, caps=False)
        stalks.append((side, b.node(name, [(skin, part)] + b.eyes([(side * 0.006, 0.023, 0.006)], 0.0027), (side * 0.004, 0.026, 0.036))))

    rot = {shell: turn(X, wave(1, 3, 0.8))}
    for side, node in stalks: rot[node] = turn(X, wave(1, 8, side))
    b.clip("move", s["beat"], 16, rot=rot, scl={body: lambda u: (1, 1, 1 + 0.05 * math.sin(2 * math.pi * u))})
    rot = {shell: turn(X, wave(1, 1))}
    for side, node in stalks: rot[node] = turn(Z, wave(1, 8 * side, 0.5 * side))
    b.clip("idle", 4.0, 24, rot=rot, scl={node: (lambda u, side=side: (1, 0.82 + 0.18 * math.cos(2 * math.pi * u + side), 1)) for side, node in stalks})
    return {"sockets": {"mouth": "Body", "back": "Shell"}}
