#!/usr/bin/env python3
"""
Render the profile README's cards as animated SVGs into cards/.

Design: nocturnal ink + mint signal (matched to Pulkit's portfolio / prior
profile redesign). Technique follows Avi Vashishta's animated SVG card system:
standalone SVGs shown through <img>, inline CSS keyframes + SMIL, fonts as
base64 WOFF data URIs, staggered top-to-bottom entrance, prefers-reduced-motion
off, STATIC=1 end-state mode.

Live contribution numbers come from data/contributions.json
(fetch_contributions.py). Hand-set achievement figures below are taken from
the portfolio / LinkedIn / existing README — do not invent new counts.

Run by .github/workflows/update-profile-art.yml after fetch_contributions.py.
"""
import base64
import datetime
import json
import os
import re
from html import escape

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
DATA = os.path.join(ROOT, "data", "contributions.json")
OUT = os.path.join(ROOT, "cards")
FONTS = os.path.join(ROOT, "fonts")

# ---- hand-set achievements (confirm before treating as final) ---------------
# Sources: LinkedIn total experience; portfolio HSBC write-up; existing README.
YEARS = "2+"          # LinkedIn ~2y6m — confirm framing
ENVIRONMENTS = "40+"  # observability dashboard — confirm still accurate
DEFECT_CUT = "75%"    # fewer recurring ops defects — confirm still accurate
LEETCODE = "350+"     # existing README Marks row — confirm if grown

# ---- brand tokens (ink / mint) ---------------------------------------------
INK = "#0B0F14"
SLATE = "#121821"
SLATE_DEEP = "#0E141C"
MIST = "#8B95A5"
PAPER = "#E9EEF5"
PAPER_SOFT = "#A8B2C1"
SIGNAL = "#5EEAD4"
SIGNAL_DIM = "#2A9B8A"
SIGNAL_DEEP = "#134E4A"
WARM = "#E8C07A"
RULE = "#1C2533"
W = 880  # full card width ≈ GitHub README column at 100%

SERIF = "'Instrument Serif', Georgia, serif"
SANS = "Geist, system-ui, -apple-system, sans-serif"
MONO = "'Geist Mono', ui-monospace, SFMono-Regular, Menlo, monospace"

FONT_FILES = {
    "serif": ("Instrument Serif", "normal", 400, "serif-400.woff"),
    "serif-i": ("Instrument Serif", "italic", 400, "serif-italic.woff"),
    "sans": ("Geist", "normal", 400, "geist-400.woff"),
    "sans-b": ("Geist", "normal", 600, "geist-600.woff"),
    "mono": ("Geist Mono", "normal", 400, "geistmono-400.woff"),
}

