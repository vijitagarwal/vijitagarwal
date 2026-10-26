"""The castle wall: one stone tower per month for the last 12 months, redrawn from your GitHub contribution calendar.

draw(snap) -> the complete SVG text for assets/castle-wall.svg. Pure function of the data; standard library only.
"""
import json
import math
import os

import kitlib
from kitlib import esc, fmt

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT = "assets/castle-wall.svg"
G = kitlib.Glyphs(os.path.join(HERE, "glyphs.json"))
with open(os.path.join(HERE, "frame.json"), encoding="utf-8") as _fh:
    FRAME = json.load(_fh)

INK, MU, CR, ED, GOLD, GOLD2, CREAM = "#2A1C12", "#4A3620", "#7F1818", "#B89A5E", "#C8963E", "#E3B65C", "#F4E6C0"
W, GROUND, TW_, GAP, X0, MAXH, SD = 1000, 322, 60, 16, 52, 192, 6
PH = GROUND + 86
LINE2 = "most contributions in a single day"


def _callout(snap, pk_i, tops):
    """Where to put the 'Peak day' note. Returns SVG for it. Prefers the original spot (left of the peak tower), then the right,
    and falls back to the header when a neighbouring tower would be in the way or the text would leave the panel."""
    pd = snap["peak_day"]
    if not pd:
        return ""
    l1 = f"Peak day: {fmt(pd['n'])} on {pd['short']}"
    w1, w2 = G.adv(l1, "c7", 21), G.adv(LINE2, "i5", 16.5)
    px = X0 + pk_i * (TW_ + GAP)
    top = GROUND - MAXH

    def free(x0, x1, bottom):
        """No other tower (or its number) reaches into the box x0..x1 above y=bottom."""
        for j, t in enumerate(tops):
            if j == pk_i:
                continue
            xj = X0 + j * (TW_ + GAP)
            if xj + TW_ + 2 < x0 or xj - 2 > x1:
                continue
            if t - 32 < bottom + 4:
                return False
        return True

    for two in (True, False):
        w = max(w1, w2) if two else w1
        bottom = top + 17 if two else top - 4
        cx = px - 26                                         # left of the tower, text ends here, arrow points right
        if cx - w >= 24 and free(cx - w, cx + 19, bottom):
            b = G.text(cx, top - 10, l1, "c7", 21, CR, "end")
            if two:
                b += G.text(cx, top + 13, LINE2, "i5", 16.5, MU, "end")
            return b + f'<path d="M{cx + 8},{top - 16}l10,0" stroke="{CR}" stroke-width="2" stroke-linecap="round"/><path d="M{cx + 19},{top - 16}l-5,-4v8z" fill="{CR}"/>'
        rx = px + TW_ + 26                                   # right of the tower, text starts here, arrow points left
        if rx + w <= W - 24 and free(rx - 19, rx + w, bottom):
            b = G.text(rx, top - 10, l1, "c7", 21, CR, "start")
            if two:
                b += G.text(rx, top + 13, LINE2, "i5", 16.5, MU, "start")
            return b + f'<path d="M{rx - 8},{top - 16}l-10,0" stroke="{CR}" stroke-width="2" stroke-linecap="round"/><path d="M{rx - 19},{top - 16}l5,-4v8z" fill="{CR}"/>'
    # header fallback: always clear of the towers (the peak tower's flag sits above it, so stay on the far side)
    if pk_i >= 6:
        return G.text(40, 86, l1, "c7", 21, CR, "start")
    return G.text(W - 40, 86, l1, "c7", 21, CR, "end")


