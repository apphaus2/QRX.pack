# Handoff: the art pipeline, from F: to WSL (2026-11-17)

For a new Claude Code session started inside WSL, in `~/_GITHUB/apphaus2/QRX.pack`, after the clone. It replaces the Windows session that
built this pipeline; from the moment you take over, that session no longer edits this repo. Everything you need is
in this file and the files it names. Talk to the owner after each run before going on.

## 1. Where things are

| what | where |
| --- | --- |
| this repo (the art work) | `~/_GITHUB/apphaus2/QRX.pack`, branch `master` (cloned from the F: checkout) |
| the pipeline (MeshTool, a submodule) | `~/_GITHUB/apphaus2/QRX.pack/third_party/MeshTool`: make.py, intake.py, steps/, shapes.json, setup.sh, docs/ |
| this project's MeshTool file | `~/_GITHUB/apphaus2/QRX.pack/species/art/meshtool.json` (archetype terra, each creature's body shape) |
| each creature's work files (gitignored) | `~/_GITHUB/apphaus2/QRX.pack/species/art/<id>/work/` (copied from F:) |
| tools home | `~/qrx-art` (`ART_HOME`), 78 GB |
| micromamba | `~/qrx-art/bin/micromamba`, root `~/qrx-art/mamba` |
| environments | `~/qrx-art/mamba/envs/`: `art` (BiRefNet cutouts, intake, checks; 6 GB), `hy3d` (Hunyuan3D 2.1; 13 GB), `trellis` (TRELLIS; 14 GB), `unirig` (UniRig; 14 GB), `blenderlibs` (X libraries Blender needs) |
| model weights | Hugging Face cache `~/qrx-art/hf` (`HF_HOME`), 36 GB; torch hub `~/.cache/torch` |
| model code and built CUDA extensions | `~/qrx-art/src/` (Hunyuan3D-2.1 with its compiled rasterizer and mesh painter, TRELLIS, trellis-ext with nvdiffrast, UniRig) |
| Blender 4.5.16 LTS (Linux) | `~/qrx-art/blender/blender` |
| gltfpack 1.3 (Linux) | `~/qrx-art/bin/gltfpack` |
| scratch | `~/qrx-art/tmp` (make.py's `TMPDIR`) |
| the GPU | one RTX 3090, 24 GB. Hunyuan peaks at 22 GB: one creature meshes at a time |

You rarely activate an environment by hand: make.py runs each step in its own environment
(`micromamba run -n <env>`) and Blender with `blenderlibs` on its library path. By hand:
`~/qrx-art/mamba/envs/art/bin/python ...`, or `eval "$(~/qrx-art/bin/micromamba shell hook -s bash)"; micromamba activate hy3d`.
`third_party/MeshTool/setup.sh` is what installed all of it (pinned commits and versions); rerun it only to rebuild.

A copy of this file stays on F: in the Windows checkout: `F:\_GITHUB\apphaus2\QRX.pack\species\art\HANDOFF-WSL.md`.

## 2. The clone (done on 2026-11-17: skip to the check)

```
mkdir -p ~/_GITHUB/apphaus2
git clone /mnt/f/_GITHUB/apphaus2/QRX.pack ~/_GITHUB/apphaus2/QRX.pack
git -C ~/_GITHUB/apphaus2/QRX.pack remote rename origin windows
git -C ~/_GITHUB/apphaus2/QRX.pack remote add origin https://github.com/apphaus2/QRX.pack.git
# MeshTool, the submodule, from the F: checkout too (its commit may not be on GitHub yet)
git -C ~/_GITHUB/apphaus2/QRX.pack -c protocol.file.allow=always -c submodule.third_party/MeshTool.url=/mnt/f/_GITHUB/apphaus2/MeshTool submodule update --init
git -C ~/_GITHUB/apphaus2/QRX.pack/third_party/MeshTool remote set-url origin https://github.com/apphaus2/MeshTool.git
git -C ~/_GITHUB/apphaus2/QRX.pack/third_party/MeshTool remote add windows /mnt/f/_GITHUB/apphaus2/MeshTool
git config --global core.autocrlf false
cd /mnt/f/_GITHUB/apphaus2/QRX.pack/species/art
for d in */work; do mkdir -p ~/_GITHUB/apphaus2/QRX.pack/species/art/"${d%/work}"; rsync -a "$d" ~/_GITHUB/apphaus2/QRX.pack/species/art/"${d%/work}"/; done
```

- No `.gitattributes` and no Git LFS in either repo; every tracked text file is already LF. (GridLib uses LFS:
  set that up only when GridLib is cloned.)
- The work folders: 95 of them, 3.1 GB. The only other ignored files are `__pycache__`, not copied.
- Check before running anything: `git -C ~/_GITHUB/apphaus2/QRX.pack log --oneline -1` matches the F: checkout's HEAD;
  `git -C ~/_GITHUB/apphaus2/QRX.pack submodule status` shows third_party/MeshTool at the commit the pack records (no `-` or `+`);
  `git status --short` is empty in the pack and in the submodule; `ls ~/_GITHUB/apphaus2/QRX.pack/species/art/*/work/hunyuan-template/clean.blend | wc -l`
  is 65 (the 18 made and 47 of the new 77); `diff -rq /mnt/f/_GITHUB/apphaus2/QRX.pack/species/art ~/_GITHUB/apphaus2/QRX.pack/species/art -x __pycache__`
  prints nothing.
- Paths: no tracked file names `/mnt/f`; make.py finds its steps from its own folder, its tools from `~/qrx-art`
  and the project from where it runs (`species/art`, through `meshtool.json`), so it runs unchanged. Only the old session's throwaway shell scripts named `/mnt/f` (the queue script
  and the shape agents' `run.sh`/`sheet.sh` helpers); they are not in the repo. Write new ones with `~/_GITHUB/apphaus2/QRX.pack`.

## 3. The goal and the rules

**Goal.** Make every creature in `species/art/<id>/` end to end on this machine, from its picture to two rigged,
animated models the apps load, then move the pipeline into MeshTool for QRX.pack, TerraLib and GridLib.

**The standard** (the owner's; `build.py` fails a delivery that breaks it):
- Phones: `<id>.glb` = `gltfpack -cc -tc -tu -kn -km`: meshopt geometry, UASTC KTX2 textures, names and clips kept.
- Quest: `<id>.quest.glb` = `gltfpack -noq -tc -tu -kn -km`: plain float geometry and UASTC. Never meshopt (`-c`),
  never quantization, Draco or ETC1S: Meta's reader stops QRay on each.
- One skin, at most 4 weights per vertex, every vertex weighted, clips in place (`Root` never moves), each cue starts
  and ends in the rest pose, idle and the move clip loop.
- Bones (SPEC.md section 3): every shape has `Root`, `Body`, `Head` (the apps hang the back and mouth sockets on Body
  and Head). Four-legged: also `Chest`, `Neck`, `Tail1..3`, `Leg/Shin/Foot` + `FL FR BL BR`. The other shapes'
  required bones are in MeshTool's `shapes.json`.
- Clip names: each creature's `prompt.md` `| clips |` row; the species documents name what the apps play.
- About 10,000 triangles: **a soft guideline, not a limit** (the owner raised it from 8,000 and made it soft:
  "Go over if it makes sense"). The clean step decimates to 9,500. One texture, 1024 px at most. 5 MB a file at most.

**Rules.**
- Nothing a player reads has an em dash. QRay is the public name; QRX is the code name.
- Never write API keys or tokens into a repo.
- Ask before any download over a few GB.
- Talk to the owner after each run before going on.
- Don't overwrite or delete any `species/models/<id>.low.glb`, and keep build.py's checks from failing them.
- Git: the owner's word is "Nothing in branches. Everything goes to master". The pack is public and published by
  GitHub Pages at `https://qrx-pack.apphaus.us/` about a minute after a push to master: push when the owner says so.
  A change to the pipeline is pushed to MeshTool first, then the pack's pointer to it. QRX pins the pack (QRX's
  `third_party/QRX.pack`); bump that pin when the owner asks.

## 4. Where the work stands

**make.py** (`third_party/MeshTool/make.py`, run from `~/_GITHUB/apphaus2/QRX.pack`; `--help` lists everything). Steps, each skipped when its output exists:
`render, cutout, mesh, clean, rig, clips, pack, check`. A creature with a kept `cutout.png` starts at mesh.
```
python third_party/MeshTool/make.py <id> --keep-strands                 # every step not done
python third_party/MeshTool/make.py <id> --from rig --to check          # redo rig onward (CPU only)
python third_party/MeshTool/make.py <id> --from mesh --mesh-seed 2      # a fresh mesh with another seed (GPU)
python third_party/MeshTool/make.py <id> --file                         # after check passes: intake.py files mesh.glb, mesh.quest.glb, made.json
python species/build.py                                         # writes models/<id>.glb and .quest.glb, keeps the drawn one as .low.glb
```
Run it with `~/qrx-art/mamba/envs/art/bin/python`. `--keep-strands` meshes the cutout as it is; without it thin
strands are cut off first (good for a stray line, bad for legs, wings, antennae, tentacles, tails).

**Choices made.**
- Mesher: **Hunyuan3D 2.1** (the owner's pick). TRELLIS stays as the fallback: the red squirrel's curled tail came out
  a lump on four Hunyuan seeds and right on TRELLIS seed 2. A bad mesh (fused paws, a fake tail, debris) is a mesh
  problem: try other seeds before touching the cleanup.
- Rigger: the **Blender template rig** (`--rigger template`, the default), one script per body shape. UniRig was
  compared on the first animals and is still wired in (`--rigger unirig`) but nothing uses it.
- Render: Grok made every picture (native 1280x720, no crop, no upscale; 16:9 is fine). make.py's own render step
  (FLUX.1-schnell) is unused: it needs a Hugging Face login and about 30 GB.
- Cutouts: the 77 new ones were made here with BiRefNet (`--only cutout`, then copied over `cutout.png`); they keep
  thin parts better than Grok's. Grok's cellar-spider and lantern-jelly were kept; for the four dragonflies ours were
  kept, because Grok's see-through wings are half under 50% alpha and would mesh with holes.

**Filed and published.** The 18 four-legged art animals (alley-cat ... woolly-lamb) are filed and on the pack's
master: 17 Hunyuan (street-terrier, honeyglow-bear-cub, ringtail-raccoon on seed 2, the rest 1234) and red-squirrel
on TRELLIS seed 2.

**The 77 new creatures.** Body shapes in `species/art/meshtool.json`: quadruped 21, fish 14, bird 12 (two of them bats),
flyer 12 (butterflies, moths, dragonflies), crawler 13 (beetles, bees, spiders, scorpion, crabs), soft 5 (jellies,
snails). Each shape has MeshTool's `steps/blender_rig_<shape>.py` and `steps/blender_clips_<shape>.py` (the four-legged use
`blender_rig.py` and `blender_clips.py`).
- Meshed and cleaned: **all 77** (the last 30 in WSL on 2026-11-17, each looked at on a contact sheet of the clean
  step's four views). Each mesh took 154 to 189 s here against 150 to 205 s (mean 160) on F:. The mesh is GPU-bound,
  so ext4 changed nothing. All on seed 1234 except three:
  - granary-owl on **seed 3**: seeds 1234 and 2 both made a third foot between the legs.
  - lamp-moth on **seed 2**: seed 1234's wings came out warped and uneven.
  - snow-moth stays on seed 1234 (seed 2 was tried; its body was lumpier).
  The other seeds are kept beside them in `work/` as `raw-hunyuan-seed<N>.glb` and `hunyuan-template-seed<N>/`.
  A moth meshed standing on its edge is fine: the flyer rig lays every insect flat by its thin side. Judge the
  shape, not which way it stands.
  To find any id not yet meshed: `python -c "import json,os;d=json.load(open('species/art/meshtool.json'));print(' '.join(k for k in d['creatures'] if not os.path.exists('species/art/%s/work/hunyuan-template/clean.blend'%k)))"`.
- **Rigged, animated, packed and checked: all 77** (2026-11-17, with MeshTool 03915ff); check passes on every one,
  nothing filed. Two needed a new mesh first:
  - clocktower-raven: the cutout kept a patch of grey stone between the legs, which meshed as a long plank and left
    the bird rig no legs. The stone is cleared from `cutout.png` (only the large light-grey patch) and it meshed again.
  - ruby-darter on **seed 2**: on seed 1234 the flyer rig could not tell the left forewing from the body.
  Two rig fixes went into MeshTool: bone heat failed on the mice and the vole (a few cm long), so the four-legged rig
  now weights again at about a metre when it leaves more than 2% of the vertices without a bone; and a stale-reference
  crash in the leg cleanup (mangrove-kingfisher) is fixed. The 18 made before still rig byte for byte the same: all 36
  of their packed files match the sha256 in their `made.json`.
- **Filed, built and published: all 77** (2026-11-17; the owner: "dont wait for review"). build.py asked three more
  things of them, now in MeshTool fa3dce4: the 45 that swim or fly (listed under `centre` in `meshtool.json`) have
  their origin at mid-body; the two turtles have the archetype's `hide` clip (added to their `prompt.md` clips rows);
  the three jellies have a `Bell` node for their mouth socket. build.py keeps every `species/models/<id>.low.glb`
  already on disk as it is and draws one only for a creature without (the owner: no need to rebuild ones already
  there; new species need theirs).
  Contact sheets of every clip: the private review page https://claude.ai/artifact/VRxPmS8beVdYxQP5hkteqP (made
  before the centring; the clips are the same). Seen there, still to look at: birds' wings smear as they open
  (blue-skylark); boreal-emerald's wings render nearly black.
- **Six more, filed and built** (2026-11-17): tilehop, dice-beetle, bitfrog, musk-ox-calf, mudskipper, seal-pup.
  Briefs written from their definitions (clips from build.py: idle, the habitat's move, the tricks); BiRefNet cutouts;
  all on seed 1234. dice-beetle is a crawler (a beetle); the rest go through the four-legged rig: bitfrog as a sitting
  frog, seal-pup with the turtle's style but its own hide (a curl: it has no shell), tilehop (two feet) and mudskipper
  (two fins) each split front and back by the rig, which reads as a shuffle. Each new species got its drawn .low.glb.
- **Quest copies** carry 16 bytes after their last quantized animation key (Meta's reader reads 16 there):
  `standard.pad_quest`, run by make.py's pack; build.py's standard faults refuse a copy without it.
- build.py segfaulted once (exit 139) and passed on the rerun; if it happens again, run it with `-X faulthandler`.
- **Next:** the owner's look at the 83 new creatures on a phone and the Quest, and in the gallery.

**build.py.** `standard_faults` checks the standard above on both copies. The owner added the old drawn models back
as `species/models/<id>.low.glb` for a Hi-res on/off option (the apps' "Hi-res creatures", the gallery's Hi-res
button); build.py writes and keeps them. Never fail or delete them.

**Gallery.** `species/preview/gallery.html` (published with the pack) shows every model turning and walking. Serve
`species/` locally (`python -m http.server 8735 -d species`) to look before anything is pushed.

**MeshTool** (`https://github.com/apphaus2/MeshTool`, private): the pipeline's code, no assets, here as the submodule
`third_party/MeshTool`. make.py and intake.py take a project folder (`--project`, or found from where they run:
`species/art` with its `meshtool.json`); `standard.py` is the standard both make.py's check and the pack's
`build.py` read; `shapes.json` the bones each body shape requires; `archetypes/terra` (the natural look: QRX.pack,
TerraLib) and `archetypes/grid` (flat-shaded, glowing edge lines: GridLib, engine side TronX), grid still a plan.
TerraLib and GridLib will take it as a submodule too, and all three use the body rigs. A change to the pipeline is
committed in the submodule and pushed to MeshTool first, then the pack's pointer to it is committed.

## 5. Known problems and what needs the owner's eye

- **The clean step's auto turn is wrong for some shapes.** It lays the longest side along the body axis: a bat's
  wingspan, a spider's leg span, a top-down insect's wingspan. The fish, bird, flyer, crawler and soft rig scripts each
  detect this and turn the mesh themselves, and log it; the clean step should be fixed (`blender_clean.py` or
  `--turn` per creature), and `clean.glb` still faces the wrong way for those.
- **Size is the longest side.** A bat's or butterfly's brief size lands on its wingspan, so the body comes out small.
  The owner has not said whether a dragonfly's size means body length.
- **The clips step renders its look and pose pictures with Cycles on the GPU** (`common.look`). The shape scripts
  switch theirs to the CPU; the four-legged one does not. Don't render while Hunyuan is meshing.
- **Quaternion sign flips.** Blender's exporter wrote sign-flipped rotation keys for Body and Abdomen on the flyer;
  its clips script patches them after export. The four-legged clips may have the same flips (a one-frame twitch);
  not checked.
- **Birds:** the folded wings are separate thin sheets over the body (one mesh, one skin, but separate islands), and
  the wing bones scale up to 1.45 as they open. No app has been seen playing a scale track.
- **Heights:** flips and jumps of long bodies go over SPEC's 0.15 m (a ray reaches 0.19 m).
- **Leg split:** about a 3 mm hole stays at each slit end on five of the 18, between the legs.
- **bpy:** Hunyuan's requirements pin `bpy==4.0`, which PyPI no longer serves; setup.sh leaves it out and
  mesh_hunyuan.py writes the GLB with trimesh instead.
- **TRELLIS's build:** nvdiffrast v0.3.3, kaolin 0.17.0 for torch 2.5.1/cu124, spconv and diff-gaussian-rasterization are
  compiled by setup.sh with `TORCH_CUDA_ARCH_LIST=8.6`; its log is `~/qrx-art/setup-trellis.log`.
- **Hunyuan** crashed once with a torch state_dict TypeError (ringtail-raccoon, seed 3); another seed went through.
- **Hunyuan hangs in WSL** now and then: twice in 33 meshes (mangrove-kingfisher, one-claw-crab) it stopped partway
  through "Volume Decoding", one CPU core busy, the GPU idle, the log still. Killed and rerun on the same seed, both
  went through. A queue should run a watchdog that kills a mesh step whose `mesh-hunyuan.log` is quiet for 8
  minutes (a working one writes every second).
- **User-level Python packages:** a `~/.local/lib/python3.10` copied from an old Ubuntu put huggingface-hub 2.2.0
  ahead of hy3d's 0.30.2 and broke Hunyuan's transformers 4.46.0. That folder is gone, and make.py now runs every
  step with `PYTHONNOUSERSITE=1` (MeshTool 97f1c06). Keep hy3d at huggingface-hub 0.30.2 and transformers 4.46.0.
- **Writing files:** keep LF line endings; a CRLF rewrite once made a 585-line diff.
- **Needs the owner's eye:** every contact sheet before filing; the 18 and everything after them on a phone and on
  the Quest (none has been seen on a device).

## 6. Git in WSL

- Push with Windows' Git Credential Manager, already signed in on this machine:
  `git config --global credential.helper "/mnt/c/Program\ Files/Git/mingw64/bin/git-credential-manager.exe"`.
  (Or `apt install gh` and `gh auth login`, which needs the owner once.) SSH does not work.
- The F: checkouts (`F:\_GITHUB\apphaus2\QRX.pack`, `F:\_GITHUB\apphaus2\MeshTool`) stay for Windows tools and are
  read-only from now on: work only in `~/_GITHUB/apphaus2`. Keep F: in step by pulling there after a push (or straight from WSL:
  `git pull \\wsl.localhost\Ubuntu-24.04\home\smorey2\src\QRX.pack`). The 3.1 GB of work folders on F: can be deleted
  once this clone is checked, at the owner's word.

## 7. A first message for the owner to paste

```
Read species/art/HANDOFF-WSL.md in ~/_GITHUB/apphaus2/QRX.pack and take over the art pipeline from it. First check the clone
as its section 2 says and tell me what you find. Then resume meshing the remaining creatures one at a time, starting
with granary-owl, and stop after the first one to show me how long it took here compared with F:.
```
