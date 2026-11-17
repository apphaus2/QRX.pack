"""make.py's clips step for the soft shape, in Blender: the clips of a jelly or a snail (blender_rig_soft.py says which:
a skeleton with a Shell bone is a snail's), keyframed on the named bones and scaled by the creature's own bell or
shell, then the glTF with its skin and clips.

    blender -b -P blender_clips_soft.py -- <rig.blend> <rigged.glb> <idle,swim,pulse,...> <id>

Every clip is in place (Root is never keyed). Every clip, the loops too, starts and ends in the rest pose: a loop's
moves are whole waves, and what lags behind (a tentacle's end) moves only in the middle of the clip. Turns are
written about the creature's own axes (x left, up, forward). 30 frames a second.

jelly: idle (loop), swim (loop), and the cues pulse, spin, dance, jump.
snail: idle (loop), walk (loop, a crawl), and the cues dance and hide. hide is written for every snail whether or
not its brief lists it: the species documents play it."""
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
ends = {b.name: b.bone.tail_local.copy() for b in bones}
# Blender axes: the animal's left +X, up +Z, forward -Y. A pitch about +X sends the nose down.
LEFT, UP, BACK = Vector((1, 0, 0)), Vector((0, 0, 1)), Vector((0, 1, 0))
kind = "snail" if "Shell" in bones else "jelly"
if kind == "snail" and "hide" not in wanted:
    wanted.append("hide"); common.log("hide added: every snail's species document plays it")


def pose(name, *turns, offset=None, pivot=None):
    """Turn bone `name` by (axis, degrees) pairs about rest-space axes, the first written applied last, and move it by
    a rest-space offset; keyed by the caller. A pivot turns it about a point other than its own head."""
    if name not in bones: return
    b = bones[name]
    R = rest[name].to_quaternion()
    q = Quaternion()
    for axis, degrees in turns:
        if degrees: q = q @ Quaternion(axis, math.radians(degrees))
    b.rotation_quaternion = R.inverted() @ q @ R
    move = Vector(offset) if offset is not None else Vector()
    if pivot is not None:
        head = rest[name].translation
        move += (q @ (head - pivot) + pivot) - head
    b.location = R.inverted() @ move


_last = {}


def key(frame):
    for b in bones:
        if b.name == "Root": continue
        q = b.rotation_quaternion                               # the same turn, written on the side nearest the last key's
        if b.name in _last and q.dot(_last[b.name]) < 0: q.negate(); b.rotation_quaternion = q
        _last[b.name] = b.rotation_quaternion.copy()
        b.keyframe_insert("rotation_quaternion", frame=frame); b.keyframe_insert("location", frame=frame)


def rest_pose():
    for b in bones: b.rotation_quaternion = Quaternion(); b.location = Vector()


def ease(t): return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, t)))


def bump(t, start, end, rise=0.35):
    """0 outside start..end; inside, up to 1 over the first `rise` of it and slowly back down."""
    if t <= start or t >= end: return 0.0
    u = (t - start) / (end - start)
    return ease(u / rise) if u < rise else 1 - ease((u - rise) / (1 - rise))


def wave(t, turns=1.0): return math.sin(math.tau * turns * t)


def clip(name, seconds, body, loop=False):
    frames = round(seconds * FPS)
    action = bpy.data.actions.new(name); action.use_fake_user = True
    rig.animation_data_create(); rig.animation_data.action = action
    _last.clear()
    for f in range(0, frames + 1, 2 if frames > 40 else 1):
        rest_pose()
        if 0 < f < frames: body(f, f / frames)
        key(f)
    if frames % 2 and frames > 40: rest_pose(); key(frames)
    rig.animation_data.action = None
    return action


CLIPS = {}

