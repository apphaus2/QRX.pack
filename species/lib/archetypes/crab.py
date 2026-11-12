"""A crab: a wide shell, eyes on stalks, two claws with fingers that snap and four legs a side. It walks sideways
(`sideways`), as crabs do. With a `sting` it is a scorpion: a narrow shell, claws ahead and a jointed tail curled
over its back.

"move" ripples the legs with the claws held up, "idle" snaps the claws. The origin is on the ground under the
middle of the shell. An ornament sets spikes along the front of the shell; a glow lights them and the sting.
"""
import math
from ..builder import painter, turn, wave
from ..builder import both, full_turn, lean, lift, swing
from ..shapes import X, Y, Z, ball, box_of, cross, ellipsoid, moved, norm, qmul, quat, tube

HABITAT, ORIGIN, LENGTH = "ground", "ground", 0.128
SHAPE = {
    "width": 1.0,       # how wide the shell is
    "claws": 1.0,       # how big both claws are
    "bigclaw": 1.0,     # how much bigger the left claw is than the right
    "sideways": True,   # walks sideways
    "sting": 0,         # joints in a scorpion's tail (0 for a crab)
    "beat": 0.5,        # seconds per stride
}
COLOURS = {"body": "#D9643A", "belly": "#F0D9B5", "pattern": "#8C2F1B", "trim": "#F2B880", "claw": "#E8825A", "eye": "#080808", "accent": "#F2C14E", "glow": "#FFD9A0"}
PATTERNS = ("plain", "bands", "stripes", "spots", "saddle", "tips")
TRICKS = ("wave", "spin", "dance", "snap", "jump")


