# Skyspire Bloom (`skyspire-bloom`)

Real size, not a tabletop species. The clean step scales the longest side of the mesh to the size below. A plant stands and sways. It does not walk.

| | |
| --- | --- |
| size | **75.0 m** longest side |
| clips | `idle` |
| status | picture filed |

## Render prompt (`full.jpg`)

Kept word for word in `prompt.txt`:

> An original invented giant plant, the skyspire bloom: a single impossibly tall slender pale green stalk, clearly as tall as a radio tower, with small leaf rings spaced up its length and a huge drooping bell-shaped flower head at the top in soft violet and white; because the stalk is very thin it may fill the frame's height, but its whole flower and base stay in view; at its base, for scale, a few tiny distant full-grown trees that barely reach its lowest leaf ring, on a flat open salt plain, low pale hills far behind it. Natural landscape photograph, realistic proportions. Camera at eye level and very far away, as if spotted from a road across open country, a near-orthographic side view with a long lens: no wide angle, no low angle, no looking down. A single plant standing alone, seen side-on, its whole shape from the ground to its highest point in view, its base and roots meeting the ground in view, leaning or reaching toward the left. It fills about a third of the frame's width, with a low horizon, a pale plain sky behind it and generous empty space on every side, so its whole outline reads as a clean, high-contrast silhouette at a glance; nothing overlaps it and nothing in front of it. A little atmospheric haze between the camera and the plant shows the distance and its huge size. Soft, even daylight from an overcast sky, no hard shadows, no rim light. Sharp focus on the plant. Landscape frame, 16:9, 1280x720. No people, no animals, no vehicles, no roads, no buildings, no other trees except the tiny scale trees at its base, no text, no logos, no frame, no watermark.

## Cutout (`cutout.png`)

The plant alone from `full.jpg`, on transparency: no shadow, no ground, at least 16 pixels of margin, nothing touching the edge. The first cutout kept the salt plain and the scale trees inside the filled outline. This picture is the plant alone on flat grey.

## Rigged mesh (`mesh.glb`)

Made from the cutout and the picture. Longest side 75.0 m. Clip `idle`, in place. The index still draws 12 by 75 by 12 m.
