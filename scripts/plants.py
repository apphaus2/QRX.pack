"""The wild food's plants: seven small low-poly plants as glTF binaries, written by hand (standard library only,
built with the helpers in habitats.py).

One model per food kind of the apps' wild food (QRX's `FoodKind`), each in that kind's colour, at its real size
so a scene draws it at scale 1: seed grass (a tuft of blades with wheat-like seed heads), mushrooms (three capped
ones on a patch of soil), a nectar flower (pink petals on a stem with two leaves), pond weed (lily pads, a bud
and fronds on a little pool), acorns (five, capped, on an oak leaf), lichen (a flat rock crusted with patches)
and a berry bush (a small bush hung with red berries; `bush.glb`, the singing bush, stays as it is). Every model
has one clip, "sway": a slow lean for the soft ones, a near-still one for the acorns and the rock. Metres, +Y
up, the origin on the ground under the plant's middle, nothing below the ground.

    python3 scripts/plants.py <out>            ->   <out>/models/plant-<kind>.glb, seven files
    python3 scripts/plants.py <out> --check    reads the seven back and checks them
"""
import json, math, random, struct, sys
from habitats import Model, Primitive, ellipsoid, blade, tube, quat, norm, cross, sub, X, Y, Z

KINDS = ["berry-bush", "seed-grass", "mushrooms", "nectar-flower", "pond-weed", "acorns", "lichen"]
# FoodKind's colours (QRX: FoodKind.all), the main accent of each model.
COLOR = {
    "berry-bush": (0.80, 0.08, 0.22), "seed-grass": (0.83, 0.71, 0.35), "mushrooms": (0.72, 0.52, 0.36),
    "nectar-flower": (0.93, 0.55, 0.75), "pond-weed": (0.25, 0.55, 0.32), "acorns": (0.55, 0.38, 0.20),
    "lichen": (0.66, 0.74, 0.62),
}


# ---- small helpers ----------------------------------------------------------------------------------------

def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz)


def rotate(q, v):
    x, y, z, w = q
    t = (2 * (y * v[2] - z * v[1]), 2 * (z * v[0] - x * v[2]), 2 * (x * v[1] - y * v[0]))
    return (v[0] + w * t[0] + y * t[2] - z * t[1], v[1] + w * t[1] + z * t[0] - x * t[2], v[2] + w * t[2] + x * t[1] - y * t[0])


def placed(part, q=(0.0, 0.0, 0.0, 1.0), at=(0.0, 0.0, 0.0)):
    """A part turned by `q` about the origin, then moved to `at`."""
    positions, normals, triangles = part
    return ([tuple(p + a for p, a in zip(rotate(q, v), at)) for v in positions], [rotate(q, n) for n in normals], triangles)


def dome(cx, cy, cz, rx, ry, rz, segments=10, rings=4, reach=0.5, under=True):
    """The top of an ellipsoid down to `reach` of the way (0.5 = a half), closed underneath by a flat disc
    facing down when `under`. Returns (top, underside)."""
    positions, normals, triangles = [], [], []
    for i in range(rings + 1):
        phi = math.pi * reach * i / rings
        for j in range(segments + 1):
            theta = 2 * math.pi * j / segments
            nx, ny, nz = math.sin(phi) * math.cos(theta), math.cos(phi), math.sin(phi) * math.sin(theta)
            positions.append((cx + rx * nx, cy + ry * ny, cz + rz * nz))
            normals.append(norm((nx / rx, ny / ry, nz / rz)))
    for i in range(rings):
        for j in range(segments):
            a = i * (segments + 1) + j
            b = a + segments + 1
            if i > 0: triangles.append((a, b, a + 1))
            triangles.append((a + 1, b, b + 1))
    if not under: return (positions, normals, triangles), None
    edge = positions[rings * (segments + 1):]
    rim_y = edge[0][1]
    disc_p = [(cx, rim_y, cz)] + [(p[0], rim_y, p[2]) for p in edge]
    disc_t = [(0, j + 1, j + 2) for j in range(segments)]
    return (positions, normals, triangles), (disc_p, [(0.0, -1.0, 0.0)] * len(disc_p), disc_t)


