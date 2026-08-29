"""
Prepare the memoji for clean ASCII conversion:
  1. cut the flat background with a border-seeded flood fill
  2. boost LOCAL contrast (CLAHE) so the face gains highlights and shadows
     instead of reading as one flat blob
  3. composite the subject onto pure white (white -> spaces in the ascii ramp)
  4. crop to the subject and pad back to the ascii canvas aspect

The original template used rembg + a 176 MB U2-Net ONNX model here. That model
exists to segment real photos out of cluttered backgrounds. This source is a
memoji on a single uniform colour, so a flood fill does the same job exactly,
with no model download and no third-party host. If you ever swap in a real
photograph with a busy background, this step is the one to revisit.

Output: source-prepped.png (grayscale), consumed by make_ascii_svg.py.

    python scripts/prep_photo.py <input.png> [output.png]
"""
import os
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
INP = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "source-photo.png")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "source-prepped.png")

TOL = 26        # per-channel tolerance, measured against the SEED colour
                #  (FLOODFILL_FIXED_RANGE) -- without it the fill creeps across
                #  the memoji's soft gradients and eats the face
ASPECT = (80 * 8) / (53 * 15)    # ascii canvas: cols*CELL_W / rows*CELL_H

rgb = np.array(Image.open(INP).convert("RGB"))
h, w = rgb.shape[:2]

# 1. flood fill the background inward from all four corners. Only pixels
#    CONNECTED to a corner are removed, so light areas inside the face (teeth,
#    eye whites, skin highlights) are never touched.
ff_mask = np.zeros((h + 2, w + 2), np.uint8)
flood = rgb.copy()
for seed in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
    cv2.floodFill(flood, ff_mask, seed, (0, 0, 0),
                  loDiff=(TOL,) * 3, upDiff=(TOL,) * 3,
                  flags=4 | cv2.FLOODFILL_MASK_ONLY | cv2.FLOODFILL_FIXED_RANGE | (255 << 8))
background = ff_mask[1:-1, 1:-1] > 0
alpha = np.where(background, 0, 255).astype(np.uint8)

# 2. local-contrast the luminance (CLAHE)
gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
gray = cv2.createCLAHE(clipLimit=2.6, tileGridSize=(8, 8)).apply(gray)

# a touch of global lift so the face sits in the sparse end of the ramp
gray = cv2.convertScaleAbs(gray, alpha=1.05, beta=18)

# 3. paste onto white using the mask (feathered a hair to avoid a hard halo)
mask = cv2.GaussianBlur(alpha.astype(np.float32) / 255.0, (0, 0), 1.0)
out = gray.astype(np.float32) * mask + 255.0 * (1.0 - mask)
out = np.clip(out, 0, 255).astype(np.uint8)

# 4. crop to the subject's bounding box, then pad back to the canvas aspect.
#    Without this the subject sits small in the middle and half the grid is blank.
#    Bound on the flood-fill mask, NOT on the pixel values: the memoji carries a
#    faint drop shadow that is too dark to be filled but too light to become an
#    ascii character, and bounding on pixels would frame the shadow, not the face.
ys, xs = np.where(alpha > 127)
y0, y1 = ys.min(), ys.max()
x0, x1 = xs.min(), xs.max()
mh, mw = int((y1 - y0) * 0.04), int((x1 - x0) * 0.04)
out = out[max(0, y0 - mh):min(h, y1 + mh), max(0, x0 - mw):min(w, x1 + mw)]

ch, cw = out.shape
if cw / ch < ASPECT:                     # too narrow -> pad left/right
    pad = int(round(ch * ASPECT)) - cw
    out = np.pad(out, ((0, 0), (pad // 2, pad - pad // 2)), constant_values=255)
else:                                    # too short -> pad top/bottom
    pad = int(round(cw / ASPECT)) - ch
    out = np.pad(out, ((pad // 2, pad - pad // 2), (0, 0)), constant_values=255)

Image.fromarray(out, mode="L").save(OUT)
print("wrote", OUT, out.shape, "| background pixels removed:", int(background.sum()))
