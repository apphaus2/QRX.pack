"""make.py's clips step, in Blender: the same clips for every quadruped, keyframed on the named bones and scaled by
the creature's own legs, then the glTF with its skin and clips.

    blender -b -P blender_clips.py -- <rig.blend> <rigged.glb> <idle,walk,shake,...> <id>

Every clip is in place (Root is never keyed) and every cue starts and ends in the rest pose. Turns are written about
the creature's own axes (x left, up, forward) so they read the same for every skeleton. 30 frames a second."""
import json, math, os, sys
import bpy
from mathutils import Euler, Quaternion, Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blender_common as common      # noqa: E402

rig_blend, out_glb, wanted, creature = common.args()
wanted = [c for c in wanted.split(",") if c]
bpy.ops.wm.open_mainfile(filepath=rig_blend)
rig = bpy.data.objects["Skeleton"]
mesh = bpy.data.objects["Mesh"]
FPS = 30
scene = bpy.context.scene
scene.render.fps = FPS
bones = rig.pose.bones
for b in bones: b.rotation_mode = "QUATERNION"
rest = {b.name: b.bone.matrix_local.copy() for b in bones}
# Blender axes: the animal's left +X, up +Z, forward -Y. A pitch about +X sends the nose down and a hanging leg back.
LEFT, UP, BACK = Vector((1, 0, 0)), Vector((0, 0, 1)), Vector((0, 1, 0))
leg = max(rest["LegFL"].translation.z, 0.02)               # the shoulder's height: every move is scaled by it
hips = rest["Body"].translation.copy()


def pose(name, axis=None, degrees=0.0, offset=None, pivot=None):
    """Turn bone `name` by `degrees` about a rest-space axis (and move it by a rest-space offset), keyed by the caller."""
    b = bones[name]
    R = rest[name].to_quaternion()
    q = Quaternion(axis, math.radians(degrees)) if axis is not None and degrees else Quaternion()
    b.rotation_quaternion = R.inverted() @ q @ R
    move = Vector(offset) if offset is not None else Vector()
    if pivot is not None and degrees:                       # turning about a point other than the bone's head
        head = rest[name].translation
        move += (q @ (head - pivot) + pivot) - head
    b.location = R.inverted() @ move


SWELLS = False     # a clip that swells a bone (puff, sunfrill) keys scale too; no other clip carries a scale track


def key(frame):
    for b in bones:
        if b.name == "Root": continue
        b.keyframe_insert("rotation_quaternion", frame=frame); b.keyframe_insert("location", frame=frame)
        if SWELLS: b.keyframe_insert("scale", frame=frame)


def rest_pose():
    for b in bones: b.rotation_quaternion = Quaternion(); b.location = Vector(); b.scale = Vector((1, 1, 1))


def ease(t): return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, t)))


def tail(frame, amplitude, speed=2.0, phase=0.0):
    for i, name in enumerate(("Tail1", "Tail2", "Tail3")):
        if name in bones: pose(name, UP, amplitude * (0.5 + 0.35 * i) * math.sin(speed * math.tau * frame / FPS - 0.6 * i + phase))


def clip(name, seconds, body, loop=False):
    frames = round(seconds * FPS)
    action = bpy.data.actions.new(name); action.use_fake_user = True
    rig.animation_data_create(); rig.animation_data.action = action
    for f in range(0, frames + 1, 2 if frames > 40 else 1):
        rest_pose()
        if 0 < f < frames: body(f, f / frames)
        key(f)
    if frames % 2 and frames > 40: rest_pose(); key(frames)
    rig.animation_data.action = None
    return action


def legs_swing(f, t, stride=24.0, lift=35.0):
    for name, phase in (("FL", 0.0), ("BR", 0.0), ("FR", math.pi), ("BL", math.pi)):
        s = math.sin(math.tau * t + phase)
        pose("Leg" + name, LEFT, -stride * s)
        pose("Shin" + name, LEFT, lift * max(0.0, math.cos(math.tau * t + phase)) * (1 if name[0] == "F" else -1))


CLIPS = {}


def idle(f, t):
    pose("Body", offset=(0, 0, 0.012 * leg * math.sin(math.tau * 2 * t)))
    pose("Neck", UP, 10 * math.sin(math.tau * t))
    pose("Head", LEFT, 4 * math.sin(math.tau * 2 * t))
    for e in ("EarL", "EarR"): pose(e, LEFT, 6 * math.sin(math.tau * 3 * t))
    tail(f, 12, 1.0)
