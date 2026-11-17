# Glacier Owl (`glacier-owl`)

Boreal: A great white owl flecked with blue light, the quiet keeper of the ice.

| | |
| --- | --- |
| found in | snow (home: Snowfield) |
| rarity | legendary |
| habitat | air (flies) |
| size | **0.22 m** long |
| clips | `idle`, `fly`, `headturn`, `spin`, `bow`, `dance`, `snow` |
| status | render and cutout made; no mesh yet |

## Render prompt (`full.jpg`)

Kept word for word in `prompt.txt` (written in the manner of `../prompts.py`, with the shot fitted to a bird's body: a side view; never changed once an image is made from it):

> A young snowy owl, white and fluffy with a scatter of small pale blue flecks, round yellow eyes, a small dark grey beak and feathered feet, on firm packed snow in an open snowfield, a few dark spruce trees far behind it. Natural wildlife photograph, realistic proportions. Camera at the animal's eye level and far away, a near-orthographic side view with a long lens: no wide angle, no low angle, no looking down. The bird stands still on the ground, side-on, facing left, in a relaxed standing pose: head level and looking ahead, wings folded at its sides, both feet on the ground and in view, its tail in view. It is small in the frame, about a fifth of the frame's width, with generous empty space on every side, and clearly separated from everything behind it: nothing overlaps it. Soft, even daylight from an overcast sky, no hard shadows, no rim light. Sharp focus on the animal. Landscape frame, 3:2. No people, no other animals, no text, no logos, no frame, no watermark.

## Cutout (`cutout.png`)

The animal alone from `full.jpg`, on transparency: no shadow, no ground, water or plants, at least 16 pixels of margin, nothing touching the edge.

## Rigged mesh (`mesh.glb`)

Not made yet. When it is, to [SPEC.md](../SPEC.md) section 3 where it fits this body (bird): 0.22 m long, one skinned mesh, one embedded texture,
and the clips above, in place, each cue starting and ending in the rest pose. It must look like the render and the cutout, every mark included.
