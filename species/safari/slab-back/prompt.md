# Slab Back (`slab-back`)

Real size, not a tabletop species. The clean step scales the longest side of the mesh to the size below.

| | |
| --- | --- |
| size | **150.0 m** longest side |
| clips | `idle`, `walk` |
| status | new |

## Render prompt (`full.jpg`)

Kept word for word in `prompt.txt`:

> An original heavy upright walker, a deep wide chest, a small long head held forward, short thick arms held clear of the chest, three blunt pale rectangular slabs standing up on a dark back with wide gaps between them, and a thick tail as long as the body is tall held straight out behind, on flat ground at the edge of a town, low roofs far below its knees. Natural wildlife photograph, realistic proportions. Camera at eye level and very far away, as if spotted from a road across open country, a near-orthographic side view with a long lens: no wide angle, no low angle, no looking down. The animal stands still, side-on, facing left: it stands upright, head forward, both feet on the ground, the tail straight out, and the three slabs in view. It fills about two thirds of the frame's height, with room above its highest point and below its feet, with a low horizon, a pale plain sky behind it and generous empty space on every side, so its whole outline reads as a clean, high-contrast silhouette at a glance; nothing overlaps it and nothing in front of it. A little atmospheric haze between the camera and the animal shows the distance and its huge size. Soft, even daylight from an overcast sky, no hard shadows, no rim light. Sharp focus on the animal. Landscape frame, 16:9, 1280x720. No people, no vehicles, no roads, no other animals, no text, no logos, no frame, no watermark.

## Cutout (`cutout.png`)

The animal alone from `full.jpg`, on transparency: no shadow, no ground, at least 16 pixels of margin, nothing touching the edge.

## Rigged mesh (`mesh.glb`)

Made from the cutout and the render. Longest side 150.0 m. Clips `idle`, `walk`, in place.
