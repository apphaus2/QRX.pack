# Mangrove Goby (`mangrove-goby`)

Silt: A blunt, mud-coloured goby that rests on its fins in the tidal channels.

| | |
| --- | --- |
| found in | mangrove (home: Mangrove) |
| rarity | common |
| habitat | water (swims) |
| size | **0.11 m** long |
| clips | `idle`, `swim`, `jump`, `spin` |
| status | render and cutout made; no mesh yet |

## Render prompt (`full.jpg`)

Kept word for word in `prompt.txt` (written in the manner of `../prompts.py`, with the shot fitted to a fish's body: a side view; never changed once an image is made from it):

> A young goby, blunt-headed and mud brown with darker brown spots, a pale belly, spiny back fins and a rounded tail, in clear, still tidal water beside a mangrove, the roots well behind it and a plain silty floor well below it. Natural wildlife photograph, realistic proportions. Camera at the animal's eye level and far away, a near-orthographic side view with a long lens: no wide angle, no low angle, no looking down. The fish holds still in the water, side-on, facing left: its body straight and level, every fin spread and in view, its tail in view. It is small in the frame, about a fifth of the frame's width, with generous empty space on every side, and clearly separated from everything behind it: nothing overlaps it. Soft, even daylight from an overcast sky, no hard shadows, no rim light. Sharp focus on the animal. Landscape frame, 3:2. No people, no other animals, no text, no logos, no frame, no watermark.

## Cutout (`cutout.png`)

The animal alone from `full.jpg`, on transparency: no shadow, no ground, water or plants, at least 16 pixels of margin, nothing touching the edge.

## Rigged mesh (`mesh.glb`)

Not made yet. When it is, to [SPEC.md](../SPEC.md) section 3 where it fits this body (fish): 0.11 m long, one skinned mesh, one embedded texture,
and the clips above, in place, each cue starting and ending in the rest pose. It must look like the render and the cutout, every mark included.
