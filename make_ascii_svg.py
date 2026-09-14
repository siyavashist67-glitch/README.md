#!/usr/bin/env python3
"""
make_ascii_svg.py — Convert source-prepped.png into a self-typing,
monochrome ASCII-art SVG.

Usage:
    python scripts/make_ascii_svg.py

Output:
    portrait-ascii.svg  (rename to whatever you reference in your README)
"""

import os

from PIL import Image

STATIC = os.environ.get("STATIC") == "1"

# Bright (sparse) -> dark (dense). Leading space clears background to nothing.
RAMP = " .`:-=+*cs#%@"

GRID_COLS = 100

CHAR_W = 6.2      # px per character cell, horizontal
CHAR_H = 11.5     # px per character cell, vertical
FONT_SIZE = 11

FILL_COLOR_DARK = "#8b949e"    # portrait fill on dark-theme viewers
FILL_COLOR_LIGHT = "#444c56"   # portrait fill on light-theme viewers
BG_COLOR = "none"

ROW_DURATION = 0.55       # seconds for one row to wipe in
ROW_STAGGER = 0.045       # seconds between each row's start


def image_to_ascii_grid(img: Image.Image, cols: int, rows: int) -> list[str]:
    img = img.convert("L").resize((cols, rows), Image.LANCZOS)
    pixels = list(img.tobytes())
    ramp_len = len(RAMP) - 1
    lines = []
    for r in range(rows):
        row_pixels = pixels[r * cols:(r + 1) * cols]
        line = "".join(RAMP[int((255 - p) / 255 * ramp_len)] for p in row_pixels)
        lines.append(line)
    return lines


def escape_xml(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def build_svg(lines: list[str]) -> str:
    width = GRID_COLS * CHAR_W
    height = len(lines) * CHAR_H

    svg_rows = []
    style_rules = []

    for i, line in enumerate(lines):
        y = (i + 1) * CHAR_H
        row_id = f"row{i}"
        delay = i * ROW_STAGGER
        safe_line = escape_xml(line)

        # Each row sits inside a <g> that gets clipped by an animated
        # rectangle wiping left to right — this is the "typing" effect.
        # A small trailing block acts as the cursor riding the wipe edge.
        if STATIC:
            # Frozen frame: full width clip, no cursor block, no <animate>.
            # Useful for local previews (SVG renderers that don't run SMIL)
            # and for sanity-checking the portrait itself.
            svg_rows.append(f'''
    <clipPath id="clip-{row_id}">
      <rect x="0" y="{y - CHAR_H}" width="{width}" height="{CHAR_H}" />
    </clipPath>
    <g clip-path="url(#clip-{row_id})">
      <text class="ascii-fill" x="0" y="{y}" font-family="'SF Mono','Consolas','Menlo',monospace"
            font-size="{FONT_SIZE}"
            xml:space="preserve">{safe_line}</text>
    </g>''')
        else:
            svg_rows.append(f'''
    <clipPath id="clip-{row_id}">
      <rect id="clipRect-{row_id}" x="0" y="{y - CHAR_H}" width="0" height="{CHAR_H}">
        <animate attributeName="width" from="0" to="{width}"
                 begin="{delay:.3f}s" dur="{ROW_DURATION}s"
                 fill="freeze" calcMode="spline" keySplines="0.4 0 0.2 1" />
      </rect>
    </clipPath>
    <g clip-path="url(#clip-{row_id})">
      <text class="ascii-fill" x="0" y="{y}" font-family="'SF Mono','Consolas','Menlo',monospace"
            font-size="{FONT_SIZE}"
            xml:space="preserve">{safe_line}</text>
      <rect class="ascii-fill" x="0" y="{y - CHAR_H + 1}" width="{CHAR_W * 1.1}" height="{CHAR_H - 2}"
            opacity="0.85">
        <animate attributeName="x" from="0" to="{width}"
                 begin="{delay:.3f}s" dur="{ROW_DURATION}s"
                 fill="freeze" calcMode="spline" keySplines="0.4 0 0.2 1" />
        <animate attributeName="opacity" from="0.85" to="0"
                 begin="{delay + ROW_DURATION:.3f}s" dur="0.15s" fill="freeze" />
      </rect>
    </g>''')

    defs_and_rows = "\n".join(svg_rows)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {height:.0f}"
     width="{width:.0f}" height="{height:.0f}">
  <style>
    .ascii-fill {{ fill: {FILL_COLOR_LIGHT}; }}
    @media (prefers-color-scheme: dark) {{
      .ascii-fill {{ fill: {FILL_COLOR_DARK}; }}
    }}
  </style>
  <rect width="100%" height="100%" fill="{BG_COLOR}" />
  <defs></defs>
  {defs_and_rows}
</svg>
'''


def compute_grid_rows(img: Image.Image, cols: int) -> int:
    """
    Monospace character cells aren't square, so mapping a photo straight
    onto a cols x rows grid at 1:1 with the pixel resize distorts it —
    typically squishes it wider/shorter than the original crop. Solve for
    the row count that keeps the rendered SVG's aspect ratio (cols*CHAR_W
    by rows*CHAR_H) matching the source photo's aspect ratio.
    """
    img_w, img_h = img.size
    rows = round((cols * CHAR_W) / CHAR_H * (img_h / img_w))
    return max(rows, 1)


def main():
    img = Image.open("source-prepped.png")
    rows = compute_grid_rows(img, GRID_COLS)
    lines = image_to_ascii_grid(img, GRID_COLS, rows)
    svg = build_svg(lines)
    with open("portrait-ascii.svg", "w") as f:
        f.write(svg)
    print(f"Saved portrait-ascii.svg ({GRID_COLS}x{rows} chars)")


if __name__ == "__main__":
    main()
