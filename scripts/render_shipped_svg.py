#!/usr/bin/env python3
"""
Render data/shipped.json as the "shipped" card: a totals strip plus one row per
selected project, each carrying a real distribution number.

This card replaced a contribution heatmap. The heatmap duplicated the graph
GitHub already draws twenty pixels further down the profile page, and it only
ever said how MUCH work happened. This says what the work produced and whether
anyone actually uses it.

Stars and downloads come from data/shipped.json (live). The blurbs and the
project selection are hand-authored below -- a machine cannot say why a project
matters.

Run by .github/workflows/update-profile-art.yml after fetch_shipped.py.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
IN_PATH = os.path.join(HERE, "..", "data", "shipped.json")
OUT_PATH = os.path.join(HERE, "..", "shipped-card.svg")
STATIC = bool(os.environ.get("STATIC"))

# ===========================================================================
#  EDIT THIS -- which projects to feature, in this order, and what each one is.
#
#  repo    must match the repository name exactly (case sensitive)
#  blurb   <= 44 chars, lowercase, no full stop. Say what it DOES
#  metric  the headline number. None -> derived from npm data when available
#  label   what the number means, shown under it
# ===========================================================================
PROJECTS = [
    {"repo": "OCR-buddy",
     "blurb": "local-first Chrome OCR, fully on-device",
     "metric": "3,000+", "label": "users"},
    {"repo": "Lupin",
     "blurb": "run Claude Code on any LLM provider",
     "metric": None, "label": "npm / 30d"},          # filled from npm data
    {"repo": "MCP_Trenitalia",
     "blurb": "MCP server for Italian train data",
     "metric": "in production", "label": ""},
]

# Every row must carry a real number or a real state. KoboOfflineBackup was cut
# for having neither -- an empty right-hand column reads as an unfinished row.

# The Chrome Web Store publishes no API. Scraping it would add a third-party
# host and a second undocumented-markup dependency to a pipeline that otherwise
# only talks to github.com and registry.npmjs.org. Update this by hand instead.
STORE_USERS = "3,000+ extension users"

W = 860
PAD = 22
TITLEBAR_H = 30
ROW_H = 30

BG = "#0d1117"
BG2 = "#111722"
FRAME = "#30363d"
MUTED = "#7d8590"
INK = "#c9d1d9"
KEY = "#8b949e"
ACCENT = "#58a6ff"
GREEN = "#39d353"
STAR = "#8b949e"   # deliberately NOT gold: colour is reserved for live numbers

# column grid, in px from the left edge
X_NAME = PAD
X_STARS = PAD + 210
X_LANG = PAD + 290
X_BLURB = PAD + 400
X_METRIC = W - PAD          # right-aligned


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def rise(inner, i):
    """fade + slight upward slide, staggered; freezes visible. ~1.5s total,
    in step with the info card so the three windows settle together."""
    if STATIC:
        return f"<g>{inner}</g>"
    delay = 0.15 + i * 0.09
    return (f'<g opacity="0" transform="translate(0,5)">{inner}'
            f'<animate attributeName="opacity" from="0" to="1" begin="{delay:.2f}s" '
            f'dur="0.4s" fill="freeze"/>'
            f'<animateTransform attributeName="transform" type="translate" from="0 5" '
            f'to="0 0" begin="{delay:.2f}s" dur="0.4s" fill="freeze" calcMode="spline" '
            f'keySplines="0.2 0.8 0.2 1"/></g>')


def render(data):
    repos = data["repos"]
    totals = data["totals"]

    rows = []
    for p in PROJECTS:
        r = repos.get(p["repo"])
        if r is None:                      # repo renamed or made private
            continue
        metric, label = p["metric"], p["label"]
        npm = r.get("npm") or {}
        if metric is None and npm.get("downloads_30d") is not None:
            metric = f"{npm['downloads_30d']:,}"
        rows.append({**p, "repo_data": r, "metric": metric, "label": label})

    H = TITLEBAR_H + 52 + len(rows) * ROW_H + 46

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" font-family="ui-monospace, SFMono-Regular, Menlo, '
        f'Consolas, monospace">',
        '<defs>'
        f'<linearGradient id="sbg" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/>'
        f'</linearGradient></defs>',
        f'<rect width="{W}" height="{H}" rx="12" fill="url(#sbg)"/>',
        f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="12" fill="none" '
        f'stroke="{FRAME}"/>',
        f'<line x1="0" y1="{TITLEBAR_H}" x2="{W}" y2="{TITLEBAR_H}" stroke="{FRAME}"/>',
    ]
    for i, dotcol in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        parts.append(f'<circle cx="{PAD + i*16}" cy="{TITLEBAR_H/2}" r="5" fill="{dotcol}"/>')
    parts.append(f'<text x="{W/2}" y="{TITLEBAR_H/2 + 4}" fill="{MUTED}" font-size="12" '
                 f'text-anchor="middle">{esc(data["user"])}@github: ~$ ./shipped</text>')

    # ---- totals strip -----------------------------------------------------
    y = TITLEBAR_H + 32
    npm_total = sum((r.get("npm") or {}).get("downloads_30d") or 0
                    for r in repos.values())
    strip = (f'<text x="{PAD}" y="{y}" font-size="13" fill="{MUTED}">'
             f'<tspan fill="{GREEN}" font-weight="700">{totals["stars"]}</tspan>'
             f'<tspan> stars   ·   </tspan>'
             f'<tspan fill="{GREEN}" font-weight="700">{totals["forks"]}</tspan>'
             f'<tspan> forks   ·   </tspan>'
             f'<tspan fill="{GREEN}" font-weight="700">{npm_total:,}</tspan>'
             f'<tspan> npm downloads / 30d   ·   </tspan>'
             f'<tspan fill="{GREEN}" font-weight="700">{esc(STORE_USERS)}</tspan>'
             f'</text>')
    parts.append(rise(strip, 0))
    parts.append(f'<line x1="{PAD}" y1="{y+14}" x2="{W-PAD}" y2="{y+14}" stroke="{FRAME}"/>')

    # ---- one row per project ---------------------------------------------
    y += 44
    for i, row in enumerate(rows):
        r = row["repo_data"]
        stars = r["stars"]
        lang = r["language"] or ""
        inner = (
            f'<text x="{X_NAME}" y="{y}" fill="{INK}" font-size="13" '
            f'font-weight="700">{esc(r["name"])}</text>'
            f'<text x="{X_STARS}" y="{y}" fill="{STAR}" font-size="12.5">'
            f'&#9733; {stars}</text>'
            f'<text x="{X_LANG}" y="{y}" fill="{KEY}" font-size="12.5">{esc(lang)}</text>'
            f'<text x="{X_BLURB}" y="{y}" fill="{MUTED}" font-size="12.5">'
            f'{esc(row["blurb"])}</text>'
        )
        if row["metric"]:
            label = f'<tspan fill="{MUTED}" font-weight="400"> {esc(row["label"])}</tspan>' \
                    if row["label"] else ""
            inner += (f'<text x="{X_METRIC}" y="{y}" font-size="12.5" text-anchor="end" '
                      f'fill="{GREEN}" font-weight="700">{esc(row["metric"])}{label}</text>')
        parts.append(rise(inner, i + 1))
        y += ROW_H

    # ---- footer -----------------------------------------------------------
    y += 2
    parts.append(f'<line x1="0" y1="{y-18}" x2="{W}" y2="{y-18}" stroke="{FRAME}"/>')
    parts.append(f'<text x="{PAD}" y="{y+4}" font-size="11.5" fill="{MUTED}">'
                 f'live from the GitHub and npm APIs, refreshed daily</text>')
    parts.append(f'<text x="{W-PAD}" y="{y+4}" font-size="11.5" fill="{MUTED}" '
                 f'text-anchor="end">{esc(data["generated_at"][:10])}</text>')

    parts.append("</svg>")
    return "".join(parts)


if __name__ == "__main__":
    with open(IN_PATH, encoding="utf-8") as f:
        data = json.load(f)
    svg = render(data)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {OUT_PATH} ({len(svg)} bytes)")
