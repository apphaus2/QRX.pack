# Pond Turtle (`pond-turtle`)

Tumble: A green turtle that basks on logs and slips in at the first footstep.

| | |
| --- | --- |
| found in | water, wetland (home: Open Water) |
| rarity | uncommon |
| habitat | water (swims) |
| size | **0.15 m** long |
| clips | `idle`, `swim`, `spin`, `wave` |
| status | render and cutout made; no mesh yet |

## Render prompt (`full.jpg`)

Kept word for word in `prompt.txt` (written in the manner of `../prompts.py`, with the shot fitted to a turtle's body: a side view; never changed once an image is made from it):

> A young pond turtle with a dark olive-green shell with yellow spots, yellow-streaked dark skin and a short tail, on a flat pebbly riverbank, the water and the far bank well behind it. Natural wildlife photograph, realistic proportions. Camera at the animal's eye level and far away, a near-orthographic side view with a long lens: no wide angle, no low angle, no looking down. The animal stands still, side-on, facing left, in a relaxed standing pose: head out and level, looking ahead, all four legs out and every foot on the ground and in view, its tail in view. It is small in the frame, about a fifth of the frame's width, with generous empty space on every side, and clearly separated from everything behind it: nothing overlaps it. Soft, even daylight from an overcast sky, no hard shadows, no rim light. Sharp focus on the animal. Landscape frame, 3:2. No people, no other animals, no text, no logos, no frame, no watermark.

## Cutout (`cutout.png`)

The animal alone from `full.jpg`, on transparency: no shadow, no ground, water or plants, at least 16 pixels of margin, nothing touching the edge.

## Rigged mesh (`mesh.glb`)

Not made yet. When it is, to [SPEC.md](../SPEC.md) section 3 where it fits this body (turtle): 0.15 m long, one skinned mesh, one embedded texture,
and the clips above, in place, each cue starting and ending in the rest pose. It must look like the render and the cutout, every mark included.
