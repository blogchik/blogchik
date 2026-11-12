#!/usr/bin/env python3
"""Render the profile SVGs.

    python3 scripts/render.py static            # banner, project cards, stack, footer -> assets/
    python3 scripts/render.py live --out dist   # stats card + repo cards -> dist/ (needs GITHUB_TOKEN)

Standard library only, so it runs on a bare GitHub Actions runner.
Fonts: Bricolage Grotesque and Geist Mono (SIL OFL 1.1), subset in assets/fonts;
metrics.json holds their advance widths so text can be measured for layout.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import math
import os
import sys
import urllib.request
from functools import lru_cache
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
FONTS = ASSETS / "fonts"
USER = "blogchik"
NAME = "Jabborov Abduroziq"

THEMES = {
    "dark": {
        "bg": "#09090b", "card": "#0c0c0e", "cover": "#131316", "border": "#27272a", "dot": "#2c2c31",
        "ink": "#fafafa", "ink2": "#a1a1aa", "muted": "#8b8b94",
        "accent": "#E28413", "accent2": "#F5A24B", "deep": "#9a5208", "mark": "#E28413",
        "track": "#1f1f23", "chip": "#18181b", "chip_bd": "#2e2e33", "handle": "#09090b",
        "live": "#22c55e", "idle": "#71717a", "agent": "#8b5cf6", "glow": 0.2,
        "slabs": ["#F5A24B", "#E28413", "#B8680E", "#8A4D0B", "#5E3508"],
    },
    "light": {
        "bg": "#fafafa", "card": "#ffffff", "cover": "#f4f4f5", "border": "#e4e4e7", "dot": "#d4d4d8",
        "ink": "#18181b", "ink2": "#52525b", "muted": "#71717a",
        "accent": "#E28413", "accent2": "#F5A24B", "deep": "#BF6A0A", "mark": "#BF6A0A",
        "track": "#f1f1f3", "chip": "#f4f4f5", "chip_bd": "#e4e4e7", "handle": "#ffffff",
        "live": "#16a34a", "idle": "#a1a1aa", "agent": "#7c3aed", "glow": 0.13,
        "slabs": ["#FAD3A0", "#F5B05A", "#E28413", "#BF6A0A", "#8F4F07"],
    },
}

# The editor panel in the banner is dark in both themes.
CODE = {"panel": "#141417", "border": "#2e2e33", "chrome": "#1b1b1f", "gutter": "#55555e", "tab": "#a1a1aa",
        "ink": "#e4e4e7", "kw": "#c4b5fd", "str": "#F5A24B", "punct": "#8b8b94", "ok": "#22c55e"}

# Karimov Academy's own black and gold, used in its project illustration.
KARIMOV = {"bg": "#0b0b0b", "line": "#3a3122", "pill": "#15120c", "gold": "#d5af6f", "gold_dark": "#8a6338",
           "gold_light": "#e4cb91"}

# TAVRYN's own design-system colours, used in its project illustration.
TAVRYN = {"surface": "#ece8e7", "raised": "#f8f4f3", "dark": "#22211d", "line": "#d9d4d2", "ink2": "#6b6862",
          "accent": "#dc6008"}

SANS = "Bricolage, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "GeistMono, ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
METRICS = json.loads((FONTS / "metrics.json").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- helpers

def tw(text: str, font: str = "sans500", size: float = 14, ls: float = 0) -> float:
    """Width of a single line of text in px."""
    m = METRICS[font]
    units = sum(m["adv"].get(ch, m["avg"]) for ch in text)
    return units * size / m["upm"] + ls * max(len(text) - 1, 0)


def wrap(text: str, max_w: float, font: str = "sans500", size: float = 14, max_lines: int = 2) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if not cur or tw(trial, font, size) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        last = " ".join(lines[max_lines - 1:])
        while tw(last + "…", font, size) > max_w and " " in last:
            last = last.rsplit(" ", 1)[0]
        lines = lines[:max_lines - 1] + [last.rstrip(",.:;—- ") + "…"]
    return lines


def rule(selector: str, body: str) -> str:
    return selector + "{" + body + "}"


def keyframes(name: str, frames: list[tuple[str, str]]) -> str:
    return "@keyframes " + name + "{" + "".join(rule(sel, body) for sel, body in frames) + "}"


@lru_cache(maxsize=1)
def font_faces() -> str:
    def face(file: str, family: str, weight: int) -> str:
        data = base64.b64encode((FONTS / file).read_bytes()).decode()
        return rule("@font-face", f"font-family:{family};font-weight:{weight};"
                                  f"src:url(data:font/woff2;base64,{data}) format('woff2')")

    return (face("bricolage-700.woff2", "Bricolage", 700) + face("bricolage-500.woff2", "Bricolage", 500)
            + face("geistmono-500.woff2", "GeistMono", 500))


def doc(w: int, h: int, title: str, desc: str, body: str, t: dict, css: str = "") -> str:
    base = (rule(".sans", f"font-family:{SANS}") + rule(".mono", f"font-family:{MONO};font-weight:500")
            + rule(".ink", f"fill:{t['ink']}") + rule(".ink2", f"fill:{t['ink2']}") + rule(".muted", f"fill:{t['muted']}")
            + rule(".fb", "transform-box:fill-box;transform-origin:center")
            + keyframes("pulse", [("0%,100%", "opacity:1"), ("50%", "opacity:.3")])
            + rule(".pulse", "animation:pulse 2.4s ease-in-out infinite")
            + keyframes("bob", [("0%,100%", "transform:translateY(0)"), ("50%", "transform:translateY(-5px)")])
            + rule(".bob", "animation:bob 3.4s ease-in-out infinite"))
    reduced = "@media (prefers-reduced-motion:reduce){" + rule("*", "animation:none!important") + "}"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img" aria-labelledby="title desc"><title id="title">{escape(title)}</title>'
            f'<desc id="desc">{escape(desc)}</desc><style>{font_faces()}{base}{css}{reduced}</style>\n{body}\n</svg>\n')


def text(x: float, y: float, s: str, cls: str = "sans ink", size: float = 14, weight: int | None = None,
         anchor: str | None = None, ls: float | None = None, fill: str | None = None, extra: str = "") -> str:
    attrs = f' font-size="{size}"'
    if weight:
        attrs += f' font-weight="{weight}"'
    if anchor:
        attrs += f' text-anchor="{anchor}"'
    if ls is not None:
        attrs += f' letter-spacing="{ls}"'
    if fill:
        attrs += f' fill="{fill}"'
    return f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}"{attrs}{extra}>{escape(s)}</text>'


def dots(pid: str, color: str, step: int = 22, r: float = 1.1) -> str:
    return (f'<pattern id="{pid}" width="{step}" height="{step}" patternUnits="userSpaceOnUse">'
            f'<circle cx="2" cy="2" r="{r}" fill="{color}"/></pattern>')


def chip(x: float, y: float, label: str, t: dict, size: float = 11, h: float = 22, pad: float = 9) -> tuple[str, float]:
    w = tw(label, "mono500", size) + pad * 2
    svg = (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h}" rx="{h / 2}" fill="{t["chip"]}" stroke="{t["chip_bd"]}"/>'
           + text(x + w / 2, y + h / 2 + size * 0.36, label, "mono ink2", size, anchor="middle"))
    return svg, w


def chip_row(x: float, y: float, labels: list[str], t: dict, gap: float = 8, **kw) -> str:
    out = []
    for label in labels:
        svg, w = chip(x, y, label, t, **kw)
        out.append(svg)
        x += w + gap
    return "".join(out)


def status_pill(x: float, y: float, kind: str, t: dict) -> str:
    label, color = {"live": ("LIVE", t["live"]), "design": ("IN DESIGN", t["accent"]),
                    "planning": ("PLANNING", t["idle"])}[kind]
    w = tw(label, "mono500", 10.5, 1.2) + 34
    pulse = ' class="pulse"' if kind == "live" else ""
    return (f'<rect x="{x}" y="{y}" width="{w:.1f}" height="24" rx="12" fill="{t["card"]}" stroke="{t["border"]}"/>'
            f'<circle cx="{x + 14}" cy="{y + 12}" r="4" fill="{color}"{pulse}/>'
            + text(x + 24, y + 16, label, "mono ink2", 10.5, ls=1.2))


def shade(hex_color: str, k: float) -> str:
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % (round(r * k), round(g * k), round(b * k))


def frame(w: int, h: int, t: dict, fill: str | None = None) -> str:
    return (f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="19.5" '
            f'fill="{fill or t["card"]}" stroke="{t["border"]}"/>')


# --------------------------------------------------------------------------- banner

CODE_LINES = [
    [("kw", "const "), ("ink", "abduroziq"), ("punct", " = {")],
    [("punct", "  "), ("ink", "role"), ("punct", ": "), ("str", '"product engineer"'), ("punct", ",")],
    [("punct", "  "), ("ink", "design"), ("punct", ": "), ("str", '"Figma"'), ("punct", ",")],
    [("punct", "  "), ("ink", "build"), ("punct", ": ["), ("str", '"Next.js"'), ("punct", ", "),
     ("str", '"FastAPI"'), ("punct", "],")],
    [("punct", "  "), ("ink", "ship"), ("punct", ": "), ("str", '"Kubernetes"'), ("punct", ",")],
    [("punct", "};")],
]

CURSOR = "M0,0 L0,17 L4.6,13 L7.6,20 L10.2,18.9 L7.3,12.2 L13,12.2 Z"


def cursor(cls: str, color: str, label: str, label_ink: str) -> str:
    lw = tw(label, "sans500", 11) + 16
    return (f'<g class="{cls}"><path d="{CURSOR}" fill="{color}" stroke="#ffffff" stroke-width="1.3" stroke-linejoin="round"/>'
            f'<rect x="11" y="19" width="{lw:.1f}" height="20" rx="6" fill="{color}"/>'
            + text(19, 33, label, "sans", 11, 500, fill=label_ink) + "</g>")


def banner_svg(t: dict) -> str:
    w, h = 960, 380
    cycle = 11

    # name inside a Figma-style selection
    nx, ny, nsize, nls = 50, 150, 54, -1.5
    name_w = tw(NAME, "sans700", nsize, nls)
    bx0, by0, bx1, by1 = nx - 12, ny - 47, nx + name_w + 12, ny + 17
    size_label = f"{round(bx1 - bx0)} × {round(by1 - by0)}"
    sw = tw(size_label, "mono500", 11) + 16
    scx = (bx0 + bx1) / 2
    handles = "".join(f'<rect x="{x - 4:.1f}" y="{y - 4:.1f}" width="8" height="8" fill="{t["handle"]}" '
                      f'stroke="{t["accent"]}" stroke-width="1.5"/>'
                      for x, y in [(bx0, by0), (bx1, by0), (bx0, by1), (bx1, by1)])
    selection = (f'<rect x="{bx0:.1f}" y="{by0:.1f}" width="{bx1 - bx0:.1f}" height="{by1 - by0:.1f}" fill="none" '
                 f'stroke="{t["accent"]}" stroke-width="1.5"/>{handles}'
                 f'<rect x="{scx - sw / 2:.1f}" y="{by1 + 10:.1f}" width="{sw:.1f}" height="20" rx="5" fill="{t["accent"]}"/>'
                 + text(scx, by1 + 24, size_label, "mono", 11, anchor="middle", fill="#18181b"))

    tagline = ["Designing and building products —", "from Figma to production."]
    left = (f'<circle cx="56" cy="63" r="4.5" fill="{t["accent"]}" class="pulse"/>'
            + text(70, 67.5, "PRODUCT ENGINEER · TASHKENT, UZ", "mono ink2", 12, ls=1.6)
            + selection
            + text(nx, ny, NAME, "sans ink", nsize, 700, ls=nls)
            + text(nx + 1, 240, tagline[0], "sans ink2", 21, 500)
            + text(nx + 1, 268, tagline[1], "sans ink2", 21, 500)
            + text(nx + 1, 330, "NEXT.JS · FASTAPI · NESTJS · KUBERNETES · SWIFT", "mono muted", 11.5, ls=1.4))

    # editor panel with a typing animation
    px, py, pw, ph = 604, 46, 316, 242
    css = []
    code = [f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="14" fill="{CODE["panel"]}" stroke="{CODE["border"]}"/>',
            f'<path d="M{px},{py + 30} V{py + 14} Q{px},{py} {px + 14},{py} H{px + pw - 14} Q{px + pw},{py} {px + pw},{py + 14} V{py + 30} Z" fill="{CODE["chrome"]}"/>',
            f'<line x1="{px}" y1="{py + 30.5}" x2="{px + pw}" y2="{py + 30.5}" stroke="{CODE["border"]}"/>']
    code += [f'<circle cx="{px + 16 + i * 14}" cy="{py + 15}" r="4.5" fill="#3f3f46"/>' for i in range(3)]
    code.append(text(px + 68, py + 19.5, "engineer.ts", "mono", 11, fill=CODE["tab"]))
    lines_g = []
    for i, tokens in enumerate(CODE_LINES):
        y = py + 58 + i * 21
        n = sum(len(s) for _, s in tokens)
        start, end = 4 + i * 7, 4 + i * 7 + 5.5
        css.append(keyframes(f"ty{i}", [(f"0%,{start}%", f"clip-path:inset(0 100% 0 0);animation-timing-function:steps({n},end)"),
                                        (f"{end}%,100%", "clip-path:inset(0 0 0 0)")]))
        css.append(rule(f".ty{i}", f"animation:ty{i} {cycle}s infinite"))
        spans = "".join(f'<tspan fill="{CODE[k]}">{escape(s)}</tspan>' for k, s in tokens)
        lines_g.append(text(px + 30, y, str(i + 1), "mono", 12, anchor="end", fill=CODE["gutter"])
                       + f'<text x="{px + 42}" y="{y}" class="mono ty{i}" font-size="12" xml:space="preserve">{spans}</text>')
    ty_term = py + 58 + 7 * 21 - 4
    term = "git push origin main"
    css.append(keyframes("tyt", [("0%,50%", f"clip-path:inset(0 100% 0 0);animation-timing-function:steps({len(term) + 2},end)"),
                                 ("57%,100%", "clip-path:inset(0 0 0 0)")]))
    css.append(rule(".tyt", f"animation:tyt {cycle}s infinite"))
    caret_x = px + 42 + tw("$ " + term, "mono500", 12) + 3
    lines_g.append(f'<text x="{px + 42}" y="{ty_term}" class="mono tyt" font-size="12" xml:space="preserve">'
                   f'<tspan fill="{CODE["ok"]}">$ </tspan><tspan fill="{CODE["ink"]}">{term}</tspan></text>'
                   f'<g class="caretwin"><rect class="caret" x="{caret_x:.1f}" y="{ty_term - 11}" width="7" height="14" fill="{CODE["ink"]}"/></g>')
    css += [keyframes("caretwin", [("0%,56%", "opacity:0"), ("57%,88%", "opacity:1"), ("89%,100%", "opacity:0")]),
            rule(".caretwin", f"animation:caretwin {cycle}s infinite"),
            keyframes("blink", [("0%,49%", "opacity:1"), ("50%,100%", "opacity:0")]),
            rule(".caret", "animation:blink 1s infinite"),
            keyframes("codefade", [("0%,88%", "opacity:1"), ("95%,100%", "opacity:0")]),
            rule(".codefade", f"animation:codefade {cycle}s infinite")]
    code.append(f'<g class="codefade">{"".join(lines_g)}</g>')

    # deploy toast
    tx, tyy = 562, 270
    toast = (f'<g class="toast"><rect x="{tx}" y="{tyy}" width="252" height="52" rx="12" fill="{t["card"]}" '
             f'stroke="{t["border"]}" filter="url(#shadow)"/>'
             f'<circle cx="{tx + 26}" cy="{tyy + 26}" r="11" fill="{t["live"]}"/>'
             f'<path d="M{tx + 21},{tyy + 26.5} l3.5,3.5 l6.5,-7" fill="none" stroke="#ffffff" stroke-width="2.2" '
             f'stroke-linecap="round" stroke-linejoin="round"/>'
             + text(tx + 46, tyy + 23, "Deployed to production", "sans ink", 14, 500)
             + text(tx + 46, tyy + 40, "main · 41s · all checks passed", "mono muted", 10.5) + "</g>")
    css += [keyframes("toast", [("0%,60%", "opacity:0;transform:translateY(10px)"),
                                ("65%,88%", "opacity:1;transform:translateY(0)"),
                                ("95%,100%", "opacity:0;transform:translateY(0)")]),
            rule(".toast", f"animation:toast {cycle}s cubic-bezier(.2,.8,.2,1) infinite")]

    # multiplayer cursors: mine (around the selection) and an AI agent (around the editor)
    me = [(530, 300), (bx1 - 3, by0 + 3), (bx1 - 3, by0 + 3), (scx + sw / 2 + 12, by1 + 12), (scx + sw / 2 + 12, by1 + 12),
          (300, 262), (300, 262), (530, 300)]
    stops = [0, 20, 30, 48, 58, 76, 86, 100]
    css += [keyframes("me", [(f"{s}%", f"transform:translate({x:.0f}px,{y:.0f}px)") for s, (x, y) in zip(stops, me)]),
            rule(".me", f"transform:translate({me[0][0]}px,{me[0][1]}px);animation:me 12s cubic-bezier(.45,0,.25,1) infinite")]
    agent = [(892, 196), (770, 150), (770, 150), (868, 104), (868, 104), (892, 196)]
    astops = [0, 25, 40, 65, 80, 100]
    css += [keyframes("agent", [(f"{s}%", f"transform:translate({x}px,{y}px)") for s, (x, y) in zip(astops, agent)]),
            rule(".agent", f"transform:translate({agent[0][0]}px,{agent[0][1]}px);animation:agent 9s cubic-bezier(.45,0,.25,1) infinite")]

    defs = (f'<defs>{dots("dots", t["dot"])}'
            f'<radialGradient id="glow" cx="0.8" cy="0.42" r="0.5"><stop offset="0" stop-color="{t["accent"]}" stop-opacity="{t["glow"]}"/>'
            f'<stop offset="1" stop-color="{t["accent"]}" stop-opacity="0"/></radialGradient>'
            f'<filter id="shadow" x="-20%" y="-30%" width="140%" height="180%"><feDropShadow dx="0" dy="6" stdDeviation="8" '
            f'flood-color="#000000" flood-opacity="0.18"/></filter>'
            f'<clipPath id="frame"><rect width="{w}" height="{h}" rx="20"/></clipPath></defs>')
    body = (defs + f'<g clip-path="url(#frame)"><rect width="{w}" height="{h}" fill="{t["bg"]}"/>'
            f'<rect width="{w}" height="{h}" fill="url(#dots)"/><rect width="{w}" height="{h}" fill="url(#glow)"/></g>'
            f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="19.5" fill="none" stroke="{t["border"]}"/>'
            + left + "".join(code) + toast
            + cursor("agent", t["agent"], "AI agent", "#ffffff")
            + cursor("me", t["accent"], "Abduroziq", "#18181b"))
    return doc(w, h, f"{NAME} — Product Engineer",
               "Designing and building products, from Figma to production. A design canvas with my name selected, "
               "an editor typing my stack and a deploy notification.", body, t, "".join(css))


# --------------------------------------------------------------------------- project cards

def art_coins(t: dict) -> str:
    out = []
    for x, n in [(232, 3), (282, 5), (332, 4)]:
        for k in range(n):
            y = 108 - k * 7
            out.append(f'<ellipse cx="{x}" cy="{y + 6}" rx="21" ry="6.5" fill="{t["deep"]}"/>'
                       f'<rect x="{x - 21}" y="{y}" width="42" height="6" fill="{t["deep"]}"/>'
                       f'<ellipse cx="{x}" cy="{y}" rx="21" ry="6.5" fill="{t["accent"]}" stroke="{t["accent2"]}" stroke-width="1"/>')
    gem = (f'<g class="bob"><polygon points="398,38 418,56 398,86 378,56" fill="{t["accent"]}"/>'
           f'<polygon points="398,38 418,56 378,56" fill="{t["accent2"]}"/>'
           f'<polygon points="398,38 406,56 390,56" fill="#ffffff" fill-opacity="0.35"/></g>')
    receipt = (f'<rect x="104" y="54" width="96" height="58" rx="10" fill="{t["card"]}" stroke="{t["border"]}"/>'
               + text(116, 72, "TOP-UP", "mono muted", 9.5, ls=1.2)
               + text(116, 93, "+500", "sans ink", 18, 700)
               + f'<circle cx="120" cy="103" r="3" fill="{t["live"]}"/>' + text(127, 106.5, "PAID", "mono ink2", 9.5, ls=1.2))
    return receipt + "".join(out) + gem


def art_ecosystem(t: dict) -> str:
    """Karimov Academy: one hub, many products. Drawn in the academy's own black and gold."""
    c = KARIMOV
    cx, cy, rx, ry = 288, 76, 108, 36
    nodes = [("CRM", 0), ("TASKS", 60), ("QUIZ", 120), ("LESSONS", 180), ("SITE", 240), ("CHATS", 300)]
    out = [f'<defs><linearGradient id="kagold" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{c["gold_light"]}"/>'
           f'<stop offset="0.5" stop-color="{c["gold"]}"/><stop offset="1" stop-color="{c["gold_dark"]}"/></linearGradient></defs>',
           f'<rect x="140" y="22" width="296" height="108" rx="16" fill="{c["bg"]}" stroke="{c["line"]}"/>',
           f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="none" stroke="{c["line"]}" stroke-dasharray="2 4"/>']
    pills, signals = [], []
    for i, (label, deg) in enumerate(nodes):
        a = math.radians(deg)
        x, y = cx + rx * math.cos(a), cy + ry * math.sin(a)
        out.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="{c["line"]}"/>')
        if i % 2 == 0:
            signals.append(f'<circle class="sig" cx="{cx}" cy="{cy}" r="2.6" fill="{c["gold_light"]}" '
                           f'style="--dx:{x - cx:.1f}px;--dy:{y - cy:.1f}px;animation-delay:-{i * 0.9:.1f}s"/>')
        w = tw(label, "mono500", 9, 1) + 16
        pills.append(f'<rect x="{x - w / 2:.1f}" y="{y - 9:.1f}" width="{w:.1f}" height="18" rx="9" fill="{c["pill"]}" stroke="{c["line"]}"/>'
                     + text(x, y + 3.2, label, "mono", 9, anchor="middle", ls=1, fill=c["gold"]))
    hub = (f'<circle cx="{cx}" cy="{cy}" r="27" fill="none" stroke="{c["gold_dark"]}" stroke-opacity="0.6" class="pulse"/>'
           f'<circle cx="{cx}" cy="{cy}" r="21" fill="url(#kagold)"/>'
           + text(cx, cy + 5, "KA", "sans", 14, 700, anchor="middle", fill=c["bg"], ls=0.5))
    return "".join(out) + "".join(signals) + "".join(pills) + hub


def art_schedule(t: dict) -> str:
    c = TAVRYN
    x0, y0, wd, ht = 168, 28, 252, 96
    out = [f'<rect x="{x0}" y="{y0}" width="{wd}" height="{ht}" rx="18" fill="{c["surface"]}"/>',
           text(x0 + 16, y0 + 24, "Today", "sans", 14, 700, fill=c["dark"]),
           text(x0 + wd - 16, y0 + 23, "THU 19", "mono", 9.5, anchor="end", ls=1.2, fill=c["ink2"])]

    def block(x: float, y: float, w: float, label: str, dark: bool) -> str:
        fill = c["dark"] if dark else c["raised"]
        stroke = "" if dark else f' stroke="{c["line"]}"'
        ink = c["raised"] if dark else c["dark"]
        return (f'<rect x="{x}" y="{y}" width="{w}" height="22" rx="11" fill="{fill}"{stroke}/>'
                + text(x + 12, y + 15, label, "sans", 11, 500, fill=ink))

    out += [block(x0 + 14, y0 + 36, 108, "Deep work", True), block(x0 + 130, y0 + 36, 108, "Design review", False),
            block(x0 + 14, y0 + 64, 76, "Gym", False), block(x0 + 98, y0 + 64, 140, "Ship TestFlight", True)]
    out.append(f'<g class="now"><line x1="{x0 + 60}" y1="{y0 + 32}" x2="{x0 + 60}" y2="{y0 + 90}" stroke="{c["accent"]}" stroke-width="2"/>'
               f'<circle cx="{x0 + 60}" cy="{y0 + 32}" r="3.5" fill="{c["accent"]}"/></g>')
    return "".join(out)


def art_alert(t: dict) -> str:
    x0, y0 = 150, 38
    return (text(x0, 30, "OBS WIDGET", "mono muted", 9.5, ls=1.2)
            + f'<g class="pop fb"><rect x="{x0}" y="{y0}" width="236" height="80" rx="16" fill="{t["card"]}" '
              f'stroke="{t["accent"]}" stroke-width="1.5"/>'
              f'<circle cx="{x0 + 38}" cy="{y0 + 40}" r="20" fill="{t["accent2"]}"/>'
            + text(x0 + 38, y0 + 47, "A", "sans", 20, 700, anchor="middle", fill="#18181b")
            + text(x0 + 70, y0 + 27, "Aziz sent", "sans ink2", 12, 500)
            + text(x0 + 70, y0 + 51, "50 000 UZS", "sans ink", 21, 700)
            + text(x0 + 70, y0 + 68, "“Great stream!”", "mono muted", 10.5) + "</g>"
            + f'<g class="bob"><path d="M414,62 c-6,-8 -18,-4 -16,6 c2,8 16,16 16,16 c0,0 14,-8 16,-16 c2,-10 -10,-14 -16,-6 z" '
              f'fill="{t["accent"]}"/></g>')


PROJECTS = [
    {"slug": "payzone", "name": "Payzone", "status": "live", "art": art_coins,
     "desc": "Marketplace for game top-ups and in-game currency in Uzbekistan and the CIS.",
     "stack": ["FastAPI", "Next.js", "Kubernetes"]},
    {"slug": "karimov-academy", "name": "Karimov Academy Ecosystem", "status": "live", "art": art_ecosystem,
     "desc": "Website, lead API and an in-house cabinet for a trading academy: CRM, tasks, chats, lessons and quizzes.",
     "stack": ["NestJS", "Next.js", "PostgreSQL"]},
    {"slug": "tavryn", "name": "TAVRYN", "status": "design", "art": art_schedule,
     "desc": "A calm, premium planner for tasks, projects and your schedule. iOS first.",
     "stack": ["Swift", "SwiftUI", "NestJS"]},
    {"slug": "ezdonation", "name": "EzDonation", "status": "planning", "art": art_alert,
     "desc": "Donations and real-time stream alerts for streamers in Uzbekistan.",
     "stack": ["NestJS", "Next.js", "RabbitMQ"]},
]


def project_svg(p: dict, t: dict) -> str:
    w, h = 460, 276
    css = (keyframes("now", [("0%,100%", "transform:translateX(0)"), ("50%", "transform:translateX(120px)")])
           + rule(".now", "animation:now 9s ease-in-out infinite")
           + keyframes("pop", [("0%", "opacity:0;transform:scale(.92)"), ("12%,84%", "opacity:1;transform:scale(1)"),
                               ("96%,100%", "opacity:0;transform:scale(.96)")])
           + rule(".pop", "animation:pop 5s cubic-bezier(.2,.8,.2,1) infinite")
           + keyframes("sig", [("0%", "transform:translate(0,0);opacity:0"), ("15%", "opacity:1"),
                               ("70%", "transform:translate(var(--dx),var(--dy));opacity:1"),
                               ("82%,100%", "transform:translate(var(--dx),var(--dy));opacity:0")])
           + rule(".sig", "animation:sig 2.7s ease-in-out infinite"))
    desc = wrap(p["desc"], w - 52, "sans500", 14.5, 2)
    body = (f'<defs>{dots("dots", t["dot"], 18)}<clipPath id="cover"><rect x="12" y="12" width="{w - 24}" height="128" rx="12"/></clipPath></defs>'
            + frame(w, h, t)
            + f'<g clip-path="url(#cover)"><rect x="12" y="12" width="{w - 24}" height="128" fill="{t["cover"]}"/>'
              f'<rect x="12" y="12" width="{w - 24}" height="128" fill="url(#dots)"/>{p["art"](t)}</g>'
            + status_pill(24, 24, p["status"], t)
            + text(26, 176, p["name"], "sans ink", 25, 700, ls=-0.5)
            + "".join(text(26, 202 + i * 20, line, "sans ink2", 14.5, 500) for i, line in enumerate(desc))
            + chip_row(26, 236, p["stack"], t))
    return doc(w, h, p["name"], f'{p["name"]} — {p["desc"]} Status: {p["status"]}. Stack: {", ".join(p["stack"])}.',
               body, t, css)


# --------------------------------------------------------------------------- stack diagram

STACK = [
    ("Design", ["Figma", "Photoshop", "Illustrator", "Design systems"]),
    ("Interface", ["TypeScript", "React", "Next.js", "Tailwind", "SwiftUI"]),
    ("Services", ["Python", "FastAPI", "NestJS", "Node.js", "aiogram", "PHP"]),
    ("Data", ["PostgreSQL", "Redis", "RabbitMQ", "SQLAlchemy"]),
    ("Infrastructure", ["Docker", "Kubernetes", "Terraform", "GitHub Actions", "Cloudflare"]),
]


def stack_svg(t: dict) -> str:
    w, h = 960, 470
    cx, cy0, step, a, b, d = 236, 112, 64, 132, 66, 16
    slabs, labels, css = [], [], []
    for i, (name, tools) in enumerate(STACK):
        cy = cy0 + i * step
        top = t["slabs"][i]
        faces = (f'<polygon points="{cx - a},{cy} {cx},{cy + b} {cx},{cy + b + d} {cx - a},{cy + d}" fill="{shade(top, .78)}"/>'
                 f'<polygon points="{cx},{cy + b} {cx + a},{cy} {cx + a},{cy + d} {cx},{cy + b + d}" fill="{shade(top, .62)}"/>'
                 f'<polygon points="{cx},{cy - b} {cx + a},{cy} {cx},{cy + b} {cx - a},{cy}" fill="{top}"/>'
                 f'<polygon points="{cx},{cy - b + 14} {cx + a - 28},{cy} {cx},{cy + b - 14} {cx - a + 28},{cy}" fill="none" '
                 f'stroke="#ffffff" stroke-opacity="0.28" stroke-width="1"/>')
        lift = (len(STACK) - 1 - i) * 3
        css += [keyframes(f"lift{i}", [("0%,100%", "transform:translateY(0)"), ("50%", f"transform:translateY(-{lift}px)")]),
                rule(f".lift{i}", "animation:lift%d 5s ease-in-out infinite" % i)]
        slabs.append(f'<g class="lift{i}">{faces}</g>')
        lx = 478
        labels.append(f'<line x1="{cx + a + 12}" y1="{cy + 0.5}" x2="{lx - 14}" y2="{cy + 0.5}" stroke="{t["border"]}" '
                      f'stroke-dasharray="3 4"/><circle cx="{cx + a + 12}" cy="{cy}" r="3" fill="{t["accent"]}"/>'
                      + text(lx, cy - 8, f"0{i + 1}", "mono", 11, fill=t["accent"], ls=1)
                      + text(lx + 26, cy - 8, name, "sans ink", 18, 700)
                      + chip_row(lx, cy + 4, tools, t, gap=7, size=11, h=22, pad=8))
    body = (frame(w, h, t)
            + text(478, 52, "THE STACK · LAYER BY LAYER", "mono muted", 12, ls=1.4)
            + "".join(reversed(slabs)) + "".join(labels))
    return doc(w, h, "Tech stack, layer by layer",
               "; ".join(f"{n}: {', '.join(tools)}" for n, tools in STACK) + ".", body, t, "".join(css))


# --------------------------------------------------------------------------- footer

def footer_svg(t: dict) -> str:
    w, h = 960, 180
    motto = "“Think beyond limits…”"
    size = 38
    mw = tw(motto, "sans700", size, -0.5)
    x0, x1 = 480 - mw / 2 + 20, 480 + mw / 2 - 20
    length = (x1 - x0) * 1.08
    path = f"M{x0:.1f},112 C{x0 + (x1 - x0) * .3:.1f},104 {x0 + (x1 - x0) * .62:.1f},120 {x1:.1f},106"
    css = (keyframes("draw", [("0%", f"stroke-dashoffset:{length:.0f}"), ("30%,100%", "stroke-dashoffset:0")])
           + rule(".draw", f"stroke-dasharray:{length:.0f};animation:draw 4s cubic-bezier(.6,0,.2,1) 1 both"))
    body = (text(480, 88, motto, "sans ink", size, 700, anchor="middle", ls=-0.5)
            + f'<path class="draw" d="{path}" fill="none" stroke="{t["accent"]}" stroke-width="4" stroke-linecap="round"/>'
            + text(480, 150, "JABBOROV ABDUROZIQ · TASHKENT", "mono muted", 12, anchor="middle", ls=1.8))
    return doc(w, h, "Think beyond limits", "My motto: think beyond limits.", body, t, css)


# --------------------------------------------------------------------------- live data

REPOS = ["subagent-monitor", "bananapicsbot", "bitrix24-widget-callanalytics", "my-website"]
REPO_DESC = {"my-website": "Source of abduroziq.uz: Next.js and FastAPI, shipped with Docker and Dokploy."}

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
    repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC) {
      totalCount
      nodes {
        isFork
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
  }
  %s
}
""" % "\n  ".join(f'r{i}: repository(owner: "{USER}", name: "{name}") '
                  "{ name description stargazerCount forkCount pushedAt primaryLanguage { name color } }"
                  for i, name in enumerate(REPOS))


def fetch(token: str) -> dict:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "profile-readme-renderer"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.load(resp)
    if payload.get("errors"):
        sys.exit(f"GraphQL error: {payload['errors']}")
    return payload["data"]


def summarize(user: dict) -> dict:
    cc = user["contributionsCollection"]
    cal = cc["contributionCalendar"]
    days = sorted((d for w in cal["weeks"] for d in w["contributionDays"]), key=lambda d: d["date"])
    counts = [d["contributionCount"] for d in days]

    longest = run = 0
    for c in counts:
        run = run + 1 if c else 0
        longest = max(longest, run)
    current = 0
    tail = counts[:-1] if counts and counts[-1] == 0 else counts  # today may still be empty
    for c in reversed(tail):
        if not c:
            break
        current += 1

    months: dict[str, int] = {}
    for d in days:
        months[d["date"][:7]] = months.get(d["date"][:7], 0) + d["contributionCount"]

    langs: dict[str, int] = {}
    stars = 0
    for repo in user["repositories"]["nodes"]:
        if repo["isFork"]:
            continue
        stars += repo["stargazerCount"]
        for edge in repo["languages"]["edges"]:
            langs[edge["node"]["name"]] = langs.get(edge["node"]["name"], 0) + edge["size"]
    total_bytes = sum(langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: kv[1], reverse=True)[:4]

    total = cal["totalContributions"]
    return {
        "total": total,
        "private_share": round(100 * cc["restrictedContributionsCount"] / total) if total else 0,
        "current": current,
        "longest": longest,
        "repos": user["repositories"]["totalCount"],
        "stars": stars,
        "months": list(months.items())[-12:],
        "langs": [(name, 100 * size / total_bytes) for name, size in top],
        "updated": days[-1]["date"] if days else dt.date.today().isoformat(),
    }


def bar_path(x: float, base: float, w: float, h: float, r: float = 4) -> str:
    """Bar anchored to the baseline with rounded top corners only."""
    if h <= 0:
        return ""
    r = min(r, w / 2, h)
    top = base - h
    return (f"M{x:.1f},{base:.1f}V{top + r:.1f}Q{x:.1f},{top:.1f} {x + r:.1f},{top:.1f}"
            f"H{x + w - r:.1f}Q{x + w:.1f},{top:.1f} {x + w:.1f},{top + r:.1f}V{base:.1f}Z")


def stats_svg(t: dict, s: dict) -> str:
    w, h = 960, 372
    fmt = lambda n: f"{n:,}"
    updated = dt.date.fromisoformat(s["updated"]).strftime("%d %b %Y").upper()

    left, right, base, max_h = 40, 580, 318, 120
    slot = (right - left) / max(len(s["months"]), 1)
    bw = min(28, slot * 0.6)
    peak = max((v for _, v in s["months"]), default=0) or 1
    bars = []
    for i, (key, value) in enumerate(s["months"]):
        x = left + i * slot + (slot - bw) / 2
        bh = max_h * value / peak
        month = dt.date.fromisoformat(key + "-01")
        cx = x + bw / 2
        bars.append(f'<g><title>{month:%B %Y}: {fmt(value)} contributions</title>'
                    f'<path d="{bar_path(x, base, bw, bh)}" fill="{t["mark"]}"/>'
                    + text(cx, base + 24, f"{month:%b}", "mono muted", 12, anchor="middle") + "</g>")
        if value == peak:
            bars.append(text(cx, base - bh - 8, fmt(value), "mono ink2", 12, anchor="middle"))

    cells = [(str(s["current"]), "days", "CURRENT STREAK"), (str(s["longest"]), "days", "LONGEST STREAK"),
             (fmt(s["repos"]), "", "PUBLIC REPOS"), (fmt(s["stars"]), "", "STARS EARNED")]
    rx, colw = 660, 140
    grid = []
    for i, (value, unit, label) in enumerate(cells):
        x, y = rx + (i % 2) * colw, 106 + (i // 2) * 74
        unit_svg = f'<tspan class="ink2" font-size="15" font-weight="500" dx="5">{unit}</tspan>' if unit else ""
        grid.append(f'<text x="{x}" y="{y}" class="sans ink" font-size="30" font-weight="700">{value}{unit_svg}</text>'
                    + text(x, y + 22, label, "mono muted", 11, ls=1.2))

    lang_rows = []
    lw = 920 - rx
    for i, (name, pct) in enumerate(s["langs"]):
        y = 268 + i * 26
        lang_rows.append(text(rx, y, name, "sans ink", 14, 500) + text(920, y, f"{pct:.1f}%", "mono ink2", 12, anchor="end")
                         + f'<rect x="{rx}" y="{y + 6}" width="{lw}" height="5" rx="2.5" fill="{t["track"]}"/>'
                         + f'<rect x="{rx}" y="{y + 6}" width="{max(lw * pct / 100, 5):.1f}" height="5" rx="2.5" fill="{t["mark"]}"/>')

    desc = (f"{fmt(s['total'])} contributions in the last 12 months, {s['private_share']}% in private repositories. "
            f"Current streak {s['current']} days, longest {s['longest']} days. {s['repos']} public repositories, "
            f"{s['stars']} stars. Top languages: " + ", ".join(f"{n} {p:.0f}%" for n, p in s["langs"]) + ".")
    body = (frame(w, h, t)
            + text(40, 56, "ACTIVITY · LAST 12 MONTHS", "mono muted", 12, ls=1.4)
            + text(38, 122, fmt(s["total"]), "sans ink", 58, 700, ls=-1.5)
            + text(40, 154, f"contributions · {s['private_share']}% in private repositories", "sans ink2", 17, 500)
            + f'<line x1="{left}" y1="{base + 0.5}" x2="{right}" y2="{base + 0.5}" stroke="{t["border"]}"/>'
            + "".join(bars)
            + f'<line x1="620.5" y1="40" x2="620.5" y2="{h - 40}" stroke="{t["border"]}"/>'
            + text(920, 56, f"UPDATED {updated}", "mono muted", 11, anchor="end", ls=1.2)
            + "".join(grid)
            + text(rx, 238, "TOP LANGUAGES · PUBLIC REPOS", "mono muted", 11, ls=1.2)
            + "".join(lang_rows))
    return doc(w, h, f"GitHub activity — {USER}", desc, body, t)


def star_points(cx: float, cy: float, r: float) -> str:
    pts = []
    for k in range(10):
        rr = r if k % 2 == 0 else r * 0.45
        ang = math.pi / 2 + k * math.pi / 5
        pts.append(f"{cx + rr * math.cos(ang):.1f},{cy - rr * math.sin(ang):.1f}")
    return " ".join(pts)


def repo_svg(r: dict, t: dict) -> str:
    w, h = 460, 156
    desc = wrap(REPO_DESC.get(r["name"]) or r["description"] or "", w - 52, "sans500", 14, 2)
    lang = r["primaryLanguage"] or {"name": "—", "color": t["muted"]}
    pushed = dt.datetime.fromisoformat(r["pushedAt"].replace("Z", "+00:00")).strftime("%b %Y").upper()
    x = 26
    meta = [f'<circle cx="{x + 5}" cy="{h - 30}" r="5" fill="{lang["color"] or t["muted"]}"/>',
            text(x + 16, h - 26, lang["name"], "mono ink2", 12)]
    x += 16 + tw(lang["name"], "mono500", 12) + 22
    meta += [f'<polygon points="{star_points(x + 6, h - 30.5, 6.5)}" fill="none" stroke="{t["muted"]}" stroke-width="1.3" stroke-linejoin="round"/>',
             text(x + 18, h - 26, str(r["stargazerCount"]), "mono ink2", 12)]
    x += 18 + tw(str(r["stargazerCount"]), "mono500", 12) + 22
    meta += [f'<g fill="none" stroke="{t["muted"]}" stroke-width="1.3"><circle cx="{x + 2}" cy="{h - 36}" r="2"/>'
             f'<circle cx="{x + 12}" cy="{h - 36}" r="2"/><circle cx="{x + 7}" cy="{h - 24}" r="2"/>'
             f'<path d="M{x + 2},{h - 34} v2 q0,3 3,3 h4 q3,0 3,-3 v-2 M{x + 7},{h - 29} v3"/></g>',
             text(x + 20, h - 26, str(r["forkCount"]), "mono ink2", 12),
             text(w - 26, h - 26, f"UPDATED {pushed}", "mono muted", 10.5, anchor="end", ls=1.1)]
    body = (frame(w, h, t)
            + f'<g fill="none" stroke="{t["muted"]}" stroke-width="1.4" stroke-linejoin="round">'
              f'<path d="M27,25 h10 a2,2 0 0 1 2,2 v15 h-10 a2,2 0 0 0 -2,2 z"/><path d="M27,44 v-19"/></g>'
            + text(48, 40, r["name"], "sans ink", 19, 700)
            + f'<path d="M{w - 38},40 l10,-10 M{w - 35},30 h7 v7" fill="none" stroke="{t["muted"]}" stroke-width="1.6" stroke-linecap="round"/>'
            + "".join(text(26, 72 + i * 20, line, "sans ink2", 14, 500) for i, line in enumerate(desc))
            + "".join(meta))
    return doc(w, h, r["name"], f'{r["name"]}: {" ".join(desc)} {lang["name"]}, {r["stargazerCount"]} stars.', body, t)


# --------------------------------------------------------------------------- cli

def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("what", choices=["static", "live"])
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    if args.what == "static":
        out = args.out or ASSETS
        for mode, t in THEMES.items():
            write(out / f"banner-{mode}.svg", banner_svg(t))
            write(out / f"stack-{mode}.svg", stack_svg(t))
            write(out / f"footer-{mode}.svg", footer_svg(t))
            for p in PROJECTS:
                write(out / f"project-{p['slug']}-{mode}.svg", project_svg(p, t))
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            sys.exit("GITHUB_TOKEN is not set")
        out = args.out or ROOT / "dist"
        data = fetch(token)
        summary = summarize(data["user"])
        for mode, t in THEMES.items():
            write(out / f"stats-{mode}.svg", stats_svg(t, summary))
            for i, name in enumerate(REPOS):
                if data.get(f"r{i}"):
                    write(out / f"repo-{name}-{mode}.svg", repo_svg(data[f"r{i}"], t))
        print(json.dumps({k: v for k, v in summary.items() if k != "months"}, indent=2))
    print(f"wrote {args.what} SVGs to {out}")


if __name__ == "__main__":
    main()
