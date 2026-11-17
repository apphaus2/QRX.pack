# Arctic Char (`arctic-char`)

Tarn: A dark fish with a red belly from the cold tundra lakes.

| | |
| --- | --- |
| found in | tundra (home: Tundra) |
| rarity | rare |
| habitat | water (swims) |
| size | **0.14 m** long |
| clips | `idle`, `swim`, `jump`, `spin`, `flip` |
| status | render and cutout made; no mesh yet |

## Render prompt (`full.jpg`)

Kept word for word in `prompt.txt` (written in the manner of `../prompts.py`, with the shot fitted to a fish's body: a side view; never changed once an image is made from it):

> A young arctic char, dark grey-green back with small cream spots, a bright red-orange belly, and red fins with white front edges, in a clear, cold tundra lake, a plain stony floor well below it and open water all round it. Natural wildlife photograph, realistic proportions. Camera at the animal's eye level and far away, a near-orthographic side view with a long lens: no wide angle, no low angle, no looking down. The fish holds still in the water, side-on, facing left: its body straight and level, every fin spread and in view, its tail in view. It is small in the frame, about a fifth of the frame's width, with generous empty space on every side, and clearly separated from everything behind it: nothing overlaps it. Soft, even daylight from an overcast sky, no hard shadows, no rim light. Sharp focus on the animal. Landscape frame, 3:2. No people, no other animals, no text, no logos, no frame, no watermark.

## Cutout (`cutout.png`)

The animal alone from `full.jpg`, on transparency: no shadow, no ground, water or plants, at least 16 pixels of margin, nothing touching the edge.

## Rigged mesh (`mesh.glb`)

Not made yet. When it is, to [SPEC.md](../SPEC.md) section 3 where it fits this body (fish): 0.14 m long, one skinned mesh, one embedded texture,
and the clips above, in place, each cue starting and ending in the rest pose. It must look like the render and the cutout, every mark included.
