"""make.py's cutout step: the creature alone from full.jpg with BiRefNet, to SPEC.md section 2.

    python cutout.py <full.jpg> <cutout.png> <model> <revision>

Full transparency outside, solid inside (holes in the largest region filled, other regions dropped), the soft fur edge
kept, trimmed to the animal with a 16 px margin."""
import sys
import numpy as np
import torch
from PIL import Image
from scipy import ndimage
from torchvision import transforms
from transformers import AutoModelForImageSegmentation

source, out, model, revision = sys.argv[1:5]
MARGIN = 16
net = AutoModelForImageSegmentation.from_pretrained(model, revision=revision, trust_remote_code=True).to("cuda").eval().half()
image = Image.open(source).convert("RGB")
prep = transforms.Compose([transforms.Resize((1024, 1024)), transforms.ToTensor(), transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])
with torch.no_grad():
    pred = net(prep(image).unsqueeze(0).to("cuda").half())[-1].sigmoid()[0, 0].float().cpu().numpy()
alpha = np.array(Image.fromarray((pred * 255).astype(np.uint8)).resize(image.size, Image.BILINEAR)).astype(np.float32) / 255
solid = alpha > 0.5
labels, count = ndimage.label(solid)
if count == 0: sys.exit("make: BiRefNet found nothing in the picture")
biggest = 1 + int(np.argmax(ndimage.sum(solid, labels, range(1, count + 1))))
body = ndimage.binary_fill_holes(labels == biggest)
near = ndimage.binary_dilation(body, iterations=6)               # the soft edge round the body, nothing further out
alpha = np.where(body, 1.0, np.where(near, alpha, 0.0))
alpha[alpha < 0.02] = 0
ys, xs = np.nonzero(alpha > 0)
x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
rgba = np.dstack([np.array(image), (alpha * 255).astype(np.uint8)])[y0:y1, x0:x1]
canvas = np.zeros((y1 - y0 + 2 * MARGIN, x1 - x0 + 2 * MARGIN, 4), np.uint8)
canvas[MARGIN:-MARGIN, MARGIN:-MARGIN] = rgba
Image.fromarray(canvas, "RGBA").save(out)
print("make: %d regions, kept the largest; %dx%d with a %d px margin -> %s" % (count, canvas.shape[1], canvas.shape[0], MARGIN, out))
