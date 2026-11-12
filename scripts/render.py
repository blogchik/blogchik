#!/usr/bin/env python3
"""Render the profile SVGs.

    python3 scripts/render.py banner            # assets/banner-{dark,light}.svg (static, commit them)
    python3 scripts/render.py stats --out dist  # dist/stats-{dark,light}.svg (needs GITHUB_TOKEN)

Standard library only, so it runs on a bare GitHub Actions runner.
Fonts: Bricolage Grotesque and Geist Mono (SIL OFL 1.1), subset in assets/fonts.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import sys
import urllib.request
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"
USER = "blogchik"

THEMES = {
    "dark": {
        "bg": "#09090b", "card": "#0c0c0e", "border": "#27272a", "dot": "#3f3f46",
        "ink": "#fafafa", "ink2": "#a1a1aa", "muted": "#8b8b94",
        "accent": "#E28413", "mark": "#E28413", "track": "#1f1f23", "glow": 0.22,
    },
    "light": {
        "bg": "#fafafa", "card": "#ffffff", "border": "#e4e4e7", "dot": "#d4d4d8",
        "ink": "#18181b", "ink2": "#52525b", "muted": "#71717a",
        "accent": "#E28413", "mark": "#BF6A0A", "track": "#f1f1f3", "glow": 0.14,
    },
}

SANS = "Bricolage, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "GeistMono, ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"


def font_faces() -> str:
    def face(family: str, file: str, weight: int) -> str:
        data = base64.b64encode((FONTS / file).read_bytes()).decode()
        return (f"@font-face{{font-family:{family};font-weight:{weight};"
                f"src:url(data:font/woff2;base64,{data}) format('woff2')}}")

    return "".join([
        face("Bricolage", "bricolage-700.woff2", 700),
        face("Bricolage", "bricolage-500.woff2", 500),
        face("GeistMono", "geistmono-500.woff2", 500),
    ])


def text_styles(t: dict) -> str:
    return (
        f".sans{{font-family:{SANS}}}.mono{{font-family:{MONO};font-weight:500}}"
        f".ink{{fill:{t['ink']}}}.ink2{{fill:{t['ink2']}}}.muted{{fill:{t['muted']}}}"
    )


# --------------------------------------------------------------------------- banner

def banner_svg(t: dict) -> str:
    w, h = 960, 300
    steps = [
        ("design", "Figma · design systems"),
        ("build", "web · mobile · bots"),
        ("ship", "Kubernetes · CI/CD"),
    ]
    sx, y0, gap = 748, 92, 64
    rows = []
    for i, (title, sub) in enumerate(steps):
        y = y0 + i * gap
        rows.append(
            f'<circle cx="{sx}" cy="{y}" r="7" fill="{t["bg"]}" stroke="{t["accent"]}" stroke-width="2"/>'
            f'<text x="{sx + 22}" y="{y + 1}" class="sans ink" font-size="20" font-weight="500">{title}</text>'
            f'<text x="{sx + 22}" y="{y + 21}" class="mono muted" font-size="12">{escape(sub)}</text>'
        )
    travel = gap * (len(steps) - 1)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-labelledby="title desc">
<title id="title">Jabborov Abduroziq — Product Engineer</title>
<desc id="desc">Designing and building products, from Figma to production. Tashkent, Uzbekistan.</desc>
<style>{font_faces()}{text_styles(t)}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.3}}}}
@keyframes travel{{0%{{transform:translateY(0);opacity:0}}12%{{opacity:1}}88%{{opacity:1}}100%{{transform:translateY({travel}px);opacity:0}}}}
.pulse{{animation:pulse 2.4s ease-in-out infinite}}
.runner{{animation:travel 3.2s cubic-bezier(.65,0,.35,1) infinite}}
@media (prefers-reduced-motion:reduce){{.pulse,.runner{{animation:none}}}}
</style>
<defs>
<pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1.1" fill="{t['dot']}"/></pattern>
<linearGradient id="fade" x1="0" x2="1"><stop offset="0.35" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff" stop-opacity="0.9"/></linearGradient>
<mask id="dotmask"><rect width="{w}" height="{h}" fill="url(#fade)"/></mask>
<radialGradient id="glow" cx="0.86" cy="0.12" r="0.62"><stop offset="0" stop-color="{t['accent']}" stop-opacity="{t['glow']}"/><stop offset="1" stop-color="{t['accent']}" stop-opacity="0"/></radialGradient>
<clipPath id="frame"><rect width="{w}" height="{h}" rx="20"/></clipPath>
</defs>
<g clip-path="url(#frame)">
<rect width="{w}" height="{h}" fill="{t['bg']}"/>
<rect width="{w}" height="{h}" fill="url(#dots)" mask="url(#dotmask)"/>
<rect width="{w}" height="{h}" fill="url(#glow)"/>
</g>
<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="19.5" fill="none" stroke="{t['border']}"/>
<circle cx="62" cy="83" r="4.5" fill="{t['accent']}" class="pulse"/>
<text x="76" y="88" class="mono ink2" font-size="13" letter-spacing="1.6">PRODUCT ENGINEER · TASHKENT, UZ</text>
<text x="56" y="156" class="sans ink" font-size="58" font-weight="700" letter-spacing="-1.6">Jabborov Abduroziq</text>
<text x="57" y="198" class="sans ink2" font-size="21" font-weight="500">Designing and building products — from Figma to production.</text>
<text x="57" y="246" class="mono muted" font-size="12" letter-spacing="1.4">NEXT.JS · FASTAPI · NESTJS · POSTGRESQL · KUBERNETES · SWIFT</text>
<line x1="{sx}" y1="{y0}" x2="{sx}" y2="{y0 + travel}" stroke="{t['border']}" stroke-width="2"/>
<circle cx="{sx}" cy="{y0}" r="4" fill="{t['accent']}" class="runner"/>
{''.join(rows)}
</svg>
"""


