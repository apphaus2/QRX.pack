"""make.py's clips step for the bird shape, in Blender: the clips of a standing bird or of a bat in flight (the kind
blender_rig_bird.py gave the skeleton), keyframed on the named bones and scaled by the creature's own body, then the
glTF with its skin and clips.

    blender -b -P blender_clips_bird.py -- <rig.blend> <rigged.glb> <idle,fly,jump,...> <id>

Every clip is in place (Root is never keyed). idle and fly are loops; every other clip is a cue that starts and ends in
the rest pose. A bird's rest pose is the picture's: standing, wings folded. Its idle stands and looks about; fly opens
the wings, lays the body level and tucks the legs. A bat's rest pose is in flight: its idle hangs in the air on slow
beats. Turns are written about the creature's own axes (x left, up, forward). 30 frames a second."""
import json, math, os, sys
import bpy
from mathutils import Matrix, Quaternion, Vector
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
head0 = {b.name: b.bone.head_local.copy() for b in bones}
tail0 = {b.name: b.bone.tail_local.copy() for b in bones}
parent = {b.name: (b.parent.name if b.parent else None) for b in bones}
kind = rig.get("kind") or ("bird" if "LegL" in bones else "bat")
# Blender axes: the animal's left +X, up +Z, forward -Y. A pitch about +X sends the nose down and a hanging leg back;
# a turn about +Z sends the nose to the animal's left.
LEFT, UP, BACK = Vector((1, 0, 0)), Vector((0, 0, 1)), Vector((0, 1, 0))
SIDES = (("L", 1), ("R", -1))
IDLE_HOVERS = False        # True: a bird's idle beats its wings in the air (as the drawn birds' did) instead of standing

tall = max((mesh.matrix_world @ v.co).z for v in mesh.data.vertices)
spine = (tail0["Body"] - head0["Body"]).normalized()                # from the hips to the chest
centre = (head0["Body"] + tail0["Body"]) / 2
tilt = math.degrees(math.atan2(spine.z, -spine.y))                   # how far the body stands up from level
dorsal = Vector((0, spine.z, -spine.y))                              # square to the spine, towards the back
leg = max(head0["ShinL"].z, 0.01) if kind == "bird" else max(centre.z, 0.01)     # where the legs leave the body: moves are scaled by it


def rad(d): return math.radians(d)
def turn_x(d): return Quaternion(LEFT, rad(d))
def turn_up(d): return Quaternion(UP, rad(d))
def turn_back(d): return Quaternion(BACK, rad(d))
def ease(t): return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, t)))
def bump(t, a, b): return math.sin(math.pi * (t - a) / (b - a)) ** 2 if a < t < b else 0.0      # 0 at a and b, 1 between
def step(t, a, b): return ease((t - a) / (b - a))


class Pose:
    """One frame's pose. turn() gives a bone a turn relative to its parent, written in the rest pose's axes (and a move,
    and a point to turn about); it keeps where each bone's head has gone and how far it has turned in all, so legs
    can be planted and wings held to the body's frame. Parents are posed before their children."""
    def __init__(self): self.local, self.q, self.at, self.size = {}, {}, {}, {}

    def world(self, name):
        if name not in self.q: self.turn(name)
        return self.q[name], self.at[name]

    def turn(self, name, q=None, offset=None, pivot=None):
        q = q if q is not None else Quaternion()
        move = Vector(offset) if offset is not None else Vector()
        if pivot is not None: move += (q @ (head0[name] - pivot) + pivot) - head0[name]
        p = parent[name]
        if p:
            pq, pat = self.world(p)
            self.q[name], self.at[name] = pq @ q, pat + pq @ (head0[name] + move - head0[p])
        else:
            self.q[name], self.at[name] = q, head0[name] + move
        self.local[name] = (q, move)

    def apply(self):
        for b in bones:
            q, move = self.local.get(b.name, (Quaternion(), Vector()))
            R = rest[b.name].to_quaternion()
            b.rotation_quaternion = R.inverted() @ q @ R
            b.location = R.inverted() @ move
            b.scale = (self.size.get(b.name, 1.0),) * 3