def flat(outline, y, centre=None):
    """A flat fan facing up through the points of `outline` (x, z), around `centre`; draw it double-sided."""
    cx, cz = centre if centre else (sum(p[0] for p in outline) / len(outline), sum(p[1] for p in outline) / len(outline))
    positions = [(cx, y, cz)] + [(x, y, z) for x, z in outline]
    triangles = [(0, k + 2, k + 1) for k in range(len(outline) - 1)]
    return positions, [Y] * len(positions), triangles


def outward(primitive):
    """Turns every triangle so that its corners run counter-clockwise seen from the side its normals point to,
    glTF's front face (the shape helpers do not all wind that way, and a renderer that culls back faces would
    show their insides)."""
    p, n = primitive.positions, primitive.normals
    fixed = []
    for a, b, c in primitive.triangles:
        face = cross(sub(p[b], p[a]), sub(p[c], p[a]))
        along = sum(face[k] * (n[a][k] + n[b][k] + n[c][k]) for k in range(3))
        fixed.append((a, b, c) if along >= 0 else (a, c, b))
    primitive.triangles = fixed
    return primitive


class Plant(Model):
    """habitats.Model, with every primitive's triangles turned to face out before it is written."""

    def node(self, name, primitives, at=(0.0, 0.0, 0.0), parent=None):
        return super().node(name, [outward(p) for p in primitives], at, parent)


def faceted(part):
    """The same triangles, each with its own corners and its face's normal: a low-poly look for a rock."""
    positions, _, triangles = part
    p, n, t = [], [], []
    for a, b, c in triangles:
        face = norm(cross(sub(positions[b], positions[a]), sub(positions[c], positions[a])))
        base = len(p)
        p += [positions[a], positions[b], positions[c]]
        n += [face] * 3
        t.append((base, base + 1, base + 2))
    return p, n, t


def keys(duration, count, fn):
    times = [duration * i / count for i in range(count + 1)]
    return times, [fn(2 * math.pi * t / duration) for t in times]


def sway_clip(m, duration, count, spec):
    """The "sway" clip: rotation keys from `spec` {node: fn(phase)}; the last key equals the first, so it loops."""
    times, rotations = None, {}
    for node, fn in spec.items():
        times, rotations[node] = keys(duration, count, fn)
    m.clip("sway", times, rotations)


def lean(dz, dx=0.0):
    return qmul(quat(Z, dz), quat(X, dx))


# ---- the plants -------------------------------------------------------------------------------------------

def berry_bush(out):
    """A small round bush, about 0.3 m, with red berries in clusters over its crown."""
    m, rng = Plant("PlantBerryBush", "QRX.pack scripts/plants.py"), random.Random(3)
    dark, mid, light = m.material("leaf-dark", (0.20, 0.42, 0.16)), m.material("leaf", (0.30, 0.54, 0.20)), m.material("leaf-light", (0.46, 0.66, 0.26))
    stem_m = m.material("stem", (0.36, 0.23, 0.11))
    berry, berry_dark = m.material("berry", COLOR["berry-bush"], roughness=0.35), m.material("berry-dark", (0.55, 0.04, 0.12), roughness=0.35)
    crown = {k: Primitive(k) for k in (dark, mid, light, berry, berry_dark)}
    lumps = [(0.0, 0.18, 0.0, 0.12)]
    crown[dark].add(ellipsoid(0, 0.18, 0, 0.12, 0.10, 0.12, 10, 7))
    for k in range(7):
        a = 2 * math.pi * k / 7 + rng.uniform(-0.2, 0.2)
        d, r, y = rng.uniform(0.08, 0.11), rng.uniform(0.065, 0.08), 0.15 + rng.uniform(-0.02, 0.03)
        lumps.append((d * math.cos(a), y, d * math.sin(a), r))
        crown[mid if k % 2 else dark].add(ellipsoid(*lumps[-1][:3], r, r, r, 8, 6))
    for k in range(4):
        a = 2 * math.pi * k / 4 + 0.4
        d, r = rng.uniform(0.03, 0.06), rng.uniform(0.05, 0.065)
        lumps.append((d * math.cos(a), 0.25 + rng.uniform(-0.015, 0.015), d * math.sin(a), r))
        crown[mid].add(ellipsoid(*lumps[-1][:3], r, r, r, 8, 6))
    for k in range(8):
        a, d = rng.uniform(0, 2 * math.pi), rng.uniform(0.06, 0.14)
        r = rng.uniform(0.022, 0.032)
        crown[light].add(ellipsoid(d * math.cos(a), 0.18 + rng.uniform(-0.05, 0.09), d * math.sin(a), r, r, r, 6, 4))
    # Berries: clusters of two to four on the outside of the lumps, above the lowest third.
    for k in range(9):
        cx, cy, cz, r = lumps[1 + k % (len(lumps) - 1)]
        a = math.atan2(cz, cx) + rng.uniform(-0.9, 0.9) if (cx or cz) else rng.uniform(0, 2 * math.pi)
        e = rng.uniform(-0.1, 0.9)
        direction = norm((math.cos(a) * math.cos(e), math.sin(e), math.sin(a) * math.cos(e)))
        centre = tuple(c + d * (r + 0.004) for c, d in zip((cx, cy, cz), direction))
        for b in range(rng.randint(2, 4)):
            br = rng.uniform(0.010, 0.013)
            off = (rng.uniform(-0.012, 0.012), rng.uniform(-0.012, 0.006), rng.uniform(-0.012, 0.012))
            crown[berry if rng.random() < 0.7 else berry_dark].add(ellipsoid(*(c + o for c, o in zip(centre, off)), br, br, br, 6, 4))
    stem = Primitive(stem_m).add(tube([(0, 0, 0), (0, 0.12, 0)], [0.026, 0.016], 8, caps=False))
    root = m.node("Bush", [])
    crown_node = m.node("Crown", list(crown.values()), parent=root)
    m.node("Stem", [stem], parent=root)
    sway_clip(m, 4.0, 16, {crown_node: lambda p: lean(4 * math.sin(p), 1.2 * math.sin(2 * p))})
    m.write(f"{out}/models/plant-berry-bush.glb")


