"""A four-legged animal that stands on its legs, shaped by its parameters into a dog, a cat, a piglet, a lamb, a
calf, a pony, a goat kid, a fawn, a bear cub, a raccoon, a badger, a wolf, an otter or a capybara. A critter is a
mouse's cousin, low to the ground; this is everything with daylight under its belly.

Its body, its head and each half of each leg are skins (lib/skin.py): rounded shapes that flow into one another,
so a shoulder runs into the chest, the muzzle into the skull and an ear into the head, with no joins showing. The
legs bend at the knee.

"move" walks on diagonal pairs of legs, lifting each foot as it comes forward, with a nod of the head; "idle"
looks about and moves its tail. The origin is on the ground under the middle of the body. An ornament adds a
collar at the neck and a tip to the tail; a glow lights them.
"""
import math
from ..builder import painter, turn, wave
from ..builder import about, both, full_turn, hold, lean, lift, swing
from ..shapes import X, Y, Z, ball, box_of, ellipsoid, moved, qmul, quat, smooth, tube
from .. import skin as clay

HABITAT, ORIGIN, LENGTH = "ground", "ground", 0.30
SHAPE = {
    "plump": 1.0,       # how round the body is
    "long": 1.0,        # how long the body is
    "chest": 1.0,       # how deep the chest is
    "tuck": 0.4,        # how far the belly rises behind the ribs: 0 a barrel (a pig, a calf), 1 a greyhound
    "legs": 1.0,        # how long the legs are
    "stout": 1.0,       # how thick the legs are
    "neck": 1.0,        # how long the neck is
    "carry": 0.4,       # how the head is carried: 0 level with the back (a pig), 1 high (a pony, a fawn)
    "head": 1.0,        # how big the head is
    "snout": 1.0,       # how long the muzzle is
    "nod": 0,           # degrees the head is tipped nose down (a head carried high looks down its nose)
    "muzzle": "taper",  # taper (a dog, a fox, a deer), short (a cat), blunt (a pig's disc) or broad (a calf, a bear)
    "ears": "point",    # point, flop, round, leaf (out to the sides: a deer, a calf, a pony) or none
    "earsize": 1.0,
    "tail": "long",     # long, curl, bushy, stub, whip (thin with a tuft), plume (a pony's), thick (an otter's) or none
    "taillen": 1.0,
    "tailtip": False,   # the end of the tail in the trim colour
    "rings": 0,         # rings of the pattern colour around a bushy tail (a raccoon's)
    "feet": "paw",      # paw or hoof
    "socks": False,     # the lower legs in the sock colour
    "mane": False,      # a mane down the neck and a forelock, in the mane colour
    "wool": False,      # a fleece over the body, in the mane colour
    "horns": "none",    # none, nubs, back (a goat's), curl (a ram's) or antler
    "beard": False,
    "mask": "none",     # none, band (across the eyes: a raccoon) or blaze (down the face: a badger, a pony)
    "beat": 0.8,        # seconds per stride
}
CHOICES = {"muzzle": ("taper", "short", "blunt", "broad"), "ears": ("point", "flop", "round", "leaf", "none"),
           "tail": ("long", "curl", "bushy", "stub", "whip", "plume", "thick", "none"), "feet": ("paw", "hoof"),
           "horns": ("none", "nubs", "back", "curl", "antler"), "mask": ("none", "band", "blaze")}
COLOURS = {"body": "#A9825A", "belly": "#EFE3CE", "muzzle": "#EFE3CE", "pattern": "#5E4630", "trim": "#F6EEDF", "ear": "#D9A99A", "nose": "#2B2222",
           "eye": "#080808", "toe": "#3A2E28", "sock": "#F6EEDF", "mane": "#4A3828", "horn": "#D8CDB8", "accent": "#C9463A", "glow": "#FFE2B0"}
PATTERNS = ("plain", "bands", "stripes", "spots", "saddle", "tips")
TRICKS = ("shake", "roll", "bow", "jump", "spin", "dead", "wave", "dance")


