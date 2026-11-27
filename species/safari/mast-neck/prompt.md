# Mast Neck (`mast-neck`)

Real size, not a tabletop species. The clean step scales the longest side of the mesh to the size below.

| | |
| --- | --- |
| size | **110.0 m** longest side |
| clips | `idle`, `walk` |
| status | new |

## Render prompt (`full.jpg`)

Kept word for word in `prompt.txt`:

> An original sea animal, a heavy body low in calm water and a long neck with a small head rising high above the surface, plain dark grey, open sea to a flat horizon. Natural wildlife photograph, realistic proportions. Camera at eye level and very far away, as if spotted from a road across open country, a near-orthographic side view with a long lens: no wide angle, no low angle, no looking down. The animal stands still, side-on, facing left: the neck rises nearly straight, the small head is at the top, and the back just breaks the water. It fills about two thirds of the frame's height, with room above its highest point and below its feet, with a low horizon, a pale plain sky behind it and generous empty space on every side, so its whole outline reads as a clean, high-contrast silhouette at a glance; nothing overlaps it and nothing in front of it. A little atmospheric haze between the camera and the animal shows the distance and its huge size. Soft, even daylight from an overcast sky, no hard shadows, no rim light. Sharp focus on the animal. Landscape frame, 16:9, 1280x720. No people, no vehicles, no roads, no other animals, no text, no logos, no frame, no watermark.

## Cutout (`cutout.png`)

The animal alone from `full.jpg`, on transparency: no shadow, no ground, at least 16 pixels of margin, nothing touching the edge.

## Rigged mesh (`mesh.glb`)

Made from the cutout and the render. Longest side 110.0 m. Clips `idle`, `walk`, in place.
