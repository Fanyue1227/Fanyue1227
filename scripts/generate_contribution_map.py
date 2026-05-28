from __future__ import annotations

import base64
import calendar
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen


USERNAME = "Fanyue1227"
ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
OUTPUT = ASSETS / "contribution-map.svg"

TEXTURES = {
    "grass": ASSETS / "Grass_Block_(side_texture)_JE2_BE2.png",
    "stone": ASSETS / "Stone_(texture)_JE5_BE3.png",
    1: ASSETS / "96px-Coal_Ore_(texture)_JE5_BE4.png",
    2: ASSETS / "96px-Iron_Ore_(texture)_JE6_BE4.png",
    3: ASSETS / "96px-Gold_Ore_(texture)_JE7_BE4.png",
    4: ASSETS / "96px-Diamond_Ore_(texture)_JE5_BE5.png",
}


class ContributionParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.days: list[tuple[date, int]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "td":
            return
        data = dict(attrs)
        if "ContributionCalendar-day" not in (data.get("class") or ""):
            return
        day = data.get("data-date")
        if not day:
            return
        level = int(data.get("data-level") or 0)
        self.days.append((date.fromisoformat(day), level))


def fetch_contributions() -> list[tuple[date, int]]:
    url = f"https://github.com/users/{USERNAME}/contributions"
    request = Request(url, headers={"User-Agent": "Fanyue1227-profile-updater"})
    with urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8")

    parser = ContributionParser()
    parser.feed(html)
    days = sorted(parser.days, key=lambda item: item[0])
    if not days:
        raise RuntimeError("No contribution data found in GitHub response.")
    return days


def data_uri(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(path)
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def image_tag(href: str, x: int, y: int, size: int, title: str) -> str:
    return (
        f'<image class="tile" href="{href}" x="{x}" y="{y}" '
        f'width="{size}" height="{size}" preserveAspectRatio="none">'
        f"<title>{title}</title></image>"
    )


def build_svg(records: list[tuple[date, int]]) -> str:
    cell = 18
    gap = 3
    left = 52
    top = 42
    month_y = 18
    grid_top = top + cell + gap
    bottom_pad = 30
    right_pad = 14

    start = records[0][0]
    end = records[-1][0]
    weeks = ((end - start).days // 7) + 1
    width = left + weeks * (cell + gap) - gap + right_pad
    height = grid_top + 7 * (cell + gap) - gap + bottom_pad

    uris = {key: data_uri(path) for key, path in TEXTURES.items()}
    labels = {
        0: "stone",
        1: "coal ore",
        2: "iron ore",
        3: "gold ore",
        4: "diamond ore",
    }

    svg: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Minecraft block contribution map from {start} to {end}">',
        f"<title>Minecraft block contribution map, {start:%b %Y} - {end:%b %Y}</title>",
        '<rect width="100%" height="100%" fill="#0d1117"/>',
        (
            "<style>"
            "text{font-family:Consolas,Monaco,monospace;font-size:11px;fill:#8b949e}"
            ".year{font-size:12px;fill:#c9d1d9}"
            ".tile{shape-rendering:crispEdges}"
            "</style>"
        ),
        f'<text class="year" x="{left}" y="14">{start:%b %Y} - {end:%b %Y}</text>',
    ]

    seen_months: set[tuple[int, int]] = set()
    for day, _level in records:
        key = (day.year, day.month)
        if key in seen_months:
            continue
        seen_months.add(key)
        col = (day - start).days // 7
        x = left + col * (cell + gap)
        svg.append(f'<text x="{x}" y="{month_y + 16}">{calendar.month_abbr[day.month]}</text>')

    for row, label in [(1, "Mon"), (3, "Wed"), (5, "Fri")]:
        y = grid_top + row * (cell + gap) + 13
        svg.append(f'<text x="14" y="{y}">{label}</text>')

    for col in range(weeks):
        x = left + col * (cell + gap)
        svg.append(image_tag(uris["grass"], x, top, cell, "decorative grass row"))

    for day, level in records:
        col = (day - start).days // 7
        weekday = day.weekday() + 1
        if weekday == 7:
            weekday = 0
        x = left + col * (cell + gap)
        y = grid_top + weekday * (cell + gap)
        texture = "stone" if level == 0 else min(level, 4)
        label = labels[min(level, 4)]
        svg.append(image_tag(uris[texture], x, y, cell, f"{day.isoformat()}: {label}"))

    svg.append(
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" '
        'fill="none" stroke="#30363d"/>'
    )
    svg.append("</svg>")
    return "\n".join(svg) + "\n"


def main() -> None:
    records = fetch_contributions()
    OUTPUT.write_text(build_svg(records), encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)} for {records[0][0]}..{records[-1][0]}")


if __name__ == "__main__":
    main()
