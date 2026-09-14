#!/usr/bin/env python3
"""
render_heatmap_svg.py — Render data/contributions.json as the classic
53-week x 7-day GitHub contribution calendar: rounded colored boxes that
slide in diagonally, then a legend and a stats footer.

Usage:
    python scripts/render_heatmap_svg.py

Output:
    contrib-heatmap.svg
"""

import calendar
import json
import os
from datetime import datetime
from pathlib import Path

STATIC = os.environ.get("STATIC") == "1"

# none -> brightest. Level 0 (no contributions) is theme-adaptive via a CSS
# class below; levels 1-5 (the green scale) stay fixed since they read fine
# against either a light or dark page background.
PALETTE = [None, "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0"]
EMPTY_LIGHT = "#ebedf0"
EMPTY_DARK = "#161b22"
TEXT_LIGHT = "#57606a"
TEXT_DARK = "#8b949e"

BOX = 11
GAP = 3
CELL = BOX + GAP

LEFT_PAD = 28     # room for weekday labels
TOP_PAD = 24      # room for month labels
RIGHT_PAD = 24
BOTTOM_PAD = 64   # room for legend + stats line

WEEKDAY_LABELS = {1: "Mon", 3: "Wed", 5: "Fri"}  # row index -> label (Sun=0)

REVEAL_STAGGER = 0.010   # seconds between each box's start (diagonal wave)
REVEAL_DUR = 0.35

BG = "none"


def load_days(path: str = "data/contributions.json") -> dict:
    return json.loads(Path(path).read_text())


def assign_grid(days: list[dict]) -> tuple[list[dict], int]:
    """Attach (col, row) grid coordinates to each day. row 0 = Sunday."""
    first_date = datetime.strptime(days[0]["date"], "%Y-%m-%d")
    start_weekday = (first_date.weekday() + 1) % 7  # Mon=0..Sun=6 -> Sun=0

    for i, d in enumerate(days):
        idx = i + start_weekday
        d["col"] = idx // 7
        d["row"] = idx % 7

    n_cols = days[-1]["col"] + 1
    return days, n_cols


