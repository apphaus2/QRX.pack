"""Shapes for the archetypes (standard library only), after QRX.pack's scripts/habitats.py and fish.py.

A *part* is (positions, normals, triangles): lists of 3-tuples in metres, +Y up, the creature's head along +Z
and its left along +X. Every helper returns a part whose triangles are wound to agree with its normals, so a
single-sided material shows the outside.
"""
import math

X, Y, Z = (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)


# ---- vectors and rotations --------------------------------------------------------------------------------

def add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def mul(a, k): return (a[0] * k, a[1] * k, a[2] * k)
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def length(a): return math.sqrt(dot(a, a))


def norm(a):
    n = length(a)
    return (a[0] / n, a[1] / n, a[2] / n) if n > 1e-12 else (0.0, 1.0, 0.0)


def quat(axis, degrees):
    """A turn of `degrees` about `axis` as (x, y, z, w)."""
    h = math.radians(degrees) / 2
    s = math.sin(h)
    return (axis[0] * s, axis[1] * s, axis[2] * s, math.cos(h))


def qmul(a, b):
    """The turn b, then the turn a."""
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz)


def qrot(q, v):
    u, w = q[:3], q[3]
    t = mul(cross(u, v), 2.0)
    return add(add(v, mul(t, w)), cross(u, t))


