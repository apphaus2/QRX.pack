"""make.py's clips step for the crawler shape, in Blender: the clips of the many-legged walkers (beetles, bees,
spiders, the scorpion, crabs), keyframed on the bones blender_rig_crawler.py made and scaled by the creature's own
legs, then the glTF with its skin and clips.

    blender -b -P blender_clips_crawler.py -- <rig.blend> <rigged.glb> <idle,walk,spin,...> <id>

Every clip is in place (Root is never keyed) and every cue starts and ends in the rest pose. Turns are written about
the model's axes (x left, up, forward) so they read the same for every skeleton. 30 frames a second.

A leg steps by where its foot should go, not by a fixed turn: forward and back along the way the creature walks
(glTF +Z), lifted on the way forward. A leg that stands out to the side swings about its hip; one that points along
the way reaches and folds. So a crab, whose own front is across the model, walks sideways with the same rule.
A bee is in the air in every clip: its wings beat in each, and its idle is a hover.

QRX_LOOK=cpu renders the pictures on the CPU (when the GPU is busy); QRX_LOOK=none writes none."""
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
tips = {b.name: b.bone.tail_local.copy() for b in bones}
facts = json.load(open(os.path.join(os.path.dirname(rig_blend), "rig.json")))
KIND, absent = facts["kind"], set(facts.get("absent", []))
BEE = KIND == "bee"
# Blender axes: the model's left +X, up +Z, forward -Y. A pitch about +X sends the nose down.
LEFT, UP, BACK = Vector((1, 0, 0)), Vector((0, 0, 1)), Vector((0, 1, 0))
FORWARD = -BACK
high = max(rest["Body"].translation.z, 0.004)                # the height of the middle of the body: moves are scaled by it
lo, hi = common.bounds([mesh])
top, half_width = hi.z, max(hi.x, -lo.x)
ground = Vector((rest["Root"].translation.x, rest["Root"].translation.y, 0))
centre = (rest["Body"].translation + tips["Body"]) / 2


def has(name): return name in bones and name not in absent
def turn(axis, degrees): return Quaternion(axis, math.radians(degrees))
def clamp(v, most): return max(-most, min(most, v))
def ease(t): return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, t)))
def there_and_back(t, rise=0.25): return ease(t / rise) if t < 0.5 else ease((1 - t) / rise)


def pose(name, q=None, offset=None, pivot=None):
    """Turn bone `name` by q, written in the model's rest axes (and move it by a rest-space offset); about `pivot`
    when one is given, else about the bone's own head. Keyed by the caller."""
    if name not in bones: return
    b = bones[name]
    R = rest[name].to_quaternion()
    q = q if q is not None else Quaternion()
    b.rotation_quaternion = R.inverted() @ q @ R
    move = Vector(offset) if offset is not None else Vector()
    if pivot is not None:
        head = rest[name].translation
        move += (q @ (head - pivot) + pivot) - head
    b.location = R.inverted() @ move


def key(frame):
    for b in bones:
        if b.name == "Root": continue
        b.keyframe_insert("rotation_quaternion", frame=frame); b.keyframe_insert("location", frame=frame)


def rest_pose():
    for b in bones: b.rotation_quaternion = Quaternion(); b.location = Vector()


def clip(name, seconds, body, loop=False):
    frames = round(seconds * FPS)
    action = bpy.data.actions.new(name); action.use_fake_user = True
    rig.animation_data_create(); rig.animation_data.action = action
    step = 2 if frames > 40 and not BEE else 1               # a bee's wings need every frame
    for f in range(0, frames + 1, step):
        rest_pose()
        if loop or 0 < f < frames: body(f, f / frames)       # a loop's two ends are the same pose, not the rest pose
        key(f)
    if frames % 2 and step == 2:
        rest_pose()
        if loop: body(frames, 1.0)
        key(frames)
    rig.animation_data.action = None
    return action