BASE_CSS = """
@keyframes rise{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}
@keyframes fade{from{opacity:0}to{opacity:1}}
@keyframes grow{from{transform:scaleY(0)}to{transform:scaleY(1)}}
@keyframes pop{0%{opacity:0;transform:scale(.3)}70%{opacity:1;transform:scale(1.15)}100%{opacity:1;transform:none}}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}
@keyframes nudge{0%,100%{transform:none}50%{transform:translateX(4px)}}
@keyframes nudgeup{0%,100%{transform:none}50%{transform:translate(3px,-3px)}}
@keyframes tilein{0%{opacity:0;transform:translateY(90px) scale(.6) rotate(-9deg)}55%{opacity:1;transform:translateY(-10px) scale(1.05) rotate(2deg)}75%{transform:translateY(3px) scale(.98) rotate(-.8deg)}90%{transform:translateY(-1px) scale(1.01) rotate(.2deg)}100%{opacity:1;transform:none}}
@keyframes slidein{from{opacity:0;transform:translateX(-26px)}to{opacity:1;transform:none}}
@keyframes arrowin{0%{opacity:0;transform:translateX(-30px)}60%{opacity:1;transform:translateX(6px)}100%{opacity:1;transform:none}}
@keyframes roll{from{transform:translateY(60px)}to{transform:none}}
@keyframes sheen{0%{transform:translateX(-260px) skewX(-20deg)}22%,100%{transform:translateX(420px) skewX(-20deg)}}
@keyframes ring{0%{opacity:.7;transform:scale(.2)}100%{opacity:0;transform:scale(2.4)}}
@keyframes scan{0%{transform:translateY(-40px)}100%{transform:translateY(460px)}}
.r{opacity:0;animation:rise .8s cubic-bezier(.2,.7,.2,1) both;transform-box:fill-box}
.f{opacity:0;animation:fade .9s ease-out both}
.g{transform-box:fill-box;transform-origin:bottom;transform:scaleY(0);animation:grow .8s cubic-bezier(.2,.7,.2,1) both}
.p{opacity:0;transform-box:fill-box;transform-origin:center;animation:pop .4s ease-out both}
.live{animation:pulse 1.6s ease-in-out infinite}
.n{transform-box:fill-box;animation:nudge 1.8s ease-in-out infinite}
.nu{transform-box:fill-box;animation:nudgeup 1.8s ease-in-out infinite}
.ti{opacity:0;transform-box:fill-box;transform-origin:50% 60%;animation:tilein 1.1s cubic-bezier(.2,.8,.2,1) both}
.sl{opacity:0;transform-box:fill-box;animation:slidein .6s cubic-bezier(.2,.7,.2,1) both}
.ai{opacity:0;transform-box:fill-box;animation:arrowin .7s cubic-bezier(.2,.7,.2,1) both}
.ro{transform-box:fill-box;animation:roll .8s cubic-bezier(.15,.8,.2,1) both}
.sh{animation:sheen 5s ease-in-out infinite}
.rg{opacity:0;transform-box:fill-box;transform-origin:center;animation:ring 1s ease-out both}
.sc{animation:scan 9s linear infinite}
@media (prefers-reduced-motion: reduce){.r,.f,.g,.p,.live,.n,.nu,.ti,.sl,.ai,.ro,.rg,.sc{animation:none!important;opacity:1!important;transform:none!important}.sh,.rg{display:none}}
"""


def font_face(keys):
    out = []
    for k in keys:
        fam, style, weight, fn = FONT_FILES[k]
        b64 = base64.b64encode(open(os.path.join(FONTS, fn), "rb").read()).decode()
        out.append(
            f"@font-face{{font-family:'{fam}';font-style:{style};font-weight:{weight};"
            f"src:url(data:font/woff;base64,{b64}) format('woff')}}"
        )
    return "".join(out)


GAP = 12
BOTTOM = 12
COL = W / 3


def svg(w, h, body, fonts, label, extra_css="", left=0, right=0, bottom=BOTTOM):
    """Card of w x h drawn at x=left inside a transparent canvas, padded so rows tile."""
    if left:
        body = f'<g transform="translate({left:.3f} 0)">{body}</g>'
    w, h = w + left + right, h + bottom
    css = font_face(fonts) + BASE_CSS + extra_css
    if os.environ.get("STATIC"):
        css += (
            ".r,.f,.g,.p,.live,.n,.nu,.ti,.sl,.ai,.ro,.sc{animation:none!important;"
            "opacity:1!important;transform:none!important}.sh,.rg{display:none}"
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.3f}" height="{h}" '
        f'viewBox="0 0 {w:.3f} {h}" role="img" aria-label="{escape(label)}">'
        f"<title>{escape(label)}</title><style>{css}</style>{body}</svg>"
    )


def write(name, content):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    with open(path, "w") as f:
        f.write(content)
    print(f"wrote cards/{name} ({len(content) // 1024} KB)")


def d(s):
    return f'style="animation-delay:{s:.2f}s"'


def wrap(text, n):
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > n:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    return lines + [line] if line else lines


def text_lines(x, y, lines, lh, attrs):
    return "".join(
        f'<text x="{x}" y="{y + i * lh}" {attrs}>{escape(l)}</text>' for i, l in enumerate(lines)
    )


