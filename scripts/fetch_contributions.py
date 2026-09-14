#!/usr/bin/env python3
"""
fetch_contributions.py — Pull a GitHub user's public contribution calendar
with no auth, no token, no GraphQL API call.

GitHub serves the same HTML fragment the profile page uses at:
    https://github.com/users/<username>/contributions

Each day is a <td class="ContributionCalendar-day"> with a `data-date` and
a `data-level` (0-4, the color bucket), and a matching <tool-tip for="...">
holding the human-readable count ("3 contributions on September 12th." /
"No contributions on ..."). We parse both and write a flat JSON file the
heatmap renderer consumes.

Usage:
    python scripts/fetch_contributions.py [username]

Output:
    data/contributions.json
"""

import json
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DEFAULT_USERNAME = "siyavashist67-glitch"
CONTRIB_URL = "https://github.com/users/{username}/contributions"

COUNT_RE = re.compile(r"(\d[\d,]*)\s+contributions?\s+on", re.IGNORECASE)
NO_CONTRIB_RE = re.compile(r"no contributions on", re.IGNORECASE)


def fetch_contributions(username: str) -> dict:
    url = CONTRIB_URL.format(username=username)
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Tooltip text keyed by the day cell's id, so we can pull an exact count
    # instead of relying on the coarse 0-4 data-level bucket alone.
    tooltip_text_by_id = {}
    for tip in soup.find_all("tool-tip"):
        target_id = tip.get("for")
        if target_id:
            tooltip_text_by_id[target_id] = tip.get_text(strip=True)

    day_cells = soup.find_all("td", class_="ContributionCalendar-day")
    if not day_cells:
        raise RuntimeError(
            "No contribution cells found — GitHub may have changed its "
            "markup, or the username may not exist / have no public activity."
        )

    days = []
    for cell in day_cells:
        date = cell.get("data-date")
        level = int(cell.get("data-level", 0))
        if not date:
            continue

        count = 0
        tip_text = tooltip_text_by_id.get(cell.get("id", ""), "")
        if tip_text and not NO_CONTRIB_RE.search(tip_text):
            match = COUNT_RE.search(tip_text)
            if match:
                count = int(match.group(1).replace(",", ""))

        days.append({"date": date, "level": level, "count": count})

    days.sort(key=lambda d: d["date"])

    total = sum(d["count"] for d in days)

    # Current streak: consecutive days with count > 0, walking back from the
    # most recent day that has data.
    current_streak = 0
    for d in reversed(days):
        if d["count"] > 0:
            current_streak += 1
        else:
            break

    longest_streak = 0
    running = 0
    for d in days:
        if d["count"] > 0:
            running += 1
            longest_streak = max(longest_streak, running)
        else:
            running = 0

    best_day = max(days, key=lambda d: d["count"]) if days else None

    monthly_totals = {}
    for d in days:
        month_key = d["date"][:7]  # "YYYY-MM"
        monthly_totals[month_key] = monthly_totals.get(month_key, 0) + d["count"]

    result = {
        "username": username,
        "total_contributions": total,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "best_day": best_day,
        "monthly_totals": monthly_totals,
        "days": days,
    }
    return result


def main():
    username = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_USERNAME
    print(f"Fetching contributions for {username}...")
    data = fetch_contributions(username)

    Path("data").mkdir(exist_ok=True)
    out_path = Path("data/contributions.json")
    out_path.write_text(json.dumps(data, indent=2))

    print(f"Saved {out_path} — {data['total_contributions']} contributions, "
          f"{len(data['days'])} days, current streak {data['current_streak']}")


if __name__ == "__main__":
    main()
