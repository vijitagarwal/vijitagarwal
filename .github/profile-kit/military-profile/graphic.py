"""The contribution radar: one bar per month for the last 12 months, redrawn from your GitHub contribution calendar.

draw(snap) -> the complete SVG text for assets/radar.svg. Pure function of the data; standard library only.
"""
import json
import math
import os

import kitlib
from kitlib import esc, fmt, short

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT = "assets/radar.svg"
G = kitlib.Glyphs(os.path.join(HERE, "glyphs.json"))
with open(os.path.join(HERE, "frame.json"), encoding="utf-8") as _fh:
    FRAME = json.load(_fh)

INK, INK2, MUTE, HULL, PLATE, LINE = "#EEF2F3", "#C9D4DA", "#9FB1BB", "#18222A", "#202C35", "#35464F"
GRN, YEL, AMB2 = "#5CC97A", "#F2C230", "#F3B574"
CX, CY, R, R0 = 296, 226, 150, 18
W, H = 1000, 452
HALO = ' paint-order="stroke" stroke="#0A131A" stroke-width="3.5" stroke-linejoin="round"'
CAPTION = "Bar length is scaled by square root, so quiet months stay visible next to the peak."


def pt(r, deg):
    a = math.radians(deg)
    return CX + r * math.sin(a), CY - r * math.cos(a)


def wedge(r1, a0, a1, r0=R0):
    x0, y0 = pt(r0, a0); x1, y1 = pt(r1, a0); x2, y2 = pt(r1, a1); x3, y3 = pt(r0, a1)
    return f"M{x0:.1f},{y0:.1f} L{x1:.1f},{y1:.1f} A{r1:.1f},{r1:.1f} 0 0 1 {x2:.1f},{y2:.1f} L{x3:.1f},{y3:.1f} A{r0},{r0} 0 0 0 {x0:.1f},{y0:.1f} Z"


def chart(rows, pk_i, vmax):
    rad = lambda v: R0 + (R - R0) * math.sqrt(v / vmax)
    ring_vals = kitlib.rings(vmax)
    b = f'<rect x="14" y="14" width="580" height="424" rx="8" fill="#0A131A" stroke="{LINE}"/>'
    for v in ring_vals:
        b += f'<circle cx="{CX}" cy="{CY}" r="{rad(v):.1f}" fill="none" stroke="#2A4252" stroke-width="1"/>'
    b += f'<circle cx="{CX}" cy="{CY}" r="{R}" fill="none" stroke="#35566B" stroke-width="1.4"/>'
    b += "".join(f'<path d="M{pt(R0, 30 * k)[0]:.1f},{pt(R0, 30 * k)[1]:.1f} L{pt(R + 8, 30 * k)[0]:.1f},{pt(R + 8, 30 * k)[1]:.1f}" stroke="#1D303C"/>' for k in range(12))
    labels = ""
    for i, r in enumerate(rows):
        v = r["n"]
        a = 15 + 30 * i
        peak = i == pk_i
        r1 = rad(v)
        if v:
            b += f'<path d="{wedge(r1, a - 10, a + 10)}" fill="{YEL if peak else GRN}" fill-opacity="{1 if peak else .85}" stroke="#0A131A" stroke-width="1.2"/>'
        else:
            x, y = pt(R0 + 5, a)
            b += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.4" fill="{MUTE}"/>'
        vx, vy = pt(max(r1, R0 + 8) + 16, a)
        lab = short(v)
        labels += G.text(round(vx, 1), round(vy + 5, 1), lab, "mo", 14.5 if len(lab) < 5 else 12.5, INK, "middle", extra=HALO)
        mx, my = pt(R + 52, a)
        labels += G.text(round(mx, 1), round(my + 5.5, 1), r["abbr"].upper(), "b7", 15, YEL if peak else INK2, "middle", 1)
    shown = ring_vals[-2:]
    for k, v in enumerate(shown):
        rr = rad(v)
        if k == 0 and len(shown) == 2 and rad(shown[1]) - rr < 24:
            continue                                           # no room between the two rings: label only the outer one
        near_bar = any(rows[i]["n"] and rad(rows[i]["n"]) > rr - 14 for i in (0, 11))      # Nov / Oct bars flank the 12 o'clock label
        lab = short(v)
        if near_bar:
            labels += G.text(CX, round(CY - rr + 5, 1), lab, "mo", 14, MUTE, "middle", extra=HALO)
        else:
            labels += (f'<rect x="{CX - 19}" y="{CY - rr - 10:.1f}" width="38" height="21" rx="3" fill="#0A131A"/>'
                       + G.text(CX, round(CY - rr + 5, 1), lab, "mo", 14, MUTE, "middle"))
    sw = "".join(f'<path d="{wedge(R, -a0, 0, 0)}" fill="{GRN}" fill-opacity="{o}"/>' for a0, o in ((50, .05), (32, .06), (16, .08)))
    b += (f'<g class="mt"><g><animateTransform attributeName="transform" type="rotate" from="0 {CX} {CY}" to="360 {CX} {CY}" dur="10s" repeatCount="indefinite"/>{sw}'
          f'<path d="M{CX},{CY} V{CY - R}" stroke="{GRN}" stroke-opacity=".45" stroke-width="1.4"/></g></g>')
    b += labels
    b += f'<circle cx="{CX}" cy="{CY}" r="{R0 - 3}" fill="#0A131A" stroke="#35566B"/><circle cx="{CX}" cy="{CY}" r="3" fill="{GRN}"/>'
    return b