# ---- 1 · hero -----------------------------------------------------------------
def hero():
    h = 420
    # Decorative mint grid on the right (no portrait asset required)
    cells = []
    for col in range(8):
        for row in range(10):
            delay = 0.35 + col * 0.05 + row * 0.03
            opac = 0.08 + ((col * 3 + row * 5) % 7) * 0.04
            fill = SIGNAL if (col + row) % 5 == 0 else SIGNAL_DIM
            cells.append(
                f'<rect class="p" style="animation-delay:{delay:.2f}s" '
                f'x="{540 + col * 34}" y="{70 + row * 28}" width="22" height="18" rx="3" '
                f'fill="{fill}" fill-opacity="{opac:.2f}"/>'
            )
    body = f"""
<defs>
  <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
    <stop offset="0%" stop-color="{INK}"/><stop offset="55%" stop-color="{SLATE}"/>
    <stop offset="100%" stop-color="{SLATE_DEEP}"/>
  </linearGradient>
  <radialGradient id="glow" cx="78%" cy="28%" r="42%">
    <stop offset="0%" stop-color="{SIGNAL}" stop-opacity="0.28"/>
    <stop offset="55%" stop-color="{SIGNAL_DIM}" stop-opacity="0.08"/>
    <stop offset="100%" stop-color="{INK}" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="shine" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="600" y2="0">
    <stop offset="0" stop-color="{PAPER}"/><stop offset=".42" stop-color="{PAPER}"/>
    <stop offset=".5" stop-color="{SIGNAL}"/><stop offset=".58" stop-color="{PAPER}"/>
    <stop offset="1" stop-color="{PAPER}"/>
    <animateTransform attributeName="gradientTransform" type="translate" values="-600 0;600 0;600 0"
      keyTimes="0;.45;1" dur="7s" begin="1.6s" repeatCount="indefinite"/>
  </linearGradient>
  <linearGradient id="scan" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" stop-color="{SIGNAL}" stop-opacity="0"/>
    <stop offset="50%" stop-color="{SIGNAL}" stop-opacity="0.16"/>
    <stop offset="100%" stop-color="{SIGNAL}" stop-opacity="0"/>
  </linearGradient>
  <clipPath id="frame"><rect width="{W}" height="{h}" rx="14"/></clipPath>
</defs>
<g clip-path="url(#frame)">
  <rect width="{W}" height="{h}" rx="14" fill="url(#bg)"/>
  <rect width="{W}" height="{h}" fill="url(#glow)"/>
  <rect class="sc" x="0" y="0" width="{W}" height="48" fill="url(#scan)" opacity="0.7"/>
  <g class="f" {d(0)}>
    <rect class="live" x="48" y="49" width="8" height="8" rx="2" fill="{SIGNAL}"/>
    <text x="66" y="57" font-family="{MONO}" font-size="12" letter-spacing="1.2" fill="{MIST}">SOFTWARE ENGINEER  ·  HSBC  ·  PUNE</text>
  </g>
  <text class="r" {d(0.15)} x="44" y="168" font-family="{SERIF}" font-size="72" letter-spacing="-1.5" fill="{PAPER}">Pulkit</text>
  <text class="r" {d(0.3)} x="44" y="248" font-family="{SERIF}" font-style="italic" font-size="72" letter-spacing="-1.5" fill="url(#shine)">Giddu</text>
  <g class="r" {d(0.55)}>
    {text_lines(48, 300, ["Payments at HSBC. Products of my own —", "currently building Wynklo."], 26, f'font-family="{SANS}" font-size="17" fill="{PAPER_SOFT}"')}
  </g>
  <g class="f" {d(0.8)}>
    <text x="48" y="380" font-family="{MONO}" font-size="13" fill="{PAPER}">portfolio</text>
    <text class="nu" x="126" y="380" font-family="{MONO}" font-size="13" fill="{SIGNAL}">&#8599;</text>
  </g>
  {''.join(cells)}
</g>
"""
    write(
        "hero.svg",
        svg(
            W,
            h,
            body,
            ["serif", "serif-i", "sans", "mono"],
            "Pulkit Giddu. Software engineer at HSBC. Payments by day, products by choice.",
        ),
    )


# ---- 2 · world / achievement tiles -------------------------------------------
TILE_W, TILE_H = 880 / 3 - 8, 210


