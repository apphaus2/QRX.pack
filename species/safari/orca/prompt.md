# Orca (`orca`)

Real size, not a tabletop species. The clean step scales the longest side of the mesh to the size below.

| | |
| --- | --- |
| size | **8.0 m** longest side |
| clips | `idle`, `swim` |
| status | rendered |

## Render prompt (`full.jpg`)

Kept word for word in `prompt.txt`:

> An adult male orca, a glossy black and white body, a white eye patch, a grey saddle behind the very tall straight dorsal fin, paddle-shaped pectoral fins and a notched tail fluke, leaping clear of a calm grey sea, open water to a flat horizon far behind it. Natural wildlife photograph, realistic proportions. Camera at eye level and very far away, as if spotted from a road across open country, a near-orthographic side view with a long lens: no wide angle, no low angle, no looking down. The whale is caught in mid-leap, side-on, facing left, its whole body clear of the water with a small splash below, its dorsal fin, both pectoral fins and tail fluke in view. It fills about a third of the frame's width, with a low horizon, a pale plain sky behind it and generous empty space on every side, so its whole outline reads as a clean, high-contrast silhouette at a glance; nothing overlaps it and nothing in front of it. A little atmospheric haze between the camera and the animal shows the distance and its huge size. Soft, even daylight from an overcast sky, no hard shadows, no rim light. Sharp focus on the animal. Landscape frame, 16:9, 1280x720. No people, no vehicles, no roads, no other animals, no text, no logos, no frame, no watermark.

## Cutout (`cutout.png`)

The animal alone from `full.jpg`, on transparency: no shadow, no ground, at least 16 pixels of margin, nothing touching the edge.

## Rigged mesh (`mesh.glb`)

Made from the cutout and the render. Longest side 8.0 m. Clips `idle`, `swim`, in place.
