"""The TV's habitats: the tank, the terrarium and the aviary as glTF binaries, written by hand (standard
library only).

A habitat fills a TV screen: there is no box, no glass and no edge. The camera stands still where the front
glass would be (each scene's `camera` in habitats/*.json) and the floor and the backdrop run past every side of
its view. The backdrop is one quad behind everything with the habitat's gradient as an emissive texture over a
black base colour, so it draws the same under any lighting and the 3D view is opaque without the app's help.
Everything else is a painted base-colour PNG (metallic 0, a roughness factor, TEXCOORD_0), the same kind of
albedo the creature meshes carry. The files stay plain glTF 2.0: no meshopt, no KTX2, power-of-two PNGs, so
SceneKit through GLTFKit2 and Filament both load them, and one habitat is small enough for a Fire TV stick.
Plants are their own nodes with one "idle" clip that sways them. Metres, +Y up, the camera on +Z looking to -Z.
The origin, the extents and the sway clip are what habitats/*.json already assumes, so creatures keep the same
places to swim, stand and perch.

    python3 scripts/habitats.py <out>    ->   <out>/models/habitat-tank.glb, habitat-terrarium.glb, habitat-aviary.glb

`Model` and the shape helpers are also what scripts/lizard.py and scripts/plants.py build with. Their calls
pass no texture coordinates, and a part without them is unchanged.
"""
import json, math, random, struct, sys, zlib


# ---- shapes: each returns (positions, normals, triangles) ------------------------------------------------
# Pass `uvs` (a list) and the shape appends one coordinate per vertex, for a painted texture. Leave it out and
# the shape is what it was. A repeat around a tube or a sphere is a whole number so the seam meets.

def norm(a):
    length = math.sqrt(sum(x * x for x in a)) or 1.0
    return tuple(x / length for x in a)


def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def sub(a, b): return tuple(x - y for x, y in zip(a, b))
def mix(a, b, t): return tuple(a[i] + (b[i] - a[i]) * t for i in range(len(a)))
def shade(c, k): return tuple(v * k for v in c)


class Primitive:
    def __init__(self, material):
        self.material, self.positions, self.normals, self.triangles, self.uvs = material, [], [], [], None

    def add(self, part, uvs=None):
        positions, normals, triangles = part
        if uvs is not None and len(uvs) != len(positions):
            raise ValueError("a part has %d vertices and %d texture coordinates" % (len(positions), len(uvs)))
        base = len(self.positions)
        self.positions += positions
        self.normals += normals
        self.triangles += [(a + base, b + base, c + base) for a, b, c in triangles]
        if uvs is not None:
            if self.uvs is None:
                if base:
                    raise ValueError("texture coordinates started after bare vertices")
                self.uvs = []
            self.uvs += list(uvs)
        elif self.uvs is not None:
            raise ValueError("a textured primitive gained a part with no coordinates")
        return self


def add_uv(prim, fn, *args, **kwargs):
    """Build `fn`(*args, uvs=...) and add it. `fn` appends one coordinate per vertex it creates."""
    coords = []
    prim.add(fn(*args, uvs=coords, **kwargs), coords)
    return prim


def _whole(n, what):
    if abs(n - round(n)) > 1e-4:
        raise ValueError(what)
    return int(round(n))


def ellipsoid(cx, cy, cz, rx, ry, rz, segments=10, rings=6, uvs=None, proj="sphere", scale=1.0):
    positions, normals, triangles = [], [], []
    if uvs is not None and proj == "sphere":
        scale = _whole(scale, "a sphere's texture repeat must be a whole number so the seam meets")
    for i in range(rings + 1):
        phi = math.pi * i / rings
        for j in range(segments + 1):
            theta = 2 * math.pi * j / segments
            nx, ny, nz = math.sin(phi) * math.cos(theta), math.cos(phi), math.sin(phi) * math.sin(theta)
            positions.append((cx + rx * nx, cy + ry * ny, cz + rz * nz))
            normals.append(norm((nx / rx, ny / ry, nz / rz)))
            if uvs is not None:
                if proj == "top":
                    uvs.append((0.5 + (positions[-1][0] - cx) / (2 * rx), 0.5 + (positions[-1][2] - cz) / (2 * rz)))
                else:
                    uvs.append((j / segments * scale, i / rings * scale))
    # Counterclockwise when the normal points at the camera. glTF culls the other side, and these
    # normals already point outward. Plants fix a wrong winding on the way out; a habitat does not.
    for i in range(rings):
        for j in range(segments):
            a = i * (segments + 1) + j
            b = a + segments + 1
            if i > 0: triangles.append((a, a + 1, b))
            if i < rings - 1: triangles.append((a + 1, b + 1, b))
    return positions, normals, triangles


def blade(angle, length, width, lean, segments=4, at=(0.0, 0.0, 0.0), curl=0.0, uvs=None):
    """A tapered flat leaf standing at `at`, turned `angle` degrees about y, bending outwards by `lean` (the tip
    ends lean * length out) and sideways by `curl`. 2 * segments - 1 triangles; draw it double-sided.
    Coordinates run across the blade (0 to 1) and from the base up to the tip, for a frond texture."""
    a = math.radians(angle)
    out_dir, side = (math.sin(a), 0.0, math.cos(a)), (math.cos(a), 0.0, -math.sin(a))
    positions = []
    for i in range(segments + 1):
        h = i / segments
        w = width * (0.45 + 1.6 * h) * (1 - h) ** 0.7 if i < segments else 0.0
        o, c, y = lean * h * h * length, curl * math.sin(h * math.pi) * length, length * (h - 0.25 * lean * h * h)
        centre = (at[0] + out_dir[0] * o + side[0] * c, at[1] + y, at[2] + out_dir[2] * o + side[2] * c)
        if i == segments:
            positions.append(centre)
            if uvs is not None: uvs.append((0.5, 1.0))
        else:
            for s in (-1, 1):
                positions.append((centre[0] + side[0] * w * s / 2, centre[1], centre[2] + side[2] * w * s / 2))
                if uvs is not None: uvs.append((0.0 if s < 0 else 1.0, h))
    normal = norm((-out_dir[0] * 0.5, 0.35, -out_dir[2] * 0.5))
    # Same rule as the ellipsoid: the lit side is the front face.
    triangles = []
    for i in range(segments - 1):
        triangles += [(2 * i, 2 * i + 3, 2 * i + 1), (2 * i, 2 * i + 2, 2 * i + 3)]
    triangles.append((2 * segments - 2, 2 * segments, 2 * segments - 1))
    return positions, [normal] * len(positions), triangles


