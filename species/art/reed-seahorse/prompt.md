# Reed Seahorse (`reed-seahorse`)

Nib: A yellow-green seahorse that holds on to weed with its tail.

| | |
| --- | --- |
| found in | water, mangrove (home: Open Water) |
| rarity | common |
| habitat | water (swims) |
| size | **0.11 m** long |
| clips | `idle`, `swim`, `spin`, `bow` |
| status | render and cutout made; no mesh yet |

## Render prompt (`full.jpg`)

Kept word for word in `prompt.txt` (written in the manner of `../prompts.py`, with the shot fitted to a seahorse's body: a side view; never changed once an image is made from it):

> A young seahorse, yellow-green with fine darker bands round its body and a long curling tail, in clear, still river water, a plain gravel bed well below it and open water all round it. Natural wildlife photograph, realistic proportions. Camera at the animal's eye level and far away, a near-orthographic side view with a long lens: no wide angle, no low angle, no looking down. The seahorse holds still upright in open water, side-on, facing left: head level and snout forward, its tail curled loosely below it, its whole body in view. It is small in the frame, about a fifth of the frame's width, with generous empty space on every side, and clearly separated from everything behind it: nothing overlaps it. Soft, even daylight from an overcast sky, no hard shadows, no rim light. Sharp focus on the animal. Landscape frame, 3:2. No people, no other animals, no text, no logos, no frame, no watermark.

## Cutout (`cutout.png`)

The animal alone from `full.jpg`, on transparency: no shadow, no ground, water or plants, at least 16 pixels of margin, nothing touching the edge.

## Rigged mesh (`mesh.glb`)

Not made yet. When it is, to [SPEC.md](../SPEC.md) section 3 where it fits this body (seahorse): 0.11 m long, one skinned mesh, one embedded texture,
and the clips above, in place, each cue starting and ending in the rest pose. It must look like the render and the cutout, every mark included.
