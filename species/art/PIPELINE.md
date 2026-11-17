# Making a creature here, end to end

Today an outside agent (Grok) does every step from the prompt to the two packed meshes, and this repository only
checks what comes back (`intake.py`, `build.py`). This is the plan to run the whole chain on one of the owner's own
computers, so a creature can be made, fixed and remade without waiting on anyone. **None of it is built yet.** Write
it as `species/art/make.py` (one command per creature, each step resumable) beside `intake.py`.

## The machine

Image-to-3D and texture generation want an NVIDIA GPU with CUDA; an Apple M2 Pro with 16 GB cannot run them.

| part | at least | better |
| --- | --- | --- |
| GPU | 24 GB VRAM (RTX 3090 or 4090) | 32 GB or more (RTX 5090, A6000) |
| memory | 64 GB | 128 GB |
| disk | 200 GB free (models are 10 to 40 GB each) | NVMe |
| system | Linux (Ubuntu 24.04) or Windows with WSL2 | |
| software | Python 3.11, CUDA 12.x, PyTorch, Blender 4.x (run headless), Node 24, git with LFS | |

Every model is downloaded once and kept outside the repository. Pin each one by name and version or commit in
`make.py`, so a creature can be remade the same way.

## The steps

Each step reads the previous step's file in `art/<id>/` and writes its own, so any step can be redone alone
(`make.py <id> --from rig`). What is kept in git is unchanged from SPEC.md: `prompt.txt`, `full.jpg`,
`cutout.png`, `mesh.glb`, and now `mesh.quest.glb` too. Work files go in `art/<id>/work/`, which git ignores.

1. **Render** (`full.jpg`). From `prompt.txt` word for word, as SPEC.md section 1 asks: side-on, facing left, a
   long lens, small in the frame, 3:2, at least 1536 px wide. Locally with FLUX.1 through diffusers or ComfyUI,
   with a fixed seed written to `work/render.json`. Several seeds per creature, and the owner picks one.
2. **Cutout** (`cutout.png`). Background removal with BiRefNet (or rembg using a BiRefNet model): full
   transparency, solid inside, soft fur edge, 16 px margin (SPEC.md section 2). `intake.py --look` shows it on gray.
3. **Mesh from the picture** (`work/raw.glb`). Image to textured 3D with Hunyuan3D 2.1 (shape, then its PBR
   texture), or TRELLIS as the second choice. Feed it the cutout. A model that takes several views does better: if
   one is used, render the back and front views in step 1 too. The result is one textured piece with no bones,
   often 100k+ triangles. **The owner looks at it before going on**: five legs, a fused tail or a face on the side
   are not visible to any check.
4. **Clean up** (`work/clean.glb`), in Blender, headless. Turn it so the head is +Z and up is +Y, scale it to the
   brief's size, put its lowest point at y = 0 and the origin under the middle of the body. Decimate to under
   10,000 triangles, bake the texture onto one 1024 x 1024 base-colour map (metallic 0, roughness 0.8), and remove
   vertex colours.
5. **Rig** (`work/rigged.glb`), in Blender. The quadruped skeleton in GROK.md, with its bone names exactly as
   written (Root, Body, Chest, Neck, Head, Tail1 to 3, Leg/Shin/Foot for FL, FR, BL, BR, plus ears if wanted). It is
   placed from the mesh as RIGGING.md step 2 describes (legs found by cutting below the belly), and the placement
   is saved to `joints.json` so a wrong guess can be fixed by hand. Weights come from Blender's automatic (heat)
   weights, at most 4 per vertex. UniRig (an ML auto-rigger) is worth trying first; keep Blender as the fallback.
6. **Clips**, in Blender, written by script and the same for every quadruped: `idle` (about 3 s loop), `walk` (one
   stride, 0.6 to 1.0 s, in place), and one clip per cue the brief lists (shake, roll, bow, jump, spin, dead,
   wave, dance), each starting and ending in the rest pose. The clips are keyframes on the named bones, scaled by
   the leg length, so one script animates all 18 animals. Export glTF with the skin and the clips.
7. **Pack the two copies.** One source, two files, with the same clips and the same size:
   - `mesh.glb` for the phones and TVs: `gltfpack -i rigged.glb -o mesh.glb -cc -tc -tu -kn -km` (meshopt
     geometry, 16-bit positions, UASTC KTX2 texture, names and clips kept).
   - `mesh.quest.glb` for the Quest: `gltfpack -i rigged.glb -o mesh.quest.glb -noq -tc -tu -kn -km` (no `-c`
     and no quantization: Meta's reader stops QRay on meshopt, Draco, 16-bit positions and ETC1S KTX2, and has
     read only plain floats with a UASTC texture). Use a gltfpack built with texture compression (basisu), and
     check `--help` lists `-tc`.
8. **Check and file.** `python3 species/art/intake.py <id> --full ... --cutout ... --mesh mesh.glb --quest
   mesh.quest.glb --tool "make.py, <date>"`, then `python3 species/build.py`. Build writes `models/<id>.glb` and
   `models/<id>.quest.glb` and checks both (5 MB each at most, Quest extensions only, the clips the habitat and
   cues play, the same box within a millimetre).
9. **Look on the devices.** The species preview and gallery (`species/preview/`) first, then the Quest, the
   iPhone and the Galaxy. Nothing is pushed to the pack's `master` without the owner's word.

## The standard (the owner, 2026-11-16)

UASTC textures on both copies. Meshopt geometry for the phones. Plain float geometry for the Quest: no meshopt, no
`KHR_mesh_quantization`, no Draco. `build.py` should fail a delivery that breaks this, so a wrong file can never
reach a headset; it does not check the texture mode or quantization yet.

## What to decide on the new machine

- Which image model renders (local FLUX, or an API), and whether to keep Grok's existing renders for the 18.
- Hunyuan3D 2.1 or TRELLIS, after one creature through each.
- UniRig or the Blender template rig, after one creature through each.
- Whether plants (`models/plants/`) go through the same chain: steps 1 to 4 and 7, with no rig and no clips.