def heightfield(x0, x1, z0, z1, nx, nz, height, uvs=None, uv_at=None):
    """A floor from (x0, z0) to (x1, z1), nx by nz cells, y = height(x, z), facing up.
    `uv_at(x, z)` gives the texture coordinate; without it the field maps to 0..1."""
    positions, normals, triangles = [], [], []
    for j in range(nz + 1):
        for i in range(nx + 1):
            x, z = x0 + (x1 - x0) * i / nx, z0 + (z1 - z0) * j / nz
            positions.append((x, height(x, z), z))
            e = 0.01
            normals.append(norm((height(x - e, z) - height(x + e, z), 2 * e, height(x, z - e) - height(x, z + e))))
            if uvs is not None:
                uvs.append(uv_at(x, z) if uv_at else ((x - x0) / (x1 - x0), (z - z0) / (z1 - z0)))
    for j in range(nz):
        for i in range(nx):
            a = j * (nx + 1) + i
            b = a + nx + 1
            triangles += [(a, b, a + 1), (a + 1, b, b + 1)]
    return positions, normals, triangles


def tube(points, radii, sides=8, squash=1.0, caps=True, uvs=None, uv_scale=(1.0, 1.0)):
    """A round tube through `points` with a radius at each; `squash` flattens it vertically.
    `uv_scale` is (repeats around, repeats per metre along). The around count is a whole number."""
    positions, normals, triangles = [], [], []
    around, per_metre = uv_scale
    if uvs is not None:
        around = _whole(around, "a tube's texture must repeat a whole number of times around it")
    travelled = [0.0]
    for k in range(1, len(points)):
        travelled.append(travelled[-1] + math.dist(points[k], points[k - 1]))
    for k, p in enumerate(points):
        d = norm(sub(points[min(k + 1, len(points) - 1)], points[max(k - 1, 0)]))
        u = norm(cross(d, (0.0, 1.0, 0.0))) if abs(d[1]) < 0.95 else (1.0, 0.0, 0.0)
        v = norm(cross(u, d))
        for s in range(sides + 1):
            t = 2 * math.pi * s / sides
            n = tuple(u[i] * math.cos(t) + v[i] * math.sin(t) * squash for i in range(3))
            positions.append(tuple(p[i] + n[i] * radii[k] for i in range(3)))
            normals.append(norm(tuple(u[i] * math.cos(t) + v[i] * math.sin(t) for i in range(3))))
            if uvs is not None:
                uvs.append((s / sides * around, travelled[k] * per_metre))
    # The wall faces out. The caps already did; only the wall was wound inward.
    for k in range(len(points) - 1):
        for s in range(sides):
            a = k * (sides + 1) + s
            b = a + sides + 1
            triangles += [(a, b, a + 1), (a + 1, b, b + 1)]
    if caps:
        for k, sign in ((0, -1), (len(points) - 1, 1)):
            if radii[k] <= 0: continue
            d = norm(sub(points[min(k + 1, len(points) - 1)], points[max(k - 1, 0)]))
            centre = len(positions)
            positions.append(points[k]); normals.append(tuple(c * sign for c in d))
            if uvs is not None: uvs.append((0.5 * around, travelled[k] * per_metre))
            ring = k * (sides + 1)
            for s in range(sides):
                triangles.append((centre, ring + s + 1, ring + s) if sign > 0 else (centre, ring + s, ring + s + 1))
    return positions, normals, triangles


def disc(centre, normal, radius, segments=18, uvs=None):
    """A flat circle facing `normal`, with coordinates centred on it, for a cut end (growth rings)."""
    normal = norm(normal)
    axis = (0.0, 1.0, 0.0) if abs(normal[1]) < 0.9 else (1.0, 0.0, 0.0)
    tangent = norm(cross(normal, axis))
    bitangent = norm(cross(normal, tangent))
    positions, normals = [centre], [normal]
    if uvs is not None: uvs.append((0.5, 0.5))
    for s in range(segments):
        t = 2 * math.pi * s / segments
        positions.append(tuple(centre[i] + radius * (tangent[i] * math.cos(t) + bitangent[i] * math.sin(t)) for i in range(3)))
        normals.append(normal)
        if uvs is not None: uvs.append((0.5 + 0.5 * math.cos(t), 0.5 + 0.5 * math.sin(t)))
    triangles = [(0, s + 1, 1 if s + 1 == segments else s + 2) for s in range(segments)]
    return positions, normals, triangles


def smooth(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def uv_floor(x0, x1, z_front, z_back):
    """0..1 across x, and 0 at the front (z_front, the camera side) running to 1 at the back."""
    def uv(x, z):
        return ((x - x0) / (x1 - x0), (z_front - z) / (z_front - z_back))
    return uv


def quat(axis, deg):
    h = math.radians(deg) / 2
    s = math.sin(h)
    return (axis[0] * s, axis[1] * s, axis[2] * s, math.cos(h))


X, Y, Z = (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)


def keep_clear(prims, box, y_max, what):
    """Creature bounds are a volume the scenery must not fill. `box` is (x0, x1, z0, z1); anything in it has to
    stay at or below `y_max` so a swimmer still has the water the scene promised."""
    x0, x1, z0, z1 = box
    for prim in prims:
        for x, y, z in prim.positions:
            if x0 < x < x1 and z0 < z < z1 and y > y_max:
                raise SystemExit("%s enters the creature bounds at (%.3f, %.3f, %.3f)" % (what, x, y, z))


# ---- painted textures --------------------------------------------------------------------------------------
# Authored in linear colour, the same numbers the old flat materials used, and stored sRGB because a glTF
# base-colour image is sRGB. Both TV loaders sample it that way. Power-of-two, no mipmaps in the file
# (the sampler is linear, not mipmapped) so a GLES 2 stick does not drop a repeating texture.

def _hash(ix, iy, seed):
    n = (int(ix) * 374761393 + int(iy) * 668265263 + int(seed) * 1442695041) & 0xFFFFFFFF
    n = (n ^ (n >> 13)) * 1274126177 & 0xFFFFFFFF
    n ^= n >> 16
    return (n & 0xFFFFFF) / 16777215.0


def _noise(x, y, seed, period):
    x0, y0 = math.floor(x), math.floor(y)
    tx, ty = smooth(x - x0), smooth(y - y0)
    def h(ix, iy):
        if period:
            ix %= period
            iy %= period
        return _hash(ix, iy, seed)
    return ((h(x0, y0) * (1 - tx) + h(x0 + 1, y0) * tx) * (1 - ty)
            + (h(x0, y0 + 1) * (1 - tx) + h(x0 + 1, y0 + 1) * tx) * ty)


def fbm(u, v, seed, octaves=4, cells=8, tile=False):
    """Value noise over a texture. `u`, `v` are 0..1. `cells` is how many blobs fit across it. `tile` makes the
    edges meet, which a repeating bark or rock needs and a one-off floor does not."""
    total = weight = 0.0
    amp = 1.0
    for o in range(octaves):
        freq = 1 << o
        total += amp * _noise(u * cells * freq, v * cells * freq, seed + o * 17, int(cells * freq) if tile else 0)
        weight += amp
        amp *= 0.5
    return total / weight


def stretch(n, gain=2.2):
    """Value noise sits near 0.5. Spread it so a stone or a moss clump actually changes colour."""
    x = (n - 0.5) * gain + 0.5
    return smooth(0.0 if x < 0.0 else 1.0 if x > 1.0 else x)


def _srgb(c):
    c = 0.0 if c < 0.0 else 1.0 if c > 1.0 else c
    return int((1.055 * c ** (1.0 / 2.4) - 0.055) * 255 + 0.5) if c > 0.0031308 else int(12.92 * c * 255 + 0.5)


def png(width, height, rows):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"".join(rows), 9)) + chunk(b"IEND", b""))