def seed_grass(out):
    """A tuft of grass, about 0.3 m, with five taller stalks ending in golden seed heads."""
    m, rng = Plant("PlantSeedGrass", "QRX.pack scripts/plants.py"), random.Random(5)
    green = m.material("blade", (0.46, 0.58, 0.22), double=True)
    dry = m.material("blade-dry", (0.66, 0.63, 0.34), double=True)
    stalk_m = m.material("stalk", (0.60, 0.56, 0.28))
    seed = m.material("seed", COLOR["seed-grass"], roughness=0.7)
    blades = {green: Primitive(green), dry: Primitive(dry)}
    for i in range(20):
        at = (rng.uniform(-0.015, 0.015), 0.0, rng.uniform(-0.015, 0.015))
        blades[green if i % 3 else dry].add(blade(360 * i / 20 + rng.uniform(-12, 12), rng.uniform(0.13, 0.22), 0.011,
                                                  rng.uniform(0.25, 0.7), 4, at, curl=rng.uniform(-0.1, 0.1)))
    stalks, heads = Primitive(stalk_m), Primitive(seed)
    for i in range(5):
        a = 2 * math.pi * i / 5 + rng.uniform(-0.3, 0.3)
        height = rng.uniform(0.26, 0.32)
        tilt = rng.uniform(5, 13)
        q = qmul(quat(Y, -math.degrees(a)), quat(Z, -tilt))
        base = (0.006 * math.cos(a), 0.001, 0.006 * math.sin(a))
        stalks.add(placed(tube([(0, 0, 0), (0, height * 0.5, 0), (0, height, 0)], [0.0028, 0.0022, 0.0016], 5, caps=False), q, base))
        # The head: grains in pairs up the last 6 cm, as wheat or foxtail carries them, and one at the tip.
        grains = []
        for g in range(5):
            y = height - 0.055 + g * 0.012
            for s in (-1, 1):
                grains.append(placed(ellipsoid(0, 0, 0, 0.0045, 0.009, 0.0045, 5, 3), quat(Z, -s * 25), (s * 0.004, y, 0)))
        grains.append(ellipsoid(0, height + 0.008, 0, 0.004, 0.008, 0.004, 5, 3))
        for gr in grains: heads.add(placed(gr, q, base))
    root = m.node("Grass", [])
    tuft = m.node("Tuft", list(blades.values()), parent=root)
    heads_node = m.node("Stalks", [stalks, heads], parent=root)
    sway_clip(m, 3.0, 18, {
        tuft: lambda p: lean(3 * math.sin(p), 1.5 * math.sin(p + 1.0)),
        heads_node: lambda p: lean(6 * math.sin(p - 0.6), 2.5 * math.sin(p + 0.4)),
    })
    m.write(f"{out}/models/plant-seed-grass.glb")