# --------------------------------------------------------------------------- stats

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
}
"""


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
    return payload["data"]["user"]


def summarize(user: dict) -> dict:
    cc = user["contributionsCollection"]
    cal = cc["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    days.sort(key=lambda d: d["date"])
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
        key = d["date"][:7]
        months[key] = months.get(key, 0) + d["contributionCount"]
    month_list = list(months.items())[-12:]

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
        "months": month_list,
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

    # monthly bars (single series, one hue)
    left, right, base, max_h = 40, 580, 318, 120
    slot = (right - left) / max(len(s["months"]), 1)
    bw = min(28, slot * 0.6)
    peak = max((v for _, v in s["months"]), default=0) or 1
    bars = []
    for i, (key, value) in enumerate(s["months"]):
        x = left + i * slot + (slot - bw) / 2
        bh = max_h * value / peak
        label = dt.date.fromisoformat(key + "-01").strftime("%b")
        full = dt.date.fromisoformat(key + "-01").strftime("%B %Y")
        cx = x + bw / 2
        bars.append(
            f'<g><title>{full}: {fmt(value)} contributions</title>'
            f'<path d="{bar_path(x, base, bw, bh)}" fill="{t["mark"]}"/>'
            f'<text x="{cx:.1f}" y="{base + 24}" class="mono muted" font-size="12" text-anchor="middle">{label}</text></g>'
        )
        if value == peak:
            bars.append(f'<text x="{cx:.1f}" y="{base - bh - 8:.1f}" class="mono ink2" font-size="12" '
                        f'text-anchor="middle">{fmt(value)}</text>')

    # right column: 2x2 numbers
    cells = [
        (f"{s['current']}", "days", "CURRENT STREAK"),
        (f"{s['longest']}", "days", "LONGEST STREAK"),
        (fmt(s["repos"]), "", "PUBLIC REPOS"),
        (fmt(s["stars"]), "", "STARS EARNED"),
    ]
    rx, colw = 660, 140
    grid = []
    for i, (value, unit, label) in enumerate(cells):
        x = rx + (i % 2) * colw
        y = 106 + (i // 2) * 74
        unit_svg = f'<tspan class="ink2" font-size="15" font-weight="500" dx="5">{unit}</tspan>' if unit else ""
        grid.append(
            f'<text x="{x}" y="{y}" class="sans ink" font-size="30" font-weight="700">{value}{unit_svg}</text>'
            f'<text x="{x}" y="{y + 22}" class="mono muted" font-size="11" letter-spacing="1.2">{label}</text>'
        )

    # languages: ranked, single hue
    lang_rows = []
    lw = 920 - rx
    for i, (name, pct) in enumerate(s["langs"]):
        y = 268 + i * 26
        lang_rows.append(
            f'<text x="{rx}" y="{y}" class="sans ink" font-size="14" font-weight="500">{escape(name)}</text>'
            f'<text x="920" y="{y}" class="mono ink2" font-size="12" text-anchor="end">{pct:.1f}%</text>'
            f'<rect x="{rx}" y="{y + 6}" width="{lw}" height="5" rx="2.5" fill="{t["track"]}"/>'
            f'<rect x="{rx}" y="{y + 6}" width="{max(lw * pct / 100, 5):.1f}" height="5" rx="2.5" fill="{t["mark"]}"/>'
        )

    desc = (f"{fmt(s['total'])} contributions in the last 12 months, {s['private_share']}% in private repositories. "
            f"Current streak {s['current']} days, longest {s['longest']} days. "
            f"{s['repos']} public repositories, {s['stars']} stars. Top languages: "
            + ", ".join(f"{n} {p:.0f}%" for n, p in s["langs"]) + ".")

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-labelledby="title desc">
<title id="title">GitHub activity — {USER}</title>
<desc id="desc">{escape(desc)}</desc>
<style>{font_faces()}{text_styles(t)}</style>
<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="19.5" fill="{t['card']}" stroke="{t['border']}"/>
<text x="40" y="56" class="mono muted" font-size="12" letter-spacing="1.4">ACTIVITY · LAST 12 MONTHS</text>
<text x="38" y="122" class="sans ink" font-size="58" font-weight="700" letter-spacing="-1.5">{fmt(s['total'])}</text>
<text x="40" y="154" class="sans ink2" font-size="17" font-weight="500">contributions · {s['private_share']}% in private repositories</text>
<line x1="{left}" y1="{base + 0.5}" x2="{right}" y2="{base + 0.5}" stroke="{t['border']}"/>
{''.join(bars)}
<line x1="620.5" y1="40" x2="620.5" y2="{h - 40}" stroke="{t['border']}"/>
<text x="920" y="56" class="mono muted" font-size="11" letter-spacing="1.2" text-anchor="end">UPDATED {updated}</text>
{''.join(grid)}
<text x="{rx}" y="238" class="mono muted" font-size="11" letter-spacing="1.2">TOP LANGUAGES · PUBLIC REPOS</text>
{''.join(lang_rows)}
</svg>
"""


# --------------------------------------------------------------------------- cli

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("what", choices=["banner", "stats"])
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    if args.what == "banner":
        out = args.out or ROOT / "assets"
        out.mkdir(parents=True, exist_ok=True)
        for mode, theme in THEMES.items():
            (out / f"banner-{mode}.svg").write_text(banner_svg(theme), encoding="utf-8")
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            sys.exit("GITHUB_TOKEN is not set")
        out = args.out or ROOT / "dist"
        out.mkdir(parents=True, exist_ok=True)
        summary = summarize(fetch(token))
        for mode, theme in THEMES.items():
            (out / f"stats-{mode}.svg").write_text(stats_svg(theme, summary), encoding="utf-8")
        print(json.dumps({k: v for k, v in summary.items() if k != "months"}, indent=2))
    print(f"wrote {args.what} SVGs to {out}")


if __name__ == "__main__":
    main()