CLIPS["idle"] = (3.0, idle, True)


def walk(f, t):
    legs_swing(f, t)
    pose("Body", offset=(0, 0, 0.03 * leg * abs(math.sin(math.tau * t))))
    pose("Head", LEFT, 4 * math.sin(2 * math.tau * t))
    tail(f, 10, 1 / 0.8)
CLIPS["walk"] = (0.8, walk, True)


def shake(f, t):
    env = math.sin(math.pi * t)
    for i, name in enumerate(("Head", "Neck", "Chest", "Body", "Tail1", "Tail2")):
        pose(name, BACK, 22 * env * math.sin(math.tau * 5 * t * 1.2 - 0.9 * i) * (0.5 if name == "Body" else 1))
CLIPS["shake"] = (1.2, shake, False)


def roll(f, t):
    a = 360 * ease((t - 0.15) / 0.7)
    down = -0.45 * leg * math.sin(math.pi * ease((t - 0.1) / 0.8))
    centre = (rest["Body"].translation + rest["Chest"].translation) / 2
    pose("Body", BACK, a, offset=(0, 0, down), pivot=centre)
    tuck = 60 * math.sin(math.pi * ease((t - 0.05) / 0.9))
    for name in ("FL", "FR"): pose("Leg" + name, LEFT, -tuck); pose("Shin" + name, LEFT, tuck)
    for name in ("BL", "BR"): pose("Leg" + name, LEFT, tuck); pose("Shin" + name, LEFT, -tuck * 0.8)
CLIPS["roll"] = (2.0, roll, False)


def bow(f, t):
    e = math.sin(math.pi * ease(t)) if t < 0.5 else math.sin(math.pi * ease(t))
    pose("Body", LEFT, 18 * e, offset=(0, 0, -0.1 * leg * e), pivot=rest["Body"].translation)
    for name in ("FL", "FR"): pose("Leg" + name, LEFT, -55 * e); pose("Shin" + name, LEFT, 25 * e)
    for name in ("BL", "BR"): pose("Leg" + name, LEFT, -18 * e)
    pose("Head", LEFT, -20 * e)
    tail(f, 30 * e, 3.0)
CLIPS["bow"] = (1.6, bow, False)


def jump(f, t):
    crouch = math.sin(math.pi * min(1.0, t / 0.3)) if t < 0.3 else 0.0
    land = math.sin(math.pi * (t - 0.75) / 0.25) if t > 0.75 else 0.0
    air = math.sin(math.pi * (t - 0.25) / 0.5) if 0.25 < t < 0.75 else 0.0
    up = 0.6 * leg * air - 0.2 * leg * (crouch + land)
    pose("Body", offset=(0, 0, up))
    tuck = 50 * air + 30 * (crouch + land)
    for name in ("FL", "FR"): pose("Leg" + name, LEFT, -tuck * 0.6); pose("Shin" + name, LEFT, tuck)
    for name in ("BL", "BR"): pose("Leg" + name, LEFT, tuck * 0.6); pose("Shin" + name, LEFT, -tuck)
CLIPS["jump"] = (1.0, jump, False)


def spin(f, t):
    pose("Body", UP, 360 * ease(t), pivot=Vector((0, (rest["Body"].translation.y + rest["Chest"].translation.y) / 2, 0)))
    legs_swing(f, (3 * t) % 1, 15, 25)
    pose("Neck", UP, -25 * math.sin(math.pi * t))
    tail(f, 25, 2.5)
CLIPS["spin"] = (1.5, spin, False)


def dead(f, t):
    e = ease(t / 0.25) if t < 0.5 else ease((1 - t) / 0.25)
    centre = (rest["Body"].translation + rest["Chest"].translation) / 2
    pose("Body", BACK, 90 * e, offset=(0, 0, -0.55 * leg * e), pivot=centre)
    for name in ("FL", "FR", "BL", "BR"): pose("Leg" + name, LEFT, 10 * e * (1 if name[0] == "B" else -1))
CLIPS["dead"] = (3.0, dead, False)


def wave(f, t):
    e = math.sin(math.pi * ease(t))
    pose("LegFL", LEFT, -75 * e)
    pose("ShinFL", LEFT, 30 * e + 25 * e * math.sin(math.tau * 3 * t))
    pose("Body", BACK, -6 * e, pivot=rest["Body"].translation)
    tail(f, 20 * e, 2.0)
CLIPS["wave"] = (1.6, wave, False)