def mushrooms(out):
    """Three brown-capped mushrooms, 5 to 13 cm, on a patch of dark soil."""
    m, rng = Plant("PlantMushrooms", "QRX.pack scripts/plants.py"), random.Random(7)
    soil = m.material("soil", (0.27, 0.21, 0.15), double=True)
    stem_m = m.material("stem", (0.90, 0.86, 0.76), roughness=0.8)
    cap = m.material("cap", COLOR["mushrooms"], roughness=0.6)
    gills = m.material("gills", (0.84, 0.74, 0.60))
    spots = m.material("cap-light", (0.86, 0.72, 0.56), roughness=0.6)
    parts = {k: Primitive(k) for k in (stem_m, cap, gills, spots)}
    ground = Primitive(soil).add(flat([(0.10 * math.cos(2 * math.pi * k / 14) * (1 + 0.12 * math.sin(6 * math.pi * k / 14)) + 0.01,
                                        0.085 * math.sin(2 * math.pi * k / 14) * (1 + 0.12 * math.cos(4 * math.pi * k / 14)) + 0.015) for k in range(15)],
                                      0.002, (0.01, 0.015)))
    for x, z, h, r, tilt, turn in ((0.0, 0.0, 0.13, 0.055, 4, 30), (0.062, 0.035, 0.085, 0.038, 9, -40), (-0.04, 0.055, 0.055, 0.028, 12, 140)):
        q = qmul(quat(Y, turn), quat(Z, -tilt))
        stem = tube([(0, 0, 0), (0, h * 0.5, 0), (0, h - 0.2 * r, 0)], [0.24 * r, 0.2 * r, 0.17 * r], 8, caps=False)
        top, under = dome(0, h - 0.25 * r, 0, r, 0.62 * r, r, 12, 4, reach=0.56)
        parts[stem_m].add(placed(stem, q, (x, 0.0015, z)))
        parts[cap].add(placed(top, q, (x, 0.0015, z)))
        parts[gills].add(placed(under, q, (x, 0.0015, z)))
        for k in range(3):   # a few pale flecks on the cap
            a, e = rng.uniform(0, 2 * math.pi), rng.uniform(0.35, 1.0)
            d = (math.cos(e) * math.cos(a), math.sin(e), math.cos(e) * math.sin(a))
            c = (d[0] * r, h - 0.25 * r + d[1] * 0.62 * r, d[2] * r)
            parts[spots].add(placed(ellipsoid(*c, 0.12 * r, 0.06 * r, 0.12 * r, 6, 3), q, (x, 0.0015, z)))
    root = m.node("Mushrooms", [ground])
    cluster = m.node("Cluster", list(parts.values()), parent=root)
    sway_clip(m, 5.0, 10, {cluster: lambda p: lean(1.2 * math.sin(p), 0.6 * math.sin(p + 1.3))})
    m.write(f"{out}/models/plant-mushrooms.glb")