def png_shader(w, h, fn):
    """`fn(u, v)` is linear RGB. Rows use the Up filter so a soft gradient (the tank getting deep) packs smaller."""
    prev = bytes(w * 3)
    rows = []
    for y in range(h):
        v = y / (h - 1)
        raw = bytearray(w * 3)
        for x in range(w):
            r, g, b = fn(x / (w - 1), v)
            i = 3 * x
            raw[i], raw[i + 1], raw[i + 2] = _srgb(r), _srgb(g), _srgb(b)
        if y == 0:
            rows.append(b"\x00" + bytes(raw))
        else:
            rows.append(b"\x02" + bytes((raw[i] - prev[i]) & 255 for i in range(w * 3)))
        prev = bytes(raw)
    return png(w, h, rows)


def hex_rgb(h): return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def gradient_png(stops, height=256, width=4):
    """A top-to-bottom gradient through `stops` [(position 0..1, "#rrggbb")] as PNG bytes. The stops are already
    sRGB hex, written through unchanged (this is the backdrop, not a linear material colour)."""
    rows = []
    for y in range(height):
        t = y / (height - 1)
        i = max(k for k in range(len(stops) - 1) if stops[k][0] <= t)
        (t0, c0), (t1, c1) = (stops[i][0], hex_rgb(stops[i][1])), (stops[i + 1][0], hex_rgb(stops[i + 1][1]))
        s = (t - t0) / (t1 - t0)
        rows.append(b"\x00" + bytes(round(c0[k] + (c1[k] - c0[k]) * s) for k in range(3)) * width)
    return png(width, height, rows)


def sand_tex(u, v):
    """v = 0 is the shallow sand by the glass, v = 1 is the deep end. Grain, grit and a few pebbles.
    The shallow end is damp sand, dark enough that a bright TV light does not wash the depth out."""
    depth = smooth(v ** 0.85)
    grain = fbm(u, v, 11, cells=16)
    fine = fbm(u, v, 19, octaves=3, cells=36)
    pebble = fbm(u, v, 23, octaves=3, cells=7)
    color = mix((0.50, 0.42, 0.26), (0.04, 0.11, 0.18), depth)
    color = mix(color, (0.72, 0.62, 0.40), smooth((fine - 0.42) / 0.22) * 0.5 * (1 - depth))
    color = mix(color, (0.24, 0.16, 0.09), smooth((grain - 0.58) / 0.14) * 0.8 * (1 - 0.45 * depth))
    color = mix(color, (0.16, 0.15, 0.14), smooth((pebble - 0.64) / 0.10) * 0.85 * (1 - 0.35 * depth))
    return color


def soil_tex(u, v):
    n = stretch(fbm(u, v, 4, cells=12), 1.7)
    grit = fbm(u, v, 12, octaves=3, cells=30)
    clod = fbm(u, v, 8, octaves=3, cells=5)
    color = mix((0.30, 0.16, 0.07), (0.70, 0.48, 0.24), n)
    color = mix(color, (0.12, 0.07, 0.03), smooth((clod - 0.60) / 0.12) * 0.85)
    color = mix(color, (0.60, 0.52, 0.38), smooth((grit - 0.72) / 0.10) * 0.45)
    return mix(color, shade(color, 0.72), smooth((v - 0.78) / 0.18) * 0.35)


def turf_tex(u, v):
    n = stretch(fbm(u, v, 2, cells=12))
    patch = stretch(fbm(u, v, 14, octaves=3, cells=4), 1.8)
    blades = fbm(u, v, 18, octaves=2, cells=28)
    color = mix((0.04, 0.14, 0.04), (0.20, 0.46, 0.14), n)
    color = mix(color, (0.48, 0.34, 0.12), smooth((patch - 0.52) / 0.16) * 0.95)
    color = mix(color, (0.55, 0.74, 0.28), smooth((blades - 0.62) / 0.12) * 0.6)
    return mix(color, shade(color, 0.5), smooth((v - 0.82) / 0.15) * 0.55)


def rock_shader(algae):
    def shader(u, v):
        n = stretch(fbm(u, v, 3, octaves=5, cells=5, tile=True))
        # Thin cracks, where the noise folds through the middle. A power of the fold used to darken
        # the whole stone, because it is near zero almost everywhere.
        fold = abs(fbm(u, v, 9, octaves=4, cells=9, tile=True) * 2 - 1)
        crack = smooth((0.14 - fold) / 0.14)
        grain = fbm(u, v, 27, octaves=3, cells=16, tile=True)
        color = mix((0.14, 0.12, 0.10), (0.76, 0.66, 0.52), n)
        color = mix(color, (0.05, 0.045, 0.04), crack)
        color = mix(color, shade(color, 0.42), smooth((0.32 - grain) / 0.12) * 0.7)
        chip = fbm(u, v, 41, octaves=2, cells=20, tile=True)
        color = mix(color, (0.88, 0.82, 0.70), smooth((chip - 0.76) / 0.10) * 0.75)
        if algae:
            a = fbm(u, v, 15, octaves=3, cells=4, tile=True)
            color = mix(color, (0.06, 0.28, 0.14), smooth((a - 0.55) / 0.12) * 0.85)
        return color
    return shader


def moss_tex(u, v):
    n = stretch(fbm(u, v, 23, cells=5, tile=True))
    clump = stretch(fbm(u, v, 31, octaves=4, cells=3, tile=True), 1.8)
    fine = fbm(u, v, 47, octaves=2, cells=14, tile=True)
    color = mix((0.03, 0.10, 0.03), (0.16, 0.34, 0.10), n)
    color = mix(color, (0.28, 0.46, 0.16), smooth((clump - 0.48) / 0.20) * 0.85)
    return mix(color, (0.02, 0.06, 0.02), smooth((0.34 - fine) / 0.14) * 0.85)