def count_up(num, word, x, y, attrs, begin, dur=1.1, frames=18):
    """Number counts up from 0 with SMIL <set> frames (works inside <img>)."""
    m = re.match(r"([\d.]+)(.*)", num)
    val, suf = float(m.group(1)), m.group(2)
    dec = len(m.group(1).split(".")[1]) if "." in m.group(1) else 0
    tail = f' <tspan font-style="italic">{escape(word)}</tspan>'
    if os.environ.get("STATIC"):
        return f'<text x="{x}" y="{y}" {attrs}>{escape(num)}{tail}</text>'
    out = []
    for i in range(frames + 1):
        e = 1 - (1 - i / frames) ** 3
        txt = num if i == frames else f"{val * e:.{dec}f}{suf}"
        on = begin + dur * i / frames
        off = (
            ""
            if i == frames
            else f'<set attributeName="opacity" to="0" begin="{begin + dur * (i + 1) / frames:.3f}s"/>'
        )
        out.append(
            f'<text x="{x}" y="{y}" {attrs} opacity="0">{escape(txt)}{tail}'
            f'<set attributeName="opacity" to="1" begin="{on:.3f}s"/>{off}</text>'
        )
    return "".join(out)


def tile(name, label, color, on, num, word, blurb, delay, pos):
    lines = wrap(blurb, 34)
    blurb_svg = "".join(
        f'<text class="r" {d(delay + 0.75 + i * 0.1)} x="24" y="{150 + i * 20}" font-family="{SANS}" '
        f'font-size="14" fill="{on}" opacity=".92">{escape(l)}</text>'
        for i, l in enumerate(lines)
    )
    body = f"""
<defs>
  <clipPath id="card"><rect width="{TILE_W}" height="{TILE_H}" rx="14"/></clipPath>
  <clipPath id="slot"><rect x="0" y="62" width="{TILE_W}" height="62"/></clipPath>
  <linearGradient id="gl" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>
    <stop offset=".5" stop-color="#fff" stop-opacity=".22"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
</defs>
<g class="ti" {d(delay)}>
  <g clip-path="url(#card)">
    <rect width="{TILE_W}" height="{TILE_H}" fill="{color}"/>
    <circle class="rg" {d(delay + 0.5)} cx="{TILE_W - 40}" cy="{TILE_H - 40}" r="60" fill="none" stroke="{on}" stroke-opacity=".45" stroke-width="2"/>
    <rect class="sh" style="animation-delay:{delay + 1.4:.2f}s" x="0" y="-20" width="90" height="{TILE_H + 40}" fill="url(#gl)" transform="translate(-260 0)"/>
  </g>
  <text class="sl" {d(delay + 0.35)} x="24" y="38" font-family="{MONO}" font-size="12" letter-spacing="1.2" fill="{on}">{label}</text>
  <g class="ai" {d(delay + 0.5)}><text class="n" style="animation-delay:{delay + 1.3:.2f}s" x="250" y="38" font-family="{MONO}" font-size="14" fill="{on}">&#8594;</text></g>
  <g clip-path="url(#slot)"><g class="ro" {d(delay + 0.45)}>
    {count_up(num, word, 22, 112, f'font-family="{SERIF}" font-size="44" fill="{on}"', delay + 0.45)}
  </g></g>
  {blurb_svg}
</g>
"""
    write(
        f"{name}.svg",
        svg(
            TILE_W,
            TILE_H,
            body,
            ["serif", "serif-i", "sans", "mono"],
            f"{label}: {num} {word}. {blurb}",
            left=4 * pos,
            right=8 - 4 * pos,
        ),
    )