def nectar_flower(out):
    """A pink flower with a yellow heart on a 0.3 m stem with two leaves."""
    m = Plant("PlantNectarFlower", "QRX.pack scripts/plants.py")
    stem_m = m.material("stem", (0.30, 0.55, 0.22))
    leaf_m = m.material("leaf", (0.36, 0.62, 0.26), double=True)
    petal = m.material("petal", COLOR["nectar-flower"], roughness=0.6)
    heart = m.material("heart", (0.98, 0.80, 0.20), roughness=0.7)
    sepal = m.material("sepal", (0.26, 0.48, 0.20))
    height = 0.30
    stem = Primitive(stem_m).add(tube([(0, 0, 0), (0.004, 0.1, 0), (0.0, 0.2, 0.004), (0, height, 0)], [0.005, 0.0045, 0.004, 0.0035], 6, caps=False))
    leaves = Primitive(leaf_m)
    for y, turn, length in ((0.07, 20, 0.09), (0.13, 200, 0.075)):
        # A long leaf leaving the stem upwards and arching out.
        pts, positions = 6, []
        a = math.radians(turn)
        out_dir, side = (math.cos(a), 0.0, math.sin(a)), (-math.sin(a), 0.0, math.cos(a))
        for i in range(pts + 1):
            s = i / pts
            w = 0.018 * math.sin(math.pi * s) ** 0.8
            o, rise = length * s, length * (0.55 * s - 0.35 * s * s)
            c = (out_dir[0] * o, y + rise, out_dir[2] * o)
            positions += [(c[0] + side[0] * w, c[1], c[2] + side[2] * w), (c[0] - side[0] * w, c[1], c[2] - side[2] * w)]
        tris = [t for i in range(pts) for t in ((2 * i, 2 * i + 1, 2 * i + 3), (2 * i, 2 * i + 3, 2 * i + 2))]
        leaves.add((positions, [Y] * len(positions), tris))
    # The head, tilted 20 degrees towards +z so it looks out a little.
    tilt = quat(X, 20)
    petals, middle, cup = Primitive(petal), Primitive(heart), Primitive(sepal)
    for k in range(8):
        a = 360 * k / 8
        p = placed(ellipsoid(0.026, 0, 0, 0.024, 0.0035, 0.011, 8, 4), qmul(quat(Y, a), quat(Z, 14)))
        petals.add(placed(p, tilt, (0, 0.004, 0)))
    top, _ = dome(0, 0.004, 0, 0.013, 0.008, 0.013, 10, 4, reach=0.5, under=False)
    middle.add(placed(top, tilt))
    cup.add(placed(ellipsoid(0, -0.004, 0, 0.012, 0.009, 0.012, 8, 5), tilt))
    root = m.node("Flower", [])
    plant = m.node("Plant", [stem, leaves], parent=root)
    head = m.node("Head", [petals, middle, cup], (0, height, 0), parent=plant)
    sway_clip(m, 3.5, 21, {
        plant: lambda p: lean(4 * math.sin(p), 2 * math.sin(p + 1.1)),
        head: lambda p: lean(2 * math.sin(p - 0.8), 3 * math.sin(p + 0.3)),
    })
    m.write(f"{out}/models/plant-nectar-flower.glb")


def pond_weed(out):
    """A little pool, about 0.36 m across, with four lily pads, a pale bud and a few fronds of weed standing up."""
    m, rng = Plant("PlantPondWeed", "QRX.pack scripts/plants.py"), random.Random(9)
    water = m.material("water", (0.20, 0.34, 0.44), double=True, roughness=0.15)
    pad = m.material("pad", COLOR["pond-weed"], double=True, roughness=0.5)
    pad_dark = m.material("pad-dark", (0.17, 0.40, 0.22), double=True, roughness=0.5)
    frond_m = m.material("frond", (0.34, 0.62, 0.30), double=True)
    bud_m = m.material("bud", (0.96, 0.86, 0.90), roughness=0.6)
    pool = Primitive(water).add(flat([(0.18 * math.cos(2 * math.pi * k / 20) * (1 + 0.07 * math.sin(6 * math.pi * k / 20)),
                                       0.16 * math.sin(2 * math.pi * k / 20) * (1 + 0.07 * math.cos(4 * math.pi * k / 20))) for k in range(21)],
                                     0.001, (0.0, 0.0)))
    pads = {pad: Primitive(pad), pad_dark: Primitive(pad_dark)}
    for i, (x, z, r, turn) in enumerate(((-0.06, 0.04, 0.07, 30), (0.07, 0.05, 0.055, 160), (0.02, -0.07, 0.06, 250), (-0.09, -0.06, 0.04, 80))):
        a0 = math.radians(turn)
        # A round pad with a narrow slit to its middle, a lily's.
        outline = [(x + r * math.cos(a0 + 0.2 + (2 * math.pi - 0.4) * k / 16), z + r * math.sin(a0 + 0.2 + (2 * math.pi - 0.4) * k / 16)) for k in range(17)]
        pads[pad if i % 2 == 0 else pad_dark].add(flat(outline, 0.006 + 0.001 * i, (x, z)))
    fronds = Primitive(frond_m)
    for k in range(6):
        a = 360 * k / 6 + rng.uniform(-20, 20)
        fronds.add(blade(a, rng.uniform(0.12, 0.2), 0.009, rng.uniform(0.1, 0.35), 5, (0.09 + rng.uniform(-0.02, 0.02), 0.0, -0.01 + rng.uniform(-0.02, 0.02)),
                         curl=rng.uniform(-0.25, 0.25)))
    bud = Primitive(bud_m)
    for k in range(5):   # five closed petals around a point, on the first pad
        bud.add(placed(ellipsoid(0.006, 0.016, 0, 0.007, 0.017, 0.006, 6, 4), qmul(quat(Y, 72 * k), quat(Z, -12)), (-0.06, 0.008, 0.04)))
    root = m.node("Pond", [pool])
    pads_node = m.node("Pads", list(pads.values()) + [bud], parent=root)
    fronds_node = m.node("Fronds", [fronds], (0.0, 0.0, 0.0), parent=root)
    sway_clip(m, 5.0, 20, {
        pads_node: lambda p: quat(Y, 2.5 * math.sin(p)),
        fronds_node: lambda p: lean(3 * math.sin(p), 2 * math.sin(2 * p + 0.5)),
    })
    m.write(f"{out}/models/plant-pond-weed.glb")