def dance(f, t):
    e = math.sin(math.pi * t)
    pose("Body", UP, 15 * e * math.sin(math.tau * 2 * t), offset=(0, 0, 0.12 * leg * e * abs(math.sin(math.tau * 4 * t))))
    legs_swing(f, (2 * t) % 1, 14 * e, 30 * e)
    pose("Head", BACK, 12 * e * math.sin(math.tau * 4 * t))
    tail(f, 25 * e, 4.0)
CLIPS["dance"] = (2.0, dance, False)

# ---- Bodies that are not a dog's (2026-11-17): lizards and a newt, frogs, turtles and a hopper, and the cues only they
# have. Everything from here down is new clips and their helpers. A creature not named in STYLES plays the clips above
# as they were; one that is plays its body's own (OWN) where there is one, else the one above.
STYLES = {"sprawl": ("banded-gecko", "rooftop-gecko", "bark-skink", "ember-skink", "sand-lizard", "sunfrill-lizard", "marsh-newt"),
          "frog": ("glowspot-frog", "pond-frog"), "turtle": ("jade-turtle", "pond-turtle"), "hopper": ("longfoot-jerboa",)}
STYLE = next((style for style, ids in STYLES.items() if creature in ids), None)
SWELLING = ("puff", "sunfrill")                             # the clips that key scale
LEGS4 = ("FL", "FR", "BL", "BR")
TAILS = ("Tail1", "Tail2", "Tail3")
SIDE = {"L": 1, "R": -1}
hip, chest = rest["Body"].translation.copy(), rest["Chest"].translation.copy()
spine = max((chest - hip).length, 0.01)
belly = max(rest["ShinFL"].translation.z / 0.8, 0.004)      # blender_rig.py puts the elbow at 0.8 of the belly's height
if STYLE == "frog": belly *= 0.25; spine *= 0.65            # a frog sits on its belly: there is little under it to sink into; its hops are low
centre = (hip + chest) / 2
ground = Vector((0, centre.y, 0))
_points = [mesh.matrix_world @ v.co for v in mesh.data.vertices]
TOP, WIDE = max(p.z for p in _points), max(abs(p.x) for p in _points)
LIFT_SIDE = max(0.0, 0.8 * WIDE - centre.z)                 # what a low, wide body rises to turn onto its side
LIFT_BACK = max(0.0, TOP - 2 * centre.z)                    # and to lie on its back


def rot(axis, degrees): return Quaternion(axis, math.radians(degrees))


def turn(name, q=None, offset=None, pivot=None, scale=None):
    """pose() with any rotation `q` (rest-space axes) and a scale along the bone's own axes; `pivot` stays where it is."""
    b = bones[name]
    R = rest[name].to_quaternion()
    q = q if q is not None else Quaternion()
    b.rotation_quaternion = R.inverted() @ q @ R
    if scale is not None: b.scale = Vector(scale)
    move = Vector(offset) if offset is not None else Vector()
    if pivot is not None:
        arm = Vector(pivot) - rest[name].translation
        local = R.inverted() @ arm
        if scale is not None: local = Vector((local.x * scale[0], local.y * scale[1], local.z * scale[2]))
        move += arm - q @ (R @ local)
    b.location = R.inverted() @ move


def unswell(child, ancestor, scale, share=1.0):
    """The scale that keeps `child` its own size (share 1) while `ancestor` is scaled; the bones between are not."""
    A, B = rest[ancestor].to_3x3().inverted(), rest[child].to_3x3()
    out = []
    for k in range(3):
        d = A @ B.col[k]
        out.append(Vector((d.x * scale[0], d.y * scale[1], d.z * scale[2])).length ** -share)
    return out


def sway(t, amplitude, cycles=1, phase=0.0, loop=False):
    """The tail, side to side, a wave running down it a whole number of times in the clip. In a loop every bone has
    to pass through the rest pose where the clip starts and ends, which the second term sees to."""
    for i, name in enumerate(TAILS):
        lag = 0.7 * i - phase
        wave = math.sin(math.tau * cycles * t - lag) + (math.sin(lag) * math.cos(2 * math.tau * cycles * t) if loop else 0.0)
        pose(name, UP, amplitude * (0.5 + 0.35 * i) * wave)


def fade(t): return min(1.0, 8 * min(t, 1 - t))             # in a loop: what cannot be at rest at the seam is let go there