def smooth(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


class Profile:
    """A smooth curve through (t, value) knots, Catmull-Rom between them."""

    def __init__(self, knots):
        self.knots = sorted(knots)

    def __call__(self, t):
        k = self.knots
        t = min(max(t, k[0][0]), k[-1][0])
        i = max(j for j in range(len(k) - 1) if k[j][0] <= t)
        t0, v0 = k[max(i - 1, 0)]; t1, v1 = k[i]; t2, v2 = k[i + 1]; t3, v3 = k[min(i + 2, len(k) - 1)]
        s = (t - t1) / (t2 - t1) if t2 > t1 else 0.0
        return 0.5 * (2 * v1 + (-v0 + v2) * s + (2 * v0 - 5 * v1 + 4 * v2 - v3) * s * s + (-v0 + 3 * v1 - 3 * v2 + v3) * s * s * s)


# ---- parts ------------------------------------------------------------------------------------------------

def wound(part):
    """The part with every triangle wound to face the way its vertex normals do; slivers are dropped."""
    positions, normals, triangles = part
    out = []
    for a, b, c in triangles:
        face = cross(sub(positions[b], positions[a]), sub(positions[c], positions[a]))
        if dot(face, face) < 1e-22: continue
        out.append((a, b, c) if dot(face, add(add(normals[a], normals[b]), normals[c])) >= 0 else (a, c, b))
    return positions, normals, out


def merge(*parts):
    positions, normals, triangles = [], [], []
    for p, n, t in parts:
        base = len(positions)
        positions += p
        normals += n
        triangles += [(a + base, b + base, c + base) for a, b, c in t]
    return positions, normals, triangles


def moved(part, at=(0.0, 0.0, 0.0), turn=None, scale=(1.0, 1.0, 1.0)):
    """The part scaled, then turned by the quaternion `turn`, then moved to `at`."""
    positions, normals, triangles = part
    if isinstance(scale, (int, float)): scale = (scale, scale, scale)
    ps = [(p[0] * scale[0], p[1] * scale[1], p[2] * scale[2]) for p in positions]
    ns = [norm((n[0] / scale[0], n[1] / scale[1], n[2] / scale[2])) for n in normals]
    if turn is not None:
        ps, ns = [qrot(turn, p) for p in ps], [qrot(turn, n) for n in ns]
    return [add(p, at) for p in ps], ns, list(triangles)


def mirrored(part):
    """The part reflected in the creature's middle plane (x to -x)."""
    positions, normals, triangles = part
    return [(-p[0], p[1], p[2]) for p in positions], [(-n[0], n[1], n[2]) for n in normals], [(a, c, b) for a, b, c in triangles]


def split(part, paint):
    """The part cut by `paint(centre, normal)`, which names each triangle's colour: {name: part}."""
    positions, normals, triangles = part
    out, index = {}, {}
    for tri in triangles:
        centre = mul(add(add(positions[tri[0]], positions[tri[1]]), positions[tri[2]]), 1 / 3)
        normal = norm(add(add(normals[tri[0]], normals[tri[1]]), normals[tri[2]]))
        key = paint(centre, normal)
        ps, ns, ts = out.setdefault(key, ([], [], []))
        new = []
        for v in tri:
            if (key, v) not in index:
                index[(key, v)] = len(ps)
                ps.append(positions[v]); ns.append(normals[v])
            new.append(index[(key, v)])
        ts.append(tuple(new))
    return out


def ellipsoid(centre, radii, segments=10, rings=6, top=0.0, bottom=1.0):
    """A UV sphere stretched to three radii; `top` and `bottom` (0..1 from the +Y pole to the -Y one) keep a slice."""
    cx, cy, cz = centre
    rx, ry, rz = radii
    positions, normals, triangles = [], [], []
    for i in range(rings + 1):
        phi = math.pi * (top + (bottom - top) * i / rings)
        for j in range(segments + 1):
            theta = 2 * math.pi * j / segments
            nx, ny, nz = math.sin(phi) * math.cos(theta), math.cos(phi), math.sin(phi) * math.sin(theta)
            positions.append((cx + rx * nx, cy + ry * ny, cz + rz * nz))
            normals.append(norm((nx / rx, ny / ry, nz / rz)))
    for i in range(rings):
        for j in range(segments):
            a = i * (segments + 1) + j
            b = a + segments + 1
            triangles += [(a, b, a + 1), (a + 1, b, b + 1)]
    return wound((positions, normals, triangles))


def ball(centre, r, segments=8, rings=5):
    return ellipsoid(centre, (r, r, r), segments, rings)


def tube(points, radii, sides=8, squash=1.0, caps=True):
    """A tube through `points` with a radius at each. The frame is carried along the path, so a path that curls
    (a shell, a tail) does not twist; `squash` flattens the section across the frame's second axis."""
    n = len(points)
    tangents = [norm(sub(points[min(k + 1, n - 1)], points[max(k - 1, 0)])) for k in range(n)]
    d = tangents[0]
    u = norm(cross(d, Y)) if abs(d[1]) < 0.95 else norm(cross(d, X))
    positions, normals, triangles = [], [], []
    for k in range(n):
        d = tangents[k]
        u = norm(sub(u, mul(d, dot(u, d))))
        v = norm(cross(d, u))
        for s in range(sides + 1):
            t = 2 * math.pi * s / sides
            c, w = math.cos(t), math.sin(t)
            positions.append(tuple(points[k][i] + (u[i] * c + v[i] * w * squash) * radii[k] for i in range(3)))
            normals.append(norm(tuple(u[i] * c * squash + v[i] * w for i in range(3))))
    for k in range(n - 1):
        for s in range(sides):
            a = k * (sides + 1) + s
            b = a + sides + 1
            triangles += [(a, a + 1, b), (a + 1, b + 1, b)]
    if caps:
        for k, sign in ((0, -1.0), (n - 1, 1.0)):
            if radii[k] <= 0: continue
            centre = len(positions)
            positions.append(tuple(points[k])); normals.append(mul(tangents[k], sign))
            ring = k * (sides + 1)
            for s in range(sides):
                # The ring's own vertices have sideways normals; the cap gets its own, facing along the path.
                a, b = len(positions), len(positions) + 1
                positions += [positions[ring + s], positions[ring + s + 1]]
                normals += [mul(tangents[k], sign)] * 2
                triangles.append((centre, a, b))
    return wound((positions, normals, triangles))


def loft(sections, around=14, caps=True):
    """A body lofted through elliptical `sections`, each (z, y, rx, ry): centre height y at z, half-width rx and
    half-height ry. Normals come from the neighbouring rings."""
    rows = []
    for z, y, rx, ry in sections:
        rows.append([(rx * math.cos(2 * math.pi * j / around), y + ry * math.sin(2 * math.pi * j / around), z) for j in range(around + 1)])
    positions, normals, triangles = [], [], []
    count = len(rows)
    for i in range(count):
        centre = (0.0, sections[i][1], sections[i][0])
        for j in range(around + 1):
            p = rows[i][j]
            along = sub(rows[min(i + 1, count - 1)][j], rows[max(i - 1, 0)][j])
            ring = sub(rows[i][(j + 1) % around], rows[i][(j - 1) % around])
            n = norm(cross(along, ring))
            if dot(n, sub(p, centre)) < 0: n = mul(n, -1.0)
            positions.append(p); normals.append(n)
    for i in range(count - 1):
        for j in range(around):
            a = i * (around + 1) + j
            b = a + around + 1
            triangles += [(a, b, a + 1), (a + 1, b, b + 1)]
    if caps:
        for i, sign in ((0, 1.0), (count - 1, -1.0)):
            direction = norm(sub(rows[0][0], rows[-1][0]))
            direction = (0.0, 0.0, math.copysign(1.0, direction[2]) * sign)
            centre = len(positions)
            positions.append((0.0, sections[i][1], sections[i][0])); normals.append(direction)
            for j in range(around):
                a = len(positions)
                positions += [rows[i][j], rows[i][j + 1]]
                normals += [direction] * 2
                triangles.append((centre, a, a + 1))
    return wound((positions, normals, triangles))


def fin(polygon, origin, u, v):
    """A flat polygon with 2D points (a, b) laid in the plane origin + a*u + b*v, fanned from its first point
    (the shapes are star-shaped from it). Draw it with a double-sided material."""
    u, v = norm(u), norm(v)
    n = norm(cross(u, v))
    positions = [add(origin, add(mul(u, a), mul(v, b))) for a, b in polygon]
    triangles = [(0, i, i + 1) for i in range(1, len(polygon) - 1)]
    return wound((positions, [n] * len(positions), triangles))


def sheet(x0, x1, front, back, across=6, along=4, height=None, under=False):
    """A wing: for each span x from x0 to x1 the surface runs from z = back(x) to z = front(x). `height(s, c)`
    lifts it (s the span fraction, c the chord fraction from the back edge); `under` gives the lower face of a
    thick wing (the height negated, facing down). x0 > x1 builds the creature's right wing."""
    grid = []
    for i in range(across + 1):
        s = i / across
        x = x0 + (x1 - x0) * s
        row = []
        for j in range(along + 1):
            c = j / along
            y = height(s, c) if height else 0.0
            row.append((x, -y if under else y, back(x) + (front(x) - back(x)) * c))
        grid.append(row)
    positions, normals, triangles = [], [], []
    facing = -1.0 if under else 1.0
    for i in range(across + 1):
        for j in range(along + 1):
            a = sub(grid[min(i + 1, across)][j], grid[max(i - 1, 0)][j])
            b = sub(grid[i][min(j + 1, along)], grid[i][max(j - 1, 0)])
            n = norm(cross(a, b))
            if n[1] * facing < 0: n = mul(n, -1.0)
            positions.append(grid[i][j]); normals.append(n)
    for i in range(across):
        for j in range(along):
            a = i * (along + 1) + j
            b = a + along + 1
            triangles += [(a, b, a + 1), (a + 1, b, b + 1)]
    return wound((positions, normals, triangles))


def box_of(*parts):
    """The (min, max) corners of the parts' positions."""
    points = [p for part in parts for p in part[0]]
    return tuple(min(p[i] for p in points) for i in range(3)), tuple(max(p[i] for p in points) for i in range(3))
