"""make.py's mesh step with TRELLIS (image-large): the cutout to a textured mesh.

    python mesh_trellis.py <cutout.png> <out.glb> <TRELLIS source> <revision> <seed>

Runs in the trellis env, ATTN_BACKEND=xformers (no flash-attn wheel for it). The weights come from the pinned
snapshot; DINOv2 comes through torch.hub from facebookresearch/dinov2 as TRELLIS asks for it."""
import os, sys, time

image_path, out, src, revision, seed = sys.argv[1], os.path.abspath(sys.argv[2]), sys.argv[3], sys.argv[4], int(sys.argv[5])
sys.path.insert(0, src)
from huggingface_hub import snapshot_download        # noqa: E402
import torch                                          # noqa: E402
from PIL import Image                                 # noqa: E402
from trellis.pipelines import TrellisImageTo3DPipeline          # noqa: E402
from trellis.utils import postprocessing_utils                  # noqa: E402

t = time.time()
local = snapshot_download("microsoft/TRELLIS-image-large", revision=revision)
pipeline = TrellisImageTo3DPipeline.from_pretrained(local)
pipeline.cuda()
image = Image.open(image_path).convert("RGBA")
outputs = pipeline.run(image, seed=seed, formats=["gaussian", "mesh"])
print("make: generated in %.0f s, peak %.1f GB" % (time.time() - t, torch.cuda.max_memory_allocated() / 2**30))
t = time.time()
glb = postprocessing_utils.to_glb(outputs["gaussian"][0], outputs["mesh"][0], simplify=0.9, texture_size=2048)
glb.export(out)
print("make: glb in %.0f s -> %s" % (time.time() - t, out))