def month_label_positions(days: list[dict]) -> list[tuple[int, str]]:
    """Return (col, month_abbrev) for the first week a new month appears in."""
    seen_months = set()
    labels = []
    for d in days:
        date = datetime.strptime(d["date"], "%Y-%m-%d")
        key = (date.year, date.month)
        if key not in seen_months and date.day <= 7:
            seen_months.add(key)
            labels.append((d["col"], calendar.month_abbr[date.month]))
    return labels


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_svg(data: dict) -> str:
    days = data["days"]
    days, n_cols = assign_grid(days)

    grid_w = n_cols * CELL
    grid_h = 7 * CELL

    width = LEFT_PAD + grid_w + RIGHT_PAD
    height = TOP_PAD + grid_h + BOTTOM_PAD

    boxes = []
    max_delay = 0.0
    for d in days:
        x = LEFT_PAD + d["col"] * CELL
        y = TOP_PAD + d["row"] * CELL
        level = min(d["level"], len(PALETTE) - 1)
        color = PALETTE[level]
        fill_attr = 'class="hm-empty"' if color is None else f'fill="{color}"'
        # Diagonal wave: delay depends on col+row so the reveal sweeps
        # top-left to bottom-right rather than column by column.
        delay = (d["col"] + d["row"]) * REVEAL_STAGGER
        max_delay = max(max_delay, delay)

        title = esc(f"{d['count']} contributions on {d['date']}" if d["count"]
                     else f"No contributions on {d['date']}")

        if STATIC:
            boxes.append(
                f'<rect x="{x}" y="{y}" width="{BOX}" height="{BOX}" rx="2" ry="2" '
                f'{fill_attr}><title>{title}</title></rect>'
            )
        else:
            boxes.append(f'''
    <rect x="{x}" y="{y}" width="{BOX}" height="{BOX}" rx="2" ry="2" {fill_attr}
          opacity="0" transform="translate(-6,-6)">
      <title>{title}</title>
      <animate attributeName="opacity" from="0" to="1"
               begin="{delay:.3f}s" dur="{REVEAL_DUR}s" fill="freeze" />
      <animateTransform attributeName="transform" type="translate"
               from="-6 -6" to="0 0"
               begin="{delay:.3f}s" dur="{REVEAL_DUR}s" fill="freeze"
               calcMode="spline" keySplines="0.2 0 0.2 1" />
    </rect>''')

    boxes_svg = "\n".join(boxes)

    # Weekday row labels (Mon / Wed / Fri, GitHub's convention)
    weekday_labels_svg = "\n".join(
        f'<text class="hm-text" x="{LEFT_PAD - 8}" y="{TOP_PAD + row * CELL + BOX - 1}" '
        f'font-family="\'SF Mono\',monospace" font-size="9" '
        f'text-anchor="end">{label}</text>'
        for row, label in WEEKDAY_LABELS.items()
    )

    # Month labels along the top
    month_labels_svg = "\n".join(
        f'<text class="hm-text" x="{LEFT_PAD + col * CELL}" y="{TOP_PAD - 8}" '
        f'font-family="\'SF Mono\',monospace" font-size="10">{label}</text>'
        for col, label in month_label_positions(days)
    )

    # Legend: Less [boxes] More — sized from the right edge so "More" never
    # runs past the canvas regardless of font metrics.
    legend_y = TOP_PAD + grid_h + 26
    less_w = 26
    more_w = 30
    boxes_w = len(PALETTE) * (BOX + 4) - 4
    legend_total_w = less_w + 8 + boxes_w + 8 + more_w
    legend_start_x = width - RIGHT_PAD - legend_total_w

    legend_boxes_list = []
    for i, color in enumerate(PALETTE):
        lx = legend_start_x + less_w + 8 + i * (BOX + 4)
        ly = legend_y - BOX + 2
        cls_or_fill = 'class="hm-empty"' if color is None else f'fill="{color}"'
        legend_boxes_list.append(
            f'<rect x="{lx}" y="{ly}" width="{BOX}" height="{BOX}" rx="2" ry="2" {cls_or_fill} />'
        )
    legend_boxes = "\n".join(legend_boxes_list)
    more_x = legend_start_x + less_w + 8 + boxes_w + 8

    total = data["total_contributions"]
    streak = data["current_streak"]
    longest = data["longest_streak"]
    contrib_word = "contribution" if total == 1 else "contributions"
    stats_text = (
        f"{total:,} {contrib_word} in the last year  \u00b7  "
        f"current streak {streak}d  \u00b7  longest streak {longest}d"
    )

    footer_y = TOP_PAD + grid_h + 50

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}"
     width="{width}" height="{height}">
  <style>
    .hm-empty {{ fill: {EMPTY_LIGHT}; }}
    .hm-text {{ fill: {TEXT_LIGHT}; }}
    @media (prefers-color-scheme: dark) {{
      .hm-empty {{ fill: {EMPTY_DARK}; }}
      .hm-text {{ fill: {TEXT_DARK}; }}
    }}
  </style>
  <rect width="100%" height="100%" fill="{BG}" />
  {month_labels_svg}
  {weekday_labels_svg}
  {boxes_svg}

  <text class="hm-text" x="{legend_start_x}" y="{legend_y}" font-family="'SF Mono',monospace" font-size="10">Less</text>
  {legend_boxes}
  <text class="hm-text" x="{more_x}" y="{legend_y}" font-family="'SF Mono',monospace" font-size="10">More</text>

  <text class="hm-text" x="{LEFT_PAD}" y="{footer_y}" font-family="'SF Mono',monospace" font-size="11">{esc(stats_text)}</text>
</svg>
'''


def main():
    data = load_days()
    svg = build_svg(data)
    with open("contrib-heatmap.svg", "w") as f:
        f.write(svg)
    print(f"Saved contrib-heatmap.svg ({data['total_contributions']} contributions)")


if __name__ == "__main__":
    main()
