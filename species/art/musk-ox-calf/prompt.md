# Musk Ox Calf (`musk-ox-calf`)

Tufty: A round, shaggy calf with a long dark coat, a pale saddle and two stubby horn buds.

| | |
| --- | --- |
| found in | tundra (home: Tundra) |
| rarity | uncommon |
| habitat | ground (walks) |
| size | **0.25 m** long |
| clips | `idle`, `walk`, `shake`, `roll` |
| status | render made; cutout, mesh and rig by MeshTool |

## Render prompt (`full.jpg`)

Kept word for word in `prompt.txt` (never changed once an image is made from it):

> A young musk ox calf, round and shaggy, a long dark brown coat with a paler saddle on its back, a short pale muzzle, two small stubby horn buds, short sturdy legs with pale hooves and a tiny tail hidden in the fur, on low flat moss and lichen on the open tundra, a few low rocks far behind it. Natural wildlife photograph, realistic proportions. Camera at the animal's eye level and far away, a near-orthographic side view with a long lens: no wide angle, no low angle, no looking down. The animal stands still, side-on, facing left, in a relaxed standing pose: head level and looking ahead, all four legs straight and a little apart, every foot on the ground and in view, its tail in view. It is small in the frame, about a fifth of the frame's width, with generous empty space on every side, and clearly separated from everything behind it: nothing overlaps it. Soft, even daylight from an overcast sky, no hard shadows, no rim light. Sharp focus on the animal. Landscape frame, 3:2. No people, no other animals, no text, no logos, no frame, no watermark.

## Cutout (`cutout.png`)

The animal alone from `full.jpg`, on transparency: no shadow, no ground, water or plants, at least 16 pixels of margin, nothing touching the edge.

## Rigged mesh (`mesh.glb`)

To [SPEC.md](../SPEC.md) section 3 where it fits this body (four-legged): 0.25 m long, one skinned mesh, one embedded texture,
and the clips above, in place, each cue starting and ending in the rest pose. It must look like the render and the cutout, every mark included.