# ---- 3 · activity (monthly bars) ---------------------------------------------
def activity(data):
    h = 340
    monthly = data["monthly"][-12:]
    best = max(monthly[:-1] or monthly, key=lambda m: m["total"])
    top = max(best["total"], 1)
    x0, x1, base, maxh, gap = 40, 600, 292, 140, 10
    bw = (x1 - x0 - gap * (len(monthly) - 1)) / max(len(monthly), 1)
    bars = []
    for i, m in enumerate(monthly):
        partial = i == len(monthly) - 1
        is_best = m is best
        bh = max(4, round(m["total"] / top * maxh)) if m["total"] else 4
        x = x0 + i * (bw + gap)
        fill = SIGNAL if is_best else (RULE if partial else PAPER_SOFT)
        if not is_best and not partial:
            fill = "#3A4556"
        label = datetime.date.fromisoformat(m["month"] + "-01").strftime("%b")
        bars.append(
            f'<rect class="g" style="animation-delay:{2.2 + i * 0.07:.2f}s" x="{x:.1f}" y="{base - bh}" '
            f'width="{bw:.1f}" height="{bh}" rx="4" fill="{fill}"><title>{label}: {m["total"]:,}</title></rect>'
            f'<text class="f" style="animation-delay:{2.2 + i * 0.07:.2f}s" x="{x + bw / 2:.1f}" y="{base + 22}" '
            f'text-anchor="middle" font-family="{MONO}" font-size="11" fill="{MIST}">{label}</text>'
        )
        if is_best:
            bars.append(
                f'<text class="p" style="animation-delay:3.2s" x="{x + bw / 2:.1f}" y="{base - bh - 10}" '
                f'text-anchor="middle" font-family="{MONO}" font-size="11" fill="{SIGNAL}">{m["total"]:,}</text>'
            )
    cs = data["current_streak"]["length"]
    ls = data["longest_streak"]["length"]
    streak_note = "current streak, and the longest" if cs >= ls else f"current streak, longest {ls}"
    total_days = len(data["days"])
    stats = [
        (f'{cs} <tspan font-style="italic">days</tspan>', streak_note),
        (f'{data["active_days"]}<tspan fill="{MIST}"> / {total_days}</tspan>', "days with a commit"),
        (f'{data["best_day"]["count"]}', "on the busiest day"),
    ]
    side = []
    for i, (big, small) in enumerate(stats):
        y = 104 + i * 92
        side.append(
            f'<g class="r" {d(2.6 + i * 0.15)}>'
            f'<text x="650" y="{y}" font-family="{SERIF}" font-size="40" fill="{PAPER}">{big}</text>'
            f'<text x="650" y="{y + 24}" font-family="{SANS}" font-size="13" fill="{MIST}">{small}</text></g>'
        )
        if i < 2:
            side.append(f'<rect class="f" {d(2.6)} x="650" y="{y + 44}" width="190" height="1" fill="{RULE}"/>')
    body = f"""
<rect width="{W}" height="{h}" rx="14" fill="{SLATE}"/>
<text class="f" {d(1.9)} x="40" y="58" font-family="{MONO}" font-size="12" letter-spacing="1" fill="{MIST}">THE LAST 12 MONTHS ON GITHUB</text>
<text class="r" {d(2.0)} x="38" y="114" font-family="{SERIF}" font-size="48" fill="{PAPER}">{data["total_contributions"]:,} <tspan font-style="italic" fill="{SIGNAL}">contributions</tspan></text>
{''.join(bars)}
{''.join(side)}
"""
    write(
        "activity.svg",
        svg(
            W,
            h,
            body,
            ["serif", "serif-i", "sans", "mono"],
            f'{data["total_contributions"]:,} contributions in the last year, {cs}-day streak',
        ),
    )


# ---- 4 · featured project / repo cards ---------------------------------------
REPO_W, REPO_H = 880 / 3 - 8, 176

# Each entry: (slug, display name, blurb, lang/label, color, href, github_full_name|None)
# "What I'm building" — current products. Snatch Mart has no public personal repo yet
# (showcased via Wynklo); Clubmates links to the live product site.
BUILDING = [
    (
        "wynklo",
        "Wynklo",
        "Digital product studio — websites, apps, and platforms shipping now.",
        "Product",
        SIGNAL,
        "https://www.wynklo.com/",
        "Wynklo/wynklo",
    ),
    (
        "snatch-mart",
        "Snatch Mart",
        "Commerce product shipped with Wynklo — public repo TBD.",
        "Commerce",
        WARM,
        "https://www.wynklo.com/",
        None,
    ),
    (
        "clubmates",
        "Clubmates",
        "Find people for the night you already want — live product.",
        "Product",
        SIGNAL,
        "https://www.clubmates.in/",
        None,
    ),
]

