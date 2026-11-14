#!/usr/bin/env python3
"""Build stats.svg: last 12 months of GitHub contributions, drawn in the portfolio's colours.

Needs GITHUB_TOKEN. Locally: GITHUB_TOKEN=$(gh auth token) python3 scripts/make_stats.py
Private contributions only show up if the token can see them and the profile setting
"Include private contributions on my profile" is on.
"""
import json
import os
import sys
import urllib.request
from datetime import date

LOGIN = os.environ.get("PROFILE_LOGIN", "ashis05")
QUERY = """query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{
totalContributions weeks{contributionDays{date contributionCount}}}}}}"""

token = os.environ.get("GITHUB_TOKEN")
if not token:
    sys.exit("GITHUB_TOKEN is not set")

req = urllib.request.Request(
    "https://api.github.com/graphql",
    data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
    headers={"Authorization": f"Bearer {token}", "User-Agent": "profile-stats"},
)
with urllib.request.urlopen(req, timeout=30) as r:
    payload = json.load(r)
if "errors" in payload:
    sys.exit(f"GraphQL error: {payload['errors']}")

cal = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
weeks = cal["weeks"]
total = cal["totalContributions"]
days = [d for w in weeks for d in w["contributionDays"]]
active = sum(1 for d in days if d["contributionCount"] > 0)

counts = sorted(d["contributionCount"] for d in days if d["contributionCount"] > 0)


def level(n: int) -> int:
    if n == 0 or not counts:
        return 0
    q = [counts[int(len(counts) * f) - 1] for f in (0.25, 0.5, 0.75)]
    return 1 + sum(n > x for x in q)


COLORS = ["#2b2620", "#355a45", "#46805c", "#63ad7b", "#8fdca6"]
CELL, GAP = 16, 3
STEP = CELL + GAP
X0, Y0 = 84, 186
W, H = 1200, 340

out = []
a = out.append
a(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" '
  f'aria-label="{total} GitHub contributions on {active} active days in the last 12 months.">')
a('<defs><pattern id="grid" width="48" height="48" patternUnits="userSpaceOnUse">'
  '<path d="M48 0H0V48" fill="none" stroke="#e9e0d0" stroke-opacity="0.045"/></pattern></defs>')
a(f'<rect width="{W}" height="{H}" fill="#1d1915"/><rect width="{W}" height="{H}" fill="url(#grid)"/>')
a('<g stroke="#e9e0d0" stroke-opacity="0.22" fill="none"><path d="M60 0V340M1140 0V340" stroke-dasharray="3 5"/>'
  '<path d="M60 48H1140"/></g>')
a('<g stroke="#e9e0d0" stroke-opacity="0.5" stroke-width="1.2"><path d="M54 48H66M60 42V54M1134 48H1146M1140 42V54"/></g>')
mono = "ui-monospace, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"
serif = "Georgia, 'Times New Roman', 'Liberation Serif', serif"
a(f'<g font-family="{mono}" font-size="13" letter-spacing="1.6" fill="#a39b8d">'
  f'<text x="84" y="40">GITHUB · LAST 12 MONTHS</text>'
  f'<text x="1116" y="40" text-anchor="end">@{LOGIN}</text></g>')
a(f'<g font-family="{serif}" fill="#e9e0d0"><text x="84" y="116" font-size="52">{total:,}</text>'
  f'<text x="260" y="116" font-size="52">{active}</text></g>')
a(f'<g font-family="{mono}" font-size="13" fill="#a39b8d" letter-spacing="0.6">'
  f'<text x="84" y="142">contributions</text><text x="260" y="142">active days</text></g>')

# month labels
a(f'<g font-family="{mono}" font-size="11" fill="#7d766a" letter-spacing="0.8">')
last_month = None
for wi, w in enumerate(weeks):
    m = date.fromisoformat(w["contributionDays"][0]["date"]).strftime("%b")
    if m != last_month and wi < len(weeks) - 2:
        a(f'<text x="{X0 + wi * STEP}" y="{Y0 - 10}">{m}</text>')
    last_month = m
a("</g>")

for wi, w in enumerate(weeks):
    for di, d in enumerate(w["contributionDays"]):
        a(f'<rect x="{X0 + wi * STEP}" y="{Y0 + di * STEP}" width="{CELL}" height="{CELL}" rx="3" '
          f'fill="{COLORS[level(d["contributionCount"])]}"><title>{d["date"]}: {d["contributionCount"]}</title></rect>')
a("</svg>")

with open(os.path.join(os.path.dirname(__file__), "..", "stats.svg"), "w") as f:
    f.write("\n".join(out) + "\n")
print(f"stats.svg: {total} contributions, {active} active days, {len(weeks)} weeks")