if kind == "jelly":
    RIBS = sum(1 for b in bones if b.name.startswith("Bell"))
    CHAIN = ("a", "b", "c")
    bell = max(ends["Head"].z - ends["Bell1"].z, 0.01)           # the bell's height: every move is scaled by it
    unit = bell
    out = {}                                                     # each rib's way out from the axis, level
    for i in range(1, RIBS + 1):
        d = ends["Bell%d" % i] - rest["Bell%d" % i].translation; d.z = 0
        out[i] = d.normalized() if d.length > 1e-6 else Vector((0, -1, 0))

    def squeeze(degrees, trail=(0.0, 0.0, 0.0), drift=(0.0, 0.0, 0.0), sway=0.0, side=0.0):
        """The bell's ribs turned in and down by `degrees` (the pulse; negative opens it) and each tentacle bone turned
        in by its `trail`; `drift` leans the tentacle bones the same way all round (about the left axis), as in a
        current, and sway and side do so for the mouth arms."""
        for i in range(1, RIBS + 1):
            inward = UP.cross(out[i])
            pose("Bell%d" % i, (inward, degrees))
            for k, letter in enumerate(CHAIN):
                pose("Tent%d%s" % (i, letter), (LEFT, drift[k]), (inward, trail[k]))
        for k in range(3):
            pose("Arm%d" % (k + 1), (LEFT, sway * (0.6 + 0.4 * k)), (BACK, side * (0.6 + 0.4 * k)))

    def idle(f, t):
        p = bump(t, 0.1, 0.6)
        squeeze(7 * p, trail=(-4 * p + 3 * bump(t, 0.2, 0.7), 4 * bump(t, 0.28, 0.8), 5 * bump(t, 0.35, 0.9)),
                drift=(3 * wave(t), 4 * wave(t) + 2 * wave(t, 2), 5 * wave(t) + 4 * wave(t, 2)),
                sway=3 * wave(t) + 2 * wave(t, 2), side=2 * wave(t, 2))
        pose("Body", (LEFT, 2.5 * wave(t)), (BACK, 1.5 * wave(t, 2)), offset=(0, 0, 0.05 * bell * bump(t, 0.15, 0.85, 0.4)), pivot=rest["Body"].translation)
        pose("Head", offset=(0, 0, 0.02 * bell * p))
    CLIPS["idle"] = (3.0, idle, True)

    def swim(f, t):
        p = bump(t, 0.04, 0.62, 0.3)
        squeeze(22 * p, trail=(-17 * p + 7 * bump(t, 0.12, 0.72), 9 * bump(t, 0.2, 0.84) - 4 * p, 12 * bump(t, 0.3, 0.96) - 5 * bump(t, 0.1, 0.6)),
                sway=4 * wave(t), side=0.0)
        pose("Body", offset=(0, 0, 0.16 * bell * bump(t, 0.1, 0.95, 0.3)))
        pose("Head", offset=(0, 0, 0.05 * bell * p))
        for k in range(3): pose("Arm%d" % (k + 1), (LEFT, (3 + 2 * k) * wave(t)), offset=(0, 0, -0.04 * bell * bump(t, 0.1 + 0.08 * k, 0.8 + 0.08 * k)))
    CLIPS["swim"] = (1.6, swim, True)

    def pulse(f, t):
        p = bump(t, 0.03, 0.47, 0.3) + bump(t, 0.45, 0.9, 0.3)
        late = bump(t, 0.1, 0.55) + bump(t, 0.52, 0.95)
        later = bump(t, 0.16, 0.6) + bump(t, 0.58, 0.99)
        squeeze(28 * p, trail=(-23 * p + 8 * late, 10 * late - 4 * p, 13 * later - 5 * late))
        pose("Body", offset=(0, 0, 0.2 * bell * late))
        pose("Head", offset=(0, 0, 0.07 * bell * p))
        for k in range(3): pose("Arm%d" % (k + 1), offset=(0, 0, -0.05 * bell * (late if k < 2 else later)))
    CLIPS["pulse"] = (1.8, pulse, False)

    def spin(f, t):
        e = math.sin(math.pi * t)
        squeeze(-4 * e, trail=(-7 * e, -5 * e, -4 * bump(t, 0.1, 0.98, 0.5)))          # the tentacles fly outward
        pose("Body", (UP, 360 * ease(t)), (LEFT, 6 * e * wave(t)), pivot=rest["Body"].translation)
    CLIPS["spin"] = (1.5, spin, False)

    def dance(f, t):
        e = math.sin(math.pi * t)
        beat = abs(wave(t, 2))
        squeeze(16 * e * beat, trail=(-9 * e * beat, 6 * e * wave(t, 4), 9 * e * wave(t, 4)),
                drift=(0, 0, 0), sway=8 * e * wave(t, 2), side=10 * e * wave(t, 2))
        pose("Body", (BACK, 16 * e * wave(t, 2)), (UP, 20 * e * wave(t, 1)), offset=(0, 0, 0.14 * bell * e * beat), pivot=rest["Body"].translation)
        pose("Head", offset=(0, 0, 0.04 * bell * e * beat))
    CLIPS["dance"] = (2.0, dance, False)

    def jump(f, t):
        gather = bump(t, 0.0, 0.25, 0.5)                    # the bell opens wide,
        push = bump(t, 0.18, 0.62, 0.25)                    # snaps shut,
        air = bump(t, 0.22, 0.97, 0.4)                      # and the jelly shoots up and sinks back
        squeeze(-8 * gather + 32 * push, trail=(-20 * push + 14 * bump(t, 0.25, 0.8), 14 * bump(t, 0.3, 0.9), 16 * bump(t, 0.35, 0.99)))
        pose("Body", offset=(0, 0, 0.5 * bell * air - 0.06 * bell * gather))
        pose("Head", offset=(0, 0, 0.08 * bell * push))
        for k in range(3): pose("Arm%d" % (k + 1), offset=(0, 0, -0.06 * bell * bump(t, 0.25 + 0.05 * k, 0.9 + 0.03 * k)))
    CLIPS["jump"] = (1.2, jump, False)

