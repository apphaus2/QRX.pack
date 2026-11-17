# Creature art: what is delivered for each creature

The pack's creatures have been drawn by `build.py` from shapes (`lib/archetypes/*.py`). This folder is the other
way, after TerraLib's species images: an image model renders the creature in its habitat, the creature is cut out
of the picture, and a rigged, textured mesh is made from it. The pictures and the prompt are kept; the mesh is
what the apps load. Nothing here replaces a species yet: a delivered creature joins the pack only when the owner
says so (see "Taking a delivery in").

One folder per creature, named by the species id: `species/art/<id>/`.

| file | what it is | kept in git |
| --- | --- | --- |
| `prompt.md` | the brief for that creature: its size, its clips, its render prompt. Written here | yes |
| `prompt.txt` | the render prompt word for word ([prompts.py](prompts.py)); never changed once an image is made from it | yes |
| `full.jpg` | the render: the creature in its habitat, as the image model made it | yes |
| `cutout.png` | the creature alone on a transparent background, cut out of `full.jpg` | yes |
| `mesh.glb` | the rigged, textured mesh with its clips | yes, once taken in |
| a gray composite | the cutout on gray, to look at once | **never**: rebuild it from the cutout when needed |

`README.md` in this folder is the table of every creature and where it stands.

## 1. The render (`full.jpg`)

Made from `prompt.txt`, word for word. What every prompt asks, so a render can be judged against it:

- The creature in its home habitat, alone: no people, no other animals, no text, no logos, no frame, no watermark.
- **Side-on, facing left, eye level with the animal, far away with a long lens (near-orthographic)**: no wide angle,
  no low angle, no looking down. Small in the frame, about a fifth of its width, with generous margins on every side.
- Standing still in a relaxed pose: head level, all four legs straight and a little apart, every foot on the ground and
  in view, the tail in view, nothing overlapping it.
- Soft, even daylight from an overcast sky; sharp on the animal; clearly separated from what is behind it.
- A realistic young animal, natural colours, friendly: a children's game, so nothing frightening.
- Landscape 3:2, at least 1024 pixels on the long side (1536 or more is better), JPEG.

## 2. The cutout (`cutout.png`)

- The animal only, on full transparency: no shadow, no ground, no grass between its feet.
- Trimmed to the animal with a margin of at least 16 pixels; no part of it touches the edge.
- Solid alpha inside the body; soft only at the fur's edge. PNG with alpha.

## 3. The rigged mesh (`mesh.glb`)

**Format.** glTF 2.0 binary (`.glb`), everything embedded (no external buffers or images). Metres, +Y up, the head
pointing along **+Z**, the animal's left side along +X. The origin on the ground under the middle of the body.
Real size: the longest side (nose to the end of the tail or rump) is the `size` in its `prompt.md`; it stands at
most 0.15 m tall, ears included, in every clip.

**Geometry and texture.** One continuous skinned mesh (no separate floating parts except eyes, which may be their
own mesh parented to the head bone). About **10,000 triangles** at most (a soft limit: more is fine where the shape needs it). One base-colour texture, 1024 x 1024 at most (512
is enough for most), embedded; a metallic-roughness value or map is optional; no normal map needed. PBR metal
roughness material, metallic 0, roughness about 0.8 for fur. No vertex colours. **The whole file 5 MB at most.**

**Skeleton.** A single skin. Bones named exactly as below (glTF node names, case as written), so the apps can find
them; extra bones (ears, jaw, toes, more tail) are welcome and may be named freely.

| bone | parent | where |
| --- | --- | --- |
| `Root` | none | on the ground under the middle of the body; never moves in a clip |
| `Body` | `Root` | the hips and spine, the middle of the body |
| `Chest` | `Body` | between the shoulders |
| `Neck` | `Chest` | the base of the neck |
| `Head` | `Neck` | the skull |
| `Tail1`, `Tail2`, `Tail3` | `Body`, then each other | from the root of the tail to its tip (fewer for a stub tail) |
| `LegFL`, `ShinFL`, `FootFL` | `Chest` | front left: shoulder to elbow, elbow to wrist, the paw or hoof |
| `LegFR`, `ShinFR`, `FootFR` | `Chest` | front right |
| `LegBL`, `ShinBL`, `FootBL` | `Body` | back left: hip to knee, knee to hock, the paw or hoof |
| `LegBR`, `ShinBR`, `FootBR` | `Body` | back right |

`Head` and `Body` are where the apps attach things (the creature's `mouth` and `back` sockets). Smooth skin weights,
at most four bones per vertex; the knees and elbows must bend cleanly, without the leg collapsing or the body
tearing. The rest pose is the render's neutral stance.

**Clips.** Named exactly; each in place (no root motion: `Root` does not move, the animal walks on the spot):

| clip | kind | what |
| --- | --- | --- |
| `idle` | loop, 3 s | breathing, looking about, the tail and ears moving a little |
| `walk` | loop, one stride, 0.6 to 1.0 s | a walk on the spot: diagonal legs together, each foot lifting as it comes forward, a slight nod of the head |
| each cue in its `prompt.md` | once, 0.8 to 3 s | the cue's move; it starts and ends exactly in the rest pose |

The cue moves (a creature's `prompt.md` says which it needs; the others are welcome):

| cue | the move |
| --- | --- |
| `shake` | shakes itself like a wet dog, from the head down to the tail |
| `roll` | rolls over onto its back and right round to its feet |
| `bow` | a play bow: front legs down and stretched forward, rump up, tail wagging |
| `jump` | a jump straight up, legs tucked, and lands |
| `spin` | turns a full circle on the spot, chasing its tail |
| `dead` | lies down on its side, still, then gets up |
| `wave` | lifts one front paw and waves it |
| `dance` | a happy bouncing dance on the spot |

## 4. Checks before it is taken in

[`intake.py`](intake.py) holds a delivery to this before filing it (`--dry-run` checks without filing): the render's
size, the cutout's alpha and clear edges, one subject, the `.glb` loads, its triangles, file size and texture within
the limits, and it reports the joints and clips it finds. Not yet checked by it, so checked by eye: the axes and
origin, the real size, every named bone and required clip present, each cue starting and ending in the rest pose.
Then the creature is looked at, turning and walking, in `species/preview/gallery.html`.

If a mesh arrives without bones, [RIGGING.md](RIGGING.md) is the fallback: a skeleton, weights and clips made here.

## Taking a delivery in

A delivered creature is filed in its folder and its row in `README.md` is filled in. It replaces the creature `build.py`
draws only at the owner's word, and only after: the pack's model limits are raised to match (today 448 KB on disk,
256 KB as served, set for untextured models); the creature has been seen on the Quest beside six others at full
frame rate; and the iPhone, Android and Quest renderers have each been seen playing its clips. JsonScene loads glTF
through GLTFKit2 (iOS), Filament (Android) and the Spatial SDK (Quest); its own example is Khronos's skinned, textured
Fox, but no QRay creature has yet been a skinned, textured model on any device.
