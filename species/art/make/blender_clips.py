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


def key(frame):
    for b in bones:
        if b.name == "Root": continue
        b.keyframe_insert("rotation_quaternion", frame=frame); b.keyframe_insert("location", frame=frame)


def rest_pose():
    for b in bones: b.rotation_quaternion = Quaternion(); b.location = Vector()


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

unknown = [c for c in wanted if c not in CLIPS]
if unknown: raise SystemExit("make: no clip written for %s" % ", ".join(unknown))
made = {}
for name in wanted:
    seconds, body, loop = CLIPS[name]
    clip(name, seconds, body, loop)
    made[name] = seconds
common.log("clips:", ", ".join("%s %.1f s" % kv for kv in made.items()))

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
