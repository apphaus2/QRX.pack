# Aurora Eel (`aurora-eel`)

Ribbon: A dark eel with lines of green light running the length of its sides.

| | |
| --- | --- |
| found in | water (home: Open Water) |
| rarity | epic |
| habitat | water (swims) |
| size | **0.24 m** long |
| clips | `idle`, `swim`, `spin`, `dance`, `jump` |
| status | render and cutout made; no mesh yet |

## Render prompt (`full.jpg`)

Kept word for word in `prompt.txt` (written in the manner of `../prompts.py`, with the shot fitted to a eel's body: a side view; never changed once an image is made from it):

> A young eel, dark blue-green, with two thin lines of bright sea-green running along its sides, a violet fringe on its long low fin, in clear, still river water, a plain gravel bed well below it and open water all round it. Natural wildlife photograph, realistic proportions. Camera at the animal's eye level and far away, a near-orthographic side view with a long lens: no wide angle, no low angle, no looking down. The eel holds still in the water, side-on, facing left: its body in one long gentle curve, head level, the whole of it from head to tail tip in view. It is small in the frame, about a fifth of the frame's width, with generous empty space on every side, and clearly separated from everything behind it: nothing overlaps it. Soft, even daylight from an overcast sky, no hard shadows, no rim light. Sharp focus on the animal. Landscape frame, 3:2. No people, no other animals, no text, no logos, no frame, no watermark.

## Cutout (`cutout.png`)

The animal alone from `full.jpg`, on transparency: no shadow, no ground, water or plants, at least 16 pixels of margin, nothing touching the edge.

## Rigged mesh (`mesh.glb`)

Not made yet. When it is, to [SPEC.md](../SPEC.md) section 3 where it fits this body (eel): 0.24 m long, one skinned mesh, one embedded texture,
and the clips above, in place, each cue starting and ending in the rest pose. It must look like the render and the cutout, every mark included.
