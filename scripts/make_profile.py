#!/usr/bin/env python3
"""Build profile.svg: the whole profile as one animated image, in the portfolio's style.

Needs GITHUB_TOKEN. Locally: GITHUB_TOKEN=$(gh auth token) python3 scripts/make_profile.py
Every number comes from the public profile or the contribution calendar, so a read-only
token gives the same result as a full-access one.
The animations are plain CSS inside the SVG (entrance only, no scripts), and they switch off
for people who ask their system for reduced motion.
"""
import html
import json
import math
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
INK, MUTED = "#1d1915", "#5d564a"
CREAM, CARD = "#e9e0d0", "#e0d6c4"
LIGHT, LIGHT_MUTED, LIGHT_DIM = "#e9e0d0", "#b7ae9d", "#7d766a"
SERIF = "Georgia, 'Times New Roman', 'Liberation Serif', serif"
MONO = "ui-monospace, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"
W = 1200
LX, RX = 84, 1116  # content edges
FRAMES = 90                       # globe frames per turn
TURN_S = 2 * math.pi / 0.16       # the site's globe turns at 0.16 rad/s, so one turn takes about 39 s
HOLD = 100 / FRAMES * 1.3         # each frame stays up a little longer than its slot, so frames overlap and never flicker
TS = 1.5  # slows every entrance down, so the page settles over a few seconds like the site


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
    add(f'<path d="M60 {y}H1140" stroke="{line}" stroke-opacity="0.28" fill="none"/>')
    add(f'<path d="M54 {y}H66M60 {y - 6}V{y + 6}M1134 {y}H1146M1140 {y - 6}V{y + 6}" stroke="{line}" stroke-opacity="0.55" stroke-width="1.2" fill="none"/>')
    text(LX, y + 28, f"{n:02d} — {name}", 13, col, MONO, spacing=1.6)
    add("</g>")


# ---------------------------------------------------------------- layout
H = 2210
GRAD_Y0, GRAD_Y1 = 430, 600       # dark -> cream
DARK2_Y0, DARK2_Y1 = 1510, 1630   # cream -> dark

add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" '
    f'aria-label="Ashis Wadhwani. Software developer. Cloud, DevOps and platform engineering. Mumbai. '
    f'{year_total} GitHub contributions on {active_days} active days in the last 12 months.">')
add(("""<style>
.rise{opacity:0;animation:rise 1.25s cubic-bezier(.2,.7,.2,1) var(--d,0s) forwards}
@keyframes rise{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}
.cell{opacity:0;animation:fade .8s ease-out var(--d,0s) forwards}
@keyframes fade{to{opacity:1}}
.sweep{transform-box:fill-box;transform-origin:left center;transform:scaleX(0);animation:sweep 1.3s cubic-bezier(.3,.7,.2,1) var(--d,0s) forwards}
@keyframes sweep{to{transform:scaleX(1)}}
@keyframes driftA{0%,100%{transform:translate(0,0)}50%{transform:translate(240px,70px)}}
@keyframes driftB{0%,100%{transform:translate(0,0)}50%{transform:translate(-220px,50px)}}
@keyframes driftC{0%,100%{transform:translate(0,0)}50%{transform:translate(180px,-60px)}}
.dA{animation:driftA 28s ease-in-out 3}.dB{animation:driftB 34s ease-in-out 3}.dC{animation:driftC 31s ease-in-out 3}
.gf{opacity:0;animation:gf __T__ linear infinite;animation-delay:var(--d)}
@keyframes gf{0%{opacity:1}__HOLD__{opacity:1}__HOLD2__{opacity:0}100%{opacity:0}}
@media (prefers-reduced-motion:reduce){.rise,.cell{animation:none;opacity:1}.sweep{animation:none;transform:none}.dA,.dB,.dC{animation:none}.gf{animation:none}.gf0{opacity:1}}
</style>""").replace("__T__", f"{TURN_S:.2f}s").replace("__HOLD__", f"{HOLD:.3f}%").replace("__HOLD2__", f"{HOLD + 0.01:.3f}%"))
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


