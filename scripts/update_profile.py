#!/usr/bin/env python3
"""Render assets/stats.svg (primary language across public repos) and assets/skyline.svg
(the contribution calendar as an isometric-style skyline) from live GitHub data.
Standard library only. Counting repos by primary language needs one request and is not
inflated by vendored UI kits or generated code, unlike byte counts.

Environment
  GH_USER          profile to read (default: vijitagarwal)
  GH_TOKEN         optional; adds the contribution calendar (GraphQL, needed for the skyline) and raises rate limits
  PROFILE_FIXTURE  optional path to a JSON file; renders offline instead of calling the API
"""
from __future__ import annotations

import datetime as dt
import html
import json
import os
import pathlib
import sys
import urllib.request

USER = os.environ.get("GH_USER") or "vijitagarwal"
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
OUT = pathlib.Path(__file__).resolve().parent.parent / "assets" / "stats.svg"
SKY_OUT = OUT.with_name("skyline.svg")

# Same Tokyo Night-derived tokens as assets/hero.svg
BG, LINE, INK, SOFT, MUTED = "#1a1b26", "#292e42", "#c0caf5", "#a9b1d6", "#8690ba"
BRIGHT = "#eef1ff"
MONO = "ui-monospace,'SF Mono',SFMono-Regular,Menlo,Consolas,'Liberation Mono','DejaVu Sans Mono',monospace"
SANS = "'Segoe UI Variable Display','SF Pro Display',system-ui,-apple-system,'Segoe UI','Helvetica Neue',Arial,sans-serif"
FALLBACK_COLORS = {
    "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Python": "#3572A5", "HTML": "#e34c26",
    "C++": "#f34b7d", "CSS": "#563d7c", "C": "#aaaaaa", "Java": "#b07219", "Shell": "#89e051",
    "Jupyter Notebook": "#DA5B0B", "PLpgSQL": "#336790",
}

GQL = """query($login:String!){user(login:$login){
  contributionsCollection{contributionCalendar{totalContributions
    weeks{contributionDays{date contributionCount}}}}}}"""