def key(frame):
    for b in bones:
        if b.name == "Root": continue
        b.keyframe_insert("rotation_quaternion", frame=frame); b.keyframe_insert("location", frame=frame)
        if b.name in GROWS: b.keyframe_insert("scale", frame=frame)


def rest_pose():
    for b in bones: b.rotation_quaternion = Quaternion(); b.location = Vector(); b.scale = (1, 1, 1)


def clip(name, seconds, body, loop=False):
    frames = round(seconds * FPS)
    action = bpy.data.actions.new(name); action.use_fake_user = True
    rig.animation_data_create(); rig.animation_data.action = action
    last = None
    for f in list(range(0, frames, 2 if frames > 40 else 1)) + [frames]:
        rest_pose()
        if loop or 0 < f < frames:                      # a loop's first and last frames are the same pose; a cue's are the rest pose
            P = Pose(); body(P, f % frames if loop else f, (f % frames) / frames if loop else f / frames); P.apply()
        # Neighbouring keys keep to the same side of the quaternion sphere, so a full turn is read as one turn.
        now = {b.name: b.rotation_quaternion.copy() for b in bones}
        if last:
            for b in bones:
                if now[b.name].dot(last[b.name]) < 0: b.rotation_quaternion = -now[b.name]; now[b.name] = -now[b.name]
        last = now
        key(f)
    rig.animation_data.action = None
    return action


# ---- the parts of a bird -----------------------------------------------------------------------------------------

def frame_turn(d0, n0, d1, n1):
    """The turn that takes the direction d0 with the normal n0 to d1 with n1."""
    def frame(d, n):
        d = d.normalized(); n = (n - d * d.dot(n)).normalized()
        return Matrix((d, n, d.cross(n))).transposed()
    return (frame(d1, n1) @ frame(d0, n0).transposed()).to_quaternion()


SWEEP = 14.0        # degrees an open wing points back from straight out
GROW = 1.45         # a folded wing is short: opened, it grows to this many times its folded size
GROWS = ("WingL", "WingR") if kind == "bird" else ()        # the bones whose size is keyed
HALF = 78.0         # and a wing that has only begun to open: it comes off the body swept right back, then swings out


def opened(s, sign, spread, along):
    """The turn, in the body's rest frame, that opens a bird's folded wing by `spread`: the folded wing's outer face
    becomes the open wing's top, and `along` is the open wing's fore and aft line. Part open, the wing lies flat and
    swept back rather than hanging."""
    spread = max(0.0, min(1.0, spread))
    sweep = rad(HALF + (SWEEP - HALF) * spread)
    folded = (tail0["Wing" + s + "Tip"] - head0["Wing" + s]).normalized()
    out = LEFT * sign * math.cos(sweep) - along * math.sin(sweep)
    flat = frame_turn(folded, LEFT * sign, out, Vector((0, along.z, -along.y)))
    off = min(1.0, spread / 0.35)
    return Quaternion().slerp(flat, off * off * (3 - 2 * off))


def wings(P, spread=1.0, up=0.0, lag=0.0, pitch=0.0):
    """Both wings: opened by `spread` (0 folded to 1 flat; a bat's are always open), lifted `up` degrees, the hand a
    further `lag` degrees. A bird's open wings lie level with the ground, not along its body, which stands up from it:
    `pitch` is how far the body has already been brought down (the whole of LEVEL in flight)."""
    along = turn_x(max(0.0, tilt - 8.0 - pitch)) @ spine if kind == "bird" else spine
    for s, sign in SIDES:
        q = Quaternion(along, sign * rad(up))
        if kind == "bird": q = q @ opened(s, sign, spread, along)
        P.turn("Wing" + s, q)
        if kind == "bird": P.size["Wing" + s] = 1 + (GROW - 1) * max(0.0, min(1.0, spread))
        P.turn("Wing" + s + "Tip", q.inverted() @ Quaternion(along, sign * rad(lag)) @ q)


