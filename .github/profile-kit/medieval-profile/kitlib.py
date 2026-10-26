"""kitlib: the small, dependency-free toolkit behind the self-updating graphic.

Python standard library only (3.8+). No fonts, no HarfBuzz, no pip install: text is drawn from a pre-built table of glyph outlines
(glyphs.json), so the redraw gives the same pixels on GitHub's runner as it did when the kit was built.
"""
import datetime
import json
import math
import re

MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTH_FULL = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


# ----------------------------------------------------------------------------------------------------------- text

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _num(v):
    s = f"{v:.1f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


_TOKEN = re.compile(r"[MLHVQCZ]|-?\d*\.?\d+")


class Glyphs:
    """Glyph outlines + advances + kerning for one theme. text() draws a run as ONE <path> (or, with live=True, as a live <text>
    element, which the kit's own tests use to measure contrast)."""

    def __init__(self, path):
        with open(path, encoding="utf-8") as fh:
            self.fonts = json.load(fh)["fonts"]
        self.live = False
        self._parsed = {}

    # -- shaping -----------------------------------------------------------------------------------------------
    def _runs(self, s, key):
        """[(font_key, text)]: characters the primary font lacks are drawn from the fallback font 'fb', as in the kit's build."""
        prim = self.fonts[key]["chars"]
        out = []
        for ch in s:
            k = key if ch in prim else "fb"
            if k not in self.fonts or ch not in self.fonts[k]["chars"]:
                raise ValueError(f"no glyph for {ch!r} in font {key!r}")
            if out and out[-1][0] == k:
                out[-1][1] += ch
            else:
                out.append([k, ch])
        return out

    def _glyphs(self, s, key):
        """-> [(font_key, char, advance in em)] with pair kerning applied inside each run."""
        res = []
        for k, sub in self._runs(s, key):
            f = self.fonts[k]
            chars, kern, upem = f["chars"], f["kern"], f["upem"]
            for i, ch in enumerate(sub):
                adv = chars[ch][0]
                if i + 1 < len(sub):
                    adv += kern.get(ch + sub[i + 1], 0)
                res.append((k, ch, adv / upem))
        return res

    def adv(self, s, key, size, ls=0.0):
        """Rendered width of s in px at the given size and letter-spacing."""
        gl = self._glyphs(s, key)
        return sum(g[2] for g in gl) * size + ls * len(gl)

    def fit(self, s, key, size, maxw, ls=0.0, floor=0.5):
        """Largest font size <= size at which s is at most maxw wide (never below floor * size)."""
        w = self.adv(s, key, size, ls)
        if w <= maxw:
            return size
        return max(round(size * maxw / w, 1), round(size * floor, 1))

    def wrap(self, s, key, size, maxw, ls=0.0):
        lines, cur = [], ""
        for w in s.split():
            t = (cur + " " + w).strip()
            if cur and self.adv(t, key, size, ls) > maxw:
                lines.append(cur)
                cur = w
            else:
                cur = t
        return lines + ([cur] if cur else [])

    # -- drawing -----------------------------------------------------------------------------------------------
    def _outline(self, k, ch):
        """Parsed outline: list of (command, [numbers]) in font units."""
        key = (k, ch)
        if key not in self._parsed:
            d = self.fonts[k]["chars"][ch][1]
            segs, cmd, nums = [], None, []
            for t in _TOKEN.findall(d):
                if t.isalpha():
                    if cmd:
                        segs.append((cmd, nums))
                    cmd, nums = t, []
                else:
                    nums.append(float(t))
            if cmd:
                segs.append((cmd, nums))
            self._parsed[key] = segs
        return self._parsed[key]

    def _draw(self, k, ch, sc, ox, oy):
        out = []
        for cmd, n in self._outline(k, ch):
            if cmd == "Z":
                out.append("Z")
            elif cmd == "H":
                out.append("H" + _num(sc * n[0] + ox))
            elif cmd == "V":
                out.append("V" + _num((-sc) * n[0] + oy))
            else:
                pts = [f"{_num(sc * n[i] + ox)} {_num((-sc) * n[i + 1] + oy)}" for i in range(0, len(n), 2)]
                out.append(cmd + " ".join(pts))
        return "".join(out)

    def text(self, x, y, s, key, size, fill, anchor="start", ls=0, extra=""):
        if self.live:
            a = f' text-anchor="{anchor}"' if anchor != "start" else ""
            l = f' letter-spacing="{ls}"' if ls else ""
            if s != s.strip():
                extra += ' xml:space="preserve"'
            return f'<text x="{x:g}" y="{y:g}" class="{key}" font-size="{size}" fill="{fill}"{a}{l}{extra}>{esc(s)}</text>'
        gl = self._glyphs(s, key)
        total = sum(g[2] for g in gl) * size + ls * len(gl)
        cx = x - (total / 2 if anchor == "middle" else total if anchor == "end" else 0)
        d = []
        for k, ch, adv in gl:
            sc = size / self.fonts[k]["upem"]
            d.append(self._draw(k, ch, sc, cx, y))
            cx += adv * size + ls
        return f'<path d="{"".join(d)}" fill="{fill}"{extra}/>'


