#!/usr/bin/env python3
"""Render assets/stats.svg (primary language across public repos) from live GitHub data.
Standard library only. Counting repos by primary language needs one request and is not
inflated by vendored UI kits or generated code, unlike byte counts.

Environment
  GH_USER          profile to read (default: vijitagarwal)
  GH_TOKEN         optional; adds the contribution count (GraphQL) and raises rate limits
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
  contributionsCollection{contributionCalendar{totalContributions}}}}"""


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


def fetch_contributions() -> int:
    """Optional extra: needs a token. Failure only drops this one line from the card."""
    res = call("https://api.github.com/graphql", {"query": GQL, "variables": {"login": USER}})
    if res.get("errors"):
        raise RuntimeError(res["errors"])
    return res["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]


def load() -> dict:
    fixture = os.environ.get("PROFILE_FIXTURE")
    if fixture:
        return json.loads(pathlib.Path(fixture).read_text())
    data = fetch_repos()
    if TOKEN:
        try:
            data["contributions"] = fetch_contributions()
        except Exception as exc:
            print(f"contribution count unavailable ({exc}); rendering without it", file=sys.stderr)
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

    kpis = []
    if data.get("contributions") is not None:
        kpis.append(f'<tspan fill="{BRIGHT}" font-weight="700">{data["contributions"]}</tspan> contributions in the last year')
    kpis.append(f'<tspan fill="{BRIGHT}" font-weight="700">{data["repos"]}</tspan> public repositories')
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


def main() -> int:
    data = load()
    if not data["languages"]:
        print("no language data returned; leaving the existing card untouched", file=sys.stderr)
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(data), encoding="utf-8")
    print(f"wrote {OUT} ({len(data['languages'])} languages, {data['repos']} repos)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