def plant(P, s, lift=0.0, forward=0.0, toe=0.0):
    """Keep the foot of leg s where it stands (or `lift` above and `forward` of it) whatever the body has done: the hip
    goes with the body, the knee and the ankle bend in the leg's own plane. Out of reach, the leg hangs straight."""
    qb, _ = P.world("Body")
    hip = P.at["Body"] + qb @ (head0["Leg" + s] - head0["Body"])
    h0, k0, a0 = head0["Leg" + s], head0["Shin" + s], head0["Foot" + s]
    def flat(v): return (v.y, v.z)
    def cross(u, v): return u[0] * v[1] - u[1] * v[0]
    def angle(u, v): return math.atan2(cross(u, v), u[0] * v[0] + u[1] * v[1])
    thigh0, shin0, reach0 = flat(k0 - h0), flat(a0 - k0), flat(a0 - h0)
    l1, l2 = math.hypot(*thigh0), math.hypot(*shin0)
    target = flat(a0 + Vector((0, -forward, lift)) - hip)
    far = math.hypot(*target) or 1e-9
    d = max(abs(l1 - l2) + 1e-6, min(l1 + l2 - 1e-7, far))
    bend = math.acos(max(-1.0, min(1.0, (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d))))
    side = cross(reach0, thigh0)
    if abs(side) < 1e-4 * l1 * (math.hypot(*reach0) or 1): side = 1.0         # a straight leg bends its joint backward
    a = math.atan2(target[1], target[0]) + math.copysign(bend, side)
    knee = (l1 * math.cos(a), l1 * math.sin(a))
    ankle = (target[0] / far * d, target[1] / far * d)
    q1 = Quaternion(LEFT, angle(thigh0, knee))
    q2 = Quaternion(LEFT, angle(shin0, (ankle[0] - knee[0], ankle[1] - knee[1])))
    P.turn("Leg" + s, qb.inverted() @ q1)
    P.turn("Shin" + s, q1.inverted() @ q2)
    P.turn("Foot" + s, q2.inverted() @ turn_x(toe))


def stand(P, toe=0.0):
    for s, _ in SIDES: plant(P, s, toe=toe)


def tuck(P, amount):
    """The legs drawn up under the tail, as in flight."""
    for s, _ in SIDES:
        P.turn("Leg" + s, turn_x(12 * amount))
        P.turn("Shin" + s, turn_x(58 * amount))
        P.turn("Foot" + s, turn_x(35 * amount))


def tail(P, pitch=0.0, wag=0.0):
    if "Tail1" in bones: P.turn("Tail1", turn_x(pitch * 0.6) @ turn_up(wag * 0.6))
    if "Tail2" in bones: P.turn("Tail2", turn_x(pitch * 0.4) @ turn_up(wag * 0.5))


def look(P, pitch=0.0, yaw=0.0, roll=0.0):
    """The head, the neck taking a share (a bat has no neck bone)."""
    if "Neck" in bones:
        P.turn("Neck", turn_up(yaw * 0.4) @ turn_x(pitch * 0.45))
        P.turn("Head", turn_up(yaw * 0.6) @ turn_x(pitch * 0.55) @ turn_back(roll))
    else:
        P.turn("Head", turn_up(yaw) @ turn_x(pitch) @ turn_back(roll))


LEVEL = max(0.0, min(72.0, tilt - 10.0))       # a standing bird's body comes down this far to fly
CLIPS = {}

