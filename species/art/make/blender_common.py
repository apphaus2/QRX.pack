"""What make.py's Blender steps share: their arguments, Cycles on the GPU, and pictures to look at.

Blender's axes are Z up; glTF's +Z (where the head points) is Blender's -Y, glTF's +X (the animal's left) is +X."""
import math, os, sys
import bpy
from mathutils import Vector

FORWARD = Vector((0, -1, 0))        # the head, in Blender's axes
UP = Vector((0, 0, 1))


def args():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def log(*parts): print("make:", *parts, flush=True)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def cycles(samples=32):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = kind
            prefs.get_devices()
            devices = [d for d in prefs.devices if d.type == kind]
            if devices:
                for d in prefs.devices: d.use = d.type == kind
                scene.cycles.device = "GPU"
                log("Cycles on", kind, ", ".join(d.name for d in devices))
                break
        except TypeError:
            continue
    else:
        scene.cycles.device = "CPU"; log("Cycles on the CPU (no CUDA device found)")
    scene.cycles.samples = samples
    scene.cycles.use_denoising = False
    return scene


def mesh_objects():
    return [o for o in bpy.context.scene.objects if o.type == "MESH"]


def bounds(objects):
    """From the vertices themselves: an object's bound_box is cached and stays stale after mesh.transform()."""
    points = [o.matrix_world @ v.co for o in objects for v in o.data.vertices]
    lo = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    hi = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return lo, hi


def look(prefix, objects=None, size=640, views=("side", "front34", "top", "back34")):
    """Pictures from the left side, the front three-quarter and above, on a light gray ground: prefix-side.png and so on."""
    scene = cycles(24)
    objects = objects or mesh_objects()
    lo, hi = bounds(objects)
    centre, extent = (lo + hi) / 2, max((hi - lo).length, 1e-3)
    world = bpy.data.worlds.new("look"); scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.82, 0.83, 0.85, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 1.2
    scene.render.resolution_x = scene.render.resolution_y = size
    scene.render.film_transparent = False
    camera_data = bpy.data.cameras.new("look"); camera_data.type = "ORTHO"; camera_data.ortho_scale = extent * 1.15
    camera = bpy.data.objects.new("look", camera_data); scene.collection.objects.link(camera); scene.camera = camera
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); scene.collection.objects.link(sun)
    sun.data.energy = 2.5; sun.rotation_euler = (math.radians(40), math.radians(10), math.radians(30))
    directions = {"side": Vector((1, 0, 0.12)), "front34": Vector((0.7, -0.7, 0.35)), "top": Vector((0.001, 0, 1)), "back34": Vector((-0.6, 0.75, 0.3))}
    written = []
    for name in views:
        direction = directions[name]
        camera.location = centre + direction.normalized() * extent * 3
        camera.rotation_euler = (centre - camera.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = "%s-%s.png" % (prefix, name)
        bpy.ops.render.render(write_still=True)
        written.append(scene.render.filepath)
    for thing in (camera, sun): bpy.data.objects.remove(thing)
    log("looked:", ", ".join(os.path.basename(w) for w in written))
    return written
