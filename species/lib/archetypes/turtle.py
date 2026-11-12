"""A turtle: a domed shell of scutes over a pale plastron, a head on a neck, two long front flippers and two
short rear ones.

"move" beats the front flippers like wings while the rear ones steer, "idle" paddles slowly with the head looking
about. The origin is at the middle of the shell. An ornament raises a keel of spikes down the shell.
"""
import math
from ..builder import painter, turn, wave
from ..shapes import X, Y, Z, ellipsoid, mirrored, moved, qmul, quat, tube

HABITAT, ORIGIN, LENGTH = "water", "centre", 0.135
SHAPE = {
    "dome": 1.0,        # how tall the shell is
    "flippers": 1.0,    # how long the front flippers are
    "beat": 1.6,        # seconds per stroke
}
COLOURS = {"body": "#5E8C4A", "belly": "#E9DFA8", "pattern": "#35602E", "trim": "#C9D98A", "skin": "#8FAE6A", "eye": "#080808", "accent": "#E0C060", "glow": "#B6FF9E"}
PATTERNS = ("plain", "spots", "bands", "stripes", "saddle")


def build(b):
    s = b.shape
    shell = ellipsoid((0, 0.004, 0), (0.040, 0.022 * s["dome"], 0.050), 16, 6, 0.0, 0.5)
    prims = b.painted(shell, painter(b, (-0.04, 0.004 - 0.022 * s["dome"], -0.05), (0.04, 0.004 + 0.022 * s["dome"], 0.05), belly=None), rough=0.45)
    prims.append((b.mat("trim" if b.has("trim") else "pattern", rough=0.5), ellipsoid((0, 0.004, 0), (0.0435, 0.0045, 0.0535), 16, 4)))
    prims.append((b.mat("belly"), ellipsoid((0, 0.004, 0), (0.038, 0.010, 0.047), 14, 4, 0.5, 1.0)))
    skin = b.mat("skin")
    prims.append((skin, tube([(0, 0.002, -0.046), (0, 0.0, -0.064)], [0.004, 0.001], 6)))
    if b.has("ornament"):
        for z in (0.026, 0.008, -0.010, -0.028):
            y = 0.004 + 0.022 * s["dome"] * math.sqrt(max(0.0, 1 - (z / 0.05) ** 2))
            prims.append((b.mat("accent", glow=True), tube([(0, y - 0.003, z + 0.004), (0, y + 0.009, z - 0.004)], [0.005, 0.0006], 6, caps=False)))
    body = b.node("Body", prims)
    head = [(skin, tube([(0, 0, -0.01), (0, 0.002, 0.01)], [0.008, 0.007], 8)), (skin, ellipsoid((0, 0.004, 0.018), (0.009, 0.008, 0.012), 10, 6))]
    head += b.eyes([(side * 0.0068, 0.0075, 0.022) for side in (1, -1)], 0.0025)
    head_node = b.node("Head", head, (0, 0.002, 0.048), body)
    flippers = {}
    long = 0.032 * s["flippers"]
    for name, side in (("L", 1), ("R", -1)):
        front = moved(ellipsoid((long, 0, 0), (long, 0.003, 0.011), 10, 5), turn=quat(Y, 25))
        rear = moved(ellipsoid((0.015, 0, 0), (0.016, 0.0025, 0.008), 8, 4), turn=quat(Y, 55))
        if side < 0: front, rear = mirrored(front), mirrored(rear)
        flippers["F" + name] = b.node("FlipF" + name, [(skin, front)], (side * 0.03, 0.001, 0.03), body)
        flippers["B" + name] = b.node("FlipB" + name, [(skin, rear)], (side * 0.026, 0.001, -0.038), body)

    def stroke(side, flap, sweep):
        return lambda u: qmul(quat(Z, side * flap * math.sin(2 * math.pi * u)), quat(Y, side * sweep * math.sin(2 * math.pi * u - 1.57)))

    def clip(name, duration, flap, sweep, steer, look, bob):
        b.clip(name, duration, 16, rot={
            flippers["FL"]: stroke(1, flap, sweep), flippers["FR"]: stroke(-1, flap, sweep),
            flippers["BL"]: turn(Y, wave(1, steer, 0.5)), flippers["BR"]: turn(Y, wave(1, -steer, 0.5)),
            head_node: (turn(Y, wave(1, look)) if look else turn(X, wave(1, 4))),
        }, pos={body: lambda u: (0, bob * math.sin(2 * math.pi * u), 0)})
    clip("move", s["beat"], 30, 12, 14, 0, 0.003)
    clip("idle", s["beat"] * 2.5, 10, 5, 6, 14, 0.0015)
    return {"sockets": {"mouth": "Head"}}
