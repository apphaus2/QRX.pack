"""A skin: rounded shapes blended into one continuous surface, the way a sculptor adds clay.

shapes.py makes parts that are stuck together (a ball for a head on a tube for a neck), and every join shows. A
skin is a list of blobs (balls, stretched balls, and limbs that taper from one end to the other); where two meet
they flow into each other over `blend` metres, and the whole is turned into one mesh with smooth normals. A
shoulder runs into a chest, a muzzle into a skull, an ear into a head.

    part = skin([ball((0, 0.05, 0), 0.03), limb((0, 0.05, 0), (0, 0.08, 0.05), 0.02, 0.012)], cell=0.005, blend=0.012)

The result is a part like any of shapes.py's: (positions, normals, triangles), to be painted and given to a node.
`cell` is the size of the mesh: smaller is smoother and heavier. Blobs given with `carve=True` are cut out of the
rest. Everything is exact arithmetic on a fixed grid, so the same blobs give the same bytes.

The mesh is made by surface nets: the space is cut into cells, each cell the surface passes through gets one
point (the mean of where the surface crosses its edges), and the points of neighbouring cells are joined.
"""
import math

from .shapes import norm, qrot, wound


def ball(centre, r, carve=False):
    return ("ball", tuple(centre), float(r), carve)


def egg(centre, radii, turn=None, carve=False):
    """A ball stretched to three radii, turned by the quaternion `turn` about its centre."""
    inverse = (-turn[0], -turn[1], -turn[2], turn[3]) if turn is not None else None
    return ("egg", tuple(centre), tuple(float(r) for r in radii), inverse, carve)


def limb(a, b, ra, rb, carve=False):
    """From a ball of radius `ra` at `a` to one of `rb` at `b`: a leg, a neck, a tail, a muzzle."""
    return ("limb", tuple(a), tuple(b), float(ra), float(rb), carve)


def chain(points, radii):
    """Limbs through `points` with a radius at each: a curved tail, a spine."""
    return [limb(points[i], points[i + 1], radii[i], radii[i + 1]) for i in range(len(points) - 1)]


def _distance(blob, x, y, z):
    kind = blob[0]
    if kind == "ball":
        c, r = blob[1], blob[2]
        return math.sqrt((x - c[0]) ** 2 + (y - c[1]) ** 2 + (z - c[2]) ** 2) - r
    if kind == "limb":
        a, b, ra, rb = blob[1], blob[2], blob[3], blob[4]
        dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        px, py, pz = x - a[0], y - a[1], z - a[2]
        span = dx * dx + dy * dy + dz * dz
        t = 0.0 if span < 1e-18 else max(0.0, min(1.0, (px * dx + py * dy + pz * dz) / span))
        return math.sqrt((px - dx * t) ** 2 + (py - dy * t) ** 2 + (pz - dz * t) ** 2) - (ra + (rb - ra) * t)
    c, r, inverse = blob[1], blob[2], blob[3]
    p = (x - c[0], y - c[1], z - c[2])
    if inverse is not None: p = qrot(inverse, p)
    k0 = math.sqrt((p[0] / r[0]) ** 2 + (p[1] / r[1]) ** 2 + (p[2] / r[2]) ** 2)
    if k0 < 1e-9: return -min(r)
    k1 = math.sqrt((p[0] / (r[0] * r[0])) ** 2 + (p[1] / (r[1] * r[1])) ** 2 + (p[2] / (r[2] * r[2])) ** 2)
    return k0 * (k0 - 1.0) / k1


def _reach(blob):
    """The box a blob fills: (min, max)."""
    kind = blob[0]
    if kind == "ball":
        c, r = blob[1], blob[2]
        return [c[i] - r for i in range(3)], [c[i] + r for i in range(3)]
    if kind == "limb":
        a, b, r = blob[1], blob[2], max(blob[3], blob[4])
        return [min(a[i], b[i]) - r for i in range(3)], [max(a[i], b[i]) + r for i in range(3)]
    c, r = blob[1], max(blob[2])
    return [c[i] - r for i in range(3)], [c[i] + r for i in range(3)]


# How fine the grid is (the owner, 2026-11-16: "make it finer grain"). A caller's `cell` is scaled by FINE, and a
# cell is never wider than THIN of the thinnest blob's radius, so a leg is round (nearly two cells from its axis to
# its skin) instead of a lumpy stick; FLOOR keeps one tiny blob from making a whole body's grid too fine to build.
# At 0.75 and 0.6 a beast has 9,500 to 20,000 triangles (6,400 at most before); 0.55 and 0.4 made 34,000 and a
# 400 KB download, for a difference too small to see at the size a creature is shown.
FINE, THIN, FLOOR = 0.75, 0.6, 0.3


