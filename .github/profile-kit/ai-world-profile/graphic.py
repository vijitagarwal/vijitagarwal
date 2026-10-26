"""The contribution ledger: twelve monthly blocks chained with SHA-256, redrawn from your GitHub contribution calendar.

draw(snap) -> the complete SVG text for assets/ledger.svg. Pure function of the data; standard library only.
"""
import hashlib
import json
import os

import kitlib
from kitlib import a_attr, a_motion, esc, fmt

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT = "assets/ledger.svg"
G = kitlib.Glyphs(os.path.join(HERE, "glyphs.json"))
with open(os.path.join(HERE, "frame.json"), encoding="utf-8") as _fh:
    FRAME = json.load(_fh)

DARK = "#050816"
PANEL, PANEL2, LINE, LINE2 = "#0C1226", "#141C3A", "#2A3766", "#3A4A86"
TXT, TXT2, MUTE = "#F2F6FF", "#C5CEEA", "#A8B3D8"
AMBER, LIME = "#FFC65A", "#C9F36B"
LT = 14.0
FOOT = "hash = sha256(prev + month + count) · every hash above is computed from these exact figures"


def chain_hashes(rows):
    """sha256 chain over (month, two-digit year, count) starting from sha256('genesis'): [(previous hash, this hash)]."""
    prev, out = hashlib.sha256(b"genesis").hexdigest(), []
    for r in rows:
        h = hashlib.sha256(f"{prev}|{r['abbr']} {str(r['y'])[-2:]}|{r['n']}".encode()).hexdigest()
        out.append((prev, h))
        prev = h
    return out


