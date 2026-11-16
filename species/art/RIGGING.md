# From a delivered mesh to a creature that walks

A mesh made from a picture is one textured piece with no bones. Before the apps can walk it, hold it still or have it
do its cues, it needs a skeleton, skin weights and clips, written into the glTF as a skin: joint nodes, `skins`
with inverse bind matrices, `JOINTS_0` and `WEIGHTS_0` on the mesh, and clips that turn the joints. `lib/gltf.py`
writes none of that today (rigid nodes and plain colours only). This is the plan for it; none of it is built.

## Can the apps show a skinned, textured model?

Read from JsonScene `c43e6f9` (the pin), read only. The renderers hand the file to a glTF library and then play clips
by name, so skinning and textures are the library's work, not JsonScene's.

| renderer | where | what it does | seen |
| --- | --- | --- | --- |
| iPhone and Apple TV (SceneKit) | `ios/Sources/JsonScene/ModelLoader.swift:221` loads with GLTFKit2, `:226` builds the scene with `GLTFSCNSceneSource`; `:244` `split` regroups each clip's channels onto the node they name, found by name at `:264` | GLTFKit2 makes the skinner and the textured materials | **Yes, in the tvOS simulator** (2026-10-19 and 20, `docs/HISTORY.md` "TV" and "The house pet"): Rusty, the Khronos Fox, a skinned and textured model (`QRX.pack/glyphs/bodies/fox.json`), walked, ate and napped. The comment at `:241` is about that fox's bone channels (`/b_Hip_01.position`). Not seen on an iPhone |
| Android phone and TV (Filament through SceneView) | `android/jsonscene-compose/.../FilamentSceneRenderer.kt:373` `createModelInstance`, `:376` `ModelNode(autoAnimate = false)`, `:403` `playAnimation` | Filament's gltfio skins and textures; SceneView's `ModelNode` applies the playing clip each frame | **Partly**: the Google TV emulator showed "the framed fox and duck" (2026-10-18). The history does not say whether the fox's legs moved. Not seen on the Galaxy |
| Quest (Spatial SDK) | `android/jsonscene-spatial/.../SpatialSceneRenderer.kt:126` a `Mesh` from the file, `:134` to `:137` an `Animated` component by clip name | Meta's renderer; its docs say glTF animations play through `Animated` but do not mention skins | **Not known.** No record of the fox on the headset |

**The cheapest proof needs no new code:** every app's Demo menu has "Fox and butterfly" (`GlyphDemo.kt:23`, the
Quest's debug build included). Open it on the Quest, the Galaxy and the iPhone and watch Rusty: if his legs move as he
walks, that renderer plays skinned, textured glTF. Do that before building anything below.

Limits the renderers put on a rig, to be kept from the start: joint names unique and plain (iOS finds them by name,
`:264`; no `.` or `/`); at most four influences per vertex; one skin per mesh; the texture inside the `.glb`; clip
names exactly as the documents play them (`idle`, `walk` or `swim` or `fly`, one per cue).

## The rig, step by step (`art/rig.py`, to be written)

1. **Normalize.** Turn the delivered mesh so the head is along +Z and up is +Y (prompts ask for the animal facing
   left, side-on, so the turn is known), scale it to the definition's `size`, stand its lowest point on y = 0, centre
   it. Bring it under the triangle limit (quadric decimation) and the texture under the texture limit.
2. **Skeleton from a template.** One template per body plan, for the 18 animals the quadruped: root, hips, three
   spine joints, neck, head, two ears, three tail joints, and each leg as upper, lower and foot: 22 joints. The joints
   are placed from the mesh itself: cut it below the belly and the four legs are the four separate pieces (front and
   back by z, left and right by x); each leg's joints sit at set fractions of its height; the spine runs along the
   body's centre line from the tail root to the neck; the head is the front piece above the shoulders. The placement
   is written to `art/<id>/joints.json`, so a wrong guess is corrected by hand and kept, and drawn in the gallery
   over the mesh for checking.
3. **Weights.** Each vertex bound to at most four joints, by its distance to each bone with a falloff, then smoothed
   over its neighbours: a leg's vertices only to that leg's chain and the hips or chest, so a step never pulls the
   belly. (Blender's automatic "heat" weights are the better known method; this is the plain-Python version of it,
   with the same check: no vertex unweighted, weights summing to 1.)
4. **Clips.** The clips the procedural animals have today, written for joints instead of rigid parts: `idle` (breath,
   tail, ears, a look about), the move (a four-beat walk for walkers: each leg's swing, the spine's flex and the
   head's bob tied to the steps), and one clip per cue the archetype animates (roll, shake, jump, spin, bow and the
   rest). The behaviour cues (come, stay, speak, hide) are handlers and need no clip of their own.
5. **Write and check.** `lib/gltf.py` learns skins, textures and samplers; `--check` learns to measure a skinned
   model (its box in every clip, from the joints' movement), so the habitat limits still hold.
6. **Into the pack, on the owner's word only.** The rigged model goes beside `build.py`'s, and a species' document
   points at it only when the owner says that species is done. Until then a rigged model is tried through a preview
   code like `preview/quantized/`.

## What changes for the pack (the owner's to accept)

- **Sizes.** A textured model is far larger than the 448 KB on disk / 256 KB downloaded limits and than anything the
  Quest has been measured with (seven creatures at 90 fps, all plain colours). Proposed in `intake.py`: 2 MB, 30,000
  triangles, a 1024 px texture.
- **Not repeatable.** Images and meshes from a generator come out differently each time, so they are kept source
  files. The pack's rule "the same definitions build the same bytes" stops at the rig: `rig.py` is repeatable from
  the kept mesh and `joints.json`, but the mesh itself is not.
- **One more decision per animal.** A delivered mesh can be wrong in ways no check sees (five legs, a fused tail,
  a face on the side). Each one is looked at before it is rigged.

## If the image agent can deliver a rigged mesh

Some image-to-3D services rig quadrupeds themselves. If the agent's tool can, `intake.py` already reads a skinned
mesh (it reports joints and clips); `rig.py` then only renames the clips and checks the limits above.