def build(b):
    s, w = b.shape, b.shape["width"]
    root = b.node("Turn", turn=quat(Y, 90)) if s["sideways"] else None
    rx = 0.034 * w
    shell = ellipsoid((0, 0.022, 0), (rx, 0.012, 0.024), 14, 8)
    prims = b.painted(shell, painter(b, *box_of(shell), belly=-0.3))
    accent = b.mat("accent", rough=0.5, glow=True)
    if b.has("ornament"):
        for k in range(-2, 3):
            x = k * rx * 0.36
            z = 0.024 * math.sqrt(max(0.0, 1 - (x / rx) ** 2))
            prims.append((accent, tube([(x, 0.025, z - 0.004), (x * 1.15, 0.031, z + 0.007)], [0.003, 0.0004], 5, caps=False)))
    body = b.node("Body", prims, parent=root)
    limb, hand = b.mat("body"), b.mat("claw")
    eyes = []
    for name, side in (("EyeL", 1), ("EyeR", -1)):
        eyes.append((side, b.node(name, [(limb, tube([(0, 0, 0), (0, 0.010, 0.002)], [0.0018, 0.0016], 5, caps=False))] + b.eyes([(0, 0.012, 0.002)], 0.0032), (side * min(0.012, rx * 0.4), 0.030, 0.019), body)))
    claws = []
    for name, side, k in (("L", 1, s["claws"] * s["bigclaw"]), ("R", -1, s["claws"])):
        wrist = (side * 0.006, 0.0, 0.026)
        arm = tube([(0, 0, 0), (side * 0.012, 0.002, 0.014), wrist], [0.005, 0.0045, 0.004], 6, caps=False)
        palm = moved(ellipsoid((0, 0, 0.009), (0.007, 0.0055, 0.010), 8, 5), at=wrist, scale=k)
        thumb = moved(tube([(0, -0.003, 0.015), (0, -0.003, 0.028)], [0.003, 0.0006], 5), at=wrist, scale=k)
        claw = b.node("Claw" + name, [(limb, arm), (hand, palm), (hand, thumb)], (side * rx * 0.76, 0.020, 0.016), body)
        finger = tube([(0, 0, 0), (0, 0.002, 0.008 * k), (0, 0.0, 0.015 * k)], [0.003 * k, 0.0022 * k, 0.0006], 5)
        claws.append((claw, b.node("Pinch" + name, [(hand, finger)], (wrist[0], wrist[1] + 0.002 * k, wrist[2] + 0.014 * k), claw)))
    legs = []
    for i, (z, reach) in enumerate(((0.012, 0.012), (0.004, 0.004), (-0.005, -0.006), (-0.014, -0.016))):
        for name, side in (("L", 1), ("R", -1)):
            foot = (side * 0.036, -0.018, reach)
            part = tube([(0, 0, 0), (side * 0.020, 0.014, reach * 0.5), foot], [0.0035, 0.003, 0.0008], 5, caps=False)
            legs.append((b.node("Leg%s%d" % (name, i + 1), [(limb, part)], (side * rx * 0.82, 0.018, z), body), side, norm(cross(norm((foot[0], 0.0, foot[2])), Y)), i))
    sting = []
    if s["sting"]:
        parent, at, count = body, (0, 0.024, -0.022), int(s["sting"])
        for k in range(count):
            angle = math.radians(15 + 150 * k / max(1, count - 1))
            step = (0.0, 0.013 * math.sin(angle), -0.013 * math.cos(angle))
            prims = [(limb, tube([(0, 0, 0), step], [0.0045 - 0.0004 * k, 0.0042 - 0.0004 * k], 6)), (limb, ball((0, 0, 0), 0.0048 - 0.0004 * k, 6, 4))]
            if k == count - 1:
                prims.append((accent, ball(step, 0.0045, 7, 5)))
                prims.append((accent, tube([step, (0.0, step[1] - 0.004, step[2] + 0.011)], [0.003, 0.0003], 5, caps=False)))
            parent = b.node("Sting%d" % (k + 1), prims, at, parent)
            sting.append(parent)
            at = step

    def ripple(side, axis, i, lift, swing):
        return lambda u: qmul(quat(axis, lift * max(0.0, math.sin(2 * math.pi * u + math.pi * i))), quat(Y, side * swing * math.cos(2 * math.pi * u + math.pi * i)))
    rot = {node: ripple(side, axis, i, 16, 10) for node, side, axis, i in legs}
    rot[body] = turn(Z, wave(1, 2))
    for claw, pinch in claws: rot[claw] = turn(X, wave(1, 5, 0, -6))
    for k, joint in enumerate(sting): rot[joint] = turn(X, wave(1, 3, 0.5 * k))
    b.clip("move", s["beat"], 12, rot=rot, pos={body: lambda u: (0, 0.0015 * math.sin(4 * math.pi * u), 0)})
    rot = {}
    for n, (claw, pinch) in enumerate(claws):
        rot[claw] = turn(X, wave(1, 6, n * 2.0, -4))
        rot[pinch] = lambda u, n=n: quat(X, -13 - 13 * math.sin(4 * math.pi * u + n * 2.0))
    for side, node in eyes: rot[node] = turn(Z, wave(1, 9, side))
    for k, joint in enumerate(sting): rot[joint] = turn(X, wave(1, 5, 0.6 * k))
    b.clip("idle", 3.0, 24, rot=rot)
    # Tricks: a wave of the left claw, snapping both, a turn, a side-to-side dance and a hop.
    b.trick("wave", 1.4, rot={claws[0][0]: both(lean(X, -55), swing(Z, 22, 3))})
    b.trick("snap", 1.2, rot={pinch: (lambda u: quat(X, -28 * abs(math.sin(4 * math.pi * u)) * math.sin(math.pi * u))) for _, pinch in claws})
    b.trick("spin", 1.1, rot={body: full_turn(Y)})
    b.trick("dance", 1.5, rot={body: swing(Y, 20, 3)}, pos={body: lift(0.008, 3)})
    b.trick("jump", 0.7, pos={body: lift(0.03)})
    return {"sockets": {"mouth": "Body", "back": "Body"}}