def draw(snap, live=False):
    G.live = live
    rows, total, pk_i = snap["months"], snap["total"], snap["peak_i"]
    peak = rows[pk_i]["n"] if pk_i is not None else 0
    b = FRAME["head"]
    title = f"{fmt(total)} contributions"
    b += G.text(40, 58, title, "pi", 32, CR) + G.text(round(40 + G.adv(title, "pi", 32) + 14, 1), 58, "in the last twelve months", "i5", 20, MU)
    b += G.text(W - 40, 56, "tower height: square-root scale", "i5", 16, MU, "end")
    towers, tops = "", []
    for i, r in enumerate(rows):
        v = r["n"]
        x = X0 + i * (TW_ + GAP)
        h = max(round(MAXH * math.sqrt(v / peak)), 4) if v else 0
        top = GROUND - h
        tops.append(top if v else GROUND - 30)
        isp = i == pk_i
        body = "url(#crG)" if isp else "url(#stG)"
        g = ""
        if v:
            g += f'<rect x="{x}" y="{top}" width="{TW_}" height="{h}" fill="{body}"/><rect x="{x}" y="{top}" width="{TW_}" height="{h}" fill="url(#brk)"/>'
            g += f'<rect x="{x}" y="{top}" width="{TW_}" height="3" fill="#FFF" opacity=".16"/>'
            mc = "#8A1F1F" if isp else "#868BA1"
            g += "".join(f'<rect x="{x + k * 23}" y="{top - 9}" width="14" height="10" fill="{mc}"/>' for k in range(3))
            if h > 60:
                g += f'<rect x="{x + TW_ / 2 - 3}" y="{top + 20}" width="6" height="22" rx="3" fill="#1A120C" opacity=".8"/>'
            lab = fmt(v)
            if isp:
                g += f'<rect x="{x}" y="{top}" width="{TW_}" height="{h}" fill="none"/>'
                g += G.text(x + TW_ / 2, top + 84, lab, "pi", G.fit(lab, "pi", 38, TW_ - 8), CREAM, "middle")
            else:
                g += G.text(x + TW_ / 2, top - 17, lab, "c7", G.fit(lab, "c7", 19, TW_ + GAP - 8), INK, "middle")
        else:
            g += f'<rect x="{x}" y="{GROUND - 5}" width="{TW_}" height="5" fill="{body}"/>' + G.text(x + TW_ / 2, GROUND - 14, "0", "c7", 19, INK, "middle")
        if isp:
            p = x + TW_ / 2
            g += f'<path d="M{p},{top - 9}V{top - 56}" stroke="{ED}" stroke-width="3"/><circle cx="{p}" cy="{top - 57}" r="3.500" fill="{GOLD2}"/>'
            g += f'<g class="fg"><path d="M{p + 2},{top - 54}h46l-11.500 11.500 11.500 11.500h-46z" fill="{GOLD}"/><circle cx="{p + 17}" cy="{top - 42.500}" r="4" fill="{CR}"/></g>'
        towers += f'<g class="up" style="animation-delay:{i * .12:.2f}s">{g}</g>'
    b += f'<g clip-path="url(#gC)">{towers}</g>'
    b += f'<rect x="24" y="{GROUND}" width="{W - 48}" height="7" rx="3.500" fill="#5B4630"/><rect x="24" y="{GROUND}" width="{W - 48}" height="2" rx="1" fill="#FFF" opacity=".14"/>'
    for i, r in enumerate(rows):
        b += G.text(X0 + i * (TW_ + GAP) + TW_ / 2, GROUND + 30, r["abbr"], "c7", 17, INK, "middle")
    yb = GROUND + 48                                          # one bracket per calendar year in the window
    a = 0
    while a < len(rows):
        z = a
        while z + 1 < len(rows) and rows[z + 1]["y"] == rows[a]["y"]:
            z += 1
        xa, xz = X0 + a * (TW_ + GAP) + 4, X0 + z * (TW_ + GAP) + TW_ - 4
        b += f'<path d="M{xa},{yb - 5}V{yb}H{xz}V{yb - 5}" fill="none" stroke="{ED}" stroke-width="1.500"/>' + G.text((xa + xz) / 2, yb + 21, str(rows[a]["y"]), "i5", 17, MU, "middle")
        a = z + 1
    if pk_i is not None:
        b += _callout(snap, pk_i, tops)
    if total:
        pr = rows[pk_i]
        label = (f"The castle wall: {fmt(total)} contributions in the last twelve months, drawn as one stone tower per month with the busiest month, "
                 f"{pr['full']} {pr['y']} with {fmt(peak)}, flying a banner. " + ", ".join(f"{r['abbr']} {fmt(r['n'])}" for r in rows) + ".")
        if snap["peak_day"]:
            label += f" Peak day: {fmt(snap['peak_day']['n'])} contributions on {snap['peak_day']['long']}."
    else:
        label = "The castle wall: no contributions in the last twelve months yet, so every tower is still a bare stone slab."
    css = (FRAME["font_css"] if live else "") + FRAME["css"]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {PH + SD}" width="{W}" height="{PH + SD}" role="img" aria-label="{esc(label)}">'
            f'<style>{css}</style>{b}</svg>')
