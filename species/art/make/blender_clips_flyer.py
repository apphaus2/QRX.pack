"""make.py's clips step for the flyer shape (butterflies, moths, dragonflies), in Blender: the clips keyframed on the
bones blender_rig_flyer.py made and scaled by the creature's own wings, then the glTF with its skin and clips.

    blender -b -P blender_clips_flyer.py -- <rig.blend> <rigged.glb> <idle,fly,spin,...> <id>

Every clip is in place (Root is never keyed) and every clip, the loops too, starts and ends in the rest pose (the
wings spread flat, as pictured). Turns are written about the creature's own axes (x left, up, forward) so they read
the same for every skeleton. 30 frames a second, a key on every frame: a wing beats five or six times a second.

The kind (butterfly, moth or dragonfly) is the one the rig step wrote on the skeleton."""
import json, math, os, sys
import bpy
from mathutils import Quaternion, Vector
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
# Blender axes: the animal's left +X, up +Z, forward -Y. A pitch about +X sends the nose down.
LEFT, UP, BACK = Vector((1, 0, 0)), Vector((0, 0, 1)), Vector((0, 1, 0))
kind = rig.get("kind", "butterfly")
span = float(rig.get("span", 0.1))                  # wing tip to wing tip, metres: every move is scaled by it
length = float(rig.get("length", 0.1))              # head to the end of the abdomen
CENTRE = Vector((0, 0, 0))                          # mid-body: where Root is, and what the body turns about
ABDOMEN = [n for n in ("Abdomen1", "Abdomen2", "Abdomen3") if n in bones]
WINGS = [n for n in ("WingFL", "WingFR", "WingBL", "WingBR") if n in bones]
last = {}                                           # each bone's last keyed turn: the next key takes the same sign


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


def key(frame):
    for b in bones:
        if b.name == "Root": continue
        # A full turn ends at minus the rest quaternion: keep each key on the side of the one before it, so nothing
        # that blends the keys component by component swings back round through the turn.
        q = b.rotation_quaternion.copy()
        if b.name in last and last[b.name].dot(q) < 0: q.negate(); b.rotation_quaternion = q
        last[b.name] = q
        b.keyframe_insert("rotation_quaternion", frame=frame); b.keyframe_insert("location", frame=frame)


def rest_pose():
    for b in bones: b.rotation_quaternion = Quaternion(); b.location = Vector()


def ease(t): return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, t)))


def clip(name, seconds, body, loop=False):
    frames = round(seconds * FPS)
    action = bpy.data.actions.new(name); action.use_fake_user = True
    rig.animation_data_create(); rig.animation_data.action = action
    last.clear()
    for f in range(0, frames + 1):
        rest_pose()
        if 0 < f < frames: body(f, f / frames)
        key(f)
    rig.animation_data.action = None
    return action


def wings(fore, hind=None):
    """Lift the wings by `fore` degrees above flat (below, when negative), the hind pair by `hind` (the same when
    None). The hinge is each wing bone's head, along the body."""
    hind = fore if hind is None else hind
    for name in WINGS:
        up = fore if name[4] == "F" else hind
        pose(name, BACK, -up if name.endswith("L") else up)


def beat(t, beats, low, high, lag=0.0):
    """The wings' angle at t of a clip with `beats` whole beats between `low` and `high` degrees, flat at both ends.
    `lag` (radians) is how far behind the hind pair is."""
    mid, amp = (low + high) / 2, (high - low) / 2
    start = math.acos(max(-1.0, min(1.0, -mid / amp)))      # where in the beat the wings are flat
    return (mid + amp * math.cos(math.tau * beats * t + start),
            mid + amp * math.cos(math.tau * beats * t + start - lag))


def abdomen(degrees):
    """Dip the abdomen (positive: the tip down), each piece a little more than the one before."""
    for i, name in enumerate(ABDOMEN):
        pose(name, LEFT, -degrees * (0.7 + 0.3 * i))


def through(t, beats, low, high, lag=0.0, edge=0.12):
    """Wings beating through a cue: `beats` whole beats, eased in and out so the cue starts and ends flat."""
    env = min(1.0, t / edge, (1 - t) / edge)
    f, h = beat(t, beats, low, high, lag)
    wings(f * env, h * env)
    return env


