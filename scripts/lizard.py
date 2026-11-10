"""The terrarium's lizard: a small spotted lizard as a glTF binary, written by hand (standard library only,
built with the helpers in habitats.py).

A flattened tube for the body and head, a tail in three jointed pieces, four bent legs with flat feet, a row
of darker spots down the back and two black eyes. The body, the tail pieces and the legs are their own nodes,
so the clips can move them: "walk" swings the legs in diagonal pairs while the body and the tail snake from
side to side, "idle" breathes with a slow curl of the tail. Metres, +Y up, the head along +Z (heading 0 faces
+Z in JsonScene), the origin on the ground under the middle of the body. About 27 cm from nose to tail.

    python3 scripts/lizard.py <out>    ->   <out>/models/lizard.glb
"""
import math, sys
from habitats import Model, Primitive, ellipsoid, tube, quat, X, Y

out = sys.argv[1]
m = Model("Lizard", "QRX.pack scripts/lizard.py")
skin = m.material("skin", (0.5, 0.76, 0.24), roughness=0.6)
spot = m.material("spot", (0.16, 0.42, 0.2), roughness=0.6)
toe = m.material("toe", (0.66, 0.82, 0.36), roughness=0.6)
eye = m.material("eye", (0.03, 0.03, 0.03), roughness=0.2)

HEIGHT = 0.024     # the body's axis above the ground
body_parts = [Primitive(skin).add(tube(
    [(0, 0, -0.05), (0, 0.001, -0.03), (0, 0.002, 0.0), (0, 0.002, 0.03), (0, 0.003, 0.05), (0, 0.005, 0.066), (0, 0.004, 0.086), (0, 0.002, 0.102)],
    [0.011, 0.017, 0.02, 0.018, 0.012, 0.016, 0.012, 0.004], 10, squash=0.72))]
spots = Primitive(spot)
for z, r in ((-0.035, 0.006), (-0.012, 0.008), (0.012, 0.008), (0.034, 0.006), (0.068, 0.005)):
    spots.add(ellipsoid(0, 0.014 + (0.003 if z > 0.05 else 0), z, r, 0.003, r * 1.2, 8, 4))
eyes = Primitive(eye)
for s in (-1, 1): eyes.add(ellipsoid(s * 0.0125, 0.011, 0.078, 0.004, 0.004, 0.0045, 8, 5))
body = m.node("Body", body_parts + [spots, eyes], (0, HEIGHT, 0))

# The tail: three pieces, each hanging off the end of the one before.
tail, parent = [], body
for i, (r0, r1, length) in enumerate(((0.011, 0.008, 0.045), (0.008, 0.005, 0.045), (0.005, 0.0008, 0.05))):
    piece = Primitive(skin).add(tube([(0, 0, 0), (0, -0.002, -length)], [r0, r1], 8, squash=0.8, caps=False))
    parent = m.node(f"Tail{i + 1}", [piece], (0, 0.0 if i == 0 else -0.002, -0.05 if i == 0 else -0.045), parent)
    tail.append(parent)

# The legs: hip, knee, foot. +x is the lizard's left.
legs = {}
for name, s, z, reach in (("LegFL", 1, 0.04, 0.012), ("LegFR", -1, 0.04, 0.012), ("LegBL", 1, -0.034, -0.008), ("LegBR", -1, -0.034, -0.008)):
    hip_y = -0.004
    foot = (s * 0.036, -(HEIGHT + hip_y) + 0.003, reach)
    limb = Primitive(skin).add(tube([(0, 0, 0), (s * 0.022, 0.006, reach * 0.4), foot], [0.0055, 0.0045, 0.003], 6, caps=False))
    pad = Primitive(toe).add(ellipsoid(foot[0] + s * 0.003, foot[1], foot[2] + 0.004, 0.008, 0.003, 0.011, 8, 4))
    legs[name] = m.node(name, [limb, pad], (s * 0.014, hip_y, z), body)


def keys(duration, count, fn):
    times = [duration * i / count for i in range(count + 1)]
    return times, [fn(2 * math.pi * t / duration) for t in times]


def clip(name, duration, count, spec):
    times, rotations = None, {}
    for node, fn in spec.items():
        times, rotations[node] = keys(duration, count, fn)
    m.clip(name, times, rotations)


SWING = 30
clip("walk", 0.6, 12, {
    body: lambda p: quat(Y, 6 * math.sin(p)),
    tail[0]: lambda p: quat(Y, -12 * math.sin(p - 0.7)),
    tail[1]: lambda p: quat(Y, -16 * math.sin(p - 1.4)),
    tail[2]: lambda p: quat(Y, -18 * math.sin(p - 2.1)),
    # A leg on +x swings forward with a negative turn about y, one on -x with a positive one; diagonal pairs together.
    legs["LegFL"]: lambda p: quat(Y, -SWING * math.sin(p)),
    legs["LegBR"]: lambda p: quat(Y, SWING * math.sin(p)),
    legs["LegFR"]: lambda p: quat(Y, -SWING * math.sin(p)),
    legs["LegBL"]: lambda p: quat(Y, SWING * math.sin(p)),
})
clip("idle", 4.0, 24, {
    body: lambda p: quat(X, -1.5 + 1.5 * math.sin(p)),
    tail[0]: lambda p: quat(Y, 5 * math.sin(p)),
    tail[1]: lambda p: quat(Y, 8 * math.sin(p - 0.8)),
    tail[2]: lambda p: quat(Y, 10 * math.sin(p - 1.6)),
})
m.write(f"{out}/models/lizard.glb")
