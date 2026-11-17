# Starlit Ray (`starlit-ray`)

Nocturne: A midnight-blue ray scattered with lights like a clear night sky.

| | |
| --- | --- |
| found in | water (home: Open Water) |
| rarity | legendary |
| habitat | water (swims) |
| size | **0.17 m** long |
| clips | `idle`, `swim`, `spin`, `flip`, `wave`, `dance`, `stars` |
| status | render and cutout made; no mesh yet |

## Render prompt (`full.jpg`)

Kept word for word in `prompt.txt` (written in the manner of `../prompts.py`, with the shot fitted to a ray's body: a top view, from directly above; never changed once an image is made from it):

> A young eagle ray, a midnight-blue disc scattered with small pale blue-white spots like stars, and a long slender tail, gliding low over a plain bottom of smooth pale grey sand in clear, still water. Natural wildlife photograph, realistic proportions. Camera directly above the animal and far away, looking straight down, a near-orthographic top view with a long lens: no wide angle, no tilt. The animal glides still with its head pointing to the left of the frame, its whole disc flat and fully in view, its tail straight out behind it and in view. It is small in the frame, about a fifth of the frame's width, with generous empty space on every side, and clearly separated from everything behind it: nothing overlaps it. Soft, even daylight from an overcast sky, no hard shadows, no rim light. Sharp focus on the animal. Landscape frame, 3:2. No people, no other animals, no text, no logos, no frame, no watermark.

## Cutout (`cutout.png`)

The animal alone from `full.jpg`, on transparency: no shadow, no ground, water or plants, at least 16 pixels of margin, nothing touching the edge.

## Rigged mesh (`mesh.glb`)

Not made yet. When it is, to [SPEC.md](../SPEC.md) section 3 where it fits this body (ray): 0.17 m long, one skinned mesh, one embedded texture,
and the clips above, in place, each cue starting and ending in the rest pose. It must look like the render and the cutout, every mark included.