def pole(tag):
    """Where the knee or elbow of leg `tag` points when a straight leg has to bend."""
    side = SIDE[tag[1]]
    if STYLE in ("sprawl", "turtle"): return Vector((side, 0, 0.6))
    if STYLE == "frog": return Vector((side, -0.7 if tag[0] == "B" else 0.7, 0.3))
    return Vector((0, 1, 0)) if tag[0] == "F" else Vector((0, -1, 0))


def plant(tag, move=None):
    """After the body is posed: bend leg `tag` at its two joints so its ankle is back where it rests (plus `move`) and
    its foot is flat, as far as the leg reaches. This is what keeps feet on the ground under a body that dips."""
    bpy.context.view_layer.update()
    L, S, F = "Leg" + tag, "Shin" + tag, "Foot" + tag
    parent = bones[L].parent
    delta = parent.matrix @ rest[parent.name].inverted()
    P = delta.to_quaternion()
    top0, mid0, low0 = rest[L].translation, rest[S].translation, rest[F].translation
    top = delta @ top0
    reach = low0 + (Vector(move) if move is not None else Vector()) - top
    u0, v0 = mid0 - top0, low0 - mid0
    a, b = u0.length, v0.length
    if a < 1e-5 or b < 1e-5 or reach.length < 1e-6: return
    d = min(max(reach.length, abs(a - b) + 1e-5), a + b - 1e-6)
    n = u0.cross(v0)
    if n.length < 0.2 * a * b: n = pole(tag).cross(u0)      # a leg that rests straight: the knee goes to the pole
    if n.length < 1e-9: n = LEFT.copy()
    n.normalize()
    phi0 = math.atan2(n.dot(u0.cross(v0)), u0.dot(v0))
    phi = math.pi - math.acos(max(-1.0, min(1.0, (a * a + b * b - d * d) / (2 * a * b))))
    knee = Quaternion(n, phi - phi0)
    aim = (P @ (u0 + knee @ v0)).rotation_difference(reach)
    turn(L, P.inverted() @ aim @ P)
    turn(S, knee)
    turn(F, (aim @ P @ knee).inverted())


def spring(air, tags=LEGS4):
    """Legs in the air, a frog's way: the back ones trailing straight behind, the front ones reaching."""
    if STYLE == "frog":                                     # folded legs: the thigh swings down, the knee and the ankle open
        for tag in tags:
            if tag[0] == "B": pose("Leg" + tag, LEFT, 30 * air); pose("Shin" + tag, LEFT, -45 * air); pose("Foot" + tag, LEFT, 30 * air)
            else: pose("Leg" + tag, LEFT, -20 * air); pose("Shin" + tag, LEFT, -15 * air)
        return
    for tag in tags:
        if tag[0] == "B": pose("Leg" + tag, LEFT, 45 * air); pose("Shin" + tag, LEFT, -50 * air)
        else: pose("Leg" + tag, LEFT, -25 * air)


def tuck(air):
    """Legs in the air, the dog's way (what jump does)."""
    for tag in ("FL", "FR"): pose("Leg" + tag, LEFT, -0.6 * air); pose("Shin" + tag, LEFT, air)
    for tag in ("BL", "BR"): pose("Leg" + tag, LEFT, 0.6 * air); pose("Shin" + tag, LEFT, -air)


OWN = {}

# -- cues any four-legged body can do
def pushup(f, t):
    dip = 0.5 - 0.5 * math.cos(math.tau * 3 * t)            # three, each back up to the rest pose
    a = math.degrees(math.asin(min(0.7, 0.6 * belly * dip / spine)))
    pose("Body", LEFT, a, pivot=hip)                        # the chest goes down about the hips; the feet stay
    pose("Neck", LEFT, -0.8 * a)
    pose("Tail1", LEFT, -a)
    for tag in LEGS4: plant(tag)
CLIPS["pushup"] = (1.5, pushup, False)


def flip(f, t):
    """A backflip: down, up and over backward, and down on its feet."""
    crouch = math.sin(math.pi * t / 0.2) if t < 0.2 else 0.0
    land = math.sin(math.pi * (t - 0.8) / 0.2) if t > 0.8 else 0.0
    u = max(0.0, min(1.0, (t - 0.2) / 0.6))
    air = math.sin(math.pi * u)
    pose("Body", LEFT, -360 * ease(u), offset=(0, 0, 2.2 * spine * air - 0.4 * belly * (crouch + land)), pivot=centre)
    if 0.2 < t < 0.8: spring(0.7 * air) if STYLE == "frog" else tuck(50 * air)
    else:
        for tag in LEGS4: plant(tag)