def build(b):
    s, p, st, hs = b.shape, b.shape["plump"], b.shape["stout"], b.shape["head"]
    leg = 0.07 * s["legs"]
    half = 0.040 * p
    cy = leg + half * 0.85
    front, rear = 0.070 * s["long"], -0.080 * s["long"]
    fur, skin_, toe = b.mat("body", rough=0.85), b.mat("ear", rough=0.8), b.mat("toe", rough=0.6)
    fleece, accent = b.mat("mane", rough=0.95), b.mat("accent", rough=0.7, glow=True)

    # The trunk: ribs, belly and rump, with the shoulders and haunches the legs hang from and the neck, all one skin.
    rise = math.radians(16 + 50 * s["carry"])
    reach = 0.036 * s["neck"]
    base = (0.0, cy + 0.012 * p, front - 0.012)
    top = (0.0, base[1] + reach * math.sin(rise), base[2] + reach * math.cos(rise))
    shoulder, haunch = (0.021 * p, cy - 0.006, front - 0.018), (0.022 * p, cy - 0.002, rear + 0.026)
    trunk = [clay.egg((0, cy + 0.002, front * 0.50), (0.035 * p, 0.042 * p * s["chest"], 0.046 * s["long"])),
             clay.egg((0, cy + 0.010 * s["tuck"] * p, -0.012 * s["long"]), (0.034 * p, (0.040 - 0.011 * s["tuck"]) * p, 0.052 * s["long"])),
             clay.egg((0, cy + 0.004, rear * 0.62), (0.035 * p, 0.039 * p, 0.042 * s["long"])),
             clay.limb(base, top, 0.030 * p, 0.0225 * hs)]
    for side in (1, -1):
        trunk.append(clay.ball((side * shoulder[0], shoulder[1], shoulder[2]), 0.021 * st))
        trunk.append(clay.ball((side * haunch[0], haunch[1], haunch[2]), 0.026 * st))
    hull = clay.skin(trunk, cell=0.0112 * math.sqrt(p), blend=0.014)
    paint = painter(b, *box_of(hull), belly=-0.42)
    prims = b.painted(hull, paint, rough=0.85)
    if s["mane"]:
        ridge = [(0.0, top[1] + 0.020 * hs, top[2] - 0.004), (0.0, (base[1] + top[1]) / 2 + 0.030, (base[2] + top[2]) / 2 - 0.014),
                 (0.0, base[1] + 0.028, base[2] - 0.020), (0.0, cy + half + 0.004, front - 0.052)]
        prims.append((fleece, clay.skin(clay.chain(ridge, [0.009, 0.012, 0.011, 0.007]), cell=0.0072, blend=0.006)))
    if s["wool"]:
        tufts = []
        for i in range(5):
            t = 0.06 + 0.88 * i / 4
            z = front * 0.95 + (rear * 0.98 - front * 0.95) * t
            wide = 0.034 * p * (0.86 + 0.14 * math.sin(math.pi * t))
            for k, degrees in enumerate((-62, -21, 21, 62, 118, -118)):
                a = math.radians(90 + degrees + (10 if i % 2 else -10))
                tufts.append(clay.ball((wide * math.cos(a) * 0.9, cy + 0.002 + 0.040 * p * math.sin(a) * 0.86, z + (0.005 if k % 2 else -0.005)), 0.0195 * p))
        prims.append((fleece, clay.skin(tufts, cell=0.0125, blend=0.007)))
    if b.has("ornament"):
        prims.append((accent, ellipsoid((0.0, base[1] + 0.006, base[2] + 0.010), (0.031 * p, 0.032 * p, 0.0055), 14, 5)))
    body = b.node("Body", prims)

    # The head: skull, muzzle and ears as one skin, drawn at its own size and scaled by `head`.
    long, e = 0.028 * s["snout"], s["earsize"]
    lumps = [clay.egg((0, 0, 0.010), (0.027, 0.025, 0.028))]
    if s["muzzle"] == "taper":
        lumps.append(clay.limb((0, -0.004, 0.022), (0, -0.0075, 0.034 + long * 0.85), 0.0165, 0.0088))
        nose_at, nose_r = (0, -0.0035, 0.0405 + long * 0.85), 0.0048
    elif s["muzzle"] == "short":
        lumps += [clay.egg((0, -0.0075, 0.031 + long * 0.1), (0.0145, 0.0105, 0.0115 + long * 0.2)), clay.ball((0.011, -0.006, 0.028), 0.0105), clay.ball((-0.011, -0.006, 0.028), 0.0105)]
        nose_at, nose_r = (0, -0.0035, 0.0415 + long * 0.3), 0.0030
    elif s["muzzle"] == "blunt":
        lumps.append(clay.limb((0, -0.005, 0.020), (0, -0.006, 0.033 + long), 0.0165, 0.0135))
        nose_at, nose_r = None, 0.0
    else:
        lumps.append(clay.limb((0, -0.006, 0.020), (0, -0.0085, 0.033 + long * 0.8), 0.0195, 0.0158))
        nose_at, nose_r = None, 0.0
    for side in (1, -1):
        if s["ears"] == "point":
            lumps.append(clay.limb((side * 0.0145, 0.014, 0.003), (side * 0.0195, 0.018 + 0.031 * e, 0.001), 0.0110, 0.0034))
        elif s["ears"] == "flop":
            lumps.append(clay.egg((side * 0.0265, 0.012 - 0.014 * e, 0.005), (0.0085, 0.019 * e, 0.0115), quat(Z, side * 14)))
        elif s["ears"] == "round":
            lumps.append(clay.egg((side * 0.0195, 0.0225, 0.002), (0.0108 * e, 0.0108 * e, 0.0080)))
        elif s["ears"] == "leaf":
            lumps.append(clay.egg((side * (0.019 + 0.0135 * e), 0.015 + 0.0090 * e, 0.0), (0.0080, 0.019 * e, 0.0075), quat(Z, -side * 56)))
    if s["wool"]: lumps.append(clay.egg((0, 0.022, 0.004), (0.018, 0.011, 0.017)))
    shell = clay.skin(lumps, cell=0.0058, blend=0.0075)

    def face(c, normal):
        beyond = (c[0] / 0.027) ** 2 + (c[1] / 0.025) ** 2 + ((c[2] - 0.010) / 0.028) ** 2
        if s["wool"] and c[1] > 0.016 and abs(c[0]) < 0.019 and c[2] < 0.024: return "mane"
        if s["ears"] in ("point", "round", "leaf") and beyond > 1.3 and c[1] > 0.004 and c[2] < 0.016 and normal[2] > 0.42: return "ear"
        if s["mask"] == "blaze" and abs(c[0]) < 0.0062 and c[1] > -0.006 and c[2] > 0.004 and beyond < 4: return "trim"
        if c[2] > (0.0305 if s["muzzle"] != "short" else 0.0285) and c[1] < 0.0045: return "muzzle"
        if s["mask"] == "band" and c[2] > 0.008 and abs(c[1] - 0.007) < 0.0078 and beyond < 1.25: return "pattern"
        return "muzzle" if c[1] < -0.0125 and c[2] > 0.008 else "body"
    head = b.painted(shell, face, rough=0.85)
    nose = b.mat("nose", rough=0.4)
    if nose_at is not None: head.append((nose, ball(nose_at, nose_r, 8, 5)))
    elif s["muzzle"] == "blunt":
        head.append((skin_, ellipsoid((0, -0.006, 0.0462 + long), (0.0122, 0.0108, 0.0022), 12, 4)))
        head += [(nose, ball((side * 0.0044, -0.0055, 0.0482 + long), 0.0018, 5, 3)) for side in (1, -1)]
    else: head.append((nose, ellipsoid((0, -0.0055, 0.0478 + long * 0.8), (0.0090, 0.0060, 0.0036), 9, 4)))
    wide = 0.0056 if s["muzzle"] == "short" else 0.0046
    head += b.eyes([(side * 0.0172, 0.0085, 0.0305) for side in (1, -1)], wide, glow=True)
    horn = b.mat("horn", rough=0.5)
    for side in (1, -1):
        if s["horns"] == "nubs":
            head.append((horn, tube([(side * 0.010, 0.021, 0.006), (side * 0.0125, 0.035, 0.004)], [0.0044, 0.0012], 6)))
        elif s["horns"] == "back":
            head.append((horn, tube([(side * 0.009, 0.021, 0.006), (side * 0.012, 0.040, -0.004), (side * 0.015, 0.051, -0.021)], [0.0048, 0.0038, 0.0010], 7)))
        elif s["horns"] == "curl":
            ring = [(side * (0.024 + 0.006 * k / 7), 0.010 + 0.014 * math.sin(math.radians(110 + 40 * k)), -0.002 + 0.014 * math.cos(math.radians(110 + 40 * k))) for k in range(8)]
            head.append((horn, tube(ring, [0.0062 - 0.0006 * k for k in range(8)], 7)))
        elif s["horns"] == "antler":
            head.append((horn, tube([(side * 0.010, 0.021, 0.004), (side * 0.020, 0.045, -0.004), (side * 0.027, 0.067, 0.002)], [0.0036, 0.0030, 0.0010], 6)))
            head.append((horn, tube([(side * 0.016, 0.036, -0.001), (side * 0.016, 0.056, 0.015)], [0.0026, 0.0008], 5)))
            head.append((horn, tube([(side * 0.022, 0.053, -0.002), (side * 0.037, 0.064, -0.009)], [0.0024, 0.0008], 5)))
    if s["beard"]: head.append((b.mat("trim", rough=0.9), tube([(0, -0.019, 0.030), (0, -0.038, 0.025)], [0.0046, 0.0010], 6)))
    if s["mane"]: head.append((fleece, clay.skin([clay.egg((0, 0.0245, 0.013), (0.0095, 0.0075, 0.016))], cell=0.0058, blend=0.0)))
    tilt = quat(X, s["nod"]) if s["nod"] else None
    head = [(material, moved(part, turn=tilt, scale=(hs, hs, hs))) for material, part in head]
    head_node = b.node("Head", head, (0.0, top[1] + 0.004 * hs, top[2] + 0.004 * hs), body)

    tail_node, far = None, s["taillen"]
    tip = "trim" if s["tailtip"] else None
    if s["tail"] != "none":
        if s["tail"] == "long":
            line = [(0, 0, 0), (0, 0.006, -0.030 * far), (0, 0.024 * far, -0.056 * far), (0, 0.050 * far, -0.066 * far)]
            parts = b.painted(tube(line, [0.0088, 0.0078, 0.0064, 0.0040], 9), lambda c, n: tip if tip and c[1] > 0.032 * far else "body", rough=0.85)
        elif s["tail"] == "curl":
            line = [(0.004 * math.sin(2 * a), 0.012 - 0.011 * math.cos(a), -0.004 - 0.011 * math.sin(a)) for a in (1.6 * math.pi * k / 8 for k in range(9))]
            parts = [(fur, tube(line, [0.0044 - 0.00025 * k for k in range(9)], 6))]
        elif s["tail"] == "bushy":
            line = [(0, 0, 0), (0, 0.010 * far, -0.030 * far), (0, 0.026 * far, -0.064 * far), (0, 0.036 * far, -0.092 * far)]
            def brush(c, n):
                t = -c[2] / (0.092 * far)
                if tip and t > 0.8: return tip
                return "pattern" if s["rings"] and int(t * s["rings"] * 2) % 2 == 1 else "body"
            parts = b.painted(clay.skin(clay.chain(line, [0.010, 0.020, 0.022, 0.008]), cell=0.0078, blend=0.006), brush, rough=0.9)
        elif s["tail"] == "stub":
            parts = [(b.mat(tip or "body", rough=0.9), ball((0, 0.004, -0.008), 0.013 * far, 10, 6))]
        elif s["tail"] == "whip":
            parts = [(fur, tube([(0, 0, 0), (0, -0.020, -0.016), (0, -0.056 * far, -0.020)], [0.0052, 0.0038, 0.0028], 6)),
                     (fleece, ellipsoid((0, -0.064 * far, -0.021), (0.0062, 0.0128, 0.0062), 8, 5))]
        elif s["tail"] == "plume":
            line = [(0, 0, 0), (0, -0.006, -0.022), (0, -0.045 * far, -0.038), (0, -0.086 * far, -0.036)]
            parts = [(fleece, clay.skin(clay.chain(line, [0.0080, 0.0125, 0.0125, 0.0065]), cell=0.0075, blend=0.006))]
        else:
            line = [(0, 0, 0), (0, -0.008, -0.040 * far), (0, -0.014, -0.085 * far), (0, -0.012, -0.120 * far)]
            parts = b.painted(clay.skin(clay.chain(line, [0.022 * p, 0.016, 0.011, 0.006]), cell=0.0078, blend=0.006), lambda c, n: tip if tip and c[2] < -0.095 * far else "body", rough=0.85)
        if b.has("ornament") and s["tail"] in ("long", "bushy", "thick"):
            end = {"long": (0, 0.050 * far, -0.066 * far), "bushy": (0, 0.036 * far, -0.092 * far), "thick": (0, -0.012, -0.120 * far)}[s["tail"]]
            parts.append((accent, ball(end, 0.0066, 8, 5)))
        tail_node = b.node("Tail", parts, (0.0, cy + 0.014 * p, rear * 0.62 - 0.036 * s["long"]), body)

    # The legs: a thigh from the shoulder or the haunch to the knee, and below it the shin and the foot.
    thighs, shins = {}, {}
    for name, side, hind in (("FL", 1, False), ("FR", -1, False), ("BL", 1, True), ("BR", -1, True)):
        joint = haunch if hind else shoulder
        hip = (side * joint[0], joint[1], joint[2])
        drop = hip[1] * 0.5                                    # the knee is halfway down
        knee = (0.0, -drop, 0.010 if hind else 0.003)
        upper = clay.skin([clay.limb((0, 0, 0), knee, (0.019 if hind else 0.016) * st, 0.0115 * st)], cell=0.0076 * st, blend=0.0)
        thighs[name] = b.node("Leg" + name, [(fur, upper)], hip, body)
        ground = -(hip[1] - drop)                              # the ground, seen from the knee
        if hind: bones = [clay.limb((0, 0, 0), (0, ground * 0.45, -0.013), 0.0115 * st, 0.0090 * st), clay.limb((0, ground * 0.45, -0.013), (0, ground + 0.009, -0.007), 0.0090 * st, 0.0085 * st)]
        else: bones = [clay.limb((0, 0, 0), (0, ground + 0.009, 0.0), 0.0115 * st, 0.0088 * st)]
        back = -0.007 if hind else 0.0
        if s["feet"] == "hoof": bones.append(clay.limb((0, ground + 0.013, back), (0, ground + 0.0105, back + 0.003), 0.0092 * st, 0.0105 * st))
        else: bones.append(clay.egg((0, ground + 0.0068, back + 0.007), (0.0115 * st, 0.0068, 0.0155 * st)))
        lower = clay.skin(bones, cell=0.0068 * st, blend=0.005)
        foot = (lambda c, n, ground=ground: "toe" if c[1] < ground + 0.016 else "sock" if s["socks"] else "body") if s["feet"] == "hoof" else \
               (lambda c, n, ground=ground: "toe" if c[1] < ground + 0.0135 else "sock" if s["socks"] else "body")
        shins[name] = b.node("Shin" + name, b.painted(lower, foot, rough=0.85), knee, thighs[name])

    # Walking: diagonal pairs swing from the shoulder and the haunch, and each knee folds as its foot comes forward.
    wag = Z if s["tail"] in ("whip", "plume") else Y
    stride, fold = 22, 34
    rot = {head_node: turn(X, wave(2, 3))}
    for name, sign in (("FL", 1), ("BR", 1), ("FR", -1), ("BL", -1)):
        rot[thighs[name]] = turn(X, wave(1, sign * stride))
        rot[shins[name]] = (lambda u, sign=sign: quat(X, fold * max(0.0, -sign * math.cos(2 * math.pi * u))))
    if tail_node is not None: rot[tail_node] = turn(wag, wave(2, 14))
    b.clip("move", s["beat"], 16, rot=rot, pos={body: lambda u: (0, 0.003 * math.sin(4 * math.pi * u), 0)})
    rot = {head_node: lambda u: qmul(quat(Y, 14 * math.sin(2 * math.pi * u)), quat(X, 4 * math.sin(4 * math.pi * u)))}     # looks about
    if tail_node is not None: rot[tail_node] = turn(wag, wave(3, 16, 0.7))
    b.clip("idle", 3.0, 24, rot=rot)

    # Tricks: a shake, a roll, a play bow, a jump, a turn, lying on its side, a paw held up and a dance.
    middle, hips = (0.0, cy, 0.0), (0.0, haunch[1], haunch[2])
    settle = lambda u: smooth(u / 0.2) * smooth((1 - u) / 0.2)
    b.trick("shake", 0.9, rot={body: swing(Z, 14, 5), head_node: swing(Z, 18, 5, math.pi / 2)}, pos={body: about(middle, swing(Z, 14, 5))})
    b.trick("roll", 1.3, rot={body: full_turn(Z)}, pos={body: about(middle, full_turn(Z))})
    b.trick("bow", 1.4, rot={body: lean(X, 17), thighs["FL"]: lean(X, -58), thighs["FR"]: lean(X, -58), head_node: lean(X, -14)}, pos={body: about(hips, lean(X, 17))})
    b.trick("jump", 0.9, rot={body: swing(X, -10, 1), thighs["FL"]: lean(X, -30), thighs["FR"]: lean(X, -30), thighs["BL"]: lean(X, 30), thighs["BR"]: lean(X, 30),
                              shins["FL"]: lean(X, 40), shins["FR"]: lean(X, 40)}, pos={body: lift(0.09)})
    b.trick("spin", 1.2, rot={body: full_turn(Y)}, pos={body: lift(0.012, 3)})
    b.trick("dead", 2.8, rot={body: hold(Z, 90)}, pos={body: about(middle, hold(Z, 90), also=lambda u: (0.0, -(cy - 0.036 * p) * settle(u), 0.0))}, keys=20)
    b.trick("wave", 1.5, rot={thighs["FL"]: both(hold(X, -72, 0.25), swing(Z, 12, 3)), shins["FL"]: hold(X, 30, 0.25), head_node: lean(Z, 10)})
    b.trick("dance", 1.5, rot={body: swing(Y, 18, 2), head_node: swing(Z, 14, 3)}, pos={body: lift(0.02, 4)})
    return {"sockets": {"mouth": "Head", "back": "Body"}}
