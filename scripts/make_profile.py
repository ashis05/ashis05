#!/usr/bin/env python3
"""Build profile.svg: the whole profile as one animated image, in the portfolio's style.

Needs GITHUB_TOKEN. Locally: GITHUB_TOKEN=$(gh auth token) python3 scripts/make_profile.py
Every number comes from the public profile or the contribution calendar, so a read-only
token gives the same result as a full-access one.
The animations are plain CSS inside the SVG (entrance and drifting light, no scripts), and they switch off
for people who ask their system for reduced motion.
"""
import html
import json
import os
import sys
import textwrap
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
        headers={"Authorization": f"Bearer {token}", "User-Agent": "profile-svg"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        sys.exit(f"GraphQL error: {data['errors']}")
    return data["data"]


# ---------------------------------------------------------------- data
base = gql("""query($l:String!){user(login:$l){createdAt followers{totalCount}
  contributionsCollection{contributionYears
    contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}""",
           {"l": LOGIN})["user"]
cal = base["contributionsCollection"]["contributionCalendar"]
weeks = cal["weeks"]
year_total = cal["totalContributions"]
days = [d for w in weeks for d in w["contributionDays"]]
counts = [d["contributionCount"] for d in days]
active_days = sum(1 for c in counts if c > 0)
best_day = max(counts) if counts else 0
streak = run = 0
for c in counts:
    run = run + 1 if c > 0 else 0
    streak = max(streak, run)

years = sorted(base["contributionsCollection"]["contributionYears"])
aliases = " ".join(
    f'y{y}:contributionsCollection(from:"{y}-01-01T00:00:00Z",to:"{y}-12-31T23:59:59Z")'
    "{contributionCalendar{totalContributions}}" for y in years)
lifetime = sum(v["contributionCalendar"]["totalContributions"]
               for v in gql("query($l:String!){user(login:$l){" + aliases + "}}", {"l": LOGIN})["user"].values())
followers = base["followers"]["totalCount"]
age = date.today().year - int(base["createdAt"][:4])

# ---------------------------------------------------------------- style
INK, MUTED = "#1d1915", "#4b453b"
CREAM, CARD = "#d4cab6", "#c9bfaa"
LIGHT, LIGHT_MUTED, LIGHT_DIM = "#e9e0d0", "#c2b9a8", "#8f877a"
SERIF = "Georgia, 'Times New Roman', 'Liberation Serif', serif"
MONO = "ui-monospace, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"
# GitHub shows the image about 860 px wide, so a 960-unit canvas renders everything roughly 25% larger
# than the 1200-unit layout did.
W = 960
LX, RX = 72, 888            # content edges
RAIL_L, RAIL_R = 48, 912    # blueprint rails
TS = 1.5                    # slows every entrance down, so the page settles over a few seconds like the site


def esc(s):
    return html.escape(s, quote=False)


out = []
add = out.append


def text(x, y, s, size, fill, family=SERIF, anchor="start", spacing=0, extra=""):
    sp = f' letter-spacing="{spacing}"' if spacing else ""
    an = f' text-anchor="{anchor}"' if anchor != "start" else ""
    add(f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" fill="{fill}"{an}{sp}{extra}>{esc(s)}</text>')


def rise(delay):
    return f'<g class="rise" style="--d:{delay * TS:.2f}s">'


def label(y, n, name, dark):
    """Section label with a ruled line and crosshairs, like the site."""
    col = LIGHT_MUTED if dark else MUTED
    line = LIGHT if dark else INK
    add(rise(0.2))
    add(f'<path d="M{RAIL_L} {y}H{RAIL_R}" stroke="{line}" stroke-opacity="0.28" fill="none"/>')
    add(f'<path d="M{RAIL_L - 6} {y}H{RAIL_L + 6}M{RAIL_L} {y - 6}V{y + 6}M{RAIL_R - 6} {y}H{RAIL_R + 6}M{RAIL_R} {y - 6}V{y + 6}" '
        f'stroke="{line}" stroke-opacity="0.55" stroke-width="1.2" fill="none"/>')
    text(LX, y + 32, f"{n:02d} — {name}", 14, col, MONO, spacing=1.6)
    add("</g>")


def ease_stops(c0, c1, n=17):
    """Eased fade between two colours, like the site's long gradients."""
    r0, r1 = [int(c0[i:i + 2], 16) for i in (1, 3, 5)], [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    out_ = []
    for k in range(n):
        t = k / (n - 1)
        e = t * t * (3 - 2 * t)  # smoothstep
        col = "#%02x%02x%02x" % tuple(round(a_ + (b_ - a_) * e) for a_, b_ in zip(r0, r1))
        out_.append(f'<stop offset="{t:.3f}" stop-color="{col}"/>')
    return "".join(out_)


# ---------------------------------------------------------------- layout (y positions, top to bottom)
H = 2400                           # placeholder, replaced by the real height at the end
GRAD_Y0, GRAD_Y1 = 450, 550        # dark -> paper
DARK2_Y0, DARK2_Y1 = 1470, 1590    # paper -> dark

def frame():
    """Open the SVG and draw what both layouts share: styles, gradients, masks, backgrounds and rails."""
    add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" '
        f'aria-label="Ashis Wadhwani. Software developer. Cloud, DevOps and platform engineering. Mumbai. '
        f'{year_total} GitHub contributions on {active_days} active days in the last 12 months.">')
    add("""<style>
    .rise{opacity:0;animation:rise 1.25s cubic-bezier(.2,.7,.2,1) var(--d,0s) forwards}
    @keyframes rise{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}
    .cell{opacity:0;animation:fade .8s ease-out var(--d,0s) forwards}
    @keyframes fade{to{opacity:1}}
    .sweep{transform-box:fill-box;transform-origin:left center;transform:scaleX(0);animation:sweep 1.3s cubic-bezier(.3,.7,.2,1) var(--d,0s) forwards}
    @keyframes sweep{to{transform:scaleX(1)}}
    @keyframes sA{0%,100%{transform:translate(0,0) rotate(0deg) scale(1,1)}33%{transform:translate(170px,40px) rotate(5deg) scale(1.18,.86)}66%{transform:translate(-90px,70px) rotate(-4deg) scale(.92,1.22)}}
    @keyframes sB{0%,100%{transform:translate(0,0) rotate(0deg) scale(1.05,1)}40%{transform:translate(-180px,30px) rotate(-6deg) scale(.85,1.15)}75%{transform:translate(110px,-50px) rotate(3deg) scale(1.2,.9)}}
    @keyframes sC{0%,100%{transform:translate(0,0) rotate(0deg) scale(.95,1.05)}30%{transform:translate(120px,-60px) rotate(-5deg) scale(1.15,.9)}70%{transform:translate(-150px,20px) rotate(6deg) scale(.9,1.2)}}
    .sA,.sB,.sC{transform-box:fill-box;transform-origin:center}
    .sA{animation:sA 34s ease-in-out infinite}.sB{animation:sB 41s ease-in-out infinite}.sC{animation:sC 29s ease-in-out infinite}
    .rev{animation-direction:reverse}
    @media (prefers-reduced-motion:reduce){.rise,.cell{animation:none;opacity:1}.sweep{animation:none;transform:none}.sA,.sB,.sC{animation:none}}
    </style>""")
    add(f"""<defs>
    <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">{ease_stops(INK, CREAM)}</linearGradient>
    <linearGradient id="g2" x1="0" y1="0" x2="0" y2="1">{ease_stops(CREAM, INK)}</linearGradient>
    <radialGradient id="glowW"><stop offset="0" stop-color="#e0a56a" stop-opacity=".24"/><stop offset=".55" stop-color="#e0a56a" stop-opacity=".08"/><stop offset="1" stop-color="#e0a56a" stop-opacity="0"/></radialGradient>
    <radialGradient id="glowC"><stop offset="0" stop-color="#e9e0d0" stop-opacity=".13"/><stop offset=".55" stop-color="#e9e0d0" stop-opacity=".04"/><stop offset="1" stop-color="#e9e0d0" stop-opacity="0"/></radialGradient>
    <radialGradient id="glowL"><stop offset="0" stop-color="#efe5d0" stop-opacity=".33"/><stop offset=".6" stop-color="#efe5d0" stop-opacity=".10"/><stop offset="1" stop-color="#efe5d0" stop-opacity="0"/></radialGradient>
    <radialGradient id="glowS"><stop offset="0" stop-color="#8f7550" stop-opacity=".18"/><stop offset=".6" stop-color="#8f7550" stop-opacity=".05"/><stop offset="1" stop-color="#8f7550" stop-opacity="0"/></radialGradient>
    <linearGradient id="fH" gradientUnits="userSpaceOnUse" x1="0" y1="{GRAD_Y0 - 140}" x2="0" y2="{GRAD_Y0 + 60}"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#000"/></linearGradient>
    <linearGradient id="fM" gradientUnits="userSpaceOnUse" x1="0" y1="{GRAD_Y1 - 80}" x2="0" y2="{DARK2_Y0 + 80}"><stop offset="0" stop-color="#000"/><stop offset="{140 / (DARK2_Y0 - GRAD_Y1 + 160):.3f}" stop-color="#fff"/><stop offset="{1 - 140 / (DARK2_Y0 - GRAD_Y1 + 160):.3f}" stop-color="#fff"/><stop offset="1" stop-color="#000"/></linearGradient>
    <linearGradient id="fF" gradientUnits="userSpaceOnUse" x1="0" y1="{DARK2_Y1 - 60}" x2="0" y2="{DARK2_Y1 + 140}"><stop offset="0" stop-color="#000"/><stop offset="1" stop-color="#fff"/></linearGradient>
    <mask id="mH" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{GRAD_Y0 + 80}"><rect width="{W}" height="{GRAD_Y0 + 80}" fill="url(#fH)"/></mask>
    <mask id="mM" maskUnits="userSpaceOnUse" x="0" y="{GRAD_Y1 - 80}" width="{W}" height="{DARK2_Y0 - GRAD_Y1 + 160}"><rect y="{GRAD_Y1 - 80}" width="{W}" height="{DARK2_Y0 - GRAD_Y1 + 160}" fill="url(#fM)"/></mask>
    <mask id="mF" maskUnits="userSpaceOnUse" x="0" y="{DARK2_Y1 - 60}" width="{W}" height="4000"><rect y="{DARK2_Y1 - 60}" width="{W}" height="4000" fill="url(#fF)"/></mask>
    <pattern id="gd" width="48" height="48" patternUnits="userSpaceOnUse">
     <path d="M48 0H0V48" fill="none" stroke="#e9e0d0" stroke-opacity=".045"/></pattern>
    <pattern id="gl" width="48" height="48" patternUnits="userSpaceOnUse">
     <path d="M48 0H0V48" fill="none" stroke="#1d1915" stroke-opacity=".05"/></pattern>
    </defs>""")

    # backgrounds (each rect overlaps the next by 2 px so no seam shows)
    add(f'<rect width="{W}" height="{GRAD_Y0 + 2}" fill="{INK}"/>')
    add(f'<rect y="{GRAD_Y0}" width="{W}" height="{GRAD_Y1 - GRAD_Y0 + 2}" fill="url(#g1)"/>')
    add(f'<rect y="{GRAD_Y1}" width="{W}" height="{DARK2_Y0 - GRAD_Y1 + 2}" fill="{CREAM}"/>')
    add(f'<rect y="{DARK2_Y0}" width="{W}" height="{DARK2_Y1 - DARK2_Y0 + 2}" fill="url(#g2)"/>')
    add(f'<rect y="{DARK2_Y1}" width="{W}" height="{H - DARK2_Y1}" fill="{INK}"/>')
    add(f'<rect width="{W}" height="{GRAD_Y0 + 60}" fill="url(#gd)"/>')
    add(f'<rect y="{GRAD_Y1 - 40}" width="{W}" height="{DARK2_Y0 - GRAD_Y1 + 80}" fill="url(#gl)"/>')
    add(f'<rect y="{DARK2_Y1 - 60}" width="{W}" height="{H - DARK2_Y1 + 60}" fill="url(#gd)"/>')
    # blueprint rails, light over dark and dark over light
    add(f'<path d="M{RAIL_L} 0V{GRAD_Y0 + 80}M{RAIL_R} 0V{GRAD_Y0 + 80}" stroke="{LIGHT}" stroke-opacity=".2" stroke-dasharray="3 5" fill="none"/>')
    add(f'<path d="M{RAIL_L} {GRAD_Y1}V{DARK2_Y0}M{RAIL_R} {GRAD_Y1}V{DARK2_Y0}" stroke="{INK}" stroke-opacity=".22" stroke-dasharray="3 5" fill="none"/>')
    add(f'<path d="M{RAIL_L} {DARK2_Y1}V{H}M{RAIL_R} {DARK2_Y1}V{H}" stroke="{LIGHT}" stroke-opacity=".2" stroke-dasharray="3 5" fill="none"/>')


frame()

# ---- smoke: long, tilted streaks of warm light that drift, turn and stretch slowly (like the site's
# background folds). Soft masks fade them out at each band's edge, so no hard line shows.


def smoke(cx, cy, rx, ry, tilt, grad, cls, rev=False):
    r = " rev" if rev else ""
    return (f'<g class="{cls}{r}"><ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" '
            f'transform="rotate({tilt} {cx} {cy})" fill="url(#{grad})"/></g>')


add('<g mask="url(#mH)">'
    + smoke(250, 150, 540, 150, -10, "glowW", "sA")
    + smoke(720, 300, 470, 130, 8, "glowC", "sB")
    + smoke(470, 70, 400, 110, -4, "glowW", "sC")
    + smoke(860, 130, 320, 120, 14, "glowW", "sA", True)
    + '</g>')
add('<g mask="url(#mM)">'
    + smoke(680, 820, 520, 170, -8, "glowL", "sC")
    + smoke(220, 1040, 460, 150, 10, "glowS", "sA")
    + smoke(640, 1260, 440, 140, -12, "glowS", "sB", True)
    + smoke(260, 720, 420, 130, 6, "glowL", "sB")
    + '</g>')
add('<g mask="url(#mF)">'
    + smoke(540, 1790, 520, 160, -9, "glowW", "sB")
    + smoke(170, 2030, 420, 140, 12, "glowC", "sC")
    + smoke(800, 2000, 400, 130, -6, "glowW", "sA", True)
    + smoke(420, 2300, 460, 140, 7, "glowW", "sC", True)
    + '</g>')

# ---- header (dark)
add(rise(0.0))
text(LX, 60, "00 — PROFILE", 14, LIGHT_MUTED, MONO, spacing=1.6)
text(RX, 60, "MUMBAI, INDIA", 14, LIGHT_MUTED, MONO, "end", 1.6)
add("</g>")
add(rise(0.15))
text(LX, 150, "Ashis Wadhwani", 80, LIGHT, SERIF, spacing=-1)
add("</g>")
add(rise(0.3))
text(LX, 194, "Software developer. Cloud, DevOps and platform engineering.", 23, LIGHT_MUTED)
add("</g>")

brief = ("I'm a software developer at BizDateUp Technologies. I run the company's AWS and on-premise "
         "infrastructure, and I write the Python and TypeScript services that sit on top of it. "
         "Outside work I build my own projects and look after a small server at home called escanor.")
add(rise(0.5))
for i, line in enumerate(textwrap.wrap(brief, 80, break_on_hyphens=False)):
    text(LX, 248 + i * 29, line, 19, "#d6cdbb")
add("</g>")

# hero spec columns
# only what the Details cards below don't already say
specs = [("RUNS", "AWS in Terraform", "keyless CI/CD"),
         ("ESCANOR", "A home server", "no public inbound ports")]
add(rise(0.7))
for i, (k, v, sub) in enumerate(specs):
    x = LX + i * 300
    if i:
        add(f'<path d="M{x - 14} 372V432" stroke="{LIGHT}" stroke-opacity=".2"/>')
    text(x, 384, k, 12, LIGHT_DIM, MONO, spacing=1.6)
    text(x, 410, v, 15, LIGHT, MONO)
    text(x, 430, sub, 13, LIGHT_DIM, MONO)
add("</g>")

# ---- 01 details (paper)
y = 570
label(y, 1, "DETAILS", False)
items = [("BASED IN", "Mumbai, India", "Open to on-site, hybrid or remote"),
         ("ROLE", "Software Developer 1", "BizDateUp Technologies, since May 2026"),
         ("SITE", "ashiswadhwani.in", "Case studies, the lab and a blog"),
         ("EMAIL", "hello@ashiswadhwani.in", "Replies come to my inbox"),
         ("LINKEDIN", "ashis-wadhwani-", "linkedin.com/in/ashis-wadhwani-"),
         ("GITHUB", "@ashis05", "You are here")]
CARD_W, CARD_STEP = 404, 420
add(rise(0.9))
for i, (k, v, sub) in enumerate(items):
    cx = LX + (i % 2) * CARD_STEP
    cy = y + 84 + (i // 2) * 100
    add(f'<rect x="{cx - 14}" y="{cy - 24}" width="{CARD_W}" height="88" rx="8" fill="{CARD}" fill-opacity=".7" stroke="{INK}" stroke-opacity=".1"/>')
    if k == "ROLE":  # highlighter behind the role, like the site
        add(f'<rect class="sweep" style="--d:{1.6 * TS:.2f}s" x="{cx - 3}" y="{cy + 8}" width="{len(v) * 11.2 + 6:.0f}" height="26" rx="2" fill="#f2dc7a" fill-opacity=".6"/>')
    text(cx, cy - 4, k, 12, MUTED, MONO, spacing=1.6)
    text(cx, cy + 28, v, 23, INK)
    text(cx, cy + 52, sub, 13, MUTED, MONO)
add("</g>")

# ---- 02 tools and skills
y = 960
label(y, 2, "TOOLS AND SKILLS", False)
groups = [("Cloud and infrastructure", ["AWS", "Terraform", "Docker", "Linux", "Cloudflare Tunnel", "Tailscale"], []),
          ("CI/CD", ["GitHub Actions", "OIDC", "Keyless deploys"], []),
          ("Monitoring", ["Prometheus", "Grafana", "Loki", "Alertmanager"], []),
          ("Languages", ["Python", "TypeScript", "JavaScript", "SQL", "Bash"], ["Java", "C", "C++", "C#"])]
add(rise(1.0))
for gi, (name, chips, dim) in enumerate(groups):
    gy = y + 70 + gi * 80
    text(LX, gy, name.upper(), 13, MUTED, MONO, spacing=1.4)
    x = LX
    for c in chips + dim:
        w = len(c) * 8.4 + 26
        faint = c in dim
        add(f'<rect x="{x:.0f}" y="{gy + 12}" width="{w:.0f}" height="36" rx="7" fill="{CARD}" '
            f'fill-opacity="{.35 if faint else .85}" stroke="{INK}" stroke-opacity="{.08 if faint else .14}"/>')
        text(f"{x + w / 2:.0f}", gy + 36, c, 15, MUTED if faint else INK, MONO, "middle")
        x += w + 10
add("</g>")
wy = y + 70 + 4 * 80
add(rise(1.2))
text(LX, wy, "WHAT I DO", 13, MUTED, MONO, spacing=1.4)
text(LX, wy + 34, "Infrastructure as code, least-privilege access, monitoring and alerting,", 21, INK)
text(LX, wy + 64, "backup restore drills, runbooks and backend services.", 21, INK)
add("</g>")

# ---- 03 github (dark)
y = 1670
label(y, 3, "GITHUB · LAST 12 MONTHS", True)
add(rise(1.4))
text(LX, y + 112, f"{year_total:,}", 58, LIGHT)
text(LX + 200, y + 112, f"{active_days}", 58, LIGHT)
text(LX, y + 142, "contributions", 15, LIGHT_MUTED, MONO, spacing=.6)
text(LX + 200, y + 142, "active days", 15, LIGHT_MUTED, MONO, spacing=.6)
add("</g>")

n_weeks = len(weeks)
STEP = (RX - LX) / n_weeks
CELL = STEP - 3.2
gx, gy0 = LX, y + 206
COLORS = ["#2b2620", "#355a45", "#46805c", "#63ad7b", "#8fdca6"]
nz = sorted(c for c in counts if c > 0)


def level(n):
    if n == 0 or not nz:
        return 0
    q = [nz[max(int(len(nz) * f) - 1, 0)] for f in (.25, .5, .75)]
    return 1 + sum(n > t for t in q)


add(rise(1.5))
last_m = None
for wi, w in enumerate(weeks):
    m = date.fromisoformat(w["contributionDays"][0]["date"]).strftime("%b")
    if m != last_m and wi < n_weeks - 2:
        text(f"{gx + wi * STEP:.1f}", gy0 - 12, m, 12, LIGHT_DIM, MONO, spacing=.8)
    last_m = m
add("</g>")
for wi, w in enumerate(weeks):
    for di, d in enumerate(w["contributionDays"]):
        delay = (1.7 + wi * 0.028 + di * 0.006) * TS
        add(f'<rect class="cell" style="--d:{delay:.2f}s" x="{gx + wi * STEP:.1f}" y="{gy0 + di * STEP:.1f}" '
            f'width="{CELL:.1f}" height="{CELL:.1f}" rx="2.5" fill="{COLORS[level(d["contributionCount"])]}">'
            f'<title>{d["date"]}: {d["contributionCount"]}</title></rect>')

# trophies: three on the first row, two wider ones on the second
ty = gy0 + 7 * STEP + 50
add(rise(3.2))
text(LX, ty, "TROPHIES", 13, LIGHT_DIM, MONO, spacing=1.6)
add("</g>")
METRICS = [("Contributions", lifetime, (1, 100, 500, 1000)),
           ("Longest streak, days", streak, (1, 5, 14, 30)),
           ("Best day", best_day, (1, 10, 30, 60)),
           ("Active days, 12 mo", active_days, (1, 50, 120, 250)),
           ("Years on GitHub", age, (1, 3, 6, 10))]
TONE = {"-": "#6b6458", "C": "#9a8f7c", "B": "#c4ae82", "A": "#dcc58c", "S": "#8fdca6"}


def rank(v, th):
    r = "-"
    for n, t in zip("CBAS", th):
        if v >= t:
            r = n
    return r


TH, TGX, TGY = 108, 10, 14
SPAN = 2 * 404 + 16              # same width as the two columns of Details cards above
ROWS = [[0, 1, 2], [3, 4]]
for i, (title, v, th) in enumerate(METRICS):
    r = rank(v, th)
    c = TONE[r]
    row = next(k for k, rw in enumerate(ROWS) if i in rw)
    n = len(ROWS[row])
    TW = (SPAN - (n - 1) * TGX) / n
    x = LX - 14 + ROWS[row].index(i) * (TW + TGX)
    yy = ty + 18 + row * (TH + TGY)
    add(f'<g transform="translate({x} {yy})"><g class="rise" style="--d:{(3.3 + i * 0.12) * TS:.2f}s">')
    add(f'<rect width="{TW:.0f}" height="{TH}" rx="8" fill="#26211c" stroke="{LIGHT}" stroke-opacity=".14"/>')
    add(f'<g transform="translate(16 26) scale(1.25)" fill="none" stroke="{c}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
        f'<path d="M10 4H34V20C34 28 28 33 22 33C16 33 10 28 10 20Z" fill="{c}" fill-opacity=".18"/>'
        '<path d="M10 8H4C4 16 7 19 11 20M34 8H40C40 16 37 19 33 20M22 33V40M14 44H30"/></g>')
    text(88, 44, f"{v:,}", 34, LIGHT, SERIF)
    text(88, 68, title, 13, LIGHT_MUTED, MONO)
    text(88, 90, "NOT YET" if r == "-" else f"RANK {r}", 14, c, MONO, spacing=1.4)
    add("</g></g>")

# closing line
fy = ty + 18 + 2 * TH + TGY + 64
add(rise(4.2))
add(f'<path d="M{RAIL_L} {fy - 34}H{RAIL_R}" stroke="{LIGHT}" stroke-opacity=".22" fill="none"/>')
text(RX, fy, "refreshed daily", 13, LIGHT_DIM, MONO, "end", 1.2)
add("</g>")

def finish(final_h, name):
    """Close the SVG, set the real height (the canvas follows the content) and write it next to the README."""
    add("</svg>")
    svg = "\n".join(p for p in out if p)
    svg = svg.replace(f'viewBox="0 0 {W} {H}"', f'viewBox="0 0 {W} {final_h}"', 1)
    svg = svg.replace(f'<rect y="{DARK2_Y1}" width="{W}" height="{H - DARK2_Y1}"', f'<rect y="{DARK2_Y1}" width="{W}" height="{final_h - DARK2_Y1}"')
    svg = svg.replace(f'<rect y="{DARK2_Y1 - 60}" width="{W}" height="{H - DARK2_Y1 + 60}"', f'<rect y="{DARK2_Y1 - 60}" width="{W}" height="{final_h - DARK2_Y1 + 60}"')
    svg = svg.replace(f'M{RAIL_L} {DARK2_Y1}V{H}M{RAIL_R} {DARK2_Y1}V{H}', f'M{RAIL_L} {DARK2_Y1}V{final_h}M{RAIL_R} {DARK2_Y1}V{final_h}')
    with open(os.path.join(os.path.dirname(__file__), "..", name), "w") as f:
        f.write(svg + "\n")
    print(f"{name}: {W}x{final_h}, {year_total} contributions, {active_days} active days, "
          f"lifetime {lifetime}, streak {streak}, best day {best_day}, followers {followers}, years {age}")


finish(int(round(fy + 46)), "profile.svg")


# ================================================================ phone version
# GitHub shows README images about 350 px wide on a phone. A 480-unit canvas shows there at roughly
# 75% scale (the desktop image would be about 37%), with one column and wrapped lines. The README
# picks this file on narrow screens through <picture>.
W = 480
LX, RX = 30, 450
RAIL_L, RAIL_R = 14, 466
out = []
add = out.append

# -- measure first: every y position depends on how the text wraps
tag_lines = textwrap.wrap("Software developer. Cloud, DevOps and platform engineering.", 38)
brief_lines = textwrap.wrap(brief, 46, break_on_hyphens=False)
y_brief = 152 + 27 * len(tag_lines) + 30
y_spec = y_brief + 27 * (len(brief_lines) - 1) + 52
GRAD_Y0 = y_spec + 84
GRAD_Y1 = GRAD_Y0 + 90

y_det = GRAD_Y1 + 22
CARD_STEP_M = 100
end_det = y_det + 84 + (len(items) - 1) * CARD_STEP_M + 64


def chip_rows(chips):
    """Lay chips out left to right, wrapping to a new row at the right edge. Returns (x, row, width, chip)."""
    placed, x, row = [], LX, 0
    for c in chips:
        w = len(c) * 9 + 26
        if x + w > RX and x > LX:
            x, row = LX, row + 1
        placed.append((x, row, w, c))
        x += w + 10
    return placed, row + 1


y_tools = end_det + 36
gy = y_tools + 70
group_layout = []
for name, chips, dim in groups:
    placed, nrows = chip_rows(chips + dim)
    group_layout.append((gy, name, placed, set(dim)))
    gy += 12 + nrows * 46 + 34
y_do = gy
do_lines = textwrap.wrap("Infrastructure as code, least-privilege access, monitoring and alerting, "
                         "backup restore drills, runbooks and backend services.", 40)
end_tools = y_do + 34 + 28 * (len(do_lines) - 1) + 20
DARK2_Y0 = end_tools + 50
DARK2_Y1 = DARK2_Y0 + 120

y_gh = DARK2_Y1 + 70
weeks_m = weeks[-26:]  # half a year of squares, so each one is big enough to see on a phone
STEP_M = (RX - LX) / len(weeks_m)
gy0_m = y_gh + 214
ty_m = gy0_m + 7 * STEP_M + 52
TH_M, TG_M = 100, 10
ROWS_M = [[0, 1], [2, 3], [4]]
fy_m = ty_m + 18 + len(ROWS_M) * TH_M + (len(ROWS_M) - 1) * TG_M + 60
H = int(round(fy_m + 40))

# -- draw
frame()
add('<g mask="url(#mH)">'
    + smoke(140, GRAD_Y0 * .28, 300, 110, -10, "glowW", "sA")
    + smoke(360, GRAD_Y0 * .62, 270, 95, 8, "glowC", "sB")
    + smoke(250, GRAD_Y0 * .10, 230, 80, -4, "glowW", "sC")
    + smoke(420, GRAD_Y0 * .45, 190, 80, 14, "glowW", "sA", True)
    + '</g>')
mid = DARK2_Y0 - GRAD_Y1
add('<g mask="url(#mM)">'
    + smoke(330, GRAD_Y1 + mid * .18, 290, 110, -8, "glowL", "sC")
    + smoke(120, GRAD_Y1 + mid * .42, 260, 100, 10, "glowS", "sA")
    + smoke(340, GRAD_Y1 + mid * .68, 250, 90, -12, "glowS", "sB", True)
    + smoke(150, GRAD_Y1 + mid * .9, 240, 90, 6, "glowL", "sB")
    + '</g>')
add('<g mask="url(#mF)">'
    + smoke(260, DARK2_Y1 + 160, 290, 110, -9, "glowW", "sB")
    + smoke(100, DARK2_Y1 + 420, 240, 90, 12, "glowC", "sC")
    + smoke(390, DARK2_Y1 + 560, 230, 90, -6, "glowW", "sA", True)
    + smoke(220, H - 120, 260, 90, 7, "glowW", "sC", True)
    + '</g>')

# header
add(rise(0.0))
text(LX, 46, "00 — PROFILE", 13, LIGHT_MUTED, MONO, spacing=1.4)
text(RX, 46, "MUMBAI, INDIA", 13, LIGHT_MUTED, MONO, "end", 1.4)
add("</g>")
add(rise(0.15))
text(LX, 118, "Ashis Wadhwani", 52, LIGHT, SERIF, spacing=-.5)
add("</g>")
add(rise(0.3))
for i, line in enumerate(tag_lines):
    text(LX, 156 + i * 27, line, 20, LIGHT_MUTED)
add("</g>")
add(rise(0.5))
for i, line in enumerate(brief_lines):
    text(LX, y_brief + i * 27, line, 18, "#d6cdbb")
add("</g>")
add(rise(0.7))
for i, (k, v, sub) in enumerate(specs):
    x = LX + i * 214
    if i:
        add(f'<path d="M{x - 14} {y_spec - 12}V{y_spec + 48}" stroke="{LIGHT}" stroke-opacity=".2"/>')
    text(x, y_spec, k, 12, LIGHT_DIM, MONO, spacing=1.4)
    text(x, y_spec + 24, v, 16, LIGHT, MONO)
    text(x, y_spec + 44, sub, 13, LIGHT_DIM, MONO)
add("</g>")

# 01 details, one card per row
label(y_det, 1, "DETAILS", False)
add(rise(0.9))
for i, (k, v, sub) in enumerate(items):
    cx, cy = LX, y_det + 84 + i * CARD_STEP_M
    add(f'<rect x="{cx - 14}" y="{cy - 24}" width="{RX - LX + 28}" height="88" rx="8" fill="{CARD}" fill-opacity=".7" stroke="{INK}" stroke-opacity=".1"/>')
    if k == "ROLE":
        add(f'<rect class="sweep" style="--d:{1.6 * TS:.2f}s" x="{cx - 3}" y="{cy + 7}" width="{len(v) * 11 + 6:.0f}" height="26" rx="2" fill="#f2dc7a" fill-opacity=".6"/>')
    text(cx, cy - 4, k, 13, MUTED, MONO, spacing=1.4)
    text(cx, cy + 28, v, 23, INK)
    text(cx, cy + 52, sub, 14, MUTED, MONO)
add("</g>")

# 02 tools and skills, chips wrap
label(y_tools, 2, "TOOLS AND SKILLS", False)
add(rise(1.0))
for gy_, name, placed, dim in group_layout:
    text(LX, gy_, name.upper(), 13, MUTED, MONO, spacing=1.2)
    for x, row, w, c in placed:
        top = gy_ + 12 + row * 46
        faint = c in dim
        add(f'<rect x="{x:.0f}" y="{top}" width="{w:.0f}" height="36" rx="7" fill="{CARD}" '
            f'fill-opacity="{.35 if faint else .85}" stroke="{INK}" stroke-opacity="{.08 if faint else .14}"/>')
        text(f"{x + w / 2:.0f}", top + 24, c, 15, MUTED if faint else INK, MONO, "middle")
add("</g>")
add(rise(1.2))
text(LX, y_do, "WHAT I DO", 13, MUTED, MONO, spacing=1.2)
for i, line in enumerate(do_lines):
    text(LX, y_do + 34 + i * 28, line, 20, INK)
add("</g>")

# 03 github
label(y_gh, 3, "GITHUB · LAST 12 MONTHS", True)
add(rise(1.4))
text(LX, y_gh + 104, f"{year_total:,}", 50, LIGHT)
text(LX + 190, y_gh + 104, f"{active_days}", 50, LIGHT)
text(LX, y_gh + 134, "contributions", 14, LIGHT_MUTED, MONO, spacing=.4)
text(LX + 190, y_gh + 134, "active days", 14, LIGHT_MUTED, MONO, spacing=.4)
add("</g>")
add(rise(1.5))
text(LX, gy0_m - 40, "LAST 26 WEEKS", 12, LIGHT_DIM, MONO, spacing=1.4)
last_m = None
for wi, w in enumerate(weeks_m):
    m = date.fromisoformat(w["contributionDays"][0]["date"]).strftime("%b")
    if m != last_m and wi < len(weeks_m) - 2:
        text(f"{LX + wi * STEP_M:.1f}", gy0_m - 12, m, 12, LIGHT_DIM, MONO)
    last_m = m
add("</g>")
for wi, w in enumerate(weeks_m):
    for di, d in enumerate(w["contributionDays"]):
        delay = (1.7 + wi * 0.05 + di * 0.008) * TS
        add(f'<rect class="cell" style="--d:{delay:.2f}s" x="{LX + wi * STEP_M:.1f}" y="{gy0_m + di * STEP_M:.1f}" '
            f'width="{STEP_M - 3:.1f}" height="{STEP_M - 3:.1f}" rx="2.5" fill="{COLORS[level(d["contributionCount"])]}">'
            f'<title>{d["date"]}: {d["contributionCount"]}</title></rect>')

# trophies, two per row (short titles so they fit)
SHORT = {"Longest streak, days": "Streak, days", "Active days, 12 mo": "Active days"}
add(rise(3.2))
text(LX, ty_m, "TROPHIES", 13, LIGHT_DIM, MONO, spacing=1.4)
add("</g>")
SPAN_M = RX - LX + 28
for i, (title, v, th) in enumerate(METRICS):
    r = rank(v, th)
    c = TONE[r]
    row = next(k for k, rw in enumerate(ROWS_M) if i in rw)
    n = len(ROWS_M[row])
    tw = (SPAN_M - (n - 1) * TG_M) / n
    x = LX - 14 + ROWS_M[row].index(i) * (tw + TG_M)
    yy = ty_m + 18 + row * (TH_M + TG_M)
    add(f'<g transform="translate({x:.1f} {yy:.1f})"><g class="rise" style="--d:{(3.3 + i * 0.12) * TS:.2f}s">')
    add(f'<rect width="{tw:.0f}" height="{TH_M}" rx="8" fill="#26211c" stroke="{LIGHT}" stroke-opacity=".14"/>')
    add(f'<g transform="translate(12 24) scale(1.05)" fill="none" stroke="{c}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">'
        f'<path d="M10 4H34V20C34 28 28 33 22 33C16 33 10 28 10 20Z" fill="{c}" fill-opacity=".18"/>'
        '<path d="M10 8H4C4 16 7 19 11 20M34 8H40C40 16 37 19 33 20M22 33V40M14 44H30"/></g>')
    text(70, 42, f"{v:,}", 30, LIGHT, SERIF)
    text(70, 64, SHORT.get(title, title), 13, LIGHT_MUTED, MONO)
    text(70, 86, "NOT YET" if r == "-" else f"RANK {r}", 13, c, MONO, spacing=1.2)
    add("</g></g>")

add(rise(4.2))
add(f'<path d="M{RAIL_L} {fy_m - 34}H{RAIL_R}" stroke="{LIGHT}" stroke-opacity=".22" fill="none"/>')
text(RX, fy_m, "refreshed daily", 13, LIGHT_DIM, MONO, "end", 1.2)
add("</g>")

finish(H, "profile-mobile.svg")
