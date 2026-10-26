#!/usr/bin/env python3
"""Redraw the contribution graphic from your GitHub contribution calendar.

    python3 .github/profile-kit/refresh.py --login YOUR-GITHUB-USERNAME

Needs only Python 3.8+ (no packages). The workflow in .github/workflows/ runs this every day and commits the file if it changed.

Environment
    GH_TOKEN or GITHUB_TOKEN   token for GitHub's GraphQL API (the workflow supplies one; it only reads public data)
    GITHUB_GRAPHQL_URL         defaults to https://api.github.com/graphql
Options
    --login NAME        whose calendar to read (default: $GITHUB_REPOSITORY_OWNER)
    --today YYYY-MM-DD  pretend today is this day (default: today, UTC)
    --from-json FILE    do not call GitHub; read a saved API response, a {"date": count} map or [["date", count], ...]
    --out FILE          where to write the SVG (default: the path the graphic names, counted from the repository root; a kit that keeps its
                        images in a theme folder puts that path in a one-line file called output.txt next to this script)
    --print-snapshot    print the numbers that will be drawn and exit without writing

If anything goes wrong the existing graphic is left untouched, a plain-English reason goes to stderr and the exit code is 1.
"""
import argparse
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import graphic  # noqa: E402
import kitlib  # noqa: E402

QUERY = """query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }
    }
  }
}"""


def fail(msg):
    print(f"refresh: {msg}", file=sys.stderr)
    sys.exit(1)


def days_from_response(payload):
    """(date, count) pairs from a GraphQL response body."""
    if payload.get("errors"):
        first = payload["errors"][0]
        text = first.get("message", "unknown error")
        if first.get("type") == "NOT_FOUND" or "Could not resolve to a User" in text:
            fail(f"GitHub does not know that user name ({text}). Check --login / the repository owner.")
        if first.get("type") in ("FORBIDDEN", "INSUFFICIENT_SCOPES") or "not accessible" in text:
            fail(f"GitHub's API would not show this calendar to the built-in token ({text}). Add a repository secret called PROFILE_TOKEN holding a "
                 "personal access token (a classic token with no scopes ticked is enough to read public data).")
        fail(f"GitHub's API answered with an error: {text}")
    user = (payload.get("data") or {}).get("user")
    if not user:
        fail("GitHub's API returned no user. Check the user name.")
    weeks = user["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [(d["date"], d["contributionCount"]) for w in weeks for d in w["contributionDays"]]


def fetch_days(login, token, start, today, url):
    body = json.dumps({"query": QUERY, "variables": {"login": login, "from": f"{start.isoformat()}T00:00:00Z", "to": f"{today.isoformat()}T23:59:59Z"}}).encode()
    headers = {"Authorization": f"bearer {token}", "Content-Type": "application/json", "Accept": "application/json", "User-Agent": "profile-kit-refresh"}
    last = "no answer"
    for attempt in range(4):
        if attempt:
            time.sleep(2 ** attempt)                                      # 2s, 4s, 8s between tries
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=body, headers=headers), timeout=30) as resp:
                return days_from_response(json.load(resp))
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                fail(f"GitHub refused the token (HTTP {e.code}). In the workflow the built-in token is used; if this keeps happening, add a repository "
                     "secret called PROFILE_TOKEN holding a personal access token (a classic token with no scopes ticked is enough to read public data).")
            if e.code in (429, 500, 502, 503, 504):
                last = f"HTTP {e.code}"
                continue
            fail(f"GitHub's API answered HTTP {e.code}.")
        except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError) as e:
            last = type(e).__name__
            continue
    fail(f"could not reach GitHub's API after 4 tries ({last}). Nothing was changed; the next scheduled run will try again.")


def repo_root():
    """The folder that holds .github/ (this script lives somewhere below it); two levels up if it is not inside a .github folder."""
    d = HERE
    while True:
        parent = os.path.dirname(d)
        if os.path.basename(d) == ".github":
            return parent
        if parent == d:
            return os.path.abspath(os.path.join(HERE, "..", ".."))
        d = parent


def default_out():
    """Where the picture lives: the path the graphic names, or the path written in output.txt next to this script, counted from the repository root."""
    rel = graphic.OUTPUT
    cfg = os.path.join(HERE, "output.txt")
    if os.path.exists(cfg):
        with open(cfg, encoding="utf-8") as fh:
            rel = fh.read().strip() or rel
    root = repo_root()
    out = os.path.abspath(os.path.join(root, *rel.split("/")))
    if os.path.commonpath([root, out]) != root:
        fail(f"output.txt points outside the repository ({rel}); nothing was written.")
    return out


def days_from_file(path):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict) and ("data" in data or "errors" in data):
        return days_from_response(data)
    if isinstance(data, dict):
        return list(data.items())
    return [(d, n) for d, n in data]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Redraw the contribution graphic from your GitHub contribution calendar.")
    ap.add_argument("--login", default=os.environ.get("GITHUB_REPOSITORY_OWNER", ""))
    ap.add_argument("--today", default=None)
    ap.add_argument("--from-json", dest="from_json", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--print-snapshot", action="store_true")
    a = ap.parse_args(argv)

    today = datetime.date.fromisoformat(a.today) if a.today else datetime.datetime.now(datetime.timezone.utc).date()
    start = kitlib.window_start(today)
    out = None if a.print_snapshot else os.path.abspath(a.out or default_out())      # settle where the file goes before asking GitHub for anything
    if a.from_json:
        days = days_from_file(a.from_json)
    else:
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if not a.login:
            fail("no GitHub user name: pass --login NAME (inside a workflow it defaults to the repository owner).")
        if not token:
            fail("no token found. Set GH_TOKEN (in the workflow: GH_TOKEN: ${{ secrets.PROFILE_TOKEN || secrets.GITHUB_TOKEN }}).")
        days = fetch_days(a.login, token, start, today, os.environ.get("GITHUB_GRAPHQL_URL", "https://api.github.com/graphql"))

    snap = kitlib.snapshot(days, today)
    pk, pd = snap["peak_i"], snap["peak_day"]
    summary = (f"{start.isoformat()} to {today.isoformat()}: {snap['total']} contributions; "
               + (f"busiest month {snap['months'][pk]['full']} {snap['months'][pk]['y']} ({snap['months'][pk]['n']}); " if pk is not None else "no busiest month yet; ")
               + (f"busiest day {pd['long']} ({pd['n']})" if pd else "no busiest day yet"))
    if a.print_snapshot:
        print(summary)
        print(", ".join(f"{r['abbr']} {r['y']}={r['n']}" for r in snap["months"]))
        return 0

    svg = graphic.draw(snap)
    try:
        ET.fromstring(svg)                                              # never write a graphic the browser cannot parse
    except ET.ParseError as e:
        fail(f"internal error: the new graphic is not valid SVG ({e}); the existing file was left as it is.")

    data = svg.encode("utf-8")
    old = None
    if os.path.exists(out):
        with open(out, "rb") as fh:
            old = fh.read()
    if old == data:
        print(f"unchanged: {summary}")
        return 0
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = out + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(data)
    os.replace(tmp, out)
    print(f"updated {os.path.relpath(out)}: {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