if kind == "bird":
    hips = (head0["LegL"] + head0["LegR"]) / 2
    upright = Vector((0, head0["Root"].y, 0))      # the vertical through Root: turns on the spot are about it

    def flying(P, t, beats, sweep, bob, level=1.0):
        beat = math.tau * beats * t
        P.turn("Body", turn_x(LEVEL * level), offset=(0, 0, bob * leg * math.sin(beat - 1.9)), pivot=centre)
        look(P, pitch=-0.85 * LEVEL * level + 2 * math.sin(beat))
        tail(P, pitch=5 * math.sin(beat - 0.5))
        wings(P, 1.0, 6 + sweep * math.sin(beat), 0.6 * sweep * math.sin(beat - 1.0), pitch=LEVEL * level)
        tuck(P, 1.0)

    def idle(P, f, t):
        if IDLE_HOVERS: return flying(P, t, 6, 26, 0.04, 0.6)
        P.turn("Body", turn_x(1.5 * math.sin(math.tau * 2 * t)), offset=(0, 0, 0.02 * leg * math.sin(math.tau * 2 * t)), pivot=hips)
        stand(P)
        # Looks about as a bird does: a quick turn, a hold, back; then the other way with the head on one side.
        yaw = 34 * (step(t, 0.10, 0.16) - step(t, 0.38, 0.44)) - 26 * (step(t, 0.56, 0.62) - step(t, 0.84, 0.90))
        roll = 12 * (step(t, 0.62, 0.67) - step(t, 0.80, 0.85))
        look(P, pitch=3 * math.sin(math.tau * 2 * t), yaw=yaw, roll=roll)
        tail(P, pitch=9 * (bump(t, 0.20, 0.32) + bump(t, 0.68, 0.80)), wag=4 * math.sin(math.tau * t))
    CLIPS["idle"] = (3.0, idle, True)

    def fly(P, f, t): flying(P, t, 2, 40, 0.06)
    CLIPS["fly"] = (0.6, fly, True)

    def jump(P, f, t):
        crouch = math.sin(math.pi * min(1.0, t / 0.3)) if t < 0.3 else 0.0
        land = math.sin(math.pi * (t - 0.75) / 0.25) if t > 0.75 else 0.0
        air = math.sin(math.pi * (t - 0.25) / 0.5) if 0.25 < t < 0.75 else 0.0
        P.turn("Body", turn_x(8 * (crouch + land) - 8 * air), offset=(0, 0, 1.1 * leg * air - 0.3 * leg * (crouch + land)), pivot=hips)
        for s, _ in SIDES: plant(P, s, lift=0.35 * leg * air, toe=30 * air)
        wings(P, 0.75 * air, 28 * air * math.sin(math.tau * 5 * t), 14 * air * math.sin(math.tau * 5 * t - 1.0))
        look(P, pitch=-6 * air + 6 * (crouch + land))
        tail(P, pitch=-10 * air)
    CLIPS["jump"] = (1.0, jump, False)

    def spin(P, f, t):
        e = math.sin(math.pi * t)
        P.turn("Body", turn_up(360 * ease(t)), offset=(0, 0, 0.45 * leg * e), pivot=upright)
        tuck(P, 0.5 * e)
        wings(P, 0.7 * e, 24 * e * math.sin(math.tau * 5 * t), 12 * e * math.sin(math.tau * 5 * t - 1.0))
        look(P, yaw=-25 * math.sin(math.tau * t))
        tail(P, wag=-20 * e)
    CLIPS["spin"] = (1.4, spin, False)

    def flip(P, f, t):
        e = math.sin(math.pi * ease(t))
        over = turn_x(-360 * ease((t - 0.18) / 0.64))
        P.turn("Body", over, offset=(0, 0, 0.9 * tall * e), pivot=centre)
        tuck(P, min(1.0, 1.6 * e))
        wings(P, min(1.0, 1.5 * e), 30 * e * math.sin(math.tau * 5 * t), 16 * e * math.sin(math.tau * 5 * t - 1.0))
        tail(P, pitch=-12 * e)
    CLIPS["flip"] = (1.3, flip, False)

    def bow(P, f, t):
        e = math.sin(math.pi * ease(t)) ** 0.8 if 0 < t < 1 else 0.0
        P.turn("Body", turn_x(30 * e), offset=(0, 0, -0.12 * leg * e), pivot=hips)
        stand(P)
        look(P, pitch=22 * e)
        tail(P, pitch=14 * e)
        wings(P, 0.4 * e, 0.0, 0.0, pitch=30 * e)
    CLIPS["bow"] = (1.6, bow, False)

    def time(P, f, t):
        """The raven strikes the hour: three deep nods, the tail flicking up on each."""
        e = math.sin(math.pi * t) ** 0.5
        nod = e * (0.5 - 0.5 * math.cos(math.tau * 3 * t))
        P.turn("Body", turn_x(20 * nod), offset=(0, 0, -0.1 * leg * nod), pivot=hips)
        stand(P)
        look(P, pitch=30 * nod)
        tail(P, pitch=22 * nod)
        wings(P, 0.22 * nod, 0.0, 0.0)
    CLIPS["time"] = (2.4, time, False)

    def dawnsong(P, f, t):
        """Sings up at the sky: stretched tall, the beak raised, the wings half open and trembling, the tail spread."""
        e = step(t, 0.0, 0.2) - step(t, 0.82, 1.0)
        P.turn("Body", turn_x(-10 * e) @ turn_back(5 * e * math.sin(math.tau * 2 * t)), offset=(0, 0, 0.08 * leg * e), pivot=hips)
        stand(P)
        look(P, pitch=-32 * e + 5 * e * math.sin(math.tau * 9 * t), yaw=10 * e * math.sin(math.tau * 2 * t))
        tail(P, pitch=18 * e, wag=8 * e * math.sin(math.tau * 4 * t))
        wings(P, 0.55 * e, 8 * e * math.sin(math.tau * 7 * t), 6 * e * math.sin(math.tau * 7 * t - 1.0))
    CLIPS["dawnsong"] = (2.8, dawnsong, False)

    def headturn(P, f, t):
        """The head right round, as an owl's seems to go."""
        e = math.sin(math.pi * t)
        P.turn("Body", offset=(0, 0, -0.05 * leg * e), pivot=hips)
        stand(P)
        P.turn("Neck", turn_up(30 * math.sin(math.tau * ease((t - 0.1) / 0.8))))
        P.turn("Head", Quaternion(UP, rad(360 * ease((t - 0.1) / 0.8) - 30 * math.sin(math.tau * ease((t - 0.1) / 0.8)))))
    CLIPS["headturn"] = (2.0, headturn, False)

    def snow(P, f, t):
        """Makes it snow: the wings thrown wide and the whole bird shaking the snow out of its feathers."""
        e = step(t, 0.0, 0.22) - step(t, 0.8, 1.0)
        shake = e * math.sin(math.tau * 6 * t)
        P.turn("Body", turn_back(9 * shake) @ turn_x(-6 * e), offset=(0, 0, 0.05 * leg * e), pivot=hips)
        stand(P)
        look(P, pitch=-12 * e, yaw=30 * e * math.sin(math.tau * 1.5 * t), roll=-8 * shake)
        tail(P, pitch=10 * e, wag=16 * shake)
        wings(P, e, 10 * e + 9 * shake, 8 * e * math.sin(math.tau * 6 * t - 1.0))
    CLIPS["snow"] = (2.6, snow, False)

    def dance(P, f, t):
        e = math.sin(math.pi * t)
        beat = math.tau * 4 * t
        P.turn("Body", turn_up(10 * e * math.sin(beat / 2)) @ turn_back(10 * e * math.sin(beat / 2)), offset=(0, 0, -0.22 * leg * e * abs(math.sin(beat / 2))), pivot=hips)
        stand(P)
        look(P, pitch=12 * e * math.sin(beat), roll=-8 * e * math.sin(beat / 2))
        tail(P, pitch=8 * e, wag=24 * e * math.sin(beat))
        wings(P, 0.5 * e, 22 * e * math.sin(beat), 10 * e * math.sin(beat - 1.0))
    CLIPS["dance"] = (2.0, dance, False)

    def dive(P, f, t):
        """The kingfisher's plunge: up, over onto its beak with the wings shut, straight down, and up again."""
        nose = (tail0["Head"] - centre).length
        up = 1.0 * tall * (step(t, 0.0, 0.25) - step(t, 0.40, 0.56)) + 0.45 * tall * (step(t, 0.60, 0.74) - step(t, 0.82, 1.0))
        down = max(0.0, nose - centre.z) * (step(t, 0.40, 0.56) - step(t, 0.60, 0.74))
        over = 100 * (step(t, 0.20, 0.38) - step(t, 0.58, 0.76))
        air = step(t, 0.0, 0.12) - step(t, 0.88, 1.0)
        shut = step(t, 0.24, 0.36) - step(t, 0.56, 0.68)
        P.turn("Body", turn_x(over), offset=(0, 0, up + down), pivot=centre)
        tuck(P, air)
        look(P, pitch=-0.2 * over)
        wings(P, air * (1 - 0.92 * shut), air * (1 - shut) * 30 * math.sin(math.tau * 6 * t), air * (1 - shut) * 16 * math.sin(math.tau * 6 * t - 1.0))
        tail(P, pitch=-8 * air)
    CLIPS["dive"] = (2.2, dive, False)