def bark_tex(u, v):
    n = stretch(fbm(u, v, 5, octaves=5, cells=6, tile=True))
    wander = fbm(u, v, 21, octaves=2, cells=4, tile=True)
    groove = abs(math.sin((u * 8 + (wander - 0.5) * 0.9) * math.pi))
    color = mix((0.24, 0.13, 0.06), (0.66, 0.40, 0.18), n)
    color = mix(color, (0.05, 0.025, 0.012), smooth((0.16 - groove) / 0.16))
    fleck = fbm(u, v, 33, octaves=2, cells=6, tile=True)
    return mix(color, (0.78, 0.58, 0.34), smooth((fleck - 0.78) / 0.10) * 0.4)


def wood_tex(u, v):
    dx, dy = u - 0.5, v - 0.5
    r = math.sqrt(dx * dx + dy * dy) * 2
    wobble = fbm(u, v, 6, octaves=3, cells=4)
    ring = 0.5 + 0.5 * math.sin((r * 13 + wobble * 0.7) * math.pi)
    color = mix((0.72, 0.54, 0.32), (0.38, 0.22, 0.10), ring ** 0.75)
    color = mix(color, (0.55, 0.36, 0.18), smooth(1 - r * 5) * 0.45)
    return mix(color, (0.22, 0.12, 0.06), smooth((r - 0.84) / 0.12))


def frond_shader(base, tip, vein):
    def shader(u, v):
        edge = abs(u - 0.5) * 2
        n = fbm(u, v, 7, octaves=3, cells=5)
        body = mix(base, tip, smooth(v))
        body = mix(body, vein, (1 - smooth(edge * 1.25)) * 0.42)
        body = mix(body, shade(body, 0.58), smooth((edge - 0.4) / 0.45) * 0.9)
        body = mix(shade(body, 0.72), body, smooth(v * 1.3))
        return mix(body, shade(body, 0.82), (n - 0.5) * 0.28)
    return shader


def petal_tex(u, v):
    """A soft grey with a darker vein. The material colour multiplies it, so one picture serves pink, gold and white."""
    dx, dy = (u - 0.5) * 2, (v - 0.5) * 2
    r = min(math.sqrt(dx * dx + dy * dy), 1.0)
    n = fbm(u, v, 9, octaves=3, cells=4)
    vein = abs(math.sin((u * 6 + (n - 0.5) * 1.2) * math.pi))
    k = 0.70 + 0.26 * smooth(1 - r) * (0.65 + 0.35 * n) - 0.36 * smooth((0.22 - vein) / 0.22)
    k = 0.0 if k < 0.0 else 1.0 if k > 1.0 else k
    return (k, k, k)


# ---- glTF -------------------------------------------------------------------------------------------------

