# One-Claw Crab (`one-claw-crab`)

Fiddle: A blue crab that waves one huge orange claw from the mouth of its burrow.

| | |
| --- | --- |
| found in | mangrove (home: Mangrove) |
| rarity | rare |
| habitat | ground (walks) |
| size | **0.13 m** long |
| clips | `idle`, `walk`, `wave`, `spin`, `dance` |
| status | render and cutout made; no mesh yet |

## Render prompt (`full.jpg`)

Kept word for word in `prompt.txt` (written in the manner of `../prompts.py`, with the shot fitted to a crab's body: a front view; never changed once an image is made from it):

> A fiddler crab with a slate-blue shell flecked with darker blue, one huge bright orange claw, one small claw and pale legs, on a flat muddy bank at the edge of a mangrove, the roots and trunks well behind it. Natural wildlife photograph, realistic proportions. Camera at the animal's eye level and far away, a near-orthographic side view with a long lens: no wide angle, no low angle, no looking down. The animal stands still, facing the camera, its shell level: both claws held in front, every leg on the ground and in view. It is small in the frame, about a fifth of the frame's width, with generous empty space on every side, and clearly separated from everything behind it: nothing overlaps it. Soft, even daylight from an overcast sky, no hard shadows, no rim light. Sharp focus on the animal. Landscape frame, 3:2. No people, no other animals, no text, no logos, no frame, no watermark.

## Cutout (`cutout.png`)

The animal alone from `full.jpg`, on transparency: no shadow, no ground, water or plants, at least 16 pixels of margin, nothing touching the edge.

## Rigged mesh (`mesh.glb`)

Not made yet. When it is, to [SPEC.md](../SPEC.md) section 3 where it fits this body (crab): 0.13 m long, one skinned mesh, one embedded texture,
and the clips above, in place, each cue starting and ending in the rest pose. It must look like the render and the cutout, every mark included.
