"""make.py's clips step for the fish shape, in Blender: the clips of a fish, an eel, a ray and a seahorse (the kind
is what blender_rig_fish.py rigged), keyframed on the named bones and scaled by the creature's own length, then the
glTF with its skin and clips.

    blender -b -P blender_clips_fish.py -- <rig.blend> <rigged.glb> <idle,swim,jump,...> <id>

Same arguments as blender_clips.py. Every clip is in place (Root is never keyed). idle and swim are loops: a whole
number of beats, so the last frame is the first. Every other clip is a cue and starts and ends in the rest pose.
Turns are written about the creature's own axes (x left, up, forward) so they read the same for every skeleton.
30 frames a second.

The pictures at the end are rendered on the CPU: the GPU is the mesher's."""
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
# Blender axes: the animal's left +X, up +Z, forward -Y. A turn about UP sends the nose left, about LEFT sends it down,
# about BACK sends the left side down.
LEFT, UP, BACK = Vector((1, 0, 0)), Vector((0, 0, 1)), Vector((0, 1, 0))
facts = json.loads(rig["qrx_rig"])
kind, chain = facts["kind"], facts["chain"]
L, H = facts["length"], facts["height"]
size = max(L, H)                                        # every move is scaled by it
base = chain.index("Body")
TAILS = chain[base + 1:]
FRONT = chain[:base][::-1]                              # from Body forward: Chest (an eel's, a seahorse's), Head
middle = Vector((0, 0, H / 2))                          # the middle of the body: what the whole animal turns about
TALL = 0.15                                             # SPEC.md: no taller than this in a clip, where the move allows

# One frame's pose is gathered here (several turns of one bone add up), then written to the bones.
turns, moves = {}, {}
last = {}


def turn(name, axis, degrees):
    """Turn bone `name` by `degrees` about a rest-space axis, after any turn it already has this frame."""
    if name in bones and degrees: turns[name] = Quaternion(axis, math.radians(degrees)) @ turns.get(name, Quaternion())


def move(name, offset):
    if name in bones: moves[name] = moves.get(name, Vector()) + Vector(offset)


def rest_pose():
    turns.clear(); moves.clear()


def apply():
    for b in bones:
        if b.name == "Root": continue
        R = rest[b.name].to_quaternion()
        q = turns.get(b.name, Quaternion())
        shift = moves.get(b.name, Vector())
        if b.name == "Body":                            # the whole animal turns about its middle, not about Body's own end
            head = rest[b.name].translation
            shift = shift + (q @ (head - middle) + middle) - head
        local = R.inverted() @ q @ R
        if b.name in last and last[b.name].dot(local) < 0: local.negate()      # the same turn, the near way round from the last frame
        last[b.name] = local.copy()
        b.rotation_quaternion = local
        b.location = R.inverted() @ shift


def key(frame):
    apply()
    for b in bones:
        if b.name == "Root": continue
        b.keyframe_insert("rotation_quaternion", frame=frame); b.keyframe_insert("location", frame=frame)


def ease(t): return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, t)))
def swell(t): return math.sin(math.pi * ease(t))       # 0 at both ends of a cue, 1 in the middle
def beat(t, n=1.0, lag=0.0): return math.sin(math.tau * n * t - lag)


def clip(name, seconds, body, loop=False):
    frames = round(seconds * FPS)
    action = bpy.data.actions.new(name); action.use_fake_user = True
    rig.animation_data_create(); rig.animation_data.action = action
    last.clear()
    for f in range(0, frames + 1):
        rest_pose()
        if loop: body((f % frames) / frames)             # a loop's last frame is its first
        elif 0 < f < frames: body(f / frames)
        key(f)
    rig.animation_data.action = None
    return action


# -- moves shared by the kinds

def bend(joint, axis, degrees):
    """Bend the chain at its joint number `joint` (0 behind the head), the part behind it going to the animal's right
    for UP and up for LEFT: the bone in front of Body turns one way, a tail bone the other."""
    if joint < base: turn(chain[joint], axis, -degrees)
    else: turn(chain[joint + 1], axis, degrees)


def ripple(t, degrees, beats=1.0, lag=0.9, axis=UP, grow=0.35):
    """A wave that runs from the head to the tail and grows on the way: how a fish and an eel swim."""
    joints = len(chain) - 1
    for j in range(joints):
        gain = grow + (1 - grow) * j / max(joints - 1, 1)
        bend(j, axis, degrees * gain * beat(t, beats, lag * j))
    if axis is UP: turn("Body", UP, -0.25 * degrees * beat(t, beats, lag * base - 0.6))     # the body gives against the tail


def arch(axis, degrees):
    """Every joint bent the same way: a C to the right (UP) or both ends up (LEFT)."""
    for j in range(len(chain) - 1): bend(j, axis, degrees)