class Model:
    """Nodes of primitives, materials by colour or by a painted PNG, rotation clips, written as one .glb."""

    def __init__(self, name, generator):
        self.name, self.generator = name, generator
        self.blob, self.views, self.accessors = bytearray(), [], []
        self.materials, self.meshes, self.nodes, self.roots = [], [], [], []
        self.images, self.textures, self.samplers, self.animations = [], [], [], []
        self.triangles = 0

    def view(self, data, target=None):
        while len(self.blob) % 4: self.blob.append(0)
        self.views.append({"buffer": 0, "byteOffset": len(self.blob), "byteLength": len(data), **({"target": target} if target else {})})
        self.blob.extend(data)
        return len(self.views) - 1

    def accessor(self, values, kind, component=5126, target=None, bounds=False):
        width = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[kind]
        flat = [v for value in values for v in (value if width > 1 else (value,))]
        data = struct.pack("<%d%s" % (len(flat), {5126: "f", 5123: "H"}[component]), *flat)
        entry = {"bufferView": self.view(data, target), "componentType": component, "count": len(values), "type": kind}
        if bounds:
            entry["min"] = [min(v[i] for v in values) for i in range(width)] if width > 1 else [min(values)]
            entry["max"] = [max(v[i] for v in values) for i in range(width)] if width > 1 else [max(values)]
        self.accessors.append(entry)
        return len(self.accessors) - 1

    def sampler(self, wrap):
        # 9729 is linear with no mipmaps (the PNG has none). 10497 repeats, 33071 clamps. A floor is one picture
        # of the whole bed, so it clamps; bark and rock repeat.
        mode = 10497 if wrap == "repeat" else 33071
        for i, s in enumerate(self.samplers):
            if s["wrapS"] == mode and s["wrapT"] == mode: return i
        self.samplers.append({"magFilter": 9729, "minFilter": 9729, "wrapS": mode, "wrapT": mode})
        return len(self.samplers) - 1

    def material(self, name, rgb, double=False, roughness=0.9):
        self.materials.append({"name": name, **({"doubleSided": True} if double else {}),
                               "pbrMetallicRoughness": {"baseColorFactor": [*rgb, 1], "metallicFactor": 0, "roughnessFactor": roughness}})
        return len(self.materials) - 1

    def picture(self, name, size, shader, wrap="clamp", double=False, roughness=0.85, tint=(1.0, 1.0, 1.0)):
        """A painted base colour. `size` is power-of-two. `tint` multiplies the texture, for a second shade of
        the same picture (a paler stone, a weed deeper in the tank) without a second image."""
        w, h = size
        if w & (w - 1) or h & (h - 1):
            raise ValueError("%s is %dx%d; textures are power-of-two so a stick can repeat them" % (name, w, h))
        image = png_shader(w, h, shader)
        self.images.append({"bufferView": self.view(image), "mimeType": "image/png"})
        self.textures.append({"source": len(self.images) - 1, "sampler": self.sampler(wrap)})
        self.materials.append({"name": name, **({"doubleSided": True} if double else {}), "pbrMetallicRoughness": {
            "baseColorFactor": [tint[0], tint[1], tint[2], 1], "baseColorTexture": {"index": len(self.textures) - 1},
            "metallicFactor": 0, "roughnessFactor": roughness}})
        return len(self.materials) - 1

    def tint(self, name, material, rgb, roughness=None):
        """The same picture as `material`, multiplied by `rgb`."""
        src = self.materials[material]
        pbr = {k: (dict(v) if isinstance(v, dict) else list(v) if isinstance(v, list) else v)
               for k, v in src["pbrMetallicRoughness"].items()}
        pbr["baseColorFactor"] = [rgb[0], rgb[1], rgb[2], 1.0]
        if roughness is not None: pbr["roughnessFactor"] = roughness
        entry = {"name": name, "pbrMetallicRoughness": pbr}
        if src.get("doubleSided"): entry["doubleSided"] = True
        self.materials.append(entry)
        return len(self.materials) - 1

    def _textured(self, index):
        mat = self.materials[index]
        return "baseColorTexture" in mat.get("pbrMetallicRoughness", {}) or "emissiveTexture" in mat

    def backdrop(self, stops, width, y_top, y_horizon, z, y_bottom=-1.0, y_max=None):
        """The quad behind everything: the gradient runs from `y_top` (the top of the camera's view there) down
        to `y_horizon` and holds its end colours beyond."""
        self.images.append({"bufferView": self.view(gradient_png(stops)), "mimeType": "image/png"})
        self.textures.append({"source": len(self.images) - 1, "sampler": self.sampler("clamp")})
        self.materials.append({"name": "backdrop", "emissiveFactor": [1, 1, 1], "emissiveTexture": {"index": len(self.textures) - 1},
                               "pbrMetallicRoughness": {"baseColorFactor": [0, 0, 0, 1], "metallicFactor": 0, "roughnessFactor": 1}})
        top = y_max if y_max is not None else y_top + 0.6
        p = Primitive(len(self.materials) - 1)
        p.add(([(-width / 2, y_bottom, z), (width / 2, y_bottom, z), (width / 2, top, z), (-width / 2, top, z)], [Z] * 4, [(0, 1, 2), (0, 2, 3)]))
        v = lambda y: (y_top - y) / (y_top - y_horizon)
        p.uvs = [(0.0, v(y_bottom)), (1.0, v(y_bottom)), (1.0, v(top)), (0.0, v(top))]
        return self.node("Backdrop", [p])

    def node(self, name, primitives, at=(0.0, 0.0, 0.0), parent=None):
        """A node with a mesh of `primitives` (empty ones are dropped; none at all makes a plain joint)."""
        entry = {"name": name, "translation": list(at)}
        prims = []
        for p in primitives:
            if not p.triangles: continue
            if self._textured(p.material) and not p.uvs:
                raise ValueError("%s has a textured material and a primitive with no TEXCOORD_0" % name)
            if len(p.positions) > 65535:
                raise ValueError("%s has %d vertices; plain glTF indexes them with 16 bits" % (name, len(p.positions)))
            attributes = {"POSITION": self.accessor(p.positions, "VEC3", target=34962, bounds=True), "NORMAL": self.accessor(p.normals, "VEC3", target=34962)}
            if p.uvs: attributes["TEXCOORD_0"] = self.accessor(p.uvs, "VEC2", target=34962)
            prims.append({"attributes": attributes, "indices": self.accessor([i for t in p.triangles for i in t], "SCALAR", 5123, target=34963), "material": p.material})
            self.triangles += len(p.triangles)
        if prims:
            self.meshes.append({"name": name.lower(), "primitives": prims})
            entry["mesh"] = len(self.meshes) - 1
        self.nodes.append(entry)
        index = len(self.nodes) - 1
        if parent is None: self.roots.append(index)
        else: self.nodes[parent].setdefault("children", []).append(index)
        return index

    def clip(self, name, times, rotations):
        """A clip of rotation keys by node index."""
        t = self.accessor(times, "SCALAR", bounds=True)
        samplers, channels = [], []
        for node, keys in rotations.items():
            samplers.append({"input": t, "output": self.accessor(keys, "VEC4"), "interpolation": "LINEAR"})
            channels.append({"sampler": len(samplers) - 1, "target": {"node": node, "path": "rotation"}})
        self.animations.append({"name": name, "samplers": samplers, "channels": channels})

    def write(self, path):
        root = {"name": self.name, "children": self.roots}
        gltf = {
            "asset": {"version": "2.0", "generator": self.generator, "copyright": "CC0 1.0, made for QRX"},
            "scene": 0, "scenes": [{"name": self.name, "nodes": [len(self.nodes)]}],
            "nodes": self.nodes + [root], "meshes": self.meshes, "materials": self.materials,
            "accessors": self.accessors, "bufferViews": self.views,
        }
        if self.animations: gltf["animations"] = self.animations
        if self.images:
            gltf.update(images=self.images, textures=self.textures, samplers=self.samplers)
        while len(self.blob) % 4: self.blob.append(0)
        gltf["buffers"] = [{"byteLength": len(self.blob)}]
        chunk = json.dumps(gltf, separators=(",", ":")).encode()
        while len(chunk) % 4: chunk += b" "
        glb = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(chunk) + 8 + len(self.blob))
        glb += struct.pack("<II", len(chunk), 0x4E4F534A) + chunk + struct.pack("<II", len(self.blob), 0x004E4942) + bytes(self.blob)
        open(path, "wb").write(glb)
        print("%s: %d bytes, %d triangles, %d images" % (path.split("/")[-1], len(glb), self.triangles, len(self.images)))


TIMES = [i / 6 for i in range(37)]   # 6 s, the last key equal to the first


def sway(axis, degrees, phase):
    # sin(2 * pi) is not a clean zero, so the sample at 6 s is copied from the sample at 0.
    keys = [quat(axis, degrees * math.sin(2 * math.pi * t / 6 + phase)) for t in TIMES]
    keys[-1] = keys[0]
    return keys


def clump(model, name, material, rng, at, leaves, height, width, lean=(0.15, 0.45), segments=4):
    # The draws stay in this order (angle, length, lean, curl) so a habitat that built its plants before the
    # textures still gets those shapes.
    p = Primitive(material)
    for i in range(leaves):
        add_uv(p, blade, 360 * i / leaves + rng.uniform(-20, 20), height * rng.uniform(0.6, 1.0), width,
               rng.uniform(*lean), segments, curl=rng.uniform(-0.12, 0.12))
    return model.node(name, [p], at)


def stones(materials, rng, spots, sizes, floor, scale=1):
    """Half-buried pebbles. The draws stay in this order too: radius, which material, then the two squashes."""
    prims = {m: Primitive(m) for m in materials}
    for x, z in spots:
        r = rng.uniform(*sizes)
        prim = prims[rng.choice(materials)]
        add_uv(prim, ellipsoid, x, floor(x, z), z, r, r * rng.uniform(0.45, 0.7), r * rng.uniform(0.7, 1.2), 8, 5, scale=scale)
    return list(prims.values())


def rock_on(prim, x, z, rx, ry, rz, floor, scale=2, sink=0.45):
    """A stone sitting in the floor, `sink` of its height below the surface."""
    add_uv(prim, ellipsoid, x, floor(x, z) + ry * (1 - sink), z, rx, ry, rz, 10, 6, scale=scale)


# ---- the tank ---------------------------------------------------------------------------------------------
# Camera (0, 0.48, 1.30) looking level, 40 degrees: at the backdrop (z = -0.7) it sees x +-1.29, y -0.25 to 1.21.
# Creatures swim in x +-0.72, y 0.12 to 0.84, z -0.45 to 0.10, so the bed stays under y = 0.10 inside that box.
SWIM = (-0.72, 0.72, -0.45, 0.10)