# ------------------------------------------------------------------------------------------------------ animation

def smil(dur, pts):
    """(keyTimes, values) strings for a looping timeline; pts = [(seconds, value)]."""
    pts = sorted(pts, key=lambda p: p[0])
    if pts[0][0] > 0:
        pts = [(0, pts[0][1])] + pts
    if pts[-1][0] < dur:
        pts = pts + [(dur, pts[-1][1])]
    f = lambda t: (f"{t / dur:.4f}".rstrip("0").rstrip(".") or "0")
    return ";".join(f(t) for t, _ in pts), ";".join(str(v) for _, v in pts)


def a_attr(name, dur, pts):
    kt, vs = smil(dur, pts)
    return f'<animate attributeName="{name}" dur="{dur}s" repeatCount="indefinite" keyTimes="{kt}" values="{vs}"/>'


def a_motion(dur, path, pts):
    kt, kp = smil(dur, pts)
    return f'<animateMotion dur="{dur}s" repeatCount="indefinite" path="{path}" keyPoints="{kp}" keyTimes="{kt}" calcMode="linear"/>'


# ------------------------------------------------------------------------------------------------ contribution data

def fmt(n):
    return f"{n:,}"


def short(n):
    """Compact count for tight spots: 1,234 stays as it is, 12,345 -> 12.3k, 123,456 -> 123k, 1,234,567 -> 1.2M."""
    if n < 10000:
        return f"{n:,}"
    if n < 100000:
        return f"{n // 100 / 10:.1f}k"
    if n < 1000000:
        return f"{n // 1000}k"
    return f"{n // 100000 / 10:.1f}M"


def window_months(today):
    """The 12 calendar months ending with today's month, oldest first, as (year, month)."""
    y, m = today.year, today.month
    out = []
    for _ in range(12):
        out.append((y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return out[::-1]


def window_start(today):
    y, m = window_months(today)[0]
    return datetime.date(y, m, 1)


def snapshot(days, today):
    """Reduce daily contribution counts to what the graphics draw.

    days  -- iterable of (ISO date string, count)
    today -- datetime.date; the window is the 12 calendar months ending with this date's month
    """
    months = window_months(today)
    start = window_start(today)
    totals = {ym: 0 for ym in months}
    best = None                                            # (count, date) -- the latest day wins a tie
    for iso, n in days:
        d = datetime.date.fromisoformat(iso)
        if d < start or d > today:
            continue
        n = int(n)
        totals[(d.year, d.month)] += n
        if n > 0 and (best is None or (n, d) >= best):
            best = (n, d)
    rows = [dict(y=y, m=m, abbr=MONTH_ABBR[m - 1], full=MONTH_FULL[m - 1], n=totals[(y, m)]) for y, m in months]
    total = sum(r["n"] for r in rows)
    peak_i = None
    if total:
        top = max(r["n"] for r in rows)
        peak_i = max(i for i, r in enumerate(rows) if r["n"] == top)          # the latest month wins a tie
    pd = None
    if best:
        n, d = best
        pd = dict(n=n, date=d.isoformat(), short=f"{MONTH_ABBR[d.month - 1]} {d.day}", long=f"{MONTH_ABBR[d.month - 1]} {d.day}, {d.year}")
    return dict(months=rows, total=total, peak_i=peak_i, peak_day=pd, start=start.isoformat(), end=today.isoformat())


def alt_text(snap, what):
    """Plain-English description of the numbers for aria-label / alt text."""
    rows = snap["months"]
    vals = ", ".join(f"{r['abbr']} {r['y']} {r['n']}" for r in rows)
    s = f"{what}: {fmt(snap['total'])} contributions in the last 12 months. Monthly totals: {vals}."
    if snap["peak_day"]:
        s += f" Peak day: {snap['peak_day']['n']} contributions on {snap['peak_day']['long']}."
    return s


_NICE = (1, 2, 4, 10)


def nice(x):
    """The value of the grid 1, 2, 4, 10, 20, 40, 100, ... nearest to x on a log scale (x > 0)."""
    dec = 10 ** math.floor(math.log10(x))
    best, bd = None, None
    for mult in (dec / 10, dec, dec * 10):
        for g in _NICE:
            v = g * mult
            if v < 1:
                continue
            dist = abs(math.log(x / v))
            if bd is None or dist < bd:
                best, bd = v, dist
    return int(round(best)) if best is not None else 1


def rings(vmax, fracs=(0.27, 0.54, 0.86)):
    """Up to three round-number values (below vmax) for the radar's guide rings, spaced evenly on a square-root radius scale."""
    out = []
    for f in fracs:
        v = nice(max(vmax * f * f, 1))
        if 1 <= v < vmax and v not in out:
            out.append(v)
    return out