def fins(lift=0.0, sweep=0.0):
    """Side fins: lifted (degrees up from rest) and swept back."""
    for name, sign in (("FinL", 1), ("FinR", -1)):
        turn(name, BACK, -sign * lift); turn(name, UP, sign * sweep)


def wings(inner, outer=None, left=1.0, right=1.0):
    """A ray's wings up by `inner` degrees at the body and `outer` more at the tip."""
    outer = inner if outer is None else outer
    turn("WingL1", BACK, -inner * left); turn("WingL2", BACK, -outer * left)
    turn("WingR1", BACK, inner * right); turn("WingR2", BACK, outer * right)


def curl(degrees, sway=0.0, t=0.0):
    """A seahorse's tail: uncurled by `degrees` a bone (less is tighter), and swung from side to side."""
    for i, name in enumerate(TAILS):
        turn(name, LEFT, degrees * (0.7 + 0.3 * i))
        if sway: turn(name, BACK, sway * beat(t, 2, 0.8 * i))


def leap(t, pitch=35.0):
    """Up and down again between t = 0.2 and 0.85, nose up on the way up and down on the way down. Returns how far
    through the air it is (0 on the ground) and the crouch before and after."""
    high = max(0.25 * H, min(0.5 * size, TALL - H - 0.005))
    crouch = math.sin(math.pi * t / 0.2) if t < 0.2 else 0.0
    land = math.sin(math.pi * (t - 0.85) / 0.15) if t > 0.85 else 0.0
    s = (t - 0.2) / 0.65 if 0.2 <= t <= 0.85 else 0.0
    air = math.sin(math.pi * s)
    move("Body", (0, 0, high * air - 0.04 * size * (crouch + land)))
    if pitch and kind != "seahorse":
        most = min(pitch, math.degrees(0.9 * high / (L / 2)))       # the tail never dips under where it started
        turn("Body", LEFT, -most * math.cos(math.pi * s) * air)
    return air, crouch + land


def loop_the_loop(t):
    """A backflip about the middle of the body, lifted clear of the resting plane while it is on end."""
    reach = 0.5 * size + 0.1 * min(L, H)
    up = ease(t / 0.22) if t < 0.5 else ease((1 - t) / 0.22)
    move("Body", (0, 0, max(0.0, reach - H / 2) * up))
    turn("Body", LEFT, -360 * ease((t - 0.12) / 0.76))
    return up


CLIPS = {}

# -- a fish and an eel

if kind in ("fish", "eel"):
    eel = kind == "eel"

    def idle(t):
        ripple(t, 9 if eel else 6, 2, 1.0 if eel else 0.9)
        move("Body", (0, 0, 0.02 * L * beat(t)))
        turn("Body", LEFT, 2 * beat(t, 1, 1.0))
        fins(12 * beat(t, 4), 6 * beat(t, 2, 0.5))
    CLIPS["idle"] = (3.0, idle, True)

    def swim(t):
        ripple(t, 24 if eel else 20, 1, 1.0 if eel else 0.9)
        move("Body", (0, 0, 0.01 * L * beat(t, 2)))
        fins(6 * beat(t, 2), 22)
    CLIPS["swim"] = (1.0 if eel else 0.8, swim, True)

    def jump(t):
        air, low = leap(t)
        arch(UP, 14 * low * (1 if t < 0.5 else -1))
        ripple(t, 16 * air, 4)
        fins(-10 * low + 15 * air, 25 * air)
    CLIPS["jump"] = (1.2, jump, False)

    def spin(t):
        e = math.sin(math.pi * t)
        turn("Body", UP, 360 * ease(t))
        arch(UP, -(24 if eel else 10) * e)               # curled into the turn: an eel nearly to its own tail
        ripple(t, 8 * e, 3)
        fins(10 * e, 15 * e)
    CLIPS["spin"] = (1.5, spin, False)

    def flip(t):
        up = loop_the_loop(t)
        arch(LEFT, (22 if eel else 6) * up)
        ripple(t, 8 * up, 3)
        fins(0, 20 * up)
    CLIPS["flip"] = (1.6, flip, False)

    def dance(t):
        e = math.sin(math.pi * t)
        ripple(t, (20 if eel else 15) * e, 4, 1.2 if eel else 0.9)
        turn("Body", BACK, 14 * e * beat(t, 2))
        move("Body", (0, 0, 0.07 * L * e * abs(beat(t, 2))))
        fins(18 * e * beat(t, 4))
    CLIPS["dance"] = (2.0, dance, False)

    def bow(t):
        e = swell(t)
        turn("Body", LEFT, 22 * e)
        move("Body", (0, 0, 0.4 * L * math.sin(math.radians(22 * e))))      # the tail goes up more than the nose goes down
        turn("Head", LEFT, 8 * e)
        for name in TAILS[-2:]: turn(name, LEFT, 6 * e)
        fins(20 * e)
    CLIPS["bow"] = (1.6, bow, False)

    def wave(t):
        e = swell(t)
        if "FinL" in bones:
            turn("Body", BACK, -12 * e)
            turn("FinL", BACK, -(30 * e + 22 * e * beat(t, 3)))
        else:
            arch(UP, -10 * e)
        for i, name in enumerate(TAILS[-2:]): turn(name, UP, 20 * e * beat(t, 3, 0.7 * i))
    CLIPS["wave"] = (1.6, wave, False)

    def stars(t):
        e = swell(t)
        move("Body", (0, 0, 0.12 * L * e))
        turn("Body", LEFT, -8 * e)
        ripple(t, 5 * e, 6)
        fins(22 * e + 5 * e * beat(t, 6))
    CLIPS["stars"] = (2.0, stars, False)

