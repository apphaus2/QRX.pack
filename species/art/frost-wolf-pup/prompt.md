# Frost Wolf Pup (`frost-wolf-pup`)

Sleet: A pale grey wolf pup with ice-blue eyes, big paws and a howl it is still practising.

| | |
| --- | --- |
| found in | snow (home: Snowfield) |
| rarity | rare |
| habitat | ground (walks) |
| size | **0.212 m** nose to tail, at most 0.15 m tall in any clip |
| clips | `idle`, `walk`, `shake`, `roll`, `bow` |
| status | waiting for the render |

## Render prompt (`full.jpg`)

Kept word for word in `prompt.txt` (written by `../prompts.py`; never changed once an image is made from it):

> A young grey wolf pup, pale silver grey with a darker grey back, a white chest and belly, ice-blue eyes, big white paws, pointed ears and a bushy tail, on firm packed snow in an open snowfield, a few dark spruce trees far behind it. Natural wildlife photograph, realistic proportions. Camera at the animal's eye level and far away, a near-orthographic side view with a long lens: no wide angle, no low angle, no looking down. The animal stands still, side-on, facing left, in a relaxed standing pose: head level and looking ahead, all four legs straight and a little apart, every foot on the ground and in view, its tail in view. It is small in the frame, about a fifth of the frame's width, with generous empty space on every side, and clearly separated from everything behind it: nothing overlaps it. Soft, even daylight from an overcast sky, no hard shadows, no rim light. Sharp focus on the animal. Landscape frame, 3:2. No people, no other animals, no text, no logos, no frame, no watermark.

## Cutout (`cutout.png`)

The animal alone from `full.jpg`, on transparency: no shadow, no ground or grass, at least 16 pixels of margin, nothing touching the edge.

## Rigged mesh (`mesh.glb`)

Made from the cutout and the render, to [SPEC.md](../SPEC.md) section 3: 0.212 m long, one skinned mesh of at most 8,000 triangles and 1 MB,
one embedded texture (1024 at most), the named skeleton (`Root`, `Body`, `Chest`, `Neck`, `Head`, `Tail1`..., `LegFL`/`ShinFL`/`FootFL`
and the other three legs), skin weights, and the clips above, in place, each cue starting and ending in the rest pose. It must look like the render and the cutout, every mark included.