def draw(snap, live=False):
    G.live = live
    rows, total, pk_i, pd = snap["months"], snap["total"], snap["peak_i"], snap["peak_day"]
    top = rows[pk_i]["n"] if pk_i is not None else 0
    w = 1000
    bw, gap, M = 146, 19.2, 14
    sh, bh = 92, 172
    r1, r2 = 14 + sh + 18, 14 + sh + 18 + bh + 30
    h = r2 + bh + 62
    b = f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="12" fill="{PANEL}" stroke="{LINE}" stroke-width="1"/>'
    sw_ = (w - 2 * M - 24) / 3
    if pk_i is not None:
        pm = rows[pk_i]
        cards = ((fmt(total), "CONTRIBUTIONS", "last 12 months"), (fmt(pm["n"]), "PEAK MONTH", f"{pm['full']} {pm['y']}"),
                 (fmt(pd["n"]), "PEAK DAY", pd["long"]) if pd else ("0", "PEAK DAY", "none yet"))
    else:
        cards = (("0", "CONTRIBUTIONS", "last 12 months"), ("0", "PEAK MONTH", "none yet"), ("0", "PEAK DAY", "none yet"))
    for i, (num, l1, l2) in enumerate(cards):
        x = M + i * (sw_ + 12)
        col = LIME if i == 0 else AMBER
        lw = max(G.adv(l1, "b7", 17, 1), G.adv(l2, "b5", 15))
        size = G.fit(num, "st", 60, sw_ - 18 - 16 - lw - 12, 1, floor=.5)
        nx = round(x + 18 + G.adv(num, "st", size, 1) + 16, 1)
        b += (f'<rect x="{x:.1f}" y="14" width="{sw_:.1f}" height="{sh}" rx="10" fill="{PANEL2}" stroke="{LINE2}"/><rect x="{x + 12:.1f}" y="14.5" width="56" height="3" rx="1.5" fill="{col}"/>'
              + G.text(round(x + 18, 1), 82, num, "st", size, col, ls=1) + G.text(nx, 56, l1, "b7", 17, TXT, ls=1)
              + G.text(nx, 80, l2, "b5", 15, TXT2))
    hashes = chain_hashes(rows)
    pos = []
    for i in range(12):
        row, c = (0, i) if i < 6 else (1, 11 - i)
        pos.append((M + c * (bw + gap), r1 if row == 0 else r2))
    ys = [p[1] + bh / 2 for p in pos]
    xs = [p[0] + bw / 2 for p in pos]
    path = f"M{xs[0]:.1f},{ys[0]:.1f} H{xs[5]:.1f} V{ys[6]:.1f} H{xs[11]:.1f}"
    seglen = [abs(xs[0] - xs[5]), abs(ys[6] - ys[0]), abs(xs[5] - xs[11])]
    plen = sum(seglen)
    b += (f'<path d="{path}" stroke="{LINE2}" stroke-width="6" fill="none" stroke-linecap="round"/><path class="fl" d="{path}" stroke="#E9FFB8" stroke-opacity=".8" stroke-width="2" stroke-dasharray="3 11" fill="none"/>')
    b += f'<g class="mt"><g>{a_motion(LT, path, [(0, 0), (.3, 0), (9.3, 1), (LT, 1)])}<circle r="11" fill="#E9FFB8" fill-opacity=".28"/><circle r="5" fill="#F4FFD4" stroke="{DARK}" stroke-width="1.4"/></g></g>'

    def prog(i):
        if i <= 5:
            return abs(xs[i] - xs[0]) / plen
        return (seglen[0] + seglen[1] + abs(xs[5] - xs[i])) / plen

    for i, (r, (prev, hh)) in enumerate(zip(rows, hashes)):
        v = r["n"]
        x, y = pos[i]
        peak, zero = i == pk_i, v == 0
        col = AMBER if peak else (MUTE if zero else LIME)
        sc = (v / top) ** .5 if top else 0
        lab = fmt(v)
        b += (f'<rect x="{x:.1f}" y="{y}" width="{bw}" height="{bh}" rx="10" fill="{PANEL2}" stroke="{col if peak else LINE2}" stroke-width="{1.8 if peak else 1}"/><rect x="{x + 10:.1f}" y="{y + .5}" width="44" height="3" rx="1.5" fill="{col}"/>'
              + G.text(round(x + 12, 1), y + 28, f"#{i + 1:02d}", "mo", 14, MUTE) + G.text(round(x + bw - 12, 1), y + 28, f"{r['abbr'].upper()} ’{str(r['y'])[-2:]}", "b7", 14.5, TXT, "end", .6)
              + G.text(round(x + 12, 1), y + 82, lab, "st", G.fit(lab, "st", 44, bw - 24, .6), col if not zero else MUTE, ls=.6)
              + G.text(round(x + 12, 1), y + 103, "pending" if zero else "contributions", "mo", 15, TXT2)
              + f'<rect x="{x + 12:.1f}" y="{y + 114}" width="{bw - 24}" height="7" rx="3.5" fill="{DARK}" stroke="{LINE}"/><rect x="{x + 12:.1f}" y="{y + 114}" width="{max((bw - 24) * sc, 0):.1f}" height="7" rx="3.5" fill="{col}"/>'
              + G.text(round(x + 12, 1), y + 145, f"hash {hh[:8]}", "mo", 15, TXT) + G.text(round(x + 12, 1), y + 164, f"prev {prev[:8]}", "mo", 15, MUTE))
        t0 = prog(i) * 9.0 + .3
        b += f'<g class="mt"><rect x="{x:.1f}" y="{y}" width="{bw}" height="{bh}" rx="10" fill="none" stroke="{LIME}" stroke-width="3" opacity="0">{a_attr("opacity", LT, [(0, 0), (t0 - .02, 0), (t0, 1), (t0 + 1.0, 0)])}</rect></g>'
    b += G.text(M + 6, h - 24, FOOT, "mo", 14.5, MUTE)
    label = kitlib.alt_text(snap, "Contribution ledger").replace("12 months.", "12 months, shown as a chain of twelve blocks hashed with SHA-256.", 1)
    css = (FRAME["font_css"] if live else "") + FRAME["css"]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{esc(label)}">'
            f'<style>{css}</style>{b}</svg>')
