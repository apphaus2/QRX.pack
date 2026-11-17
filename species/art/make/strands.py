"""Thin strands off a cutout before it is meshed: a whisker, a leash, a stray line the picture drew (the raccoon's
picture has one under its tail) becomes a thread of geometry the rig then drags about. An opening of the alpha
(erode, then grow back) takes away anything narrower than about half a percent of the picture; the soft edge of
what stays is kept as it was."""
import os
from PIL import Image, ImageChops, ImageFilter


def drop_strands(image, fraction=0.005):
    image = image.convert("RGBA")
    if os.environ.get("QRX_KEEP_STRANDS"): return image            # make.py --keep-strands: thin parts are the animal
    alpha = image.getchannel("A")
    k = max(3, int(round(max(image.size) * fraction)) | 1)          # odd
    solid = alpha.point(lambda a: 255 if a > 127 else 0)
    opened = solid.filter(ImageFilter.MinFilter(k)).filter(ImageFilter.MaxFilter(k))
    keep = opened.filter(ImageFilter.MaxFilter(3))                   # the soft fringe just outside the opened shape
    image.putalpha(ImageChops.multiply(alpha, keep))
    return image
