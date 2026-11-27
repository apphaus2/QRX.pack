# Giganotosaurus (`giganotosaurus`)

Real size, not a tabletop species. The clean step scales the longest side of the mesh to the size below.

| | |
| --- | --- |
| size | **13.0 m** longest side |
| clips | `idle`, `walk` |
| status | rendered |

## Render prompt (`full.jpg`)

Kept word for word in `prompt.txt`:

> An adult giganotosaurus, a huge two-legged predatory dinosaur, a long low narrow head with a row of teeth, tiny three-fingered arms, a deep body held level and a long stiff tail held straight out behind, mottled brown and grey skin, on a flat open floodplain, low red cliffs far behind it. Natural wildlife photograph, realistic proportions. Camera at eye level and very far away, as if spotted from a road across open country, a near-orthographic side view with a long lens: no wide angle, no low angle, no looking down. The animal stands still, side-on, facing left: body level, head level and looking ahead, both legs in view with both feet on the ground, its whole tail in view. It fills about a third of the frame's width, with a low horizon, a pale plain sky behind it and generous empty space on every side, so its whole outline reads as a clean, high-contrast silhouette at a glance; nothing overlaps it and nothing in front of it. A little atmospheric haze between the camera and the animal shows the distance and its huge size. Soft, even daylight from an overcast sky, no hard shadows, no rim light. Sharp focus on the animal. Landscape frame, 16:9, 1280x720. No people, no vehicles, no roads, no other animals, no text, no logos, no frame, no watermark.

## Cutout (`cutout.png`)

The animal alone from `full.jpg`, on transparency: no shadow, no ground, at least 16 pixels of margin, nothing touching the edge.

## Rigged mesh (`mesh.glb`)

Made from the cutout and the render. Longest side 13.0 m. Clips `idle`, `walk`, in place.