CLIPS["flip"] = (1.2, flip, False)


def puff(f, t):
    """Blows itself up: wider and taller about its own length, up on its legs, and holds it with a shiver."""
    e = ease(t / 0.3) if t < 0.6 else ease((1 - t) / 0.25)
    p = e * (1 + 0.07 * math.sin(math.tau * 4 * t))
    s = (1 + 0.38 * p, 1 + 0.10 * p, 1 + 0.30 * p)
    turn("Body", rot(LEFT, -5 * e), pivot=ground, scale=s)
    turn("Head", scale=unswell("Head", "Body", s, 0.6))
CLIPS["puff"] = (1.6, puff, False)


def swim(f, t):
    """A paddle on the spot: diagonal legs together, each sweeping back flat and coming forward lifted."""
    for tag, phase in (("FL", 0.0), ("BR", 0.0), ("FR", math.pi), ("BL", math.pi)):
        side, reach = SIDE[tag[1]], (34 if tag[0] == "F" else 22)
        s, c = math.sin(math.tau * t + phase), max(0.0, math.cos(math.tau * t + phase))
        turn("Leg" + tag, rot(UP, -side * reach * s) @ rot(LEFT, -14 * s) @ rot(BACK, -side * 16 * c * fade(t)))
        pose("Shin" + tag, UP, -side * 12 * math.sin(math.tau * t + phase - 0.6) * fade(t))
    turn("Body", rot(BACK, 3 * math.sin(math.tau * t)) @ rot(LEFT, 2 * math.sin(2 * math.tau * t)),
         offset=(0, 0, 0.05 * spine * math.sin(2 * math.tau * t)), pivot=centre)
    pose("Neck", LEFT, -6 * (0.5 - 0.5 * math.cos(2 * math.tau * t)))
    sway(t, 10, loop=True)
CLIPS["swim"] = (1.2, swim, True)

# -- the legendaries' own cues
def luck(f, t):
    """The golden harvest hare: up on its hind legs, front paws together, and wishes three times."""
    up = ease(t / 0.22) if t < 0.5 else ease((1 - t) / 0.22)
    wish = up * math.sin(math.tau * 3 * (t - 0.22) / 0.56) if 0.22 < t < 0.78 else 0.0
    a = 55 * up
    pose("Body", LEFT, -a, offset=(0, 0, 0.08 * leg * abs(wish)), pivot=hip)
    for tag in ("BL", "BR"): plant(tag)
    pose("Neck", LEFT, 0.5 * a); pose("Head", LEFT, 0.35 * a + 6 * wish)
    for tag in ("FL", "FR"): pose("Leg" + tag, LEFT, -(15 * up + 18 * wish)); pose("Shin" + tag, LEFT, 50 * up + 15 * wish)
    for e in ("EarL", "EarR"): pose(e, LEFT, 10 * wish)
    turn("Tail1", rot(UP, 15 * wish) @ rot(LEFT, 0.8 * a))
CLIPS["luck"] = (2.4, luck, False)


def lights(f, t):
    """The northlight fox: a pounce straight up, then it looks to the sky while its tail, held high, paints slow
    ribbons from side to side."""
    crouch = math.sin(math.pi * t / 0.14) if t < 0.14 else 0.0
    air = math.sin(math.pi * (t - 0.14) / 0.3) if 0.14 < t < 0.44 else 0.0
    land = math.sin(math.pi * (t - 0.44) / 0.12) if 0.44 < t < 0.56 else 0.0
    gaze = ease((t - 0.1) / 0.2) if t < 0.6 else ease((0.95 - t) / 0.2)
    ribbon = ease(t / 0.2) if t < 0.5 else ease((1 - t) / 0.15)
    pose("Body", LEFT, -18 * air, offset=(0, 0, 0.9 * leg * air - 0.3 * belly * (crouch + land)), pivot=centre)
    if air: tuck(45 * air)
    else:
        for tag in LEGS4: plant(tag)
    pose("Neck", LEFT, -22 * gaze); pose("Head", LEFT, -20 * gaze)
    for i, name in enumerate(TAILS):
        turn(name, rot(UP, 34 * ribbon * math.sin(math.tau * 3 * t - 0.9 * i)) @ rot(LEFT, (38 if i == 0 else 10) * ribbon))
CLIPS["lights"] = (2.6, lights, False)


