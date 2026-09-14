#!/usr/bin/env python3
"""
make_info_card.py — Build a neofetch-style info card SVG: a title bar
followed by colored key/value rows, each fading and sliding in on a stagger.

Edit CARD_ROWS below to change what the card says. Set STATIC=1 as an
env var to emit a frozen frame (no animation) for local previews.

Usage:
    python scripts/make_info_card.py
    STATIC=1 python scripts/make_info_card.py

Output:
    info-card.svg
"""

import os

# ─── Content — edit this ────────────────────────────────────────────────────
USERNAME = "siyavashist67"
HOSTNAME = "github"

CARD_ROWS = [
    ("Role", "Psychology Hons Grad \u2192 HR & Talent Acquisition"),
    ("Focus", "Talent Attraction, People Analytics, HR Transformation"),
    ("Stack", "R, Jamovi, JASP, Excel, LaTeX"),
    ("Highlights", "Cum Laude | Dean's Honour Roll | York University"),
    ("Location", "Toronto, ON"),
]
# ─────────────────────────────────────────────────────────────────────────────

STATIC = os.environ.get("STATIC") == "1"

WIDTH = 640
PADDING_X = 28
TITLE_BAR_H = 46
ROW_H = 40
ROW_GAP = 4
TOP_PAD = 22
BOTTOM_PAD = 22

FONT = "'SF Mono','Consolas','Menlo',monospace"

BG = "#0d1117"
BORDER = "#30363d"
TITLE_BG = "#161b22"
DOT_RED, DOT_YEL, DOT_GRN = "#ff5f56", "#ffbd2e", "#27c93f"
KEY_COLOR = "#39d353"      # green, like the contribution graph accent
VALUE_COLOR = "#c9d1d9"
PROMPT_COLOR = "#58a6ff"

ROW_FADE_DUR = 0.5
ROW_STAGGER = 0.18
START_DELAY = 0.3


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


PROMPT_BLOCK_H = 40  # space reserved for the prompt line + its underline


def build_svg() -> str:
    rows_top = TITLE_BAR_H + PROMPT_BLOCK_H + TOP_PAD
    height = rows_top + len(CARD_ROWS) * (ROW_H + ROW_GAP) + BOTTOM_PAD

    rows_svg = []
    for i, (key, value) in enumerate(CARD_ROWS):
        y = rows_top + i * (ROW_H + ROW_GAP) + ROW_H / 2 + 5
        delay = START_DELAY + i * ROW_STAGGER

        if STATIC:
            transform_attrs = ""
            opacity = "1"
            anim = ""
        else:
            transform_attrs = f'transform="translate(-16, 0)"'
            opacity = "0"
            anim = f'''
        <animate attributeName="opacity" from="0" to="1"
                 begin="{delay:.3f}s" dur="{ROW_FADE_DUR}s" fill="freeze" />
        <animateTransform attributeName="transform" type="translate"
                 from="-16 0" to="0 0"
                 begin="{delay:.3f}s" dur="{ROW_FADE_DUR}s" fill="freeze"
                 calcMode="spline" keySplines="0.2 0 0.2 1" />'''

        rows_svg.append(f'''
    <g opacity="{opacity}" {transform_attrs}>
      {anim}
      <text x="{PADDING_X}" y="{y:.1f}" font-family="{FONT}" font-size="15" fill="{KEY_COLOR}" font-weight="bold">{esc(key)}</text>
      <text x="{PADDING_X + 150}" y="{y:.1f}" font-family="{FONT}" font-size="14" fill="{VALUE_COLOR}">{esc(value)}</text>
    </g>''')

    rows_block = "\n".join(rows_svg)

    prompt_line = f"{USERNAME}@{HOSTNAME}"
    underline_width = len(prompt_line) * 8.6

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {height:.0f}"
     width="{WIDTH}" height="{height:.0f}">
  <defs>
    <clipPath id="card-round">
      <rect x="0" y="0" width="{WIDTH}" height="{height:.0f}" rx="10" ry="10" />
    </clipPath>
  </defs>

  <g clip-path="url(#card-round)">
    <rect width="{WIDTH}" height="{height:.0f}" fill="{BG}" />
    <rect width="{WIDTH}" height="{height:.0f}" fill="none" stroke="{BORDER}" stroke-width="1" />

    <!-- title bar -->
    <rect x="0" y="0" width="{WIDTH}" height="{TITLE_BAR_H}" fill="{TITLE_BG}" />
    <line x1="0" y1="{TITLE_BAR_H}" x2="{WIDTH}" y2="{TITLE_BAR_H}" stroke="{BORDER}" stroke-width="1" />
    <circle cx="24" cy="{TITLE_BAR_H/2}" r="6" fill="{DOT_RED}" />
    <circle cx="44" cy="{TITLE_BAR_H/2}" r="6" fill="{DOT_YEL}" />
    <circle cx="64" cy="{TITLE_BAR_H/2}" r="6" fill="{DOT_GRN}" />
    <text x="{WIDTH/2}" y="{TITLE_BAR_H/2 + 5}" font-family="{FONT}" font-size="13"
          fill="{VALUE_COLOR}" text-anchor="middle">neofetch</text>

    <!-- prompt line -->
    <text x="{PADDING_X}" y="{TITLE_BAR_H + 26}" font-family="{FONT}" font-size="14" fill="{PROMPT_COLOR}" font-weight="bold">{esc(prompt_line)}</text>
    <line x1="{PADDING_X}" y1="{TITLE_BAR_H + 34}" x2="{PADDING_X + underline_width:.0f}"
          y2="{TITLE_BAR_H + 34}" stroke="{BORDER}" stroke-width="1" />

    {rows_block}
  </g>
</svg>
'''


def main():
    svg = build_svg()
    with open("info-card.svg", "w") as f:
        f.write(svg)
    mode = "static" if STATIC else "animated"
    print(f"Saved info-card.svg ({mode})")


if __name__ == "__main__":
    main()