def acorns(out):
    """Five acorns with their caps, one on top of the others, on an oak leaf about 0.2 m long."""
    m, rng = Plant("PlantAcorns", "QRX.pack scripts/plants.py"), random.Random(13)
    leaf_m = m.material("oak-leaf", (0.42, 0.50, 0.22), double=True)
    rib_m = m.material("rib", (0.55, 0.55, 0.30), double=True)
    nut = m.material("nut", COLOR["acorns"], roughness=0.45)
    cap_m = m.material("cup", (0.38, 0.28, 0.17))
    # The leaf: lobed on both sides, along x.
    half, width, steps = 0.10, 0.05, 30
    leaf_pos, leaf_tri = [], []
    for i in range(steps + 1):
        t = i / steps
        x = -half + 2 * half * t
        w = width * math.sin(math.pi * t) ** 0.7 * (0.62 + 0.38 * abs(math.cos(4.5 * math.pi * t)))
        for s in (-1, 1): leaf_pos.append((x, 0.002, s * w))
        leaf_pos.append((x, 0.002, 0.0))
    for i in range(steps):
        a, b = 3 * i, 3 * (i + 1)
        leaf_tri += [(a, a + 2, b + 2), (a, b + 2, b), (a + 2, a + 1, b + 1), (a + 2, b + 1, b + 2)]
    leaf = Primitive(leaf_m).add(placed((leaf_pos, [Y] * len(leaf_pos), leaf_tri), quat(Y, 25)))
    rib = Primitive(rib_m).add(placed(([(-half - 0.025, 0.0025, -0.0012), (-half - 0.025, 0.0025, 0.0012), (half, 0.0025, 0.0), ],
                                       [Y] * 3, [(0, 2, 1)]), quat(Y, 25)))

    def acorn():
        """One acorn, its nut's middle at the origin and its tip down."""
        body = ellipsoid(0, 0, 0, 0.0125, 0.017, 0.0125, 10, 6)
        tip = ellipsoid(0, -0.017, 0, 0.003, 0.004, 0.003, 5, 3)
        top, under = dome(0, 0.006, 0, 0.0145, 0.010, 0.0145, 10, 3, reach=0.55)
        stalk = tube([(0, 0.015, 0), (0.001, 0.021, 0)], [0.0018, 0.0014], 5)
        return [(nut, body), (nut, tip), (cap_m, top), (cap_m, under), (cap_m, stalk)]

    parts = {k: Primitive(k) for k in (nut, cap_m)}
    # (x, z, lying?, yaw, roll). Lying on its side its middle is 16.5 mm up (the cup is wider than the nut); standing, 25 mm.
    for x, z, lying, yaw in ((-0.02, 0.0, True, 10), (0.012, -0.012, True, 120), (0.01, 0.022, True, 250), (-0.045, 0.03, False, 0), (0.045, 0.0, True, 300)):
        q = qmul(quat(Y, yaw), quat(Z, 90 + rng.uniform(-8, 8))) if lying else quat(Y, yaw)
        for material, part in acorn(): parts[material].add(placed(part, q, (x, 0.0165 if lying else 0.025, z)))
    # One on top, in the hollow between the first three.
    q = qmul(quat(Y, 60), quat(Z, 80))
    for material, part in acorn(): parts[material].add(placed(part, q, (0.001, 0.038, 0.003)))
    root = m.node("Acorns", [])
    pile = m.node("Pile", [leaf, rib] + list(parts.values()), parent=root)
    sway_clip(m, 6.0, 12, {pile: lambda p: quat(Y, 0.6 * math.sin(p))})
    m.write(f"{out}/models/plant-acorns.glb")