def tank(out):
    print("tank: painting")
    m, rng = Model("HabitatTank", "QRX.pack scripts/habitats.py"), random.Random(11)
    # Eleven pebbles were scattered before the weeds were shaped. Scatter them the same way and the weeds match.
    spots = [(rng.uniform(-1.3, 1.3), rng.uniform(-0.6, 0.0)) for _ in range(11)]

    def floor(x, z):
        depth = smooth((-0.05 - z) / 0.85)   # 0 by the glass, 1 toward the back
        ripples = 0.016 * math.sin(3.1 * x + 1.0) * math.cos(4.3 * z) + 0.010 * math.sin(7.0 * x - 2.0 * z)
        return ripples - 0.08 * depth

    sand = m.picture("sand", (512, 256), sand_tex, roughness=0.95)
    rock = m.picture("stone", (256, 256), rock_shader(True), wrap="repeat", roughness=0.8)
    rock_far = m.tint("stone-deep", rock, (0.62, 0.78, 0.86))
    kelp = m.picture("kelp", (128, 256), frond_shader((0.05, 0.24, 0.16), (0.20, 0.55, 0.34), (0.45, 0.72, 0.40)), double=True, roughness=0.75)
    weed = m.tint("weed", kelp, (1.06, 1.10, 0.90))
    kelp_far = m.tint("kelp-deep", kelp, (0.58, 0.78, 0.86))
    m.backdrop([(0, "#2AA7BF"), (0.3, "#0E6A8C"), (0.7, "#073553"), (1, "#04121F")], 3.6, 1.21, -0.02, -0.7)

    bed = Primitive(sand)
    # The camera sees the floor from about z = 0.05 (the bottom of the frame) back to the backdrop.
    # That span is the whole sand picture: pale at the glass, deep at the back. The nearer sand clamps.
    add_uv(bed, heightfield, -2.2, 2.2, -0.7, 1.4, 40, 18, floor, uv_at=uv_floor(-2.2, 2.2, 0.05, -0.7))
    # Both entries are the same picture: the old scatter still picks between two materials, and the draws that
    # follow (the weeds) stay put. The blue tint is only for the reef, which is actually deep.
    near = stones([rock, rock], rng, spots, (0.03, 0.07), floor, scale=1)
    sides, reef, low = Primitive(rock), Primitive(rock_far), Primitive(rock)
    for x, z, rx, ry, rz in ((1.15, -0.15, 0.18, 0.10, 0.14), (-1.22, -0.28, 0.20, 0.11, 0.15),
                             (1.28, -0.58, 0.14, 0.08, 0.11), (-1.08, 0.22, 0.16, 0.08, 0.12),
                             (0.98, 0.40, 0.13, 0.07, 0.10)):
        rock_on(sides, x, z, rx, ry, rz, floor)
    # Each stone stays in front of the backdrop (z = -0.7) and behind the swimmers (z <= -0.45).
    for x, z, rx, ry, rz in ((-0.22, -0.575, 0.20, 0.15, 0.10), (0.28, -0.565, 0.14, 0.12, 0.085),
                             (-0.55, -0.570, 0.13, 0.11, 0.080), (0.58, -0.580, 0.12, 0.10, 0.075),
                             (0.02, -0.545, 0.09, 0.08, 0.065)):
        rock_on(reef, x, z, rx, ry, rz, floor, sink=0.35)
    # Larger stones inside the swim box, buried so a swimmer still has the water above y = 0.10.
    for x, z, rx, ry, rz in ((-0.38, -0.28, 0.12, 0.040, 0.09), (0.22, -0.16, 0.10, 0.034, 0.075),
                             (0.48, -0.34, 0.09, 0.030, 0.07), (-0.12, 0.00, 0.08, 0.026, 0.06)):
        rock_on(low, x, z, rx, ry, rz, floor, sink=0.65)
    for x, y, z in reef.positions:
        if z < -0.69:
            raise SystemExit("reef sits behind the backdrop at z=%.3f" % z)
    keep_clear([bed, sides, reef, low] + near, SWIM, 0.10, "tank bed")
    m.node("Sand", [bed, sides, reef, low] + near)

    plants = [("WeedA", weed, (-0.95, -0.30), 9, 0.55, 0.05), ("WeedB", kelp, (0.92, -0.42), 10, 0.72, 0.06),
              ("WeedC", weed, (0.28, -0.58), 7, 0.24, 0.035), ("WeedD", kelp, (-0.42, -0.62), 7, 0.3, 0.04),
              ("WeedE", weed, (1.3, -0.62), 8, 0.62, 0.055), ("WeedF", kelp, (-1.32, -0.6), 8, 0.5, 0.05),
              ("WeedG", weed, (0.62, -0.2), 6, 0.16, 0.03),
              ("WeedH", kelp_far, (-0.15, -0.66), 9, 0.58, 0.055), ("WeedI", kelp_far, (0.72, -0.64), 8, 0.46, 0.05)]
    rotations = {}
    for i, (name, material, (x, z), leaves, height, width) in enumerate(plants):
        node = clump(m, name, material, rng, (x, floor(x, z), z), leaves, height, width, segments=5)
        rotations[node] = sway(Z if i % 2 == 0 else X, 3.5 if height > 0.4 else 5, i * 1.3)
    m.clip("idle", TIMES, rotations)
    m.write(f"{out}/models/habitat-tank.glb")


# ---- the terrarium ----------------------------------------------------------------------------------------
# Camera (0, 0.42, 1.25) looking at (0, 0.12, -0.30), 40 degrees: the floor fills the lower half of the view and
# the walkers keep to x +-0.75, z -0.80 to 0.10, so the log, the boulders and the deep moss stay around that patch.