# ---- limbs: what each one's bones allow
class Limb:
    """A two-bone limb (Leg + Shin, Claw + Pincer): which way it stands out, how far, and its foot put where it is
    asked (`to`, an offset from where the foot rests) by bending the knee and swinging the hip."""
    def __init__(self, upper, lower):
        self.upper, self.lower = upper, lower
        hip, knee, foot = rest[upper].translation, rest[lower].translation, tips[lower]
        self.hip, self.knee, self.foot = hip, knee, foot
        out = Vector((foot.x - hip.x, foot.y - hip.y, 0))
        self.l1, self.l2 = (knee - hip).length, (foot - knee).length
        self.length = self.l1 + self.l2
        if out.length < 0.15 * self.length:                   # a leg that hangs straight down: out is away from the body
            out = Vector((hip.x - centre.x, hip.y - centre.y, 0))
            if out.length < 1e-6: out = LEFT.copy()
        self.reach = max(out.length, 0.3 * self.length)
        self.out = out.normalized()
        self.lift = self.out.cross(UP)                        # a turn about it raises the foot
        hinge = (knee - hip).cross(foot - knee)
        self.hinge = hinge.normalized() if hinge.length > 1e-3 * self.l1 * self.l2 else self.lift
        self.clear()

    def clear(self): self.yaw = self.raise_ = self.fold = 0.0; self.to = Vector()

    def apply(self):
        swing, bend = Quaternion(), Quaternion()
        if self.to.length > 1e-7 and self.l1 > 1e-6 and self.l2 > 1e-6:
            target = self.foot + self.to
            far = max(abs(self.l1 - self.l2) * 1.05 + 1e-6, min((target - self.hip).length, self.length * 0.999))
            def angle(d): return math.acos(max(-1.0, min(1.0, (self.l1 ** 2 + self.l2 ** 2 - d * d) / (2 * self.l1 * self.l2))))
            change = angle(far) - angle((self.foot - self.hip).length)
            def foot_at(a): return self.knee + Quaternion(self.hinge, a) @ (self.foot - self.knee)
            change = min((change, -change), key=lambda a: abs((foot_at(a) - self.hip).length - far))
            bend = Quaternion(self.hinge, change)
            swing = (foot_at(change) - self.hip).rotation_difference(target - self.hip)
        pose(self.upper, turn(UP, clamp(self.yaw, 40)) @ turn(self.lift, clamp(self.raise_, 80)) @ swing)
        pose(self.lower, turn(self.lift, clamp(self.fold, 70)) @ bend)


LEGS = []
for k in range(1, 5):
    for side in "LR":
        name = "%d%s" % (k, side)
        if has("Leg" + name):
            leg = Limb("Leg" + name, "Shin" + name)
            leg.number, leg.side = k, side
            leg.phase = math.pi * ((k + (side == "R")) % 2) - 0.25 * k      # every other leg together, a ripple down the body
            LEGS.append(leg)
