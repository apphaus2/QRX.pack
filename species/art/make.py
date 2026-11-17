#!/usr/bin/env python3
"""Makes one creature end to end on this machine (art/PIPELINE.md): render, cutout, mesh, clean, rig, clips, pack,
check. Linux (WSL2 on the owner's Windows machine) with an NVIDIA GPU; what it runs on is installed by setup.sh.

    python3 species/art/make.py <id>                         every step not yet done
    python3 species/art/make.py <id> --from rig              redo rig and every step after it
    python3 species/art/make.py <id> --only mesh             one step
    python3 species/art/make.py <id> --mesher trellis --rigger unirig    the other choices PIPELINE.md leaves open
    python3 species/art/make.py <id> --only render --seeds 4             candidates for the owner to pick from
    python3 species/art/make.py <id> --pick-render 3         file work/render/seed-3.jpg as full.jpg (then cutout)
    python3 species/art/make.py <id> --file                  after check: file mesh.glb and mesh.quest.glb (intake.py)

Each step reads the step before's file and writes its own in art/<id>/work/ (git ignores it), so any step can be redone
alone. One variant per mesher and rigger: work/<mesher>-<rigger>/ holds clean, rig, clips and the packed pair, so both
choices sit side by side. The mesh step starts from the kept cutout.png when there is one (a creature already
rendered keeps its picture), else from work/cutout.png. Every step's time, peak VRAM and the models it used are
appended to work/log.json. Nothing is filed in art/<id>/ but with --pick-render or --file.

Every model is pinned below by name and revision (Hugging Face) or commit (GitHub, in setup.sh).
"""
import argparse, datetime, json, os, shutil, subprocess, sys, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
STEPS_DIR = os.path.join(HERE, "make")
ART_HOME = os.environ.get("ART_HOME", os.path.expanduser("~/qrx-art"))
MAMBA = os.path.join(ART_HOME, "bin", "micromamba")
BLENDER = os.path.join(ART_HOME, "blender", "blender")
GLTFPACK = os.path.join(ART_HOME, "bin", "gltfpack")

# Every model, by name and revision. Changing one remakes the creatures differently: say so in the commit.
PINS = {
    "render": {"model": "black-forest-labs/FLUX.1-schnell", "revision": "741f7c3ce8b383c54771c7003378a50191e9efe9", "env": "art"},
    "cutout": {"model": "ZhengPeng7/BiRefNet", "revision": "e2bf8e4460fc8fa32bba5ea4d94b3233d367b0e4", "env": "art"},
    "hunyuan": {"model": "tencent/Hunyuan3D-2.1", "revision": "0b94677654c57bb9a6b6845cd7b704ccf551d327", "env": "hy3d",
                "code": "Tencent-Hunyuan/Hunyuan3D-2.1@82920d643c0dc2f7bfd7255f45f62d386edfe60c",
                "dino": "facebook/dinov2-giant@611a9d42f2335e0f921f1e313ad3c1b7178d206d", "realesrgan": "RealESRGAN_x4plus v0.1.0"},
    "trellis": {"model": "microsoft/TRELLIS-image-large", "revision": "25e0d31ffbebe4b5a97464dd851910efc3002d96", "env": "trellis",
                "code": "microsoft/TRELLIS@193e0502b5cb3eb5997ec457d5340e95d09b158e"},
    "unirig": {"model": "VAST-AI/UniRig", "revision": "36842e2b5947e9e60f89275b83208c8e74071c63", "env": "unirig",
               "code": "VAST-AI-Research/UniRig@6793c6640ff01c8fb389f3993434124bb43d2933"},
    "blender": {"version": "4.5.16 LTS"},
    "gltfpack": {"version": "1.3"},
}
STEPS = ["render", "cutout", "mesh", "clean", "rig", "clips", "pack", "check"]
MESHERS = ("hunyuan", "trellis", "given")     # given: a mesh made elsewhere (--raw), from the clean step on
RIGGERS = ("template", "unirig")
PHONE_FLAGS = ["-cc", "-tc", "-tu", "-kn", "-km"]          # meshopt geometry, 16-bit positions, UASTC KTX2
QUEST_FLAGS = ["-noq", "-tc", "-tu", "-kn", "-km"]         # plain floats, never -c: Meta's reader stops on meshopt


