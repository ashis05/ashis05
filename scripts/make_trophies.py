#!/usr/bin/env python3
"""Build trophies.svg: a row of rank cards drawn in the portfolio's colours.

Needs GITHUB_TOKEN. Locally: GITHUB_TOKEN=$(gh auth token) python3 scripts/make_trophies.py
Every number comes from the contribution calendar or the public profile, so a read-only token
that cannot see private repositories still gives the same result as a full-access one.
"""
import json
import os
import sys
import urllib.request
from datetime import date

LOGIN = os.environ.get("PROFILE_LOGIN", "ashis05")
token = os.environ.get("GITHUB_TOKEN")
if not token:
    sys.exit("GITHUB_TOKEN is not set")


def gql(query, variables=None):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables or {}}).encode(),
        headers={"Authorization": f"Bearer {token}", "User-Agent": "profile-trophies"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        sys.exit(f"GraphQL error: {data['errors']}")
    return data["data"]


base = gql("""query($l:String!){user(login:$l){createdAt followers{totalCount}
  contributionsCollection{contributionYears}}}""", {"l": LOGIN})["user"]

years = sorted(base["contributionsCollection"]["contributionYears"])
aliases = " ".join(
    f'y{y}:contributionsCollection(from:"{y}-01-01T00:00:00Z",to:"{y}-12-31T23:59:59Z"){{contributionCalendar{{totalContributions}}}}'
    for y in years
)
per_year = gql("query($l:String!){user(login:$l){" + aliases + "}}", {"l": LOGIN})["user"]
contribs = sum(v["contributionCalendar"]["totalContributions"] for v in per_year.values())

recent = gql("""query($l:String!){user(login:$l){contributionsCollection{contributionCalendar{weeks{contributionDays{contributionCount}}}}}}""",
             {"l": LOGIN})["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
counts = [d["contributionCount"] for w in recent for d in w["contributionDays"]]
active_days = sum(1 for c in counts if c > 0)
best_day = max(counts) if counts else 0
streak = run = 0
for c in counts:
    run = run + 1 if c > 0 else 0
    streak = max(streak, run)
followers = base["followers"]["totalCount"]
age = date.today().year - int(base["createdAt"][:4])

# (title, value, thresholds for C, B, A, S)
METRICS = [
    ("Contributions", contribs, (1, 100, 500, 1000)),
    ("Longest streak, days", streak, (1, 5, 14, 30)),
    ("Best day", best_day, (1, 10, 30, 60)),
    ("Active days, 12 mo", active_days, (1, 50, 120, 250)),
    ("Followers", followers, (1, 10, 50, 200)),
    ("Years on GitHub", age, (1, 3, 6, 10)),
]
RANKS = ["C", "B", "A", "S"]
TONE = {  # cup colour per rank, from the site's warm palette
    "-": "#4a443b",
    "C": "#8a7f6e",
    "B": "#b9a47a",
    "A": "#d6bf86",
    "S": "#8fdca6",
}


def rank(value, th):
    r = "-"
    for name, t in zip(RANKS, th):
        if value >= t:
            r = name
    return r


W, H = 1200, 250
CARD_W, GAP = 162, 12
X0 = 84
mono = "ui-monospace, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"
serif = "Georgia, 'Times New Roman', 'Liberation Serif', serif"

o = []
a = o.append
a(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="GitHub trophies">')
a('<defs><pattern id="grid" width="48" height="48" patternUnits="userSpaceOnUse">'
  '<path d="M48 0H0V48" fill="none" stroke="#e9e0d0" stroke-opacity="0.045"/></pattern></defs>')
a(f'<rect width="{W}" height="{H}" fill="#1d1915"/><rect width="{W}" height="{H}" fill="url(#grid)"/>')
a('<g stroke="#e9e0d0" stroke-opacity="0.22" fill="none"><path d="M60 0V250M1140 0V250" stroke-dasharray="3 5"/>'
  '<path d="M60 48H1140"/></g>')
a('<g stroke="#e9e0d0" stroke-opacity="0.5" stroke-width="1.2"><path d="M54 48H66M60 42V54M1134 48H1146M1140 42V54"/></g>')
a(f'<g font-family="{mono}" font-size="13" letter-spacing="1.6" fill="#a39b8d">'
  f'<text x="84" y="40">TROPHIES</text><text x="1116" y="40" text-anchor="end">@{LOGIN}</text></g>')

for i, (title, value, th) in enumerate(METRICS):
    r = rank(value, th)
    x = X0 + i * (CARD_W + GAP)
    c = TONE[r]
    a(f'<g transform="translate({x} 72)">')
    a(f'<rect width="{CARD_W}" height="152" rx="8" fill="#26211c" stroke="#e9e0d0" stroke-opacity="0.12"/>')
    # cup
    a(f'<g transform="translate({CARD_W / 2 - 22} 14)" fill="none" stroke="{c}" stroke-width="2.4" '
      f'stroke-linecap="round" stroke-linejoin="round">'
      '<path d="M10 4H34V20C34 28 28 33 22 33C16 33 10 28 10 20Z" fill-opacity="0.18" fill="' + c + '"/>'
      '<path d="M10 8H4C4 16 7 19 11 20M34 8H40C40 16 37 19 33 20"/>'
      '<path d="M22 33V40M14 44H30"/></g>')
    a(f'<text x="{CARD_W / 2}" y="86" text-anchor="middle" font-family="{serif}" font-size="26" fill="#e9e0d0">{value:,}</text>')
    a(f'<text x="{CARD_W / 2}" y="108" text-anchor="middle" font-family="{mono}" font-size="12" fill="#a39b8d">{title}</text>')
    label = "not yet" if r == "-" else f"RANK {r}"
    a(f'<text x="{CARD_W / 2}" y="134" text-anchor="middle" font-family="{mono}" font-size="12" '
      f'letter-spacing="1.4" fill="{c}">{label}</text>')
    a("</g>")
a("</svg>")

with open(os.path.join(os.path.dirname(__file__), "..", "trophies.svg"), "w") as f:
    f.write("\n".join(o) + "\n")
print("trophies.svg:", ", ".join(f"{t} {v} ({rank(v, th)})" for t, v, th in METRICS))