# "What I built" — shipped with public GitHub footprints.
# Third card: VEat — clearest description + star among remaining public repos
# (spyprice also solid; portfolio-frontend is newer but undescribed).
BUILT = [
    (
        "bookit",
        "Bookit",
        "Booking side product — open for contributions on GitHub.",
        "Docs",
        SIGNAL,
        "https://github.com/PulkitGiddu/Book-IT",
        "PulkitGiddu/Book-IT",
    ),
    (
        "aadhaar-connect",
        "Aadhaar Connect",
        "Identity-connect build, also featured in Wynklo's work.",
        "JavaScript",
        SIGNAL,
        "https://github.com/PulkitGiddu/AadhaarConnect",
        "PulkitGiddu/AadhaarConnect",
    ),
    (
        "veat",
        "VEat",
        "A simple approach to order food in college canteens.",
        "Java",
        WARM,
        "https://github.com/PulkitGiddu/VEat",
        "PulkitGiddu/VEat",
    ),
]


def repo_card(i, slug, name, desc, lang, color, stars, delay_base):
    delay = delay_base + i * 0.12
    meta = f"{lang}  ·  ★ {stars}" if stars else f"{lang}  ·  live"
    body = f"""
<rect width="{REPO_W}" height="{REPO_H}" rx="14" fill="{SLATE}"/>
<g class="r" {d(delay)}>
  <rect x="24" y="30" width="8" height="8" rx="2" fill="{color}"/>
  <text x="40" y="39" font-family="{SANS}" font-weight="600" font-size="17" fill="{PAPER}">{escape(name)}</text>
  {text_lines(24, 72, wrap(desc, 34), 21, f'font-family="{SANS}" font-size="14" fill="{PAPER_SOFT}"')}
  <text x="24" y="{REPO_H - 24}" font-family="{MONO}" font-size="12" fill="{MIST}">{escape(meta)}</text>
</g>
"""
    write(
        f"repo-{slug}.svg",
        svg(
            REPO_W,
            REPO_H,
            body,
            ["sans", "sans-b", "mono"],
            f"{name}: {desc}",
            left=4 * i,
            right=8 - 4 * i,
        ),
    )


def section_title(slug, text, italic, theme, delay=4.4):
    # Profile README sits on GitHub's dark chrome for most users; ink cards stay dark.
    # Light theme variant uses ink text so GH light mode still reads.
    if theme == "dark":
        fg = PAPER
        italic_fill = SIGNAL
        bg = f'<rect width="{W}" height="64" fill="{INK}"/>'
    else:
        fg = INK
        italic_fill = SIGNAL_DIM
        bg = f'<rect width="{W}" height="64" fill="#ffffff"/>'
    body = (
        f"{bg}"
        f'<text class="r" {d(delay)} x="2" y="46" font-family="{SERIF}" font-size="34" fill="{fg}">{escape(text)} '
        f'<tspan font-style="italic" fill="{italic_fill}">{escape(italic)}</tspan></text>'
    )
    write(
        f"title-{slug}-{theme}.svg",
        svg(W, 64, body, ["serif", "serif-i"], f"{text} {italic}", bottom=0),
    )


# ---- 5 · mint contribution graph ---------------------------------------------
MINT = [SLATE_DEEP, "#134E4A", "#1D6B63", SIGNAL_DIM, "#3DB8A8", SIGNAL]


def level_for(c):
    return 0 if c == 0 else 1 if c <= 2 else 2 if c <= 5 else 3 if c <= 10 else 4 if c <= 20 else 5