CLIPS = {}
BUTTERFLY = kind != "dragonfly"
LAG = 0.5 if BUTTERFLY else math.pi / 2             # a dragonfly's two pairs beat out of step


def idle(f, t):
    if kind == "dragonfly":
        # Hovering: small quick beats, the abdomen dipping, a slow look to one side and back.
        fo, hi = beat(t, 15, -14, 14, LAG)
        wings(fo, hi)
        pose("Body", UP, 4 * math.sin(math.tau * t), offset=(0, 0, 0.012 * length * math.sin(math.tau * 2 * t)), pivot=CENTRE)
        abdomen(5 * math.sin(math.tau * t) ** 2)
        pose("Head", BACK, 8 * math.sin(math.tau * t))
    elif kind == "moth":
        # Resting flat, the wings trembling in three bursts.
        burst = math.sin(math.pi * ((3 * t) % 1)) ** 2
        wings(5 * burst * (1 - math.cos(math.tau * 18 * t)), 4 * burst * (1 - math.cos(math.tau * 18 * t - 0.6)))
        abdomen(4 * math.sin(math.pi * t) ** 2)
        pose("Head", LEFT, 4 * math.sin(math.tau * 2 * t))
    else:
        # Basking: the wings closing up over the back and opening again, slowly, twice.
        up = 29 * (1 - math.cos(math.tau * 2 * t))
        wings(up, up * 0.92)
        pose("Body", offset=(0, 0, -0.01 * span * (1 - math.cos(math.tau * 2 * t)) / 2))
        abdomen(3 * math.sin(math.tau * 2 * t))
        pose("Head", LEFT, 4 * math.sin(math.tau * 2 * t))
CLIPS["idle"] = (3.0, idle, True)


def fly(f, t):
    if kind == "dragonfly":
        fo, hi = beat(t, 3, -26, 30, LAG)
        wings(fo, hi)
        pose("Body", offset=(0, 0, 0.012 * length * math.sin(math.tau * t)))
        abdomen(3 * math.sin(math.tau * t) ** 2)
    else:
        beats = 6 if kind == "moth" else 5
        low, high = (-22, 48) if kind == "moth" else (-20, 62)
        fo, hi = beat(t, beats, low, high, LAG)
        wings(fo, hi)
        # The body drops as the wings come up and rises on the down stroke, and pitches a little with it.
        bob = -fo / max(high, 1)
        pose("Body", LEFT, -5 * bob, offset=(0, 0, 0.035 * span * bob), pivot=CENTRE)
        abdomen(8 * max(0.0, fo) / high)
CLIPS["fly"] = (0.5 if kind == "dragonfly" else 1.0, fly, True)


def cue_beat(t, seconds):
    """The wings through a cue, at about the rate they fly."""
    if kind == "dragonfly": return through(t, round(6 * seconds), -26, 30, LAG)
    return through(t, round((6 if kind == "moth" else 5) * seconds), -18, 55, LAG)


def spin(f, t):
    cue_beat(t, 1.5)
    pose("Body", UP, 360 * ease((t - 0.08) / 0.84), offset=(0, 0, 0.05 * span * math.sin(math.pi * t)), pivot=CENTRE)
    abdomen(6 * math.sin(math.pi * t))
CLIPS["spin"] = (1.5, spin, False)


def flip(f, t):
    # A loop the loop: nose up and over backwards, lifting as it goes.
    cue_beat(t, 1.5)
    pose("Body", LEFT, -360 * ease((t - 0.1) / 0.8), offset=(0, 0, 0.25 * length * math.sin(math.pi * ease(t))), pivot=CENTRE)
    abdomen(10 * math.sin(math.pi * t))
CLIPS["flip"] = (1.5, flip, False)


def dance(f, t):
    e = math.sin(math.pi * t)
    cue_beat(t, 2.0)
    if kind == "dragonfly":
        # A zigzag: swinging its nose from side to side, darting left and right.
        pose("Body", UP, 30 * e * math.sin(math.tau * 3 * t), offset=(0.12 * span * e * math.sin(math.tau * 3 * t), 0, 0), pivot=CENTRE)
        abdomen(10 * e * math.sin(math.tau * 3 * t) ** 2)
    else:
        # A sway: rocking from wing to wing, bobbing on each.
        pose("Body", BACK, 24 * e * math.sin(math.tau * 3 * t), offset=(0, 0, 0.08 * span * e * abs(math.sin(math.tau * 3 * t))), pivot=CENTRE)
        abdomen(8 * e)
    pose("Head", UP, 10 * e * math.sin(math.tau * 3 * t))
