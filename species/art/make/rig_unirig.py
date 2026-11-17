"""make.py's rig step with UniRig: skin weights predicted by UniRig's skin model for our own named skeleton.

    python rig_unirig.py <rig-template.glb> <variant dir> <UniRig source> <revision>

rig-template.glb is the mesh with the template skeleton (blender_rig.py writes it), so the bones keep SPEC.md's names
and only the weights are UniRig's. Writes <variant dir>/unirig-skin.npz: names, the points UniRig sampled, their
weights, and its joints beside ours (so blender_rig.py can undo UniRig's normalization). Also runs UniRig's own
skeleton model on the bare mesh and writes unirig-skeleton.npz, for the owner to compare joint placement."""
import glob, os, runpy, shutil, subprocess, sys
import numpy as np

rigged, variant, src, revision = sys.argv[1:5]
work = os.path.join(variant, "unirig")
shutil.rmtree(work, ignore_errors=True)
os.makedirs(os.path.join(work, "in"))
glb = os.path.join(work, "in", "creature.glb")
shutil.copyfile(rigged, glb)
npz_dir, out_dir = os.path.join(work, "npz"), os.path.join(work, "out")
os.chdir(src)
env = dict(os.environ, PYTHONPATH=src)
subprocess.check_call([sys.executable, "-m", "src.data.extract", "--config=configs/data/quick_inference.yaml", "--require_suffix=glb",
                       "--force_override=true", "--num_runs=1", "--id=0", "--time=make", "--faces_target_count=50000",
                       "--input=" + glb, "--output_dir=" + npz_dir], env=env)

import huggingface_hub                                       # noqa: E402  every checkpoint at the pinned revision
_download = huggingface_hub.hf_hub_download
def pinned(*a, **k):
    if (k.get("repo_id") or (a[0] if a else "")) == "VAST-AI/UniRig": k["revision"] = revision
    return _download(*a, **k)
huggingface_hub.hf_hub_download = pinned
sys.path.insert(0, src)


def run(*argv):
    saved = sys.argv
    sys.argv = ["run.py"] + list(argv)
    try: runpy.run_path(os.path.join(src, "run.py"), run_name="__main__")
    finally: sys.argv = saved


run("--task=configs/task/quick_inference_unirig_skin.yaml", "--seed=12345", "--input=" + glb, "--npz_dir=" + npz_dir,
    "--output_dir=" + out_dir, "--data_name=raw_data.npz")
# UniRig writes beside the input, in a folder named after it (in/creature/), whatever --npz_dir says.
raw = glob.glob(os.path.join(work, "**", "raw_data.npz"), recursive=True)[0]
skin = glob.glob(os.path.join(work, "**", "predict_skin.npz"), recursive=True)
if not skin: sys.exit("make: UniRig wrote no predict_skin.npz")
r, s = np.load(raw, allow_pickle=True), np.load(skin[0], allow_pickle=True)
weights, points = s["skin"], s["vertices"]
if weights.shape[0] != points.shape[0]: weights = weights.T
np.savez(os.path.join(variant, "unirig-skin.npz"), names=np.array(list(r["names"])), weights=weights, points=points,
         joints_unirig=s["joints"], joints_ours=r["joints"])
print("make: UniRig weights for %d bones at %d points" % (weights.shape[1], points.shape[0]))

# UniRig's own skeleton, on the mesh alone, for comparison only.
try:
    run("--task=configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml", "--seed=12345", "--input=" + glb,
        "--npz_dir=" + npz_dir, "--output_dir=" + os.path.join(work, "skeleton"))
    found = glob.glob(os.path.join(work, "**", "predict_skeleton.npz"), recursive=True)
    if found:
        k = np.load(found[0], allow_pickle=True)
        np.savez(os.path.join(variant, "unirig-skeleton.npz"), **{n: k[n] for n in k.files})
        print("make: UniRig's own skeleton: %d joints" % len(k["joints"]))
except SystemExit as error:
    print("make: UniRig's own skeleton did not run:", error)