def lichen(out):
    """A flat grey rock, about 0.27 m long and 7 cm high, crusted with pale green and a few ochre lichen patches."""
    m, rng = Plant("PlantLichen", "QRX.pack scripts/plants.py"), random.Random(17)
    rock_m = m.material("rock", (0.50, 0.49, 0.46), roughness=0.95)
    crust = m.material("lichen", COLOR["lichen"], roughness=1.0)
    ochre = m.material("lichen-ochre", (0.84, 0.66, 0.26), roughness=1.0)
    RX, RY, RZ, CY = 0.135, 0.06, 0.10, 0.018
    bumps = [(rng.uniform(0, 2 * math.pi), rng.uniform(0, math.pi), rng.uniform(1.5, 3.5), rng.uniform(0.04, 0.09)) for _ in range(5)]

    def radius(theta, phi):
        return 1 + sum(a * math.sin(f * theta + t0) * math.sin(f * phi + p0) for t0, p0, f, a in bumps)

    def surface(theta, phi):
        k = radius(theta, phi)
        nx, ny, nz = math.sin(phi) * math.cos(theta), math.cos(phi), math.sin(phi) * math.sin(theta)
        return (RX * k * nx, max(0.0, CY + RY * k * ny), RZ * k * nz)

    segments, rings = 14, 8
    positions, triangles = [], []
    for i in range(rings + 1):
        for j in range(segments + 1):
            positions.append(surface(2 * math.pi * j / segments, math.pi * i / rings))
    for i in range(rings):
        for j in range(segments):
            a = i * (segments + 1) + j
            b = a + segments + 1
            if i > 0: triangles.append((a, b, a + 1))
            if i < rings - 1: triangles.append((a + 1, b, b + 1))
    radial = [norm((x / RX ** 2, (y - CY) / RY ** 2, z / RZ ** 2)) for x, y, z in positions]
    shell = outward(Primitive(rock_m).add((positions, radial, triangles)))
    rock = Primitive(rock_m).add(faceted((shell.positions, shell.normals, shell.triangles)))
    patches = {crust: Primitive(crust), ochre: Primitive(ochre)}
    for k in range(16):
        theta, phi = rng.uniform(0, 2 * math.pi), rng.uniform(0.05, 1.05)
        s = surface(theta, phi)
        r = rng.uniform(0.012, 0.03)
        n = norm((s[0] / RX ** 2, (s[1] - CY) / RY ** 2, s[2] / RZ ** 2))
        c = tuple(si - ni * r * 0.15 for si, ni in zip(s, n))
        patches[ochre if k % 4 == 3 else crust].add(ellipsoid(*c, r, r * 0.3, r * rng.uniform(0.7, 1.1), 8, 4))
    root = m.node("Lichen", [])
    stone = m.node("Rock", [rock] + list(patches.values()), parent=root)
    sway_clip(m, 6.0, 12, {stone: lambda p: quat(Y, 0.3 * math.sin(p))})
    m.write(f"{out}/models/plant-lichen.glb")


# ---- checking what was written ----------------------------------------------------------------------------