CLIPS["dance"] = (2.0, dance, False)

unknown = [c for c in wanted if c not in CLIPS]
if unknown: raise SystemExit("make: no clip written for %s" % ", ".join(unknown))
made = {}
for name in wanted:
    seconds, body, loop = CLIPS[name]
    clip(name, seconds, body, loop)
    made[name] = seconds
common.log("clips (%s):" % kind, ", ".join("%s %.1f s" % kv for kv in made.items()))

for o in scene.objects: o.select_set(o in (rig, mesh))
bpy.context.view_layer.objects.active = rig
rest_pose()
bpy.ops.export_scene.gltf(filepath=out_glb, use_selection=True, export_format="GLB", export_image_format="JPEG", export_jpeg_quality=92,
                          export_yup=True, export_apply=False, export_skins=True, export_all_influences=False, export_def_bones=False,
                          export_animations=True, export_animation_mode="ACTIONS", export_force_sampling=True, export_frame_step=1,
                          export_optimize_animation_size=True, export_armature_object_remove=True, export_rest_position_armature=True,
                          export_anim_slide_to_zero=True, export_bake_animation=False, export_vertex_color="NONE", export_morph=False)


def steady_signs(path):
    """The exporter writes each key's turn from a matrix, so a bone that lies turned half round from its parent (Body
    under Root, the abdomen under Body) comes out now as q, now as -q: the same turn, but a player that blends two
    keys without taking the short way round would whip the bone about. Each turn is put on the side of the key
    before it, in place in the file. Returns how many keys were changed."""
    import struct
    blob = bytearray(open(path, "rb").read())
    n = struct.unpack_from("<I", blob, 12)[0]
    g = json.loads(bytes(blob[20:20 + n]))
    base, seen, changed = 20 + n + 8, set(), 0
    for animation in g.get("animations", []):
        for channel in animation["channels"]:
            index = animation["samplers"][channel["sampler"]]["output"]
            if channel["target"]["path"] != "rotation" or index in seen: continue
            seen.add(index)
            a = g["accessors"][index]
            if a["componentType"] != 5126 or a["type"] != "VEC4": continue
            view = g["bufferViews"][a["bufferView"]]
            start, stride = base + view.get("byteOffset", 0) + a.get("byteOffset", 0), view.get("byteStride") or 16
            before = None
            for k in range(a["count"]):
                q = struct.unpack_from("<4f", blob, start + k * stride)
                if before is not None and sum(x * y for x, y in zip(before, q)) < 0:
                    q = tuple(-x for x in q); struct.pack_into("<4f", blob, start + k * stride, *q); changed += 1
                before = q
    if changed:
        with open(path, "wb") as f: f.write(blob)
    return changed


common.log("%d keys' turns put on the side of the key before them" % steady_signs(out_glb))
with open(os.path.join(os.path.dirname(out_glb), "clips.json"), "w") as f:
    json.dump({"clips": made, "fps": FPS, "kind": kind, "span": span, "length": length}, f, indent=2)


def on_the_cpu(samples=32):
    """The pictures below are small: Cycles on the CPU, so this step never waits on (or crowds) a GPU that is meshing."""
    scene.render.engine = "CYCLES"; scene.cycles.device = "CPU"; scene.cycles.samples = samples; scene.cycles.use_denoising = False
    return scene


common.cycles = on_the_cpu
common.look(os.path.join(os.path.dirname(out_glb), "look-rigged"), [mesh])
# Each clip at a third and two thirds of the way: bad weights (a wing torn off the thorax, a bent body) show here.
for name in made:
    rig.animation_data.action = bpy.data.actions[name]
    end = round(made[name] * FPS)
    for k, frame in enumerate((end // 3, 2 * end // 3)):
        scene.frame_set(frame)
        common.look(os.path.join(os.path.dirname(out_glb), "pose-%s-%d" % (name, k + 1)), [mesh], size=400, views=("top", "front34"))
rig.animation_data.action = None