def heatmap(data):
    days = data["days"]
    first = datetime.date.fromisoformat(days[0]["date"])
    lead = (first.weekday() + 1) % 7  # sunday = 0
    cell, step, gx, gy = 12, 15, 44, 96
    cells, months, seen = [], [], set()
    for i, day in enumerate(days):
        k = i + lead
        col, row = divmod(k, 7)
        date = datetime.date.fromisoformat(day["date"])
        if date.day <= 7 and (date.year, date.month) not in seen and row == 0:
            seen.add((date.year, date.month))
            months.append((col, date.strftime("%b")))
        c = day["count"]
        delay = 1.0 + col * 0.03 + row * 0.02
        cells.append(
            f'<rect class="p" style="animation-delay:{delay:.2f}s" x="{gx + col * step}" y="{gy + row * step}" '
            f'width="{cell}" height="{cell}" rx="3" fill="{MINT[level_for(c)]}">'
            f'<title>{day["date"]}: {c} contribution{"s" if c != 1 else ""}</title></rect>'
        )
    ncols = (len(days) + lead + 6) // 7
    right = gx + ncols * step - 3
    labels = "".join(
        f'<text x="{gx + col * step}" y="{gy + 7 * step + 16}" font-family="{MONO}" font-size="11" fill="{MIST}">{m}</text>'
        for col, m in months
        if col < ncols - 12
    )
    legend_x = right - len(MINT) * 14
    legend = "".join(
        f'<rect x="{legend_x + i * 14}" y="{gy + 7 * step + 6}" width="11" height="11" rx="2.5" fill="{c}"/>'
        for i, c in enumerate(MINT)
    )
    h = gy + 7 * step + 44
    body = f"""
<rect width="{W}" height="{h}" rx="14" fill="{SLATE}"/>
<text class="r" {d(0.8)} x="42" y="62" font-family="{SERIF}" font-size="34" fill="{PAPER}">Every day, <tspan font-style="italic" fill="{SIGNAL}">in mint</tspan></text>
<text class="f" {d(0.8)} x="{right}" y="60" text-anchor="end" font-family="{MONO}" font-size="12" letter-spacing="1" fill="{MIST}">REFRESHED DAILY</text>
{''.join(cells)}
<g class="f" {d(2.4)}>{labels}
<text x="{legend_x - 8}" y="{gy + 7 * step + 16}" text-anchor="end" font-family="{MONO}" font-size="11" fill="{MIST}">less</text>
{legend}
<text x="{legend_x + len(MINT) * 14 + 2}" y="{gy + 7 * step + 16}" font-family="{MONO}" font-size="11" fill="{MIST}">more</text></g>
"""
    write(
        "heatmap.svg",
        svg(
            W,
            h,
            body,
            ["serif", "serif-i", "mono"],
            f'Contribution graph: {data["total_contributions"]:,} contributions in the last year',
        ),
    )


def repo_stars(projects):
    stars = {}
    try:
        import requests

        for slug, _name, _desc, _lang, _color, _href, full_name in projects:
            if not full_name:
                continue
            r = requests.get(f"https://api.github.com/repos/{full_name}", timeout=10)
            if r.ok:
                stars[slug] = r.json().get("stargazers_count", 0)
    except Exception as e:
        print(f"stars unavailable: {e}")
    return stars


if __name__ == "__main__":
    data = json.load(open(DATA))
    hero()
    heatmap(data)
    activity(data)
    # Achievement tiles — linked in README to portfolio / LinkedIn
    tile(
        "years",
        "YEARS",
        SIGNAL_DEEP,
        PAPER,
        YEARS,
        "years",
        "Shipping software — HSBC, Wynklo, and earlier builds.",
        3.1,
        0,
    )
    tile(
        "scope",
        "SCOPE",
        SIGNAL_DIM,
        PAPER,
        ENVIRONMENTS,
        "envs",
        "Observability dashboard across payment environments at HSBC.",
        3.35,
        1,
    )
    tile(
        "impact",
        "IMPACT",
        "#3D3420",
        WARM,
        DEFECT_CUT,
        "fewer",
        "Recurring operational defects cut after incident triage.",
        3.6,
        2,
    )

    section_title("building", "What I'm", "building", "dark", delay=4.4)
    section_title("building", "What I'm", "building", "light", delay=4.4)
    building_stars = repo_stars(BUILDING)
    for i, (slug, name, desc, lang, color, _href, _gh) in enumerate(BUILDING):
        repo_card(i, slug, name, desc, lang, color, building_stars.get(slug), 4.6)

    section_title("built", "What I", "built", "dark", delay=5.1)
    section_title("built", "What I", "built", "light", delay=5.1)
    built_stars = repo_stars(BUILT)
    for i, (slug, name, desc, lang, color, _href, _gh) in enumerate(BUILT):
        repo_card(i, slug, name, desc, lang, color, built_stars.get(slug), 5.3)