else:
    shell = max((ends["Shell"] - rest["Shell"].translation).length, 0.01)       # the shell's height: every move is scaled by it
    unit = shell
    neck = max((rest["Head"].translation - rest["Neck"].translation).length, 0.005)
    head = max((ends["Head"] - rest["Head"].translation).length, 0.005)
    tail = max((ends["Tail2"] - rest["Tail1"].translation).length, 0.005)
    shell_base = rest["Shell"].translation.copy()
    stalk = {s: (ends["Stalk%s2" % s] - rest["Stalk" + s].translation) for s in ("L", "R")}     # foot to tip

    def stalks(left=(0.0, 0.0), right=(0.0, 0.0), pull=(0.0, 0.0), tips=0.6):
        """Each stalk leant (forward-and-back degrees, sideways degrees) and drawn in by `pull` (0 to 1 of its length)."""
        for s, (pitch, roll), drawn in (("L", left, pull[0]), ("R", right, pull[1])):
            way = stalk[s].normalized() if stalk[s].length > 1e-6 else UP
            reach = stalk[s].length
            pose("Stalk" + s, (LEFT, pitch), (BACK, roll), offset=-way * reach * 0.35 * drawn)
            pose("Stalk%s2" % s, (LEFT, pitch * tips), (BACK, roll * tips), offset=-way * reach * 0.45 * drawn)

    def idle(f, t):
        stalks(left=(7 * wave(t) + 3 * wave(t, 2), 6 * wave(t, 2)), right=(6 * wave(t, 2) - 4 * wave(t), -5 * wave(t)),
               pull=(0.75 * bump(t, 0.55, 0.8, 0.3), 0.0))                 # one eye draws in and comes out again
        pose("Neck", (LEFT, 2.5 * wave(t, 2)), (UP, 4 * wave(t)))
        pose("Head", (UP, 7 * wave(t)), (LEFT, 3 * wave(t, 2)))
        pose("Tail2", (UP, 3 * wave(t)))
        pose("Shell", (BACK, 1.2 * wave(t)), pivot=shell_base)
    CLIPS["idle"] = (3.0, idle, True)

    def walk(f, t):
        # A crawl on the spot: the head reaches forward, the foot follows in a wave from the tail, the shell rides along.
        reach = 0.5 - 0.5 * math.cos(math.tau * t)
        pose("Neck", (UP, 3 * wave(t)), (LEFT, -3 * reach), offset=-BACK * 0.10 * neck * reach)
        pose("Head", (UP, 5 * wave(t)), (LEFT, 4 * wave(t, 2)), offset=-BACK * 0.10 * head * reach)
        pose("Body", offset=(0, 0, 0.02 * shell * (0.5 - 0.5 * math.cos(math.tau * 2 * t))))
        pose("Shell", (LEFT, 3 * wave(t)), (BACK, 2 * wave(t, 2)), pivot=shell_base)
        pose("Tail1", (LEFT, 3 * wave(t, 2)), offset=BACK * 0.06 * tail * bump(t, 0.05, 0.7, 0.5))
        pose("Tail2", (LEFT, -5 * wave(t, 2)), (UP, 4 * wave(t)), offset=BACK * 0.08 * tail * bump(t, 0.15, 0.95, 0.5))
        stalks(left=(6 * wave(t) + 3 * wave(t, 2), 4 * wave(t, 2)), right=(6 * wave(t) - 3 * wave(t, 2), -4 * wave(t, 2)))
    CLIPS["walk"] = (2.0, walk, True)

    def dance(f, t):
        e = math.sin(math.pi * t)
        pose("Shell", (BACK, 13 * e * wave(t, 3)), (LEFT, 5 * e * abs(wave(t, 3))), pivot=shell_base)
        pose("Body", (BACK, 4 * e * wave(t, 3)), offset=(0, 0, 0.04 * shell * e * abs(wave(t, 3))), pivot=Vector((0, 0, 0)))
        pose("Neck", (LEFT, -16 * e), (UP, 8 * e * wave(t, 3)))
        pose("Head", (UP, 16 * e * wave(t, 3)), (BACK, 10 * e * wave(t, 3)))
        pose("Tail1", (UP, 6 * e * wave(t, 3)))
        pose("Tail2", (UP, 14 * e * wave(t, 3)), (LEFT, -8 * e))
        stalks(left=(24 * e * wave(t, 3), 10 * e * wave(t, 6)), right=(-24 * e * wave(t, 3), -10 * e * wave(t, 6)))
    CLIPS["dance"] = (2.4, dance, False)

    def hide(f, t):
        # Into the shell: the eyes draw in, the head and the tail pull back under it, the shell tips down over them.
        e = ease(t / 0.28) if t < 0.5 else ease((1 - t) / 0.28)
        eyes = ease(t / 0.14) if t < 0.5 else ease((1 - t) / 0.2)
        stalks(left=(20 * eyes, 0), right=(20 * eyes, 0), pull=(eyes, eyes))
        pose("Neck", (LEFT, 12 * e), offset=BACK * 0.75 * neck * e - UP * 0.1 * neck * e)
        pose("Head", (LEFT, 18 * e), offset=BACK * 0.6 * head * e)
        pose("Tail1", offset=-BACK * 0.3 * tail * e)
        pose("Tail2", offset=-BACK * 0.3 * tail * e)
        pose("Shell", (LEFT, 10 * e), offset=-UP * 0.05 * shell * e, pivot=shell_base)
    CLIPS["hide"] = (2.6, hide, False)

unknown = [c for c in wanted if c not in CLIPS]
if unknown: raise SystemExit("make: no %s clip written for %s" % (kind, ", ".join(unknown)))
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
with open(os.path.join(os.path.dirname(out_glb), "clips.json"), "w") as f:
    json.dump({"clips": made, "fps": FPS, "kind": kind, "unit": unit, "loops": [n for n in made if CLIPS[n][2]]}, f, indent=2)


def cycles_cpu(samples=32):
    """The pictures below are small: they are drawn on the CPU, so this step never waits for or takes the GPU."""
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"; scene.cycles.samples = samples; scene.cycles.use_denoising = False
    return scene


common.cycles = cycles_cpu
common.look(os.path.join(os.path.dirname(out_glb), "look-rigged"), [mesh])
# Each clip at a third and two thirds of the way: bad weights (a bent shell, a torn bell) show here.
for name in made:
    rig.animation_data.action = bpy.data.actions[name]
    end = round(made[name] * FPS)
    for k, frame in enumerate((end // 3, 2 * end // 3)):
        scene.frame_set(frame)
        common.look(os.path.join(os.path.dirname(out_glb), "pose-%s-%d" % (name, k + 1)), [mesh], size=400, views=("side", "front34"))
rig.animation_data.action = None