FRILL, FRILL_BONE = 0.7, "Neck"                             # how far the frill opens, and the bone it is skinned to


def sunfrill(f, t):
    """The sunfrill lizard: rears up on its hind legs and opens its frill (the neck swells round its own length),
    which shivers while it is held."""
    up = ease(t / 0.22) if t < 0.5 else ease((1 - t) / 0.2)
    flare = ease((t - 0.12) / 0.18) if t < 0.5 else ease((0.9 - t) / 0.16)
    shiver = flare * math.sin(math.tau * 5 * t)
    a = 28 * up
    pose("Body", LEFT, -a, pivot=hip)
    for tag in ("BL", "BR"): plant(tag)
    for tag in ("FL", "FR"): pose("Leg" + tag, LEFT, 0.5 * a)
    pose("Tail1", LEFT, a)
    s = 1 + FRILL * flare + 0.05 * shiver
    turn(FRILL_BONE, rot(BACK, 5 * shiver) @ rot(LEFT, 0.45 * a), scale=(s, 1, s))
    if FRILL_BONE == "Neck": turn("Head", rot(LEFT, 0.35 * a), scale=unswell("Head", "Neck", (s, 1, s)))
CLIPS["sunfrill"] = (2.4, sunfrill, False)


def bloom(f, t):
    """The jade turtle: draws in to a bud, settles on its shell, then turns once round with all four legs lifted and
    spread like petals and its head raised."""
    sit = ease(t / 0.15) if t < 0.5 else ease((1 - t) / 0.12)
    bud = math.sin(math.pi * min(1.0, t / 0.36))
    o = ease((t - 0.3) / 0.2) if t < 0.7 else ease((0.97 - t) / 0.15)
    flutter = o * math.sin(math.tau * 6 * t)
    pose("Body", UP, 360 * ease((t - 0.3) / 0.52), offset=(0, 0, -0.85 * belly * sit), pivot=ground)
    for tag in LEGS4:
        side, fore = SIDE[tag[1]], (1 if tag[0] == "F" else -1)
        turn("Leg" + tag, rot(UP, side * fore * (45 * bud - 20 * o)) @ rot(BACK, -side * (60 * o + 6 * flutter)))
        pose("Shin" + tag, BACK, -side * 15 * o)
    pose("Neck", LEFT, 10 * bud - 30 * o, offset=(0, 0.2 * spine * bud - 0.06 * spine * o, 0))
    pose("Head", LEFT, -12 * o)
    pose("Tail1", LEFT, 40 * o)
CLIPS["bloom"] = (3.0, bloom, False)

# -- a lizard's or a newt's body: low, legs out to the side, a long tail
def _sprawl(tag):
    top, low = rest["Leg" + tag].translation, rest["Foot" + tag].translation
    return max(0.5, min(1.0, abs(low.x - top.x) / max(top.z - low.z, 1e-4)))
SPRAWL = {tag: _sprawl(tag) for tag in LEGS4}               # how far each leg swings round (1) rather than under (0)


def sprawl_legs(t, stride=26.0, lift=16.0):
    for tag, phase in (("FL", 0.0), ("BR", 0.0), ("FR", math.pi), ("BL", math.pi)):
        side, w = SIDE[tag[1]], SPRAWL[tag]
        s, c = math.sin(math.tau * t + phase), max(0.0, math.cos(math.tau * t + phase))
        turn("Leg" + tag, rot(UP, -side * stride * s * w) @ rot(LEFT, -stride * s * (1 - w)) @ rot(BACK, -side * lift * c * w))
        pose("Shin" + tag, LEFT, lift * c * (1 - w) * (1 if tag[0] == "F" else -1))


def sprawl_idle(f, t):
    look = math.sin(math.tau * t)
    pose("Body", offset=(0, 0, 0.03 * belly * math.sin(math.tau * 2 * t)))
    pose("Neck", UP, 9 * look)
    pose("Head", LEFT, -5 * max(0.0, look))
    sway(t, 9, loop=True)


def sprawl_walk(f, t):
    s = math.sin(math.tau * t)
    sprawl_legs(t, 26.0, 16.0 * fade(t))
    pose("Body", UP, 6 * s, pivot=centre)                   # the hips and the shoulders turn against each other
    pose("Chest", UP, -13 * s)
    pose("Neck", UP, 4 * s); pose("Head", UP, 3 * s)
    sway(t, 16, 1, math.pi, loop=True)