else:
    # A bat: the rest pose is in flight, so every clip beats the wings about it and each cue comes back to it.
    def beating(P, t, beats, low, sweep, e=1.0):
        beat = math.tau * beats * t
        wings(P, 1.0, e * (low + sweep * math.sin(beat)), e * 0.7 * sweep * math.sin(beat - 1.1))
        if "Tail1" in bones: P.turn("Tail1", turn_x(e * 8 * math.sin(beat - 0.8)))

    def beating_bob(t, beats, bob): return bob * leg * math.sin(math.tau * beats * t - 1.9)

    def idle(P, f, t):
        P.turn("Body", turn_x(-6 + 1.5 * math.sin(math.tau * t)), offset=(0, 0, beating_bob(t, 3, 0.05)), pivot=centre)
        beating(P, t, 3, -16, 20)
        look(P, pitch=4 * math.sin(math.tau * t), yaw=12 * math.sin(math.tau * t))
    CLIPS["idle"] = (1.2, idle, True)

    def fly(P, f, t):
        P.turn("Body", turn_x(4), offset=(0, 0, beating_bob(t, 4, 0.07)), pivot=centre)
        beating(P, t, 4, -22, 34)
        look(P, pitch=-3)
    CLIPS["fly"] = (1.0, fly, True)

    def spin(P, f, t):
        e = math.sin(math.pi * t) ** 0.5
        P.turn("Body", turn_up(360 * ease(t)) @ turn_back(-14 * math.sin(math.pi * t)), offset=(0, 0, e * beating_bob(t, 4, 0.06)), pivot=Vector((0, centre.y, centre.z)))
        beating(P, t, 4, -20, 30, e)
        look(P, yaw=-20 * math.sin(math.tau * t))
    CLIPS["spin"] = (1.2, spin, False)

    def flip(P, f, t):
        e = math.sin(math.pi * t) ** 0.5
        P.turn("Body", turn_x(-360 * ease((t - 0.1) / 0.8)), offset=(0, 0, 0.5 * tall * math.sin(math.pi * ease(t)) + e * beating_bob(t, 4, 0.05)), pivot=centre)
        beating(P, t, 4, -20, 30, e)
    CLIPS["flip"] = (1.2, flip, False)

unknown = [c for c in wanted if c not in CLIPS]
if unknown: raise SystemExit("make: no clip written for %s (a %s has %s)" % (", ".join(unknown), kind, ", ".join(CLIPS)))
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
with open(os.path.join(os.path.dirname(out_glb), "clips.json"), "w") as f: json.dump({"clips": made, "fps": FPS, "leg": leg, "kind": kind}, f, indent=2)
common.look(os.path.join(os.path.dirname(out_glb), "look-rigged"), [mesh])
# Each clip at a third and two thirds of the way: bad weights (a leg that collapses, a torn body) show here.
for name in made:
    rig.animation_data.action = bpy.data.actions[name]
    end = round(made[name] * FPS)
    for k, frame in enumerate((end // 3, 2 * end // 3)):
        scene.frame_set(frame)
        common.look(os.path.join(os.path.dirname(out_glb), "pose-%s-%d" % (name, k + 1)), [mesh], size=400, views=("side", "front34"))
rig.animation_data.action = None