add(f"""<defs>
<linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">{ease_stops(INK, CREAM)}</linearGradient>
<linearGradient id="g2" x1="0" y1="0" x2="0" y2="1">{ease_stops(CREAM, INK)}</linearGradient>
<radialGradient id="glowW"><stop offset="0" stop-color="#d9a066" stop-opacity=".20"/><stop offset="1" stop-color="#d9a066" stop-opacity="0"/></radialGradient>
<radialGradient id="glowC"><stop offset="0" stop-color="#e9e0d0" stop-opacity=".11"/><stop offset="1" stop-color="#e9e0d0" stop-opacity="0"/></radialGradient>
<radialGradient id="glowL"><stop offset="0" stop-color="#fff6e0" stop-opacity=".75"/><stop offset="1" stop-color="#fff6e0" stop-opacity="0"/></radialGradient>
<clipPath id="cH"><rect width="{W}" height="{GRAD_Y0}"/></clipPath>
<clipPath id="cM"><rect y="{GRAD_Y1}" width="{W}" height="{DARK2_Y0 - GRAD_Y1}"/></clipPath>
<clipPath id="cF"><rect y="{DARK2_Y1}" width="{W}" height="4000"/></clipPath>
<pattern id="gd" width="48" height="48" patternUnits="userSpaceOnUse">
 <path d="M48 0H0V48" fill="none" stroke="#e9e0d0" stroke-opacity=".045"/></pattern>
<pattern id="gl" width="48" height="48" patternUnits="userSpaceOnUse">
 <path d="M48 0H0V48" fill="none" stroke="#1d1915" stroke-opacity=".05"/></pattern>
</defs>""")

# backgrounds
add(f'<rect width="{W}" height="{GRAD_Y0}" fill="{INK}"/>')
add(f'<rect y="{GRAD_Y0}" width="{W}" height="{GRAD_Y1 - GRAD_Y0}" fill="url(#g1)"/>')
add(f'<rect y="{GRAD_Y1}" width="{W}" height="{DARK2_Y0 - GRAD_Y1}" fill="{CREAM}"/>')
add(f'<rect y="{DARK2_Y0}" width="{W}" height="{DARK2_Y1 - DARK2_Y0}" fill="url(#g2)"/>')
add(f'<rect y="{DARK2_Y1}" width="{W}" height="{H - DARK2_Y1}" fill="{INK}"/>')
add(f'<rect width="{W}" height="{GRAD_Y0 + 60}" fill="url(#gd)"/>')
add(f'<rect y="{GRAD_Y1 - 40}" width="{W}" height="{DARK2_Y0 - GRAD_Y1 + 80}" fill="url(#gl)"/>')
add(f'<rect y="{DARK2_Y1 - 60}" width="{W}" height="{H - DARK2_Y1 + 60}" fill="url(#gd)"/>')
# blueprint rails, light over dark and dark over light
add(f'<path d="M60 0V{GRAD_Y0 + 80}M1140 0V{GRAD_Y0 + 80}" stroke="{LIGHT}" stroke-opacity=".2" stroke-dasharray="3 5" fill="none"/>')
add(f'<path d="M60 {GRAD_Y1}V{DARK2_Y0}M1140 {GRAD_Y1}V{DARK2_Y0}" stroke="{INK}" stroke-opacity=".22" stroke-dasharray="3 5" fill="none"/>')
add(f'<path d="M60 {DARK2_Y1}V{H}M1140 {DARK2_Y1}V{H}" stroke="{LIGHT}" stroke-opacity=".2" stroke-dasharray="3 5" fill="none"/>')

# ---- drifting light (slow warm folds, like the site's background; it settles after about 80 s)
add('<g clip-path="url(#cH)"><g class="dA"><ellipse cx="380" cy="150" rx="520" ry="250" fill="url(#glowW)"/></g>'
    '<g class="dB"><ellipse cx="980" cy="330" rx="430" ry="210" fill="url(#glowC)"/></g></g>')
add('<g clip-path="url(#cM)"><g class="dC"><ellipse cx="860" cy="1010" rx="560" ry="300" fill="url(#glowL)"/></g>'
    '<g class="dA"><ellipse cx="260" cy="1330" rx="480" ry="260" fill="url(#glowL)"/></g></g>')
add('<g clip-path="url(#cF)"><g class="dB"><ellipse cx="720" cy="1930" rx="540" ry="260" fill="url(#glowW)"/></g>'
    '<g class="dC"><ellipse cx="200" cy="2180" rx="460" ry="220" fill="url(#glowC)"/></g></g>')

# ---- header (dark)
add(rise(0.0))
text(LX, 56, "00 — PROFILE", 13, LIGHT_MUTED, MONO, spacing=1.6)
text(RX, 56, "MUMBAI, INDIA", 13, LIGHT_MUTED, MONO, "end", 1.6)
add("</g>")
add(rise(0.15))
text(LX, 168, "Ashis Wadhwani", 84, LIGHT, SERIF, spacing=-1)
add("</g>")
add(rise(0.3))
text(LX, 214, "Software developer. Cloud, DevOps and platform engineering.", 26, LIGHT_MUTED)
add("</g>")