def call(url: str, payload: dict | None = None):
    headers = {"User-Agent": "profile-stats", "Accept": "application/vnd.github+json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    body = json.dumps(payload).encode() if payload else None
    with urllib.request.urlopen(urllib.request.Request(url, body, headers), timeout=30) as r:
        return json.load(r)


def fetch_repos() -> dict:
    """Primary language per public, non-fork repo. REST only: one request per 100 repos."""
    repos, page = [], 1
    while True:
        batch = call(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner&page={page}")
        repos += [r for r in batch if not r["fork"]]
        if len(batch) < 100:
            break
        page += 1
    langs: dict[str, int] = {}
    for repo in repos:
        if repo["language"]:
            langs[repo["language"]] = langs.get(repo["language"], 0) + 1
    return {"repos": len(repos), "languages": langs, "colors": {}, "contributions": None}


def fetch_contributions() -> tuple[int, dict[str, int]]:
    """Optional extra: needs a token. Failure only drops the contribution line and the skyline."""
    res = call("https://api.github.com/graphql", {"query": GQL, "variables": {"login": USER}})
    if res.get("errors"):
        raise RuntimeError(res["errors"])
    cal = res["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = {d["date"]: d["contributionCount"] for w in cal["weeks"] for d in w["contributionDays"]}
    return cal["totalContributions"], days


def load() -> dict:
    fixture = os.environ.get("PROFILE_FIXTURE")
    if fixture:
        return json.loads(pathlib.Path(fixture).read_text())
    data = fetch_repos()
    if TOKEN:
        try:
            data["contributions"], data["calendar"] = fetch_contributions()
        except Exception as exc:
            print(f"contribution calendar unavailable ({exc}); skipping it", file=sys.stderr)
    return data


def lift(hex_color: str) -> str:
    """Brighten very dark language colours so every segment reads on the dark card."""
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    lum = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
    if lum >= 0.30:
        return hex_color
    mix = 0.40
    return "#%02x%02x%02x" % tuple(round(c + (255 - c) * mix) for c in (r, g, b))


def render(data: dict) -> str:
    total = sum(data["languages"].values()) or 1
    ranked = sorted(data["languages"].items(), key=lambda kv: -kv[1])
    top, rest = ranked[:5], sum(v for _, v in ranked[5:])
    items = [(n, v / total, data["colors"].get(n) or FALLBACK_COLORS.get(n) or "#7aa2f7") for n, v in top]
    if rest:
        items.append(("Other", rest / total, "#565f89"))
    items = [(n, s, lift(c)) for n, s, c in items]

    W, H, X0, X1, GAP = 1000, 252, 48, 952, 3
    usable = (X1 - X0) - GAP * (len(items) - 1)
    widths = [max(8.0, s * usable) for _, s, _ in items]
    scale = usable / sum(widths)
    widths = [w * scale for w in widths]

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t">',
         f'<title id="t">Primary language across {data["repos"]} public repositories</title>',
         f"""<style>
.mono{{font-family:{MONO}}}
.seg{{animation:grow .6s cubic-bezier(.22,.8,.24,1) backwards}}
.lbl{{animation:fade .5s ease-out backwards}}
@keyframes grow{{from{{transform:scaleX(0)}}}}
@keyframes fade{{from{{opacity:0}}}}
@media (prefers-reduced-motion:reduce){{.seg,.lbl{{animation:none}}}}
</style>""",
         f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="18" fill="{BG}" stroke="{LINE}" stroke-width="2"/>',
         f'<text x="{X0}" y="62" fill="{BRIGHT}" font-family="{SANS}" font-size="24" font-weight="700" letter-spacing="-.4">Primary language across my public repos</text>']

    kpis = [f'<tspan fill="{BRIGHT}" font-weight="700">{data["repos"]}</tspan> public repositories',
            f'<tspan fill="{BRIGHT}" font-weight="700">{len(data["languages"])}</tspan> languages']
    for i, line in enumerate(kpis):
        o.append(f'<text class="mono" x="{X1}" y="{48 + i * 22}" text-anchor="end" fill="{SOFT}" font-size="14">{line}</text>')

    x = float(X0)
    for i, ((name, share, col), w) in enumerate(zip(items, widths)):
        o.append(f'<rect class="seg" x="{x:.1f}" y="92" width="{w:.1f}" height="24" rx="5" fill="{col}" '
                 f'style="transform-origin:{x:.1f}px 104px;animation-delay:{0.15 + i * 0.12:.2f}s"/>')
        x += w + GAP

    base = 0.15 + len(items) * 0.12
    for i, (name, share, col) in enumerate(items):
        cx, cy = X0 + (i % 3) * 304, 166 + (i // 3) * 32
        pct = f"{share * 100:.1f}%" if share >= 0.001 else "<0.1%"
        o.append(f'<g class="lbl" style="animation-delay:{base:.2f}s"><rect x="{cx}" y="{cy - 11}" width="12" height="12" rx="3" fill="{col}"/>'
                 f'<text class="mono" x="{cx + 22}" y="{cy}" fill="{INK}" font-size="15" font-weight="600">{html.escape(name)}</text>'
                 f'<text class="mono" x="{cx + 262}" y="{cy}" text-anchor="end" fill="{MUTED}" font-size="15">{pct}</text></g>')

    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    o.append(f'<text class="mono" x="{X0}" y="232" fill="#6a7299" font-size="12">rendered by scripts/update_profile.py on {stamp} UTC</text>')
    o.append("</svg>")
    return "\n".join(o)


# ---------------------------------------------------------------- contribution skyline
RAMP = ["#3b4f8f", "#5f87e8", "#7dcfff", "#b4f9f8"]   # level 1..4, cool-to-bright
PEAK, GROUND = "#ff9e64", "#222639"


def shade(hex_color: str, k: float) -> str:
    """k < 1 darkens, k > 1 lightens a #rrggbb colour."""
    rgb = [int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]
    rgb = [round(c * k) if k <= 1 else round(c + (255 - c) * (k - 1)) for c in rgb]
    return "#%02x%02x%02x" % tuple(rgb)


def render_skyline(calendar: dict[str, int], total: int | None) -> str:
    days = sorted(dt.date.fromisoformat(d) for d in calendar)
    sunday0 = days[0] - dt.timedelta(days=(days[0].weekday() + 1) % 7)   # Sunday that opens column 0
    cell = {d: divmod((d - sunday0).days, 7) for d in days}               # date -> (column, row 0=Sun)
    ncols = max(c for c, _ in cell.values()) + 1
    counts = {d: calendar[d.isoformat()] for d in days}
    active = sorted(v for v in counts.values() if v > 0)
    q1, q2, q3 = ((active[int(len(active) * f)] if active else 0) for f in (0.25, 0.5, 0.75))
    peak_day = max(counts, key=lambda d: (counts[d], d)) if active else None

    W, H, ROWS = 1000, 352, 7
    OX, OY = 5.0, 9.0                      # depth step per row (up and to the right)
    cw = min(16.0, (904 - (ROWS - 1) * OX) / ncols)
    tile, dx, dy = cw - 2.2, OX * 0.82, OY * 0.82
    x0 = 48 + (904 - (ncols * cw + (ROWS - 1) * OX)) / 2
    y_front = 282.0

    def origin(c: int, r: int) -> tuple[float, float]:
        depth = ROWS - 1 - r               # Sunday sits at the back, Saturday at the front
        return x0 + c * cw + depth * OX, y_front - depth * OY

    flat, towers, beacon = [], [], ""
    for r in range(ROWS):                  # painter's order: back rows first, left to right
        for c in range(ncols):
            d = next((k for k, v in cell.items() if v == (c, r)), None)
            if d is None:
                continue
            bx, by = origin(c, r)
            n = counts[d]
            flat.append(f"M{bx:.1f} {by:.1f}h{tile:.1f}l{dx:.1f} {-dy:.1f}h{-tile:.1f}z")
            if n == 0:
                continue
            h = 8 + 17 * (n - 1) ** 0.5
            col = PEAK if d == peak_day else RAMP[(n > q1) + (n > q2) + (n > q3)]
            front = f"{bx:.1f},{by:.1f} {bx + tile:.1f},{by:.1f} {bx + tile:.1f},{by - h:.1f} {bx:.1f},{by - h:.1f}"
            right = (f"{bx + tile:.1f},{by:.1f} {bx + tile + dx:.1f},{by - dy:.1f} "
                     f"{bx + tile + dx:.1f},{by - dy - h:.1f} {bx + tile:.1f},{by - h:.1f}")
            top = (f"{bx:.1f},{by - h:.1f} {bx + tile:.1f},{by - h:.1f} "
                   f"{bx + tile + dx:.1f},{by - dy - h:.1f} {bx + dx:.1f},{by - dy - h:.1f}")
            towers.append(
                f'<g class="tw" style="transform-origin:{bx + tile / 2:.1f}px {by:.1f}px;animation-delay:{0.25 + c * 0.032 + r * 0.01:.2f}s">'
                f'<polygon points="{front}" fill="{shade(col, .74)}"/><polygon points="{right}" fill="{shade(col, .50)}"/>'
                f'<polygon points="{top}" fill="{shade(col, 1.12)}"/></g>')
            if d == peak_day:
                tx, ty = bx + (tile + dx) / 2, by - h - dy / 2
                anchor = "end" if tx > 800 else "start" if tx < 200 else "middle"
                label = f"{n} on {d.strftime('%b')} {d.day}"
                beacon = (f'<circle cx="{tx:.1f}" cy="{ty:.1f}" r="18" fill="url(#glow)"/>'
                          f'<line x1="{tx:.1f}" y1="{ty - 6:.1f}" x2="{tx:.1f}" y2="{ty - 26:.1f}" stroke="{PEAK}" stroke-opacity=".6"/>'
                          f'<circle class="beacon" cx="{tx:.1f}" cy="{ty:.1f}" r="3.2" fill="{PEAK}"/>'
                          f'<text class="mono" x="{tx:.1f}" y="{ty - 33:.1f}" text-anchor="{anchor}" fill="{PEAK}" font-size="13" font-weight="700">{label}</text>')

    months, last_x = [], -99.0
    for c in range(ncols):
        d = next((k for k, v in cell.items() if v == (c, 0)), None)
        bx, _ = origin(c, ROWS - 1)
        if d and (c == 0 or d.month != next(k for k, v in cell.items() if v == (c - 1, 0)).month) and bx - last_x > 44:
            months.append(f'<text class="mono" x="{bx:.1f}" y="{y_front + 24}" fill="{MUTED}" font-size="12">{d.strftime("%b")}</text>')
            last_x = bx

    kpis = []
    if total is not None:
        kpis.append(f'<tspan fill="{BRIGHT}" font-weight="700">{total}</tspan> contributions in the last year')
    kpis.append(f'<tspan fill="{BRIGHT}" font-weight="700">{len(active)}</tspan> active days')
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t">',
         f'<title id="t">Contribution skyline: {total if total is not None else len(active)} contributions over {ncols} weeks</title>',
         f"""<style>
.mono{{font-family:{MONO}}}
.ground{{animation:fade .8s ease-out backwards}}
.tw{{animation:rise .75s cubic-bezier(.22,.8,.24,1) backwards}}
.beacon{{animation:ping 2.6s ease-in-out 2.8s infinite}}
@keyframes rise{{from{{transform:scaleY(0)}}}}
@keyframes fade{{from{{opacity:0}}}}
@keyframes ping{{50%{{opacity:.25}}}}
@media (prefers-reduced-motion:reduce){{.ground,.tw,.beacon{{animation:none}}}}
</style>""",
         f'<defs><radialGradient id="glow"><stop offset="0" stop-color="{PEAK}" stop-opacity=".55"/><stop offset="1" stop-color="{PEAK}" stop-opacity="0"/></radialGradient></defs>',
         f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="18" fill="{BG}" stroke="{LINE}" stroke-width="2"/>',
         f'<text x="48" y="62" fill="{BRIGHT}" font-family="{SANS}" font-size="24" font-weight="700" letter-spacing="-.4">Contribution skyline</text>']
    for i, line in enumerate(kpis):
        o.append(f'<text class="mono" x="952" y="{48 + i * 22}" text-anchor="end" fill="{SOFT}" font-size="14">{line}</text>')
    o.append(f'<path class="ground" d="{"".join(flat)}" fill="{GROUND}"/>')
    o += towers + [beacon] + months
    o.append(f'<text class="mono" x="48" y="{H - 18}" fill="#6a7299" font-size="12">tower height = contributions per day. rendered by scripts/update_profile.py on {stamp} UTC</text>')
    o.append("</svg>")
    return "\n".join(o)


def main() -> int:
    data = load()
    if not data["languages"]:
        print("no language data returned; leaving the existing card untouched", file=sys.stderr)
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(data), encoding="utf-8")
    print(f"wrote {OUT} ({len(data['languages'])} languages, {data['repos']} repos)")
    if data.get("calendar"):
        SKY_OUT.write_text(render_skyline(data["calendar"], data.get("contributions")), encoding="utf-8")
        print(f"wrote {SKY_OUT} ({len(data['calendar'])} days)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