# -- a ray

if kind == "ray":
    def trail(t, degrees, beats=1.0):
        for i, name in enumerate(TAILS): turn(name, LEFT, degrees * beat(t, beats, 0.8 * i + 1.0))

    def idle(t):
        wings(5 * beat(t), 9 * beat(t, 1, 0.9))
        move("Body", (0, 0, 0.015 * L * beat(t)))
        for i, name in enumerate(TAILS): turn(name, UP, 7 * beat(t, 1, 0.7 * i))
    CLIPS["idle"] = (3.0, idle, True)

    def swim(t):
        wings(18 * beat(t), 26 * beat(t, 1, 1.0))
        move("Body", (0, 0, -0.03 * L * beat(t)))
        turn("Body", LEFT, 3 * beat(t, 1, -math.pi / 2))
        trail(t, 6)
    CLIPS["swim"] = (1.4, swim, True)

    def jump(t):
        air, low = leap(t, 25)
        wings(18 * low - 22 * air * math.cos(math.pi * (t - 0.2) / 0.65), 24 * low - 30 * air * math.cos(math.pi * (t - 0.2) / 0.65))
        trail(t, 8 * air, 2)
    CLIPS["jump"] = (1.2, jump, False)

    def spin(t):
        e = math.sin(math.pi * t)
        turn("Body", BACK, 14 * e)                       # banked into the turn
        turn("Body", UP, 360 * ease(t))
        wings(8 * e * beat(t, 2), 14 * e * beat(t, 2, 0.9))
        for i, name in enumerate(TAILS): turn(name, UP, 12 * e)
    CLIPS["spin"] = (1.6, spin, False)

    def flip(t):
        up = loop_the_loop(t)
        wings(10 * up, 16 * up)
        trail(t, 6 * up, 2)
    CLIPS["flip"] = (1.8, flip, False)

    def wave(t):
        e = swell(t)
        turn("Body", BACK, -8 * e)
        wings(28 * e, 18 * e + 24 * e * beat(t, 3), right=0.0)
        wings(-4 * e, left=0.0)
    CLIPS["wave"] = (1.8, wave, False)

    def dance(t):
        e = math.sin(math.pi * t)
        a = beat(t, 2)
        wings(20 * e * a, 28 * e * beat(t, 2, 0.6), right=-1.0)      # one wing up as the other goes down
        turn("Body", UP, 12 * e * beat(t, 2, 0.5))
        move("Body", (0, 0, 0.06 * L * e * abs(a)))
        for i, name in enumerate(TAILS): turn(name, UP, 14 * e * beat(t, 4, 0.8 * i))
    CLIPS["dance"] = (2.0, dance, False)

    def bow(t):
        e = swell(t)
        turn("Body", LEFT, 20 * e)
        move("Body", (0, 0, 0.4 * L * math.sin(math.radians(20 * e))))
        wings(-10 * e, -14 * e)
        for name in TAILS: turn(name, LEFT, 6 * e)
    CLIPS["bow"] = (1.6, bow, False)

    def stars(t):
        e = swell(t)
        move("Body", (0, 0, 0.12 * L * e))
        turn("Body", LEFT, -6 * e)
        wings(14 * e, 20 * e + 5 * e * beat(t, 6))
        for i, name in enumerate(TAILS): turn(name, UP, 5 * e * beat(t, 6, 0.8 * i))
    CLIPS["stars"] = (2.0, stars, False)

# -- a seahorse: upright, the head at the top and the tail curled under it