def draw(snap, live=False):
    G.live = live
    rows, total, pk_i, pd = snap["months"], snap["total"], snap["peak_i"], snap["peak_day"]
    vmax = max(rows[pk_i]["n"], 1) if pk_i is not None else 1
    b = f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="8" fill="{HULL}" stroke="{LINE}"/>' + chart(rows, pk_i, vmax)
    x = 626
    b += G.text(x, 40, "LAST 12 MONTHS", "mo", 15, AMB2, ls=1.2)
    tot = fmt(total)
    lw = max(G.adv("CONTRIBUTIONS", "b7", 18, 1.2), G.adv("ON GITHUB", "b6", 16, 1.2))
    size = G.fit(tot, "st", 112, 972 - lw - 20 - (x - 3), 1, floor=.5)
    nw = G.adv(tot, "st", size, 1)
    lx = max(x + 176, round(x - 3 + nw + 20))
    b += G.text(x - 3, 146, tot, "st", size, YEL, ls=1) + G.text(lx, 112, "CONTRIBUTIONS", "b7", 18, INK, ls=1.2) + G.text(lx, 137, "ON GITHUB", "b6", 16, INK2, ls=1.2)
    if pk_i is not None:
        pm = rows[pk_i]
        cards = ((fmt(pm["n"]), "PEAK MONTH", f"{pm['full']} {pm['y']}"),
                 (fmt(pd["n"]), "PEAK DAY", pd["long"]) if pd else ("0", "PEAK DAY", "none yet"))
    else:
        cards = (("0", "PEAK MONTH", "none yet"), ("0", "PEAK DAY", "none yet"))
    for i, (num, l1, l2) in enumerate(cards):
        tx = x + i * 186
        b += (f'<rect x="{tx}" y="178" width="172" height="108" rx="8" fill="{PLATE}" stroke="{LINE}"/><rect x="{tx}" y="178" width="172" height="5" rx="2.5" fill="{GRN}"/>'
              + G.text(tx + 16, 238, num, "st", G.fit(num, "st", 56, 140, 1), INK, ls=1) + G.text(tx + 16, 262, l1, "b7", 15, INK, ls=1.1) + G.text(tx + 16, 279, l2, "b5", 15, INK2))
    for i, ln in enumerate(G.wrap(CAPTION, "b5", 16, 346)):
        b += G.text(x, 326 + i * 23, ln, "b5", 16, INK2)
    for i, (lab, col) in enumerate((("MONTH TOTAL", GRN), ("PEAK MONTH", YEL))):
        lx2 = x + i * 160
        b += f'<rect x="{lx2}" y="386" width="15" height="15" rx="3" fill="{col}"/>' + G.text(lx2 + 25, 399, lab, "b7", 14.5, INK, ls=1)
    label = kitlib.alt_text(snap, "Contribution radar")
    css = (FRAME["font_css"] if live else "") + FRAME["css"]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{esc(label)}">'
            f'<style>{css}</style>{b}</svg>')
