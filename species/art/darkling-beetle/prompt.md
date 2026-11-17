# Darkling Beetle (`darkling-beetle`)

Dune: A black beetle that drinks the fog from its own ridged back.

| | |
| --- | --- |
| found in | barren (home: Barrens) |
| rarity | common |
| habitat | ground (walks) |
| size | **0.07 m** long |
| clips | `idle`, `walk`, `spin`, `dead` |
| status | render and cutout made; no mesh yet |

## Render prompt (`full.jpg`)

Kept word for word in `prompt.txt` (written in the manner of `../prompts.py`, with the shot fitted to a beetle's body: a side view; never changed once an image is made from it):

> A darkling beetle, matt black with a high domed back ridged in rows of bumps, long black legs held high, on flat pale rock on a dry mountain slope, boulders and scree well behind it. Natural wildlife photograph, realistic proportions. Camera at the animal's eye level and far away, a near-orthographic side view with a long lens: no wide angle, no low angle, no looking down. The animal stands still, side-on, facing left: head level, all six legs on the ground and in view, its wing cases closed. It is small in the frame, about a fifth of the frame's width, with generous empty space on every side, and clearly separated from everything behind it: nothing overlaps it. Soft, even daylight from an overcast sky, no hard shadows, no rim light. Sharp focus on the animal. Landscape frame, 3:2. No people, no other animals, no text, no logos, no frame, no watermark.

## Cutout (`cutout.png`)

The animal alone from `full.jpg`, on transparency: no shadow, no ground, water or plants, at least 16 pixels of margin, nothing touching the edge.

## Rigged mesh (`mesh.glb`)

Not made yet. When it is, to [SPEC.md](../SPEC.md) section 3 where it fits this body (beetle): 0.07 m long, one skinned mesh, one embedded texture,
and the clips above, in place, each cue starting and ending in the rest pose. It must look like the render and the cutout, every mark included.