if kind == "seahorse":
    def idle(t):
        move("Body", (0, 0, 0.02 * H * beat(t)))
        turn("Body", UP, 4 * beat(t, 1, 0.8))
        turn("Chest", LEFT, 2 * beat(t, 1, 1.0))
        turn("Head", LEFT, 5 * beat(t))
        curl(4 * beat(t, 1, 0.5))
    CLIPS["idle"] = (3.0, idle, True)

    def swim(t):
        turn("Body", LEFT, 10 + 2 * beat(t))             # leaning into the swim
        turn("Body", BACK, 3 * beat(t, 2))
        move("Body", (0, 0, 0.03 * H * beat(t, 1, 0.5)))
        turn("Head", LEFT, -7 + 3 * beat(t, 1, 0.5))
        curl(6 + 5 * beat(t, 1, 1.0), 4, t / 2)
    CLIPS["swim"] = (1.2, swim, True)

    def jump(t):
        air, low = leap(t, 0)
        curl(-8 * low + 22 * air)
        turn("Head", LEFT, 8 * low - 8 * air)
        turn("Chest", LEFT, 6 * low)
    CLIPS["jump"] = (1.2, jump, False)

    def spin(t):
        e = math.sin(math.pi * t)
        turn("Body", LEFT, 8 * e)
        turn("Body", UP, 360 * ease(t))
        turn("Head", UP, -12 * e)
        curl(10 * e, 8 * e, t)
    CLIPS["spin"] = (1.6, spin, False)

    def flip(t):
        up = loop_the_loop(t)
        curl(-6 * up)
        turn("Head", LEFT, 6 * up)
    CLIPS["flip"] = (1.8, flip, False)

    def bow(t):
        e = swell(t)
        turn("Body", LEFT, 6 * e)
        turn("Chest", LEFT, 26 * e)
        turn("Head", LEFT, 22 * e)
        curl(-6 * e)
    CLIPS["bow"] = (1.8, bow, False)

    def dance(t):
        e = math.sin(math.pi * t)
        turn("Body", BACK, 13 * e * beat(t, 2))
        move("Body", (0, 0, 0.08 * H * e * abs(beat(t, 2))))
        turn("Chest", BACK, -5 * e * beat(t, 2))
        turn("Head", BACK, -8 * e * beat(t, 2, 0.4))
        curl(8 * e * beat(t, 2), 12 * e, t)
    CLIPS["dance"] = (2.0, dance, False)

    def wave(t):
        e = swell(t)
        turn("Body", BACK, -9 * e)
        turn("Head", BACK, -10 * e + 9 * e * beat(t, 3))
        curl(6 * e, 10 * e, t * 1.5)
    CLIPS["wave"] = (1.6, wave, False)

    def stars(t):
        e = swell(t)
        move("Body", (0, 0, 0.1 * H * e))
        turn("Chest", LEFT, -5 * e)
        turn("Head", LEFT, -12 * e)
        curl(10 * e + 3 * e * beat(t, 6))
    CLIPS["stars"] = (2.0, stars, False)

unknown = [c for c in wanted if c not in CLIPS]
if unknown: raise SystemExit("make: no clip written for %s" % ", ".join(unknown))
made = {}
for name in wanted:
    seconds, body, loop = CLIPS[name]
    clip(name, seconds, body, loop)
    made[name] = seconds
common.log("clips for a %s:" % kind, ", ".join("%s %.1f s" % kv for kv in made.items()))

for o in scene.objects: o.select_set(o in (rig, mesh))
bpy.context.view_layer.objects.active = rig
rest_pose(); last.clear(); apply()
bpy.ops.export_scene.gltf(filepath=out_glb, use_selection=True, export_format="GLB", export_image_format="JPEG", export_jpeg_quality=92,
                          export_yup=True, export_apply=False, export_skins=True, export_all_influences=False, export_def_bones=False,
                          export_animations=True, export_animation_mode="ACTIONS", export_force_sampling=True, export_frame_step=1,
                          export_optimize_animation_size=True, export_armature_object_remove=True, export_rest_position_armature=True,
                          export_anim_slide_to_zero=True, export_bake_animation=False, export_vertex_color="NONE", export_morph=False)
with open(os.path.join(os.path.dirname(out_glb), "clips.json"), "w") as f:
    json.dump({"clips": made, "fps": FPS, "kind": kind, "length": L, "height": H}, f, indent=2)


def cycles_on_cpu(samples=32):
    scene.render.engine = "CYCLES"; scene.cycles.device = "CPU"
    scene.cycles.samples = samples; scene.cycles.use_denoising = False
    return scene


common.cycles = cycles_on_cpu                            # common.look renders through it: never the GPU from this step
common.look(os.path.join(os.path.dirname(out_glb), "look-rigged"), [mesh])
# Each clip at a third and two thirds of the way: bad weights (a fin that tears, a body that collapses) show here.
for name in made:
    rig.animation_data.action = bpy.data.actions[name]
    end = round(made[name] * FPS)
    for k, frame in enumerate((end // 3, 2 * end // 3)):
        scene.frame_set(frame)
        common.look(os.path.join(os.path.dirname(out_glb), "pose-%s-%d" % (name, k + 1)), [mesh], size=400, views=("side", "front34"))
rig.animation_data.action = None
