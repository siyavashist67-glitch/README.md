#!/usr/bin/env python3
"""
prep_photo.py — Turn a raw photo into a clean, high-contrast, background-free
grayscale image ready for ASCII conversion.

Uses OpenCV's GrabCut for background removal instead of a deep-learning
matting model. GrabCut needs no model download and no GPU, and for a
portrait shot against a plain wall (the common case for a profile photo)
it segments just as cleanly. If your photo has a busy or low-contrast
background, GrabCut can leave rough edges — swap in `rembg` for a stronger
model if you hit that (see the commented alternative at the bottom).

Usage:
    python scripts/prep_photo.py source-photo.jpg

Output:
    source-prepped.png  (grayscale, background composited to white)
"""

import sys

import cv2
import numpy as np
from PIL import Image


def remove_background_grabcut(bgr: np.ndarray) -> np.ndarray:
    """Returns an RGBA numpy array with the background made transparent."""
    h, w = bgr.shape[:2]

    # GrabCut is slow at full resolution and doesn't need it — segment on a
    # downscaled copy, then upscale the mask back to full size.
    work_w = 800
    scale = work_w / w
    small = cv2.resize(bgr, (int(w * scale), int(h * scale)))
    sh, sw = small.shape[:2]

    mask = np.zeros((sh, sw), np.uint8)
    bgd_model = np.zeros((1, 65), np.float64)
    fgd_model = np.zeros((1, 65), np.float64)

    # Initial rectangle: assumes the subject is roughly centered with a
    # margin around the edges for background, which holds for a standard
    # headshot/portrait crop. Adjust these fractions if your photo is
    # framed differently.
    rect = (int(sw * 0.08), int(sh * 0.03), int(sw * 0.86), int(sh * 0.95))
    cv2.grabCut(small, mask, rect, bgd_model, fgd_model, 8, cv2.GC_INIT_WITH_RECT)

    fg_mask = np.where((mask == 2) | (mask == 0), 0, 255).astype(np.uint8)

    # Smooth the mask edges slightly so hair strands don't look jagged.
    fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    fg_mask = cv2.GaussianBlur(fg_mask, (5, 5), 0)

    fg_mask_full = cv2.resize(fg_mask, (w, h), interpolation=cv2.INTER_LINEAR)

    rgba = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGBA)
    rgba[:, :, 3] = fg_mask_full
    return rgba


def prep_photo(input_path: str, output_path: str = "source-prepped.png") -> None:
    bgr = cv2.imread(input_path)
    if bgr is None:
        raise FileNotFoundError(f"Could not read {input_path}")

    # 1. Remove the background so the subject is isolated on transparency.
    print("Removing background (GrabCut)...")
    rgba = remove_background_grabcut(bgr)
    cutout = Image.fromarray(cv2.cvtColor(rgba, cv2.COLOR_BGRA2RGBA), "RGBA")

    # 2. Composite onto pure white. This matters: white background maps to
    #    the blank end of the ASCII ramp (space characters), so the portrait
    #    prints against nothing instead of a gray box.
    white_bg = Image.new("RGBA", cutout.size, (255, 255, 255, 255))
    composited = Image.alpha_composite(white_bg, cutout).convert("RGB")

    # 3. Boost local contrast with CLAHE (contrast-limited adaptive
    #    histogram equalization). A flatly-lit face has almost no dynamic
    #    range once it's grayscale — CLAHE pulls out real highlights and
    #    shadow structure instead of leaving a muddy blob.
    print("Boosting local contrast...")
    gray = cv2.cvtColor(np.array(composited), cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # Re-flatten the background to pure white. CLAHE operates locally and
    # can drag a perfectly flat white background slightly gray at the
    # edges of its tile grid — stomp anything near-white back to 255 so
    # the ASCII ramp still maps it to blank space.
    enhanced = np.where(enhanced > 245, 255, enhanced).astype(np.uint8)

    out = Image.fromarray(enhanced)
    out.save(output_path)
    print(f"Saved {output_path} ({out.size[0]}x{out.size[1]})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/prep_photo.py <input-photo>")
        sys.exit(1)
    prep_photo(sys.argv[1])

# ─── Alternative: stronger background removal with rembg ───────────────────
# If GrabCut leaves rough edges on your photo (busy background, low subject/
# background contrast, stray hair everywhere), swap step 1 for rembg. It
# downloads a ~170MB-1GB model on first run depending on which one you pick,
# so only reach for it if GrabCut isn't cutting it:
#
#   pip install rembg
#
#   from rembg import remove
#   cutout_bytes = remove(open(input_path, "rb").read())
#   cutout = Image.open(io.BytesIO(cutout_bytes)).convert("RGBA")