CLAWS = {side: Limb("Claw" + side, "Pincer" + side) for side in "LR" if has("Claw" + side)}
reaches = sorted(leg.reach for leg in LEGS)
STRIDE = 0.32 * reaches[len(reaches) // 2] if reaches else 0.0
lengths = sorted(leg.length for leg in LEGS)
STEP_UP = 0.14 * lengths[len(lengths) // 2] if lengths else 0.0
FRONT = [leg for leg in LEGS if leg.number == 1]


def limbs_clear():
    for limb in LEGS + list(CLAWS.values()): limb.clear()


def limbs_apply():
    for limb in LEGS + list(CLAWS.values()): limb.apply()


def legs_step(t, cycles=1.0, amount=1.0, lift=1.0, way=None):
    """Each leg's foot goes forward lifted and back along the ground, along `way` (the way the creature walks)."""
    for leg in LEGS:
        phase = math.tau * cycles * t + leg.phase
        leg.to += ((way(leg) if way else FORWARD) * STRIDE * math.sin(phase) + UP * STEP_UP * lift * max(0.0, math.cos(phase))) * amount


def around(leg):
    """The way a leg's foot goes when the body turns to its left on the spot."""
    r = Vector((leg.hip.x - ground.x, leg.hip.y - ground.y, 0))
    return UP.cross(r).normalized() if r.length > 1e-6 else FORWARD


def plant(q=None, pivot=None, offset=None, legs=None):
    """The feet stay where they stand while the body turns by q about `pivot` and moves by `offset`: each leg is
    asked to reach back to its own footprint."""
    q = q if q is not None else Quaternion()
    pivot = pivot if pivot is not None else centre
    offset = Vector(offset) if offset is not None else Vector()
    back = q.inverted()
    for leg in (LEGS if legs is None else legs):
        leg.to += back @ (leg.foot - offset - pivot) + pivot - leg.foot


def sink(drop):
    """The body `drop` metres lower (higher when negative) with the feet where they were: returns Body's offset."""
    plant(offset=(0, 0, -drop))
    return Vector((0, 0, -drop))


def tail(t, sway, curl=0.0, speed=1.0, phase=0.0):
    for i in range(1, 7):
        name = "Tail%d" % i
        if name in bones:
            s = math.sin(math.tau * speed * t - 0.5 * i + phase)
            pose(name, turn(UP, sway * s * (0.6 + 0.2 * i)) @ turn(LEFT, curl * math.sin(math.tau * speed * t + phase)))


def feelers(t, amount=1.0):
    for side, sign in (("L", 1), ("R", -1)):
        pose("Antenna" + side, turn(UP, 10 * amount * sign * math.sin(math.tau * 2 * t + sign)) @ turn(LEFT, 8 * amount * math.sin(math.tau * 3 * t + 0.7 * sign)))


def wings(beat, amount=1.0):
    """The wings at `beat` (in turns: one is a whole beat). Two wings open from the back and beat; a mesh whose wings
    are one piece lifts and lowers it."""
    s = math.sin(math.tau * beat)
    if has("WingL") and has("WingR"):
        for side, sign in (("L", 1), ("R", -1)):
            pose("Wing" + side, turn(UP, -sign * 24 * amount) @ turn(BACK, -sign * (16 + 26 * s) * amount))
    else:
        for side in "LR":
            if has("Wing" + side): pose("Wing" + side, turn(LEFT, (7 + 9 * s) * amount))


def hover(t, seconds, amount=1.0, beats=6.0):
    """What a bee does all the time: the wings, and the legs hanging a little back."""
    wings(round(beats * seconds) * t, amount)
    for leg in LEGS:
        leg.raise_ += 6 * amount; leg.fold += -8 * amount * (1 + 0.3 * math.sin(math.tau * 2 * t + leg.number))


def claws_rest(t, amount=1.0):
    for side, sign in (("L", 1), ("R", -1)):
        if side in CLAWS:
            CLAWS[side].raise_ += 5 * amount * (1 + math.sin(math.tau * t + sign))
            CLAWS[side].fold += 7 * amount * math.sin(math.tau * 2 * t + 1.3 * sign)


CLIPS = {}


def idle(f, t):
    limbs_clear()
    if BEE:
        hover(t, 3.0, beats=5.0)
        pose("Body", turn(UP, 5 * math.sin(math.tau * t)), offset=(0, 0, 0.12 * high * math.sin(math.tau * 2 * t)))
        pose("Abdomen", turn(LEFT, -5 * math.sin(math.tau * 2 * t)))
    else:
        pose("Body", offset=sink(0.05 * high * math.sin(math.tau * (1 if KIND == "spider" else 2) * t)))
        pose("Abdomen", turn(LEFT, 2.5 * math.sin(math.tau * 2 * t)))
        if KIND == "spider":                                    # a front foot feels the ground now and then
            for leg in FRONT: leg.raise_ += 10 * max(0.0, math.sin(math.tau * 2 * t + (0 if leg.side == "L" else math.pi))) ** 2
    pose("Head", turn(UP, 5 * math.sin(math.tau * t)) @ turn(LEFT, 3 * math.sin(math.tau * 2 * t)))
    feelers(t)
    tail(t, 4, 3, 1.0)
    claws_rest(t)
    limbs_apply()
CLIPS["idle"] = (3.0, idle, True)


def walk(f, t):
    limbs_clear()
    legs_step(t)
    pose("Body", turn(UP, 2 * math.sin(math.tau * t)), offset=(0, 0, 0.025 * high * math.sin(math.tau * 2 * t)))
    pose("Abdomen", turn(UP, -3 * math.sin(math.tau * t)))
    pose("Head", turn(UP, -2 * math.sin(math.tau * t)))
    feelers(t, 0.8)
    tail(t, 5, 2, 1.0)
    claws_rest(t, 0.6)
    if BEE: wings(4 * t, 0.5)
    limbs_apply()
CLIPS["walk"] = ({"spider": 0.7, "crab": 0.7, "scorpion": 0.8}.get(KIND, 0.6), walk, True)


def fly(f, t):
    limbs_clear()
    wings(4 * t)
    for leg in LEGS: leg.raise_ += 10; leg.fold += -14 - 3 * math.sin(math.tau * t + leg.number)
    pose("Body", turn(LEFT, 7), offset=(0, 0, 0.1 * high * math.sin(math.tau * 2 * t)), pivot=centre)
    pose("Abdomen", turn(LEFT, -6 + 3 * math.sin(math.tau * 2 * t)))
    pose("Head", turn(LEFT, -4))
    feelers(t, 0.6)
    limbs_apply()
CLIPS["fly"] = (0.5, fly, True)


def spin(f, t):
    limbs_clear()
    env = math.sin(math.pi * t)
    if BEE: hover(t, 1.2, min(1.0, 4 * env))
    else: legs_step(t, 4, min(1.0, 3 * env), way=around)
    pose("Body", turn(UP, 360 * ease(t)), pivot=ground)
    pose("Abdomen", turn(UP, -8 * env))
    pose("Head", turn(UP, 8 * env))
    feelers(t, env)
    tail(t, 8 * env, 0, 2.0)
    limbs_apply()
CLIPS["spin"] = (1.2 if BEE else 1.5, spin, False)


def dead(f, t):
    limbs_clear()
    e = there_and_back(t)
    a = math.radians(180 * e)
    # Onto its back: the middle of the body goes to where the back can lie on the ground, the side clearing it on the way.
    lying = (top - centre.z) - centre.z
    over = max(0.0, half_width - centre.z) * math.sin(a)
    for leg in LEGS:
        twitch = 4 * e * math.sin(math.tau * 6 * t + leg.number)
        leg.raise_ += -22 * e + twitch; leg.fold += -34 * e + twitch
    for claw in CLAWS.values(): claw.fold += -20 * e
    pose("Body", turn(BACK, 180 * e), offset=(0, 0, lying * e + over), pivot=centre)
    pose("Head", turn(LEFT, 6 * e))
    limbs_apply()
CLIPS["dead"] = (3.0, dead, False)


def jump(f, t):
    limbs_clear()
    crouch = math.sin(math.pi * min(1.0, t / 0.3)) if t < 0.3 else 0.0
    land = math.sin(math.pi * (t - 0.75) / 0.25) if t > 0.75 else 0.0
    air = math.sin(math.pi * (t - 0.25) / 0.5) if 0.25 < t < 0.75 else 0.0
    offset = sink(0.35 * high * (crouch + land))
    offset.z += 2.2 * high * air
    for leg in LEGS: leg.raise_ += -14 * air; leg.fold += -24 * air
    pose("Body", turn(LEFT, -6 * air), offset=offset, pivot=centre)
    pose("Abdomen", turn(LEFT, 8 * air))
    tail(t, 0, -6 * air, 1.0, math.pi / 2)
    if BEE: hover(t, 1.0, math.sin(math.pi * t))
    limbs_apply()
CLIPS["jump"] = (1.0, jump, False)


def dance(f, t):
    limbs_clear()
    e = math.sin(math.pi * t)
    if BEE:                                                      # the waggle: a figure of eight, the abdomen wagging
        hover(t, 2.0, min(1.0, 4 * e))
        pose("Body", turn(UP, 26 * e * math.sin(math.tau * 2 * t)) @ turn(BACK, 10 * e * math.sin(math.tau * 4 * t)),
             offset=(1.2 * high * e * math.sin(math.tau * 2 * t), 0, 0.5 * high * e * (1 - math.cos(math.tau * 4 * t))), pivot=centre)
        pose("Abdomen", turn(UP, 22 * e * math.sin(math.tau * 9 * t)))
    else:
        offset = Vector((0, 0, -0.3 * high * e * (0.5 - 0.5 * math.cos(math.tau * 4 * t))))
        sway = turn(UP, 12 * e * math.sin(math.tau * 2 * t)) @ turn(BACK, 7 * e * math.sin(math.tau * 2 * t))
        plant(sway, centre, offset)
        pose("Body", sway, offset=offset, pivot=centre)
        pose("Abdomen", turn(UP, 10 * e * math.sin(math.tau * 4 * t)))
        for leg in FRONT:                                         # the front feet tap in turn
            leg.raise_ += 38 * e * max(0.0, math.sin(math.tau * 2 * t + (0 if leg.side == "L" else math.pi)))
        for sign, claw in ((1, CLAWS.get("L")), (-1, CLAWS.get("R"))):
            if claw: claw.raise_ += 30 * e * (0.5 + 0.5 * math.sin(math.tau * 2 * t + sign)); claw.fold += 14 * e * math.sin(math.tau * 4 * t)
    pose("Head", turn(BACK, 9 * e * math.sin(math.tau * 4 * t)))
    feelers(t, e)
    tail(t, 10 * e, 0, 4.0)
    limbs_apply()
CLIPS["dance"] = (2.0, dance, False)


def wave(f, t):
    limbs_clear()
    e = math.sin(math.pi * ease(t))
    # The larger claw waves (a fiddler's one great claw); a creature without claws waves a front foot.
    arm = max(CLAWS.values(), key=lambda c: c.length) if CLAWS else (FRONT[0] if FRONT else None)
    if arm:
        arm.raise_ += 48 * e
        arm.fold += 18 * e + 22 * e * math.sin(math.tau * 3 * t)
        arm.yaw += 10 * e * math.sin(math.tau * 3 * t)
    lean = turn(BACK, -4 * e * (1 if arm and arm.hip.x >= centre.x else -1))
    plant(lean, centre)
    pose("Body", lean, pivot=centre)
    tail(t, 6 * e, 0, 2.0)
    limbs_apply()
CLIPS["wave"] = (1.6, wave, False)


def sunrise(f, t):
    """The scarab's own: it rears up, front feet lifted like a sun held high, turns a slow circle and comes down."""
    limbs_clear()
    e = there_and_back(t, 0.2)
    hind = Vector((centre.x, hi.y, 0.3 * high))                  # the low end of its back: nothing sinks when it rears
    spin_q = turn(UP, 360 * ease((t - 0.15) / 0.7))
    rear_q = turn(LEFT, -30 * e)
    plant(rear_q, hind, legs=[leg for leg in LEGS if leg.number > 1])
    for leg in FRONT:
        leg.raise_ += 55 * e + 8 * e * math.sin(math.tau * 3 * t + (0 if leg.side == "L" else math.pi)); leg.fold += 25 * e
    legs_step(t, 5, 0.6 * min(1.0, 3 * math.sin(math.pi * t)), 0.6, way=around)
    head = rest["Body"].translation
    reared = rear_q @ (head - hind) + hind                       # first up about the hind end, then round about the ground
    pose("Body", spin_q @ rear_q, offset=(spin_q @ (reared - ground) + ground) - head)
    pose("Head", turn(LEFT, -10 * e))
    feelers(t, e)
    limbs_apply()
CLIPS["sunrise"] = (2.6, sunrise, False)


def flip(f, t):
    limbs_clear()
    e = math.sin(math.pi * t)
    hover(t, 1.0, min(1.0, 4 * e))
    pose("Body", turn(LEFT, -360 * ease((t - 0.1) / 0.8)), offset=(0, 0, 2.5 * high * e), pivot=centre)
    pose("Abdomen", turn(LEFT, 10 * e))
    limbs_apply()
CLIPS["flip"] = (1.0, flip, False)


def crown(f, t):
    """The honeycrown's own: it rises, lifts its head to show the crown and turns a slow circle with it."""
    limbs_clear()
    e = there_and_back(t, 0.2)
    hover(t, 2.2, min(1.0, 5 * math.sin(math.pi * t)))
    pose("Body", turn(UP, 360 * ease((t - 0.15) / 0.7)) @ turn(LEFT, -14 * e), offset=(0, 0, 1.2 * high * e), pivot=Vector((ground.x, ground.y, centre.z)))
    pose("Head", turn(LEFT, -16 * e) @ turn(BACK, 8 * e * math.sin(math.tau * 3 * t)))
    pose("Abdomen", turn(LEFT, 12 * e))
    feelers(t, e)
    limbs_apply()
CLIPS["crown"] = (2.2, crown, False)

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
with open(os.path.join(os.path.dirname(out_glb), "clips.json"), "w") as f:
    json.dump({"clips": made, "fps": FPS, "kind": KIND, "high": high, "stride": STRIDE, "legs": [leg.upper for leg in LEGS]}, f, indent=2)
look = os.environ.get("QRX_LOOK", "")
if look == "cpu":
    def _cycles_cpu(samples=32):
        scene.render.engine = "CYCLES"; scene.cycles.device = "CPU"; scene.cycles.samples = samples; scene.cycles.use_denoising = False
        return scene
    common.cycles = _cycles_cpu
if look != "none":
    common.look(os.path.join(os.path.dirname(out_glb), "look-rigged"), [mesh])
    # Each clip at a third and two thirds of the way: bad weights (a leg that collapses, a torn belly) show here.
    for name in made:
        rig.animation_data.action = bpy.data.actions[name]
        end = round(made[name] * FPS)
        for k, frame in enumerate((end // 3, 2 * end // 3)):
            scene.frame_set(frame)
            common.look(os.path.join(os.path.dirname(out_glb), "pose-%s-%d" % (name, k + 1)), [mesh], size=400, views=("side", "front34"))
    rig.animation_data.action = None