def _thinnest(blob):
    kind = blob[0]
    if kind == "ball": return blob[2]
    if kind == "limb": return min(blob[3], blob[4])
    return min(blob[2])


def skin(blobs, cell=0.005, blend=0.01):
    """The blobs as one part. `blend` is how far two blobs flow into each other; a blob may also be a list of blobs."""
    flat = []
    for blob in blobs:
        flat += blob if isinstance(blob, list) else [blob]
    solid, holes = [b for b in flat if not b[-1]], [b for b in flat if b[-1]]
    cell = max(cell * FLOOR, min(cell * FINE, THIN * min(_thinnest(b) for b in solid)))
    boxes = [_reach(b) for b in solid]
    lo = [min(box[0][i] for box in boxes) - blend - cell for i in range(3)]
    hi = [max(box[1][i] for box in boxes) + blend + cell for i in range(3)]
    # The grid is laid out from the creature's middle plane, so both sides come out the same.
    half = max(abs(lo[0]), abs(hi[0]))
    nx = 2 * int(math.ceil(half / cell))
    ny, nz = int(math.ceil((hi[1] - lo[1]) / cell)), int(math.ceil((hi[2] - lo[2]) / cell))
    x0, y0, z0 = -nx / 2 * cell, lo[1], lo[2]
    pad = blend + cell * 1.8
    near = [([box[0][i] - pad for i in range(3)], [box[1][i] + pad for i in range(3)]) for box in boxes]

    def field(x, y, z):
        d = 1e9
        for blob, (a, b) in zip(solid, near):
            if x < a[0] or x > b[0] or y < a[1] or y > b[1] or z < a[2] or z > b[2]: continue
            e = _distance(blob, x, y, z)
            if blend > 0:
                h = max(blend - abs(d - e), 0.0) / blend
                d = min(d, e) - h * h * blend * 0.25
            elif e < d: d = e
        for blob in holes:
            e = -_distance(blob, x, y, z)
            if e > d: d = e
        return d

    values =[[[field(x0 + i * cell, y0 + j * cell, z0 + k * cell) for k in range(nz + 1)] for j in range(ny + 1)] for i in range(nx + 1)]
    index, positions = {}, []
    corners = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0), (0, 0, 1), (1, 0, 1), (0, 1, 1), (1, 1, 1)]
    edges = [(0, 1), (2, 3), (4, 5), (6, 7), (0, 2), (1, 3), (4, 6), (5, 7), (0, 4), (1, 5), (2, 6), (3, 7)]
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                v = [values[i + c[0]][j + c[1]][k + c[2]] for c in corners]
                inside = sum(1 for value in v if value < 0)
                if inside == 0 or inside == 8: continue
                px = py = pz = 0.0
                count = 0
                for a, b in edges:
                    if (v[a] < 0) == (v[b] < 0): continue
                    t = v[a] / (v[a] - v[b])
                    px += corners[a][0] + (corners[b][0] - corners[a][0]) * t
                    py += corners[a][1] + (corners[b][1] - corners[a][1]) * t
                    pz += corners[a][2] + (corners[b][2] - corners[a][2]) * t
                    count += 1
                index[(i, j, k)] = len(positions)
                positions.append((x0 + (i + px / count) * cell, y0 + (j + py / count) * cell, z0 + (k + pz / count) * cell))
    triangles = []
    for i in range(nx + 1):
        for j in range(ny + 1):
            for k in range(nz + 1):
                here = values[i][j][k] < 0
                # Each grid edge the surface crosses is shared by four cells: their points make a quad.
                for axis in range(3):
                    ni, nj, nk = i + (axis == 0), j + (axis == 1), k + (axis == 2)
                    if ni > nx or nj > ny or nk > nz: continue
                    if here == (values[ni][nj][nk] < 0): continue
                    if axis == 0: ring = [(i, j - 1, k - 1), (i, j, k - 1), (i, j, k), (i, j - 1, k)]
                    elif axis == 1: ring = [(i - 1, j, k - 1), (i - 1, j, k), (i, j, k), (i, j, k - 1)]
                    else: ring = [(i - 1, j - 1, k), (i, j - 1, k), (i, j, k), (i - 1, j, k)]
                    quad = [index.get(cell_at) for cell_at in ring]
                    if None in quad: continue
                    triangles += [(quad[0], quad[1], quad[2]), (quad[0], quad[2], quad[3])]
    e = cell * 0.5
    normals = []
    for x, y, z in positions:
        normals.append(norm((field(x + e, y, z) - field(x - e, y, z), field(x, y + e, z) - field(x, y - e, z), field(x, y, z + e) - field(x, y, z - e))))
    return wound((positions, normals, triangles))