def terrarium(out):
    print("terrarium: painting")
    m, rng = Model("HabitatTerrarium", "QRX.pack scripts/habitats.py"), random.Random(23)

    def floor(x, z):
        ridge = 0.16 * smooth((-0.9 - z) / 0.3) * (0.65 + 0.35 * math.sin(2.1 * x + 0.5) + 0.12 * math.sin(6.3 * x))
        return 0.012 * math.sin(5.0 * x + 0.4) * math.cos(6.0 * z) + 0.006 * math.sin(11.0 * x - 3.0 * z) + ridge

    pebbles = [(rng.uniform(-0.75, 0.75), rng.uniform(0.18, 0.6)) for _ in range(6)] + [(-0.95, -0.05), (0.98, -0.2), (-0.2, -0.95), (1.2, -0.62)]
    soil = m.picture("soil", (512, 256), soil_tex, roughness=0.98)
    moss = m.picture("moss", (256, 256), moss_tex, wrap="repeat", roughness=0.95)
    stone = m.picture("rock", (256, 256), rock_shader(False), wrap="repeat", roughness=0.82)
    stone_pale = m.tint("rock-pale", stone, (1.12, 1.08, 1.02))
    bark = m.picture("bark", (256, 256), bark_tex, wrap="repeat", roughness=0.9)
    wood = m.picture("wood", (128, 128), wood_tex, roughness=0.85)
    succulent = m.picture("succulent", (128, 256), frond_shader((0.16, 0.36, 0.20), (0.40, 0.60, 0.32), (0.55, 0.70, 0.38)), double=True, roughness=0.7)
    grass = m.picture("dry-grass", (128, 256), frond_shader((0.40, 0.38, 0.16), (0.62, 0.58, 0.26), (0.74, 0.68, 0.34)), double=True, roughness=0.9)
    m.backdrop([(0, "#2B1B14"), (0.45, "#7A4A2A"), (0.72, "#C98A4B"), (1, "#E2B470")], 4.8, 0.85, 0.1, -1.2)

    ground = Primitive(soil)
    add_uv(ground, heightfield, -2.2, 2.2, -1.2, 1.4, 40, 22, floor, uv_at=uv_floor(-2.2, 2.2, 1.4, -1.2))
    peb = stones([stone, stone_pale], rng, pebbles, (0.018, 0.04), floor, scale=1)
    extra = random.Random(24)
    more = [(extra.uniform(-1.7, 1.7), extra.uniform(-1.05, 0.9)) for _ in range(8)]
    peb += stones([stone, stone_pale], extra, more, (0.02, 0.045), floor, scale=1)
    boulders = Primitive(stone)
    for x, z, rx, ry, rz in ((1.12, -0.84, 0.30, 0.20, 0.22), (0.82, -0.90, 0.15, 0.10, 0.12), (-1.28, -0.20, 0.14, 0.09, 0.12)):
        rock_on(boulders, x, z, rx, ry, rz, floor, sink=0.4)
    path = [(-1.3, 0.06, -0.8), (-1.05, 0.065, -0.66), (-0.8, 0.06, -0.5)]
    radii = [0.06, 0.065, 0.058]
    log = Primitive(bark)
    add_uv(log, tube, path, radii, 12, caps=False, uv_scale=(2, 6))
    ends = Primitive(wood)
    add_uv(ends, disc, path[0], sub(path[0], path[1]), radii[0] * 0.98, 20)
    add_uv(ends, disc, path[-1], sub(path[-1], path[-2]), radii[-1] * 0.98, 20)
    moss_prim = Primitive(moss)
    for x, z, rx, rz in ((-0.95, -1.08, 0.24, 0.15), (-0.15, -1.12, 0.28, 0.16), (0.6, -1.02, 0.22, 0.14),
                         (1.2, -0.92, 0.16, 0.11), (-1.4, -0.4, 0.18, 0.12), (-1.15, 0.2, 0.14, 0.10),
                         (1.45, -0.3, 0.16, 0.11), (1.2, 0.35, 0.12, 0.09), (-1.05, 0.55, 0.12, 0.08),
                         (0.85, 0.6, 0.11, 0.08), (-0.62, -0.2, 0.08, 0.06), (0.55, -0.6, 0.07, 0.05)):
        # Buried a little, so the rim is in the soil and the top reads as a cushion.
        add_uv(moss_prim, ellipsoid, x, floor(x, z) - 0.004, z, rx, 0.022, rz, 8, 4, proj="top")
    for x, z, rx, rz in ((-1.18, -0.75, 0.055, 0.04), (-1.02, -0.64, 0.06, 0.045), (-0.88, -0.55, 0.05, 0.04)):
        add_uv(moss_prim, ellipsoid, x, 0.108, z, rx, 0.020, rz, 8, 4, proj="top")
    add_uv(moss_prim, ellipsoid, 1.12, floor(1.12, -0.84) + 0.14, -0.84, 0.12, 0.028, 0.09, 8, 4, proj="top")
    m.node("Ground", [ground, boulders, log, ends, moss_prim] + peb)

    rotations, n = {}, 0
    for name, (x, z), leaves, height, width in (("SucculentA", (-0.45, -0.98), 11, 0.17, 0.07), ("SucculentB", (0.92, -0.42), 12, 0.2, 0.08),
                                                ("SucculentC", (-0.9, -0.33), 10, 0.13, 0.06), ("SucculentD", (0.3, -1.0), 9, 0.12, 0.055),
                                                ("SucculentE", (-0.52, 0.34), 9, 0.07, 0.035), ("SucculentF", (0.6, 0.46), 8, 0.06, 0.03)):
        node = clump(m, name, succulent, rng, (x, floor(x, z), z), leaves, height, width, (0.5, 0.9), 3)
        rotations[node] = sway(Z, 1.5, n); n += 1.1
    for i, (x, z) in enumerate(((-1.15, -0.95), (-0.75, -1.0), (0.05, -0.95), (0.55, -0.9), (1.4, -0.85), (-1.5, -0.6), (1.35, -0.3))):
        node = clump(m, f"Grass{i + 1}", grass, rng, (x, floor(x, z), z), 7, rng.uniform(0.2, 0.34), 0.016, (0.2, 0.6), 3)
        rotations[node] = sway(Z if i % 2 else X, 6, i * 0.9)
    m.clip("idle", TIMES, rotations)
    m.write(f"{out}/models/habitat-terrarium.glb")


# ---- the aviary -------------------------------------------------------------------------------------------
# Camera (0, 0.62, 1.35) looking level, 45 degrees: at the backdrop (z = -1.0) it sees x +-1.73, y -0.35 to 1.59.
# Creatures perch in x +-0.80, y 0.22 to 1.05, z -0.55 to 0.15. The right-hand branch still ends at
# (0.46, 0.885, -0.2); a left perch and a back perch sit in that same volume.

def _limb(prim, path, radii, sides=8, around=2, per_metre=7):
    # Caps close the cut. An open ring reads as a split end.
    add_uv(prim, tube, path, radii, sides, caps=True, uv_scale=(around, per_metre))


def _pad(prim, tip, rx=0.022, rz=0.016):
    """A small crown on the tip. The tip point the scene perches on does not move."""
    add_uv(prim, ellipsoid, tip[0], tip[1] + 0.012, tip[2], rx, 0.008, rz, 8, 4, proj="top")


def _foliage(model, name, material, rng, spots, origin, rotations, degrees, phase):
    leaves = Primitive(material)
    ox, oy, oz = origin
    for x, y, z in spots:
        for _ in range(2):
            add_uv(leaves, blade, rng.uniform(0, 360), rng.uniform(0.07, 0.115), 0.05, rng.uniform(0.6, 1.2), 3,
                   (x - ox, y - oy, z - oz))
    rotations[model.node(name, [leaves], origin)] = sway(Z, degrees, phase)