def sprawl_spin(f, t):
    e = math.sin(math.pi * t)
    go = min(1.0, 4 * e)
    pose("Body", UP, 360 * ease(t), pivot=ground)
    sprawl_legs((3 * t) % 1, 20 * go, 14 * go)
    pose("Chest", UP, 16 * e); pose("Neck", UP, 10 * e); pose("Head", UP, 8 * e)     # bent round after its tail
    for i, name in enumerate(TAILS): pose(name, UP, -(18 + 6 * i) * e)


def sprawl_roll(f, t):
    a = 360 * ease((t - 0.12) / 0.72)
    r = math.radians(a)
    e = math.sin(math.pi * ease((t - 0.05) / 0.9))
    pose("Body", BACK, a, offset=(0, 0, LIFT_SIDE * abs(math.sin(r)) + LIFT_BACK * (0.5 - 0.5 * math.cos(r))), pivot=centre)
    for tag in LEGS4: pose("Leg" + tag, BACK, SIDE[tag[1]] * 30 * e)
    sway(t, 14 * e, 2)


_tail = rest["Tail3"].translation - rest["Tail1"].translation
TAIL_SLOPE = math.degrees(math.atan2(-_tail.z, max(_tail.y, 1e-4))) if _tail.length > 1e-4 else 0.0     # how far the tail slopes down, rump to tip


def sprawl_dead(f, t):
    """Onto its back, legs fallen open, and up again."""
    e = ease(t / 0.22) if t < 0.5 else ease((1 - t) / 0.22)
    r = math.pi * e
    pose("Body", BACK, 180 * e, offset=(0, 0, LIFT_SIDE * math.sin(r) + LIFT_BACK * (0.5 - 0.5 * math.cos(r))), pivot=centre)
    for tag in LEGS4: pose("Leg" + tag, BACK, -SIDE[tag[1]] * 20 * e)
    turn("Tail1", rot(UP, 10 * e) @ rot(LEFT, 2 * TAIL_SLOPE * e))       # the tail, which sloped down, lies down again
    for name in TAILS[1:]: pose(name, UP, 10 * e)
if STYLE == "sprawl":
    OWN.update(idle=(3.0, sprawl_idle, True), walk=(0.8, sprawl_walk, True), spin=(1.5, sprawl_spin, False),
               roll=(1.6, sprawl_roll, False), dead=(3.0, sprawl_dead, False))

# -- a frog's body: it sits, and it goes by hops
def frog_idle(f, t):
    pose("Body", LEFT, -2 * math.sin(math.tau * t), offset=(0, 0, 0.03 * belly * math.sin(math.tau * 3 * t)), pivot=hip)
    pose("Neck", UP, 6 * math.sin(math.tau * t))


def frog_walk(f, t):
    s = math.sin(math.tau * t)
    air, sit = max(0.0, s), max(0.0, -s)
    pose("Body", LEFT, -12 * air + 4 * sit, offset=(0, 0, 0.7 * spine * air - 0.25 * belly * sit), pivot=centre)
    if air: spring(air)
    else:
        for tag in LEGS4: plant(tag)


def frog_jump(f, t):
    crouch = math.sin(math.pi * t / 0.25) if t < 0.25 else 0.0
    land = math.sin(math.pi * (t - 0.75) / 0.25) if t > 0.75 else 0.0
    air = math.sin(math.pi * (t - 0.25) / 0.5) if 0.25 < t < 0.75 else 0.0
    pose("Body", LEFT, -16 * air * math.cos(math.pi * (t - 0.25) / 0.5), offset=(0, 0, 1.6 * spine * air - 0.4 * belly * (crouch + land)), pivot=centre)
    if air: spring(air)
    else:
        for tag in LEGS4: plant(tag)


def frog_spin(f, t):
    """Round in three hops."""
    e = min(1.0, 4 * math.sin(math.pi * t))
    hop = math.sin(3 * math.tau * t - math.pi / 2) * e
    air = max(0.0, hop)
    pose("Body", UP, 360 * ease(t), offset=(0, 0, 0.35 * spine * air), pivot=ground)
    if air: spring(0.6 * air)
if STYLE == "frog": OWN.update(idle=(3.0, frog_idle, True), walk=(0.8, frog_walk, True), jump=(1.0, frog_jump, False), spin=(1.5, frog_spin, False))

