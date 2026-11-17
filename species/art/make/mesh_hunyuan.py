"""make.py's mesh step with Hunyuan3D 2.1: the cutout to a textured mesh (shape, then its PBR paint).

    python mesh_hunyuan.py <cutout.png> <out.glb> <Hunyuan3D-2.1 source> <revision> <seed>

Runs in the hy3d env. Every Hugging Face download is held to its pinned revision. The untextured shape is kept beside
the output (raw-hunyuan-shape.glb) so the owner can look at the form before the paint."""
import gc, os, shutil, sys, time

image_path, out, src, revision, seed = sys.argv[1], os.path.abspath(sys.argv[2]), sys.argv[3], sys.argv[4], int(sys.argv[5])
PINNED = {"tencent/Hunyuan3D-2.1": revision, "facebook/dinov2-giant": "611a9d42f2335e0f921f1e313ad3c1b7178d206d"}

import huggingface_hub                                   # noqa: E402
_download = huggingface_hub.snapshot_download
def pinned_download(*a, **k):
    repo = k.get("repo_id") or (a[0] if a else None)
    if repo in PINNED: k["revision"] = PINNED[repo]
    return _download(*a, **k)
huggingface_hub.snapshot_download = pinned_download

os.chdir(src)
sys.path[:0] = [src, os.path.join(src, "hy3dshape"), os.path.join(src, "hy3dpaint")]
os.environ.setdefault("HY3DGEN_MODELS", os.path.join(os.environ.get("HF_HOME", "."), "hy3dgen"))
import torch                                             # noqa: E402
from PIL import Image                                    # noqa: E402
try:
    from torchvision_fix import apply_fix; apply_fix()
except Exception as error: print("make: torchvision fix not applied:", error)

work = os.path.dirname(out)
shape_path = out.replace(".glb", "-shape-%d.glb" % seed)
from strands import drop_strands          # noqa: E402
image = drop_strands(Image.open(image_path))

t = time.time()
if os.path.exists(shape_path) and os.path.getmtime(shape_path) > os.path.getmtime(image_path):
    print("make: the shape for seed %d is already made: %s" % (seed, shape_path))
else:
  from hy3dshape.pipelines import Hunyuan3DDiTFlowMatchingPipeline   # noqa: E402
  local = pinned_download(repo_id="tencent/Hunyuan3D-2.1", allow_patterns=["hunyuan3d-dit-v2-1/*", "hunyuan3d-paintpbr-v2-1/*", "*.json"])
  shape = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(local)     # an absolute path: smart_load_model reads it as it is
  mesh = shape(image=image, generator=torch.Generator("cuda").manual_seed(seed), num_inference_steps=50, octree_resolution=384)[0]
  mesh.export(shape_path)
  print("make: shape %d faces in %.0f s, peak %.1f GB" % (len(mesh.faces), time.time() - t, torch.cuda.max_memory_allocated() / 2**30))
  del shape, mesh; gc.collect(); torch.cuda.empty_cache(); torch.cuda.reset_peak_memory_stats()

t = time.time()
import types                                             # noqa: E402
sys.modules.setdefault("bpy", types.ModuleType("bpy"))   # imported by mesh_utils for its OBJ-to-GLB only, which save_glb=False never calls
from textureGenPipeline import Hunyuan3DPaintPipeline, Hunyuan3DPaintConfig  # noqa: E402
conf = Hunyuan3DPaintConfig(6, 512)
conf.realesrgan_ckpt_path = os.path.join(src, "hy3dpaint/ckpt/RealESRGAN_x4plus.pth")
conf.multiview_cfg_path = os.path.join(src, "hy3dpaint/cfgs/hunyuan-paint-pbr.yaml")
conf.custom_pipeline = os.path.join(src, "hy3dpaint/hunyuanpaintpbr")
conf.dino_ckpt_path = pinned_download(repo_id="facebook/dinov2-giant")
paint = Hunyuan3DPaintPipeline(conf)
paint_dir = os.path.join(work, "hunyuan-paint")
os.makedirs(paint_dir, exist_ok=True)
shutil.copyfile(shape_path, os.path.join(paint_dir, "shape.glb"))
result = paint(mesh_path=os.path.join(paint_dir, "shape.glb"), image_path=image, output_mesh_path=os.path.join(paint_dir, "textured.obj"), save_glb=False)
import trimesh                                           # noqa: E402  the OBJ (base colour in its .mtl) to one GLB
textured = trimesh.load(result if isinstance(result, str) else os.path.join(paint_dir, "textured.obj"), process=False)
textured.export(out)
print("make: paint in %.0f s, peak %.1f GB -> %s" % (time.time() - t, torch.cuda.max_memory_allocated() / 2**30, out))