def aviary(out):
    print("aviary: painting")
    m, rng = Model("HabitatAviary", "QRX.pack scripts/habitats.py"), random.Random(31)

    def floor(x, z):
        return 0.03 * math.sin(1.3 * x + 0.7) + 0.015 * math.sin(3.7 * x - 1.9 * z) + 0.05 * smooth((-0.6 - z) / 0.4)

    turf = m.picture("turf", (512, 256), turf_tex, roughness=0.98)
    grass = m.picture("grass", (128, 256), frond_shader((0.08, 0.28, 0.14), (0.30, 0.56, 0.24), (0.58, 0.72, 0.32)), double=True, roughness=0.85)
    grass2 = m.tint("grass-light", grass, (1.10, 1.08, 0.96))
    bark = m.picture("bark", (256, 256), bark_tex, wrap="repeat", roughness=0.9)
    leafy = m.picture("leaf", (128, 256), frond_shader((0.08, 0.26, 0.12), (0.24, 0.50, 0.22), (0.62, 0.74, 0.34)), double=True, roughness=0.8)
    petal = m.picture("petal", (128, 128), petal_tex, roughness=0.7)
    petals = [m.tint("petal-pink", petal, (0.96, 0.62, 0.75)), m.tint("petal-gold", petal, (0.98, 0.80, 0.36)),
              m.tint("petal-white", petal, (0.95, 0.93, 0.90))]
    m.backdrop([(0, "#141B45"), (0.45, "#4A4A93"), (0.78, "#C97C8A"), (1, "#F4B183")], 4.6, 1.59, 0.06, -1.0)
    meadow = Primitive(turf)
    # Same idea as the tank: the picture spans the floor the camera sees, bright at the near edge.
    add_uv(meadow, heightfield, -2.4, 2.4, -1.0, 1.5, 36, 16, floor, uv_at=uv_floor(-2.4, 2.4, 0.10, -1.0))
    m.node("Meadow", [meadow])

    rotations = {}
    rows = [(-0.82, 0.14), (-0.52, 0.12), (-0.22, 0.12), (0.1, 0.14)]
    for r, (zc, spread) in enumerate(rows):
        a, b, heads, stems = Primitive(grass), Primitive(grass2), {p: Primitive(p) for p in petals}, Primitive(grass)
        for k in range(18):
            x, z = -1.75 + 3.5 * (k + rng.uniform(0.1, 0.9)) / 18, rng.uniform(-spread, spread)
            y = floor(x, zc + z)
            for _ in range(5):
                target = a if rng.random() < 0.6 else b
                add_uv(target, blade, rng.uniform(0, 360), rng.uniform(0.08, 0.2), 0.013, rng.uniform(0.2, 0.7), 3,
                       (x + rng.uniform(-0.05, 0.05), y, z + rng.uniform(-0.03, 0.03)))
        for _ in range(3):
            x, z, h = rng.uniform(-1.5, 1.5), rng.uniform(-spread, spread), rng.uniform(0.14, 0.24)
            y = floor(x, zc + z)
            add_uv(stems, tube, [(x, y, z), (x + 0.01, y + h, z)], [0.003, 0.0025], 4, caps=False, uv_scale=(1, 12))
            add_uv(heads[rng.choice(petals)], ellipsoid, x + 0.01, y + h, z, 0.022, 0.013, 0.022, 7, 4, scale=1)
        rotations[m.node(f"Grass{r + 1}", [a, b, stems] + list(heads.values()), (0.0, 0.0, zc))] = sway(X, 2.5, r * 1.4)

    right = [(2.1, 0.74, -0.32), (1.6, 0.79, -0.3), (1.15, 0.84, -0.26), (0.8, 0.885, -0.22), (0.6, 0.895, -0.2), (0.46, 0.885, -0.2)]
    left = [(-2.15, 0.40, -0.42), (-1.55, 0.46, -0.34), (-1.0, 0.52, -0.26), (-0.62, 0.50, -0.20), (-0.32, 0.49, -0.16)]
    back = [(0.15, 1.42, -0.98), (0.05, 1.18, -0.72), (0.12, 1.00, -0.52), (-0.02, 0.90, -0.40)]
    for name, path, radii, twig, twig_r in (
            ("Branch", right, [0.05, 0.043, 0.034, 0.026, 0.020, 0.016],
             [(1.15, 0.84, -0.26), (1.06, 0.97, -0.28), (0.93, 1.08, -0.3)], [0.016, 0.011, 0.007]),
            ("BranchLeft", left, [0.042, 0.034, 0.026, 0.020, 0.016],
             [(-1.0, 0.52, -0.26), (-0.92, 0.66, -0.30), (-0.84, 0.78, -0.32)], [0.014, 0.009, 0.007]),
            ("BranchBack", back, [0.036, 0.028, 0.022, 0.016],
             [(0.12, 1.00, -0.52), (0.22, 1.08, -0.48), (0.30, 1.16, -0.46)], [0.012, 0.008, 0.006])):
        limb = Primitive(bark)
        _limb(limb, path, radii)
        _limb(limb, twig, twig_r, sides=6, around=1, per_metre=8)
        _pad(limb, path[-1])
        m.node(name, [limb])
    for tip in (right[-1], left[-1], back[-1]):
        if not (abs(tip[0]) <= 0.80 and 0.22 <= tip[1] <= 1.05 and -0.55 <= tip[2] <= 0.15):
            raise SystemExit("a perch at %s is outside the air bounds" % (tip,))

    _foliage(m, "Leaves", leafy, rng,
             ((0.93, 1.08, -0.3), (1.0, 1.03, -0.29), (1.08, 0.95, -0.28), (1.36, 0.82, -0.28),
              (1.5, 0.8, -0.3), (0.86, 0.89, -0.23), (0.68, 0.9, -0.2), (1.25, 0.84, -0.27)),
             (1.15, 0.84, -0.26), rotations, 1.6, 0.5)
    leaves = random.Random(32)
    # Bases sit on the wood. The earlier spots hovered a few centimetres off the branch.
    _foliage(m, "LeavesLeft", leafy, leaves,
             ((-0.84, 0.792, -0.32), (-0.92, 0.674, -0.30), (-1.00, 0.538, -0.26),
              (-0.55, 0.518, -0.19), (-0.42, 0.512, -0.175)),
             (-0.9, 0.62, -0.28), rotations, 2.0, 1.2)
    _foliage(m, "LeavesBack", leafy, leaves,
             ((0.30, 1.172, -0.46), (0.22, 1.094, -0.48), (0.12, 1.022, -0.52), (-0.02, 0.918, -0.40)),
             (0.12, 1.04, -0.48), rotations, 1.4, 2.1)
    m.clip("idle", TIMES, rotations)
    m.write(f"{out}/models/habitat-aviary.glb")


if __name__ == "__main__":
    out = sys.argv[1]
    tank(out); terrarium(out); aviary(out)
