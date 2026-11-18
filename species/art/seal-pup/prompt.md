# Seal Pup (`seal-pup`)

Snowdrop: A fluffy white seal pup with big dark eyes, lying on the snow at the edge of the ice.

| | |
| --- | --- |
| found in | snow (home: Snowfield) |
| rarity | uncommon |
| habitat | water (swims) |
| size | **0.28 m** long |
| clips | `idle`, `swim`, `hide`, `spin`, `wave` |
| status | render made; cutout, mesh and rig by MeshTool |

## Render prompt (`full.jpg`)

Kept word for word in `prompt.txt` (never changed once an image is made from it):

> A young harp seal pup, a fluffy white coat with a faint cream tint, large round dark eyes, a small black nose, short whiskers, two small front flippers and its hind flippers together behind it, lying on firm packed snow at the edge of sea ice, open grey water and ice floes far behind it. Natural wildlife photograph, realistic proportions. Camera at the animal's eye level and far away, a near-orthographic side view with a long lens: no wide angle, no low angle, no looking down. The animal lies still on its belly, side-on, facing left: head up and level, looking ahead, both front flippers on the snow and in view, its hind flippers in view. It is small in the frame, about a fifth of the frame's width, with generous empty space on every side, and clearly separated from everything behind it: nothing overlaps it. Soft, even daylight from an overcast sky, no hard shadows, no rim light. Sharp focus on the animal. Landscape frame, 3:2. No people, no other animals, no text, no logos, no frame, no watermark.

## Cutout (`cutout.png`)

The animal alone from `full.jpg`, on transparency: no shadow, no ground, water or plants, at least 16 pixels of margin, nothing touching the edge.

## Rigged mesh (`mesh.glb`)

To [SPEC.md](../SPEC.md) section 3 where it fits this body (turtle): 0.28 m long, one skinned mesh, one embedded texture,
and the clips above, in place, each cue starting and ending in the rest pose. It must look like the render and the cutout, every mark included.