# ---- the globe: the site's dot globe (same land mask, same tilt and turn speed), drawn as frames
land = json.load(open(os.path.join(os.path.dirname(__file__), "land.json")))


def is_land(lat, lon):
    j = int((90 - lat) / 180 * land["h"])
    i = int((lon + 180) / 360 * land["w"]) % land["w"]
    if j < 0 or j >= land["h"]:
        return False
    return (int(land["rows"][j][i >> 2], 16) >> (3 - (i & 3))) & 1 == 1


GN = 2400
gold = math.pi * (3 - math.sqrt(5))
dots = []
for k in range(GN):
    yy = 1 - 2 * (k + .5) / GN
    la = math.degrees(math.asin(yy))
    lo = (math.degrees(gold * k) % 360 + 540) % 360 - 180
    if is_land(la, lo):
        dots.append((math.radians(la), math.radians(lo)))
MUM = (math.radians(19.07), math.radians(72.87))
TILT = -0.38
GCX, GCY, GR = 1008, 164, 88


def project(la, lo, rot):
    cl = math.cos(la)
    X, Y, Z = cl * math.sin(lo + rot), math.sin(la), cl * math.cos(lo + rot)
    return X, Y * math.cos(TILT) - Z * math.sin(TILT), Y * math.sin(TILT) + Z * math.cos(TILT)


add(rise(0.6))
add(f'<circle cx="{GCX}" cy="{GCY}" r="{GR}" fill="none" stroke="{LIGHT}" stroke-opacity=".18"/>')
for f in range(FRAMES):
    rot = -MUM[1] - 0.6 + 2 * math.pi * f / FRAMES
    layers = [[], [], []]
    for la, lo in dots:
        X, Y, Z = project(la, lo, rot)
        if Z <= 0.03:
            continue
        layers[0 if Z < .33 else 1 if Z < .66 else 2].append(f"M{GCX + X * GR:.1f} {GCY - Y * GR:.1f}h0")
    add(f'<g class="gf gf{f}" style="--d:{f * TURN_S / FRAMES:.2f}s">')
    for d, (w_, op) in zip(layers, [(1.5, .35), (2.0, .6), (2.6, .9)]):
        add(f'<path d="{"".join(d)}" stroke="{LIGHT}" stroke-opacity="{op}" stroke-width="{w_}" stroke-linecap="round" fill="none"/>')
    mx, my, mz = project(MUM[0], MUM[1], rot)
    if mz > 0:
        add(f'<circle cx="{GCX + mx * GR:.1f}" cy="{GCY - my * GR:.1f}" r="3.4" fill="#e5645a"/>'
            f'<circle cx="{GCX + mx * GR:.1f}" cy="{GCY - my * GR:.1f}" r="7" fill="none" stroke="#e5645a" stroke-opacity=".55"/>')
    add("</g>")
add("</g>")

brief = ("I'm a software developer at BizDateUp Technologies. I run the company's AWS and on-premise "
         "infrastructure, and I write the Python and TypeScript services that sit on top of it. "
         "Outside work I build my own projects and look after a small server at home called escanor.")
add(rise(0.5))
for i, line in enumerate(textwrap.wrap(brief, 112, break_on_hyphens=False)):
    text(LX, 276 + i * 31, line, 20, "#cfc6b4")
add("</g>")

# hero spec columns
specs = [("NOW", "Software Developer 1", "BizDateUp Technologies"),
         ("BASED", "Mumbai, India", "open to remote"),
         ("RUNS", "AWS in Terraform", "keyless CI/CD"),
         ("ESCANOR", "A home server", "no public inbound ports")]
add(rise(0.7))
for i, (k, v, sub) in enumerate(specs):
    x = LX + i * 262
    add(f'<path d="M{x - 14} 362V412" stroke="{LIGHT}" stroke-opacity=".2"/>' if i else "")
    text(x, 370, k, 11, LIGHT_DIM, MONO, spacing=1.6)
    text(x, 394, v, 15, LIGHT, MONO)
    text(x, 412, sub, 12, LIGHT_DIM, MONO)
add("</g>")

# ---- 01 details (cream)
y = 640
label(y, 1, "DETAILS", False)
items = [("BASED IN", "Mumbai, India", "Open to on-site, hybrid or remote"),
         ("ROLE", "Software Developer 1", "BizDateUp Technologies, since May 2026"),
         ("SITE", "ashiswadhwani.in", "Case studies, the lab and a blog"),
         ("EMAIL", "hello@ashiswadhwani.in", "Replies come to my inbox"),
         ("LINKEDIN", "ashis-wadhwani-", "linkedin.com/in/ashis-wadhwani-"),
         ("GITHUB", "@ashis05", "You are here")]
