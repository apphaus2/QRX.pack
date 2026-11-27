# White Rhino (`white-rhino`)

Real size, not a tabletop species. The clean step scales the longest side of the mesh to the size below.

| | |
| --- | --- |
| size | **4.0 m** longest side |
| clips | `idle`, `walk` |
| status | rendered |

## Render prompt (`full.jpg`)

Kept word for word in `prompt.txt`:

> An adult white rhinoceros, a massive grey barrel body, a broad square lip, two horns with a long front horn, a heavy head held low, thick legs and a thin tail, on open short savanna grass, low thorn bushes far behind it. Natural wildlife photograph, realistic proportions. Camera at eye level and very far away, as if spotted from a road across open country, a near-orthographic side view with a long lens: no wide angle, no low angle, no looking down. The animal stands still, side-on, facing left: head low and level, every leg in view with every foot on the ground, its tail in view. It fills about a third of the frame's width, with a low horizon, a pale plain sky behind it and generous empty space on every side, so its whole outline reads as a clean, high-contrast silhouette at a glance; nothing overlaps it and nothing in front of it. A little atmospheric haze between the camera and the animal shows the distance. Soft, even daylight from an overcast sky, no hard shadows, no rim light. Sharp focus on the animal. Landscape frame, 16:9, 1280x720. No people, no vehicles, no roads, no fences, no other animals, no text, no logos, no frame, no watermark.

## Cutout (`cutout.png`)

The animal alone from `full.jpg`, on transparency: no shadow, no ground, at least 16 pixels of margin, nothing touching the edge.

## Rigged mesh (`mesh.glb`)

Made from the cutout and the render. Longest side 4.0 m. Clips `idle`, `walk`, in place.