def check(path):
    """Reads a .glb back and checks it: the header and chunks, every view and accessor inside the buffer, the
    positions' bounds and indices against the data, and a "sway" clip on existing nodes. Returns the scene's
    bounding box (rest pose) and the file's size; raises on anything wrong."""
    data = open(path, "rb").read()
    magic, version, length = struct.unpack_from("<III", data, 0)
    assert magic == 0x46546C67 and version == 2 and length == len(data), "header"
    json_len, json_type = struct.unpack_from("<II", data, 12)
    assert json_type == 0x4E4F534A, "JSON chunk"
    gltf = json.loads(data[20:20 + json_len])
    bin_at = 20 + json_len
    bin_len, bin_type = struct.unpack_from("<II", data, bin_at)
    assert bin_type == 0x004E4942 and bin_at + 8 + bin_len == len(data), "BIN chunk"
    blob = data[bin_at + 8:]
    assert gltf["buffers"][0]["byteLength"] <= bin_len, "buffer length"
    for v in gltf["bufferViews"]:
        assert v["byteOffset"] + v["byteLength"] <= gltf["buffers"][0]["byteLength"], "view out of the buffer"
    size = {5126: 4, 5123: 2, 5125: 4}
    width = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}

    def read(index):
        a = gltf["accessors"][index]
        v = gltf["bufferViews"][a["bufferView"]]
        n = a["count"] * width[a["type"]]
        assert a.get("byteOffset", 0) + n * size[a["componentType"]] <= v["byteLength"], f"accessor {index} longer than its view"
        flat = struct.unpack_from("<%d%s" % (n, {5126: "f", 5123: "H", 5125: "I"}[a["componentType"]]), blob, v["byteOffset"] + a.get("byteOffset", 0))
        w = width[a["type"]]
        return [flat[i:i + w] for i in range(0, n, w)] if w > 1 else list(flat)

    nodes = gltf["nodes"]
    lo, hi = [math.inf] * 3, [-math.inf] * 3
    triangles = 0

    def walk(i, offset):
        nonlocal triangles
        node = nodes[i]
        assert "rotation" not in node and "scale" not in node and "matrix" not in node, "only translations at rest"
        at = [o + t for o, t in zip(offset, node.get("translation", [0, 0, 0]))]
        if "mesh" in node:
            for p in gltf["meshes"][node["mesh"]]["primitives"]:
                a = gltf["accessors"][p["attributes"]["POSITION"]]
                positions = read(p["attributes"]["POSITION"])
                normals = read(p["attributes"]["NORMAL"])
                assert len(normals) == len(positions), "normals"
                for k in range(3):
                    assert abs(min(q[k] for q in positions) - a["min"][k]) < 1e-6 and abs(max(q[k] for q in positions) - a["max"][k]) < 1e-6, "bounds"
                    lo[k], hi[k] = min(lo[k], a["min"][k] + at[k]), max(hi[k], a["max"][k] + at[k])
                indices = read(p["indices"])
                assert len(indices) % 3 == 0 and max(indices) < len(positions), "indices"
                assert all(abs(math.sqrt(sum(c * c for c in n)) - 1) < 1e-3 for n in normals), "unit normals"
                assert 0 <= p["material"] < len(gltf["materials"]), "material"
                facing = sum(1 for t in range(0, len(indices), 3) if sum(
                    cross(sub(positions[indices[t + 1]], positions[indices[t]]), sub(positions[indices[t + 2]], positions[indices[t]]))[k]
                    * sum(normals[indices[t + j]][k] for j in range(3)) for k in range(3)) >= 0)
                assert facing == len(indices) // 3, f"{len(indices) // 3 - facing} triangles face in"
                triangles += len(indices) // 3
        for c in node.get("children", []): walk(c, at)

    for r in gltf["scenes"][gltf["scene"]]["nodes"]: walk(r, [0, 0, 0])
    sway = [a for a in gltf.get("animations", []) if a["name"] == "sway"]
    assert len(sway) == 1, "one clip named sway"
    for ch in sway[0]["channels"]:
        assert 0 <= ch["target"]["node"] < len(nodes), "clip's node"
        s = sway[0]["samplers"][ch["sampler"]]
        times, values = read(s["input"]), read(s["output"])
        assert len(times) == len(values) and all(b > a for a, b in zip(times, times[1:])), "keys"
        assert all(abs(math.sqrt(sum(c * c for c in q)) - 1) < 1e-4 for q in values), "unit quaternions"
        assert max(abs(a - b) for a, b in zip(values[0], values[-1])) < 1e-5, "the clip loops"
    return lo, hi, len(data), triangles


if __name__ == "__main__":
    out = sys.argv[1]
    if "--check" not in sys.argv[2:]:
        for build in (berry_bush, seed_grass, mushrooms, nectar_flower, pond_weed, acorns, lichen): build(out)
    for kind in KINDS:
        lo, hi, size, triangles = check(f"{out}/models/plant-{kind}.glb")
        assert lo[1] > -1e-4, f"plant-{kind}.glb goes below the ground"
        print(f"plant-{kind}.glb ok: {size} bytes, {triangles} triangles, x {lo[0]:+.3f}..{hi[0]:+.3f}, y {lo[1]:+.3f}..{hi[1]:+.3f}, z {lo[2]:+.3f}..{hi[2]:+.3f} m")