add(rise(0.9))
for i, (k, v, sub) in enumerate(items):
    cx = LX + (i % 3) * 354
    cy = y + 78 + (i // 3) * 92
    add(f'<rect x="{cx - 14}" y="{cy - 22}" width="338" height="80" rx="8" fill="{CARD}" fill-opacity=".7" stroke="{INK}" stroke-opacity=".1"/>')
    if k == "ROLE":  # highlighter behind the role, like the site
        add(f'<rect class="sweep" style="--d:{1.6 * TS:.2f}s" x="{cx - 3}" y="{cy + 7}" width="{len(v) * 10.2 + 6:.0f}" height="23" rx="2" fill="#f2dc7a" fill-opacity=".6"/>')
    text(cx, cy - 2, k, 11, MUTED, MONO, spacing=1.6)
    text(cx, cy + 24, v, 21, INK)
    text(cx, cy + 46, sub, 12, MUTED, MONO)
add("</g>")

# ---- 02 tools and skills
y = 900
label(y, 2, "TOOLS AND SKILLS", False)
groups = [("Cloud and infrastructure", ["AWS", "Terraform", "Docker", "Linux", "Cloudflare Tunnel", "Tailscale"], []),
          ("CI/CD", ["GitHub Actions", "OIDC", "Keyless deploys"], []),
          ("Monitoring", ["Prometheus", "Grafana", "Loki", "Alertmanager"], []),
          ("Languages", ["Python", "TypeScript", "JavaScript", "SQL", "Bash"], ["Java", "C", "C++", "C#"])]
add(rise(1.0))
for gi, (name, chips, dim) in enumerate(groups):
    gy = y + 76 + gi * 56
    text(LX, gy + 5, name.upper(), 11, MUTED, MONO, spacing=1.4)
    x = 330
    for c in chips + dim:
        w = len(c) * 7.9 + 22
        faint = c in dim
        add(f'<rect x="{x:.0f}" y="{gy - 17}" width="{w:.0f}" height="30" rx="6" fill="{CARD}" '
            f'fill-opacity="{.35 if faint else .85}" stroke="{INK}" stroke-opacity="{.08 if faint else .14}"/>')
        text(f"{x + w / 2:.0f}", gy + 3, c, 13, MUTED if faint else INK, MONO, "middle")
        x += w + 10
add("</g>")
add(rise(1.2))
text(LX, y + 76 + 4 * 56 + 6, "WHAT I DO", 11, MUTED, MONO, spacing=1.4)
text(330, y + 76 + 4 * 56 + 10, "Infrastructure as code, least-privilege access, monitoring and alerting,", 18, INK)
text(330, y + 76 + 4 * 56 + 36, "backup restore drills, runbooks and backend services.", 18, INK)
add("</g>")

# ---- 03 things I've built
y = 1270
label(y, 3, "THINGS I'VE BUILT", False)
built = [("P1 · 2026", "Vulcan", "An AI fitness app that turns a photo of a meal into a calorie entry."),
         ("P2 · 2026", "Text-to-CAD", "Describe a part in plain English and get exact solid geometry."),
         ("P3 · 2026", "Manga Translator", "A Chrome extension that translates manga pages in place.")]
add(rise(1.3))
for i, (k, name, desc) in enumerate(built):
    cx = LX + i * 354
    cy = y + 62
    add(f'<rect x="{cx - 14}" y="{cy}" width="338" height="150" rx="8" fill="{CARD}" fill-opacity=".7" stroke="{INK}" stroke-opacity=".1"/>')
    text(cx, cy + 30, k, 11, MUTED, MONO, spacing=1.6)
    text(cx, cy + 66, name, 28, INK)
    for j, line in enumerate(textwrap.wrap(desc, 36)):
        text(cx, cy + 96 + j * 20, line, 14, MUTED)
add("</g>")

# ---- 04 github (dark)
y = 1700
label(y, 4, "GITHUB · LAST 12 MONTHS", True)
add(rise(1.4))
text(LX, y + 100, f"{year_total:,}", 52, LIGHT)
text(LX + 176, y + 100, f"{active_days}", 52, LIGHT)
text(LX, y + 126, "contributions", 13, LIGHT_MUTED, MONO, spacing=.6)
text(LX + 176, y + 126, "active days", 13, LIGHT_MUTED, MONO, spacing=.6)
add("</g>")

CELL, GAP = 16, 3
STEP = CELL + GAP
gx, gy0 = LX, y + 176
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
    if m != last_m and wi < len(weeks) - 2:
        text(gx + wi * STEP, gy0 - 10, m, 11, LIGHT_DIM, MONO, spacing=.8)
    last_m = m
add("</g>")
for wi, w in enumerate(weeks):
    for di, d in enumerate(w["contributionDays"]):
        delay = (1.7 + wi * 0.028 + di * 0.006) * TS
        add(f'<rect class="cell" style="--d:{delay:.2f}s" x="{gx + wi * STEP}" y="{gy0 + di * STEP}" '
            f'width="{CELL}" height="{CELL}" rx="3" fill="{COLORS[level(d["contributionCount"])]}">'
            f'<title>{d["date"]}: {d["contributionCount"]}</title></rect>')

# trophies
ty = gy0 + 7 * STEP + 40
add(rise(3.2))
text(LX, ty, "TROPHIES", 11, LIGHT_DIM, MONO, spacing=1.6)
add("</g>")
METRICS = [("Contributions", lifetime, (1, 100, 500, 1000)),
           ("Longest streak, days", streak, (1, 5, 14, 30)),
           ("Best day", best_day, (1, 10, 30, 60)),
           ("Active days, 12 mo", active_days, (1, 50, 120, 250)),
           ("Followers", followers, (1, 10, 50, 200)),
           ("Years on GitHub", age, (1, 3, 6, 10))]
TONE = {"-": "#4a443b", "C": "#8a7f6e", "B": "#b9a47a", "A": "#d6bf86", "S": "#8fdca6"}


def rank(v, th):
    r = "-"
    for n, t in zip("CBAS", th):
        if v >= t:
            r = n
    return r


CW, CG = 162, 12
for i, (title, v, th) in enumerate(METRICS):
    r = rank(v, th)
    c = TONE[r]
    x = LX + i * (CW + CG)
    add(f'<g transform="translate({x} {ty + 16})"><g class="rise" style="--d:{(3.3 + i * 0.12) * TS:.2f}s">')
    add(f'<rect width="{CW}" height="150" rx="8" fill="#26211c" stroke="{LIGHT}" stroke-opacity=".12"/>')
    add(f'<g transform="translate({CW / 2 - 22} 12)" fill="none" stroke="{c}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">'
        f'<path d="M10 4H34V20C34 28 28 33 22 33C16 33 10 28 10 20Z" fill="{c}" fill-opacity=".18"/>'
        '<path d="M10 8H4C4 16 7 19 11 20M34 8H40C40 16 37 19 33 20M22 33V40M14 44H30"/></g>')
    text(CW / 2, 84, f"{v:,}", 26, LIGHT, SERIF, "middle")
    text(CW / 2, 106, title, 12, LIGHT_MUTED, MONO, "middle")
    text(CW / 2, 132, "NOT YET" if r == "-" else f"RANK {r}", 12, c, MONO, "middle", 1.4)
    add("</g></g>")

# closing line
fy = ty + 16 + 150 + 56
add(rise(4.2))
add(f'<path d="M60 {fy - 30}H1140" stroke="{LIGHT}" stroke-opacity=".22" fill="none"/>')
text(LX, fy, "ashiswadhwani.in  ·  hello@ashiswadhwani.in  ·  linkedin.com/in/ashis-wadhwani-", 13, LIGHT_MUTED, MONO, spacing=.4)
text(RX, fy, "refreshed daily", 12, LIGHT_DIM, MONO, "end", 1.2)
add("</g>")

add("</svg>")
svg = "\n".join(p for p in out if p)
# the canvas height follows the content, so nothing is cut off or left empty
final_h = fy + 60
svg = svg.replace(f'viewBox="0 0 {W} {H}"', f'viewBox="0 0 {W} {final_h}"', 1)
svg = svg.replace(f'<rect y="{DARK2_Y1}" width="{W}" height="{H - DARK2_Y1}"', f'<rect y="{DARK2_Y1}" width="{W}" height="{final_h - DARK2_Y1}"')
svg = svg.replace(f'<rect y="{DARK2_Y1 - 60}" width="{W}" height="{H - DARK2_Y1 + 60}"', f'<rect y="{DARK2_Y1 - 60}" width="{W}" height="{final_h - DARK2_Y1 + 60}"')
svg = svg.replace(f'M60 {DARK2_Y1}V{H}M1140 {DARK2_Y1}V{H}', f'M60 {DARK2_Y1}V{final_h}M1140 {DARK2_Y1}V{final_h}')
with open(os.path.join(os.path.dirname(__file__), "..", "profile.svg"), "w") as f:
    f.write(svg + "\n")
print(f"profile.svg: {W}x{final_h}, {year_total} contributions, {active_days} active days, "
      f"lifetime {lifetime}, streak {streak}, best day {best_day}, followers {followers}, years {age}")