class Run:
    def __init__(self, args):
        self.args = args
        self.id = args.id
        self.folder = os.path.join(HERE, args.id)
        self.work = os.path.join(self.folder, "work")
        self.variant = os.path.join(self.work, "%s-%s" % (args.mesher, args.rigger))
        os.makedirs(self.variant, exist_ok=True)
        self.brief = brief(self.folder)
        self.shape = BODIES["creatures"].get(self.id, "quadruped")
        self.rig_script = "blender_rig.py" if self.shape == "quadruped" else "blender_rig_%s.py" % self.shape
        self.clips_script = "blender_clips.py" if self.shape == "quadruped" else "blender_clips_%s.py" % self.shape

    # -- the files each step reads and writes
    def path(self, name): return os.path.join(self.work, name)
    def vpath(self, name): return os.path.join(self.variant, name)

    def cutout(self):
        kept = os.path.join(self.folder, "cutout.png")
        return kept if os.path.exists(kept) and not self.args.fresh_cutout else self.path("cutout.png")

    def outputs(self, step):
        return {"render": [self.path("render/render.json")], "cutout": [self.path("cutout.png")],
                "mesh": [self.path("raw-%s.glb" % self.args.mesher)], "clean": [self.vpath("clean.blend")],
                "rig": [self.vpath("rig.blend")], "clips": [self.vpath("rigged.glb")],
                "pack": [self.vpath("mesh.glb"), self.vpath("mesh.quest.glb")], "check": [self.vpath("check.json")]}[step]

    def done(self, step): return all(os.path.exists(p) for p in self.outputs(step))

    # -- running a step, timed, with the GPU watched
    def run(self, step, command, env_name=None, extra_env=None):
        env = dict(os.environ, HF_HOME=os.path.join(ART_HOME, "hf"), PYTHONUNBUFFERED="1", TMPDIR=os.path.join(ART_HOME, "tmp"))
        env.update(extra_env or {})
        if env_name:
            env["LD_LIBRARY_PATH"] = os.path.join(ART_HOME, "mamba", "envs", env_name, "lib") + ":" + env.get("LD_LIBRARY_PATH", "")   # bpy's X11 libs
            env["CUDA_HOME"] = os.path.join(ART_HOME, "mamba", "envs", env_name)
            # Conda's CUDA keeps its headers and libraries under targets/: for extensions compiled on first use (nvdiffrast).
            targets = os.path.join(env["CUDA_HOME"], "targets", "x86_64-linux")
            env["CPATH"] = os.path.join(targets, "include") + ":" + env.get("CPATH", "")
            env["LIBRARY_PATH"] = os.path.join(targets, "lib") + ":" + os.path.join(targets, "lib", "stubs") + ":" + env.get("LIBRARY_PATH", "")
            env["MAMBA_ROOT_PREFIX"] = os.path.join(ART_HOME, "mamba")
            command = [MAMBA, "run", "-n", env_name] + command
        if command[0] == BLENDER:
            env["LD_LIBRARY_PATH"] = os.path.join(ART_HOME, "mamba", "envs", "blenderlibs", "lib") + ":" + env.get("LD_LIBRARY_PATH", "")
        print("\n== %s: %s" % (step, " ".join(os.path.basename(c) if i == 0 else c for i, c in enumerate(command))), flush=True)
        watch = GpuWatch(); watch.start()
        started = time.time()
        log_path = (os.path.join(self.work, "mesh-%s.log" % self.args.mesher) if step == "mesh" else
                    os.path.join(self.work, "%s.log" % step) if step in ("render", "cutout") else os.path.join(self.variant, "%s.log" % step))
        with open(log_path, "w", encoding="utf-8") as log:
            process = subprocess.Popen(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
            for line in process.stdout:
                log.write(line)
                if not self.args.quiet or line.startswith(("make:", "Traceback", "Error")): sys.stdout.write(line)
            code = process.wait()
        watch.stop()
        record = {"step": step, "variant": os.path.basename(self.variant), "seconds": round(time.time() - started, 1),
                  "vram_peak_mib": watch.peak, "vram_before_mib": watch.base, "exit": code,
                  "pins": step_pins(step, self.args), "date": datetime.datetime.now().isoformat(timespec="seconds")}
        append_log(self.path("log.json"), record)
        print("== %s: %s in %.0f s, VRAM peak %s MiB (%s before)" % (step, "done" if code == 0 else "FAILED", record["seconds"], watch.peak, watch.base), flush=True)
        if code: sys.exit("%s failed (exit %d): see %s" % (step, code, log_path))

    def blender(self, step, script, *script_args):
        self.run(step, [BLENDER, "-b", "--factory-startup", "-noaudio", "--python-exit-code", "1",
                        "-P", os.path.join(STEPS_DIR, script), "--"] + [str(a) for a in script_args])

    # -- the steps
    def render(self):
        self.run("render", ["python", os.path.join(STEPS_DIR, "render.py"), os.path.join(self.folder, "prompt.txt"),
                            self.path("render"), str(self.args.seeds), str(self.args.first_seed), PINS["render"]["model"], PINS["render"]["revision"]], "art")

    def cutout_step(self):
        source = os.path.join(self.folder, "full.jpg")
        if not os.path.exists(source): sys.exit("no full.jpg: render, then pick one with --pick-render N")
        self.run("cutout", ["python", os.path.join(STEPS_DIR, "cutout.py"), source, self.path("cutout.png"),
                            PINS["cutout"]["model"], PINS["cutout"]["revision"]], "art")

    def mesh(self):
        image = self.cutout()
        if not os.path.exists(image): sys.exit("no cutout: run the cutout step")
        out = self.path("raw-%s.glb" % self.args.mesher)
        pin = PINS.get(self.args.mesher, {})
        if self.args.mesher == "given":
            if not self.args.raw: sys.exit("--mesher given needs --raw <mesh.glb>")
            shutil.copyfile(self.args.raw, out); print("== mesh: %s copied as %s" % (self.args.raw, os.path.basename(out))); return
        if self.args.mesher == "hunyuan":
            src = os.path.join(ART_HOME, "src", "Hunyuan3D-2.1")
            self.run("mesh", ["python", os.path.join(STEPS_DIR, "mesh_hunyuan.py"), image, out, src, pin["revision"], str(self.args.mesh_seed)], "hy3d")
        else:
            src = os.path.join(ART_HOME, "src", "TRELLIS")
            self.run("mesh", ["python", os.path.join(STEPS_DIR, "mesh_trellis.py"), image, out, src, pin["revision"], str(self.args.mesh_seed)], "trellis",
                     {"ATTN_BACKEND": "xformers", "SPCONV_ALGO": "native"})

    def clean(self):
        self.blender("clean", "blender_clean.py", self.path("raw-%s.glb" % self.args.mesher), self.vpath("clean.blend"),
                     self.vpath("clean.glb"), self.brief["size"], self.args.mesher, self.args.turn if self.args.turn is not None else "auto")

    def rig(self):
        kept = os.path.join(self.folder, "joints.json")
        joints = kept if os.path.exists(kept) else self.vpath("joints.json")
        mode = "keep" if os.path.exists(kept) else "place"
        if self.args.rigger == "unirig":
            # The template skeleton first (its joints and a rigged glb for UniRig), then UniRig's weights on it.
            self.blender("rig", self.rig_script, self.vpath("clean.blend"), self.vpath("rig.blend"), joints, mode, "template", "-")
            self.unirig()
            mode = "keep"
        self.blender("rig", self.rig_script, self.vpath("clean.blend"), self.vpath("rig.blend"), joints, mode, self.args.rigger, self.vpath("unirig-skin.npz"))

    def unirig(self):
        src = os.path.join(ART_HOME, "src", "UniRig")
        self.run("rig", ["python", os.path.join(STEPS_DIR, "rig_unirig.py"), self.vpath("rig-template.glb"), self.variant, src, PINS["unirig"]["revision"]], "unirig")

    def clips(self):
        self.blender("clips", self.clips_script, self.vpath("rig.blend"), self.vpath("rigged.glb"), ",".join(self.brief["clips"]), self.id)

    def pack(self):
        for flags, name in ((PHONE_FLAGS, "mesh.glb"), (QUEST_FLAGS, "mesh.quest.glb")):
            self.run("pack", [GLTFPACK, "-i", self.vpath("rigged.glb"), "-o", self.vpath(name)] + flags + ["-v"])

    def check(self):
        try: import PIL                      # noqa: F401  intake reads textures with Pillow: the art env has it
        except ImportError:
            python = os.path.join(ART_HOME, "mamba", "envs", "art", "bin", "python")
            code = subprocess.call([python, os.path.abspath(__file__), self.id, "--only", "check", "--mesher", self.args.mesher, "--rigger", self.args.rigger])
            if code: sys.exit(code)
            return
        sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
        import intake, build
        report = {}
        for name, quest in (("mesh.glb", False), ("mesh.quest.glb", True)):
            faults, notes, facts = intake.check_mesh(self.vpath(name))
            blob = open(self.vpath(name), "rb").read()
            import struct
            gltf = json.loads(blob[20:20 + struct.unpack("<I", blob[12:16])[0]])
            faults += build.standard_faults(gltf, facts, quest)
            joints = [n.get("name") for n in gltf.get("nodes", [])]
            missing = [b for b in BODIES["shapes"][self.shape]["bones"] if b not in joints]
            if missing: faults.append("no bone named %s" % ", ".join(missing))
            lacking = sorted(set(self.brief["clips"]) - set(facts.get("clips", [])))
            if lacking: faults.append("no clip named %s" % ", ".join(lacking))
            if len(blob) > intake.LIMITS["bytes"]: faults.append("%d bytes, over %d" % (len(blob), intake.LIMITS["bytes"]))
            report[name] = {"faults": faults, "notes": notes, "facts": facts}
            print("make: %s %s" % (name, "ok" if not faults else "FAULTS"))
            for f in faults: print("make:   fault: " + f)
            for n in notes: print("make:   note: " + n)
            print("make:   " + json.dumps({k: facts.get(k) for k in ("bytes", "triangles", "size", "joints", "clips")}))
        a, b = report["mesh.glb"]["facts"].get("box"), report["mesh.quest.glb"]["facts"].get("box")
        if a and b and any(abs(p - q) > 0.001 for x, y in zip(a, b) for p, q in zip(x, y)):
            report["mesh.quest.glb"]["faults"].append("not the same size as mesh.glb"); print("make:   fault: the two copies are not the same size")
        with open(self.vpath("check.json"), "w", encoding="utf-8") as f: json.dump(report, f, indent=2)
        append_log(self.path("log.json"), {"step": "check", "variant": os.path.basename(self.variant), "faults": sum(len(r["faults"]) for r in report.values())})
        if any(r["faults"] for r in report.values()): sys.exit("check: faults (above)")

    def file(self):
        report = json.load(open(self.vpath("check.json"), encoding="utf-8"))
        if any(r["faults"] for r in report.values()): sys.exit("not filed: the check has faults")
        command = [sys.executable, os.path.join(HERE, "intake.py"), self.id, "--mesh", self.vpath("mesh.glb"), "--quest", self.vpath("mesh.quest.glb"),
                   "--tool", "make.py %s-%s" % (self.args.mesher, self.args.rigger), "--replace"]
        subprocess.check_call(command)


# Each creature's body shape and the bones its check requires (make/bodies.json).
with open(os.path.join(STEPS_DIR, "bodies.json"), encoding="utf-8") as _f: BODIES = json.load(_f)


def brief(folder):
    """size (m) and clips from the creature's prompt.md table."""
    text = open(os.path.join(folder, "prompt.md"), encoding="utf-8").read()
    size = clips = None
    for line in text.splitlines():
        if line.startswith("| size |"): size = float(line.split("**")[1].split()[0])
        if line.startswith("| clips |"): clips = [c.strip(" `") for c in line.split("|")[2].split(",")]
    if size is None or not clips: sys.exit("%s/prompt.md has no size or clips row" % folder)
    return {"size": size, "clips": clips}


def step_pins(step, args):
    if step == "mesh": return {args.mesher: PINS.get(args.mesher, args.raw)}
    if step == "rig": return {"blender": PINS["blender"], **({"unirig": PINS["unirig"]} if args.rigger == "unirig" else {})}
    if step in ("clean", "clips"): return {"blender": PINS["blender"]}
    if step == "pack": return {"gltfpack": PINS["gltfpack"]}
    return {step: PINS.get(step)}


def append_log(path, record):
    log = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else []
    log.append(record)
    with open(path, "w", encoding="utf-8") as f: json.dump(log, f, indent=2)


class GpuWatch(threading.Thread):
    """The most VRAM in use (MiB, the whole GPU) while a step runs, sampled twice a second with nvidia-smi."""
    def __init__(self):
        super().__init__(daemon=True); self.peak = self.base = None; self.halt = threading.Event()

    def sample(self):
        try: return int(subprocess.check_output(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], text=True).split()[0])
        except (OSError, subprocess.CalledProcessError, ValueError, IndexError): return None

    def run(self):
        self.base = self.peak = self.sample()
        while not self.halt.wait(0.5):
            v = self.sample()
            if v is not None and (self.peak is None or v > self.peak): self.peak = v

    def stop(self): self.halt.set(); self.join(2)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("id")
    p.add_argument("--from", dest="start", choices=STEPS, help="redo this step and every one after it")
    p.add_argument("--only", choices=STEPS, help="this step alone")
    p.add_argument("--to", choices=STEPS, default="check", help="stop after this step")
    p.add_argument("--mesher", choices=MESHERS, default="hunyuan")
    p.add_argument("--rigger", choices=RIGGERS, default="template")
    p.add_argument("--seeds", type=int, default=4); p.add_argument("--first-seed", type=int, default=1)
    p.add_argument("--raw", help="with --mesher given: the mesh to start from")
    p.add_argument("--mesh-seed", type=int, default=1234)
    p.add_argument("--turn", type=float, help="degrees about +Y that bring the raw mesh's head to +Z (default: per mesher, then checked)")
    p.add_argument("--pick-render", type=int, metavar="SEED", help="file work/render/seed-N.jpg as full.jpg")
    p.add_argument("--fresh-cutout", action="store_true", help="mesh from work/cutout.png even when a cutout.png is kept")
    p.add_argument("--file", action="store_true", help="file the checked pair with intake.py")
    p.add_argument("--keep-strands", action="store_true", help="mesh the cutout as it is: no strand removal (thin legs, antennae, wings, tentacles, tails)")
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args()
    if args.keep_strands: os.environ["QRX_KEEP_STRANDS"] = "1"
    r = Run(args)
    if args.pick_render is not None:
        shutil.copyfile(r.path("render/seed-%d.jpg" % args.pick_render), os.path.join(r.folder, "full.jpg"))
        print("filed work/render/seed-%d.jpg as full.jpg" % args.pick_render); return
    if args.file: r.file(); return
    actions = {"render": r.render, "cutout": r.cutout_step, "mesh": r.mesh, "clean": r.clean, "rig": r.rig,
               "clips": r.clips, "pack": r.pack, "check": r.check}
    if args.only: actions[args.only](); return
    # A creature with a kept render and cutout starts at the mesh: render and cutout run only when asked for.
    first = STEPS.index(args.start) if args.start else (2 if os.path.exists(os.path.join(r.folder, "cutout.png")) else 0)
    for i, step in enumerate(STEPS[first:STEPS.index(args.to) + 1], first):
        if not args.start and step != "check" and r.done(step): print("== %s: already done (--from %s redoes it)" % (step, step)); continue
        actions[step]()


if __name__ == "__main__":
    main()