# -- a turtle's body: nothing bends the shell (Chest never turns against Body), the head and the legs do the moving
def turtle_idle(f, t):
    reach = 0.5 - 0.5 * math.cos(math.tau * t)
    pose("Body", offset=(0, 0, 0.02 * belly * math.sin(math.tau * 2 * t)))
    pose("Neck", UP, 12 * math.sin(math.tau * t), offset=(0, -0.05 * spine * reach, 0))
    pose("Head", LEFT, -6 * reach)
    for tag, phase in (("FL", 0.0), ("BR", 0.0), ("FR", math.pi), ("BL", math.pi)): pose("Leg" + tag, UP, SIDE[tag[1]] * 4 * math.sin(math.tau * t + phase))
    sway(t, 8, loop=True)
if STYLE == "turtle": OWN.update(idle=(3.0, turtle_idle, True))

# -- a hopper (the jerboa): it goes on its back legs alone, the front paws held up, the tail keeping time
def hopper_paws(amount=1.0):
    for tag in ("FL", "FR"): pose("Leg" + tag, LEFT, -15 * amount); pose("Shin" + tag, LEFT, 35 * amount)


def hopper_hop(air):
    if air: spring(0.8 * air, ("BL", "BR"))
    else:
        for tag in ("BL", "BR"): plant(tag)


def hopper_walk(f, t):
    s = math.sin(math.tau * t)
    air, sit = max(0.0, s), max(0.0, -s)
    pose("Body", LEFT, -6 * air + 5 * sit, offset=(0, 0, 0.6 * spine * air - 0.25 * belly * sit), pivot=hip)
    hopper_hop(air)
    hopper_paws(0.5 - 0.5 * math.cos(math.tau * t))
    pose("Head", LEFT, 5 * s)
    pose("Tail1", LEFT, 14 * s); pose("Tail2", LEFT, -10 * math.sin(2 * math.tau * t))


def hopper_spin(f, t):
    e = min(1.0, 4 * math.sin(math.pi * t))
    hop = math.sin(3 * math.tau * t - math.pi / 2) * e
    air, sit = max(0.0, hop), max(0.0, -hop)
    pose("Body", UP, 360 * ease(t), offset=(0, 0, 0.45 * spine * air - 0.2 * belly * sit), pivot=ground)
    hopper_hop(air)
    hopper_paws(e)
    sway(t, 20 * e, 2)
if STYLE == "hopper": OWN.update(walk=(0.6, hopper_walk, True), spin=(1.5, hopper_spin, False))

unknown = [c for c in wanted if c not in CLIPS and c not in OWN]
if unknown: raise SystemExit("make: no clip written for %s" % ", ".join(unknown))
made = {}
for name in wanted:
    seconds, body, loop = OWN.get(name) or CLIPS[name]
    SWELLS = name in SWELLING
    clip(name, seconds, body, loop)
    made[name] = seconds
SWELLS = False
common.log("clips:", ", ".join("%s %.1f s" % kv for kv in made.items()) + (" (the %s's own: %s)" % (STYLE, ", ".join(n for n in made if n in OWN)) if STYLE else ""))

for o in scene.objects: o.select_set(o in (rig, mesh))
bpy.context.view_layer.objects.active = rig
rest_pose()
bpy.ops.export_scene.gltf(filepath=out_glb, use_selection=True, export_format="GLB", export_image_format="JPEG", export_jpeg_quality=92,
                          export_yup=True, export_apply=False, export_skins=True, export_all_influences=False, export_def_bones=False,
                          export_animations=True, export_animation_mode="ACTIONS", export_force_sampling=True, export_frame_step=1,
                          export_optimize_animation_size=True, export_armature_object_remove=True, export_rest_position_armature=True,
                          export_anim_slide_to_zero=True, export_bake_animation=False, export_vertex_color="NONE", export_morph=False)
with open(os.path.join(os.path.dirname(out_glb), "clips.json"), "w") as f: json.dump({"clips": made, "fps": FPS, "leg": leg}, f, indent=2)
common.look(os.path.join(os.path.dirname(out_glb), "look-rigged"), [mesh])
# Each clip at a third and two thirds of the way: bad weights (a leg that collapses, a torn belly) show here.
for name in made:
    rig.animation_data.action = bpy.data.actions[name]
    end = round(made[name] * FPS)
    for k, frame in enumerate((end // 3, 2 * end // 3)):
        scene.frame_set(frame)
        common.look(os.path.join(os.path.dirname(out_glb), "pose-%s-%d" % (name, k + 1)), [mesh], size=400, views=("side", "front34"))
rig.animation_data.action = None
