"""Regenerate the data cards in assets/ from live npm and GitHub data.

    python3 scripts/data_cards.py

Needs `gh` logged in (or GITHUB_TOKEN set) for the contribution calendar.
Standard library only. Writes assets/card-npm.svg, assets/card-activity.svg
and assets/card-bench.svg, and prints the README data table.
"""
import datetime as dt
import json
import os
import subprocess
import urllib.request
from collections import OrderedDict
from pathlib import Path

USER = "vishaal2002"
ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

# Validated categorical slots 1-3 (dark), surface #0F0F16; colour follows the package.
PACKAGES = [
    ("rn-rich-text-editor", "#3987e5"),
    ("react-native-board-view", "#d95926"),
    ("react-native-geocodex", "#199e70"),
]
SURFACE = "#0F0F16"
INK, INK2, MUTED = "#F4F4F5", "#D4D4D8", "#8B8B95"
GRID, BASE = "#26262F", "#3A3A44"
SANS = '-apple-system,BlinkMacSystemFont,&quot;Segoe UI&quot;,Inter,&quot;Helvetica Neue&quot;,Helvetica,Arial,sans-serif'
MONO = 'ui-monospace,SFMono-Regular,&quot;SF Mono&quot;,Menlo,Consolas,monospace'
HEAT = ["#1C1C27", "#184f95", "#256abf", "#3987e5", "#86b6ef"]  # blue ramp, dark: brighter = more


def get_json(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {"User-Agent": "profile-data-cards"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def npm_monthly(pkg, start, end):
    d = get_json(f"https://api.npmjs.org/downloads/range/{start}:{end}/{pkg}")
    months = OrderedDict()
    for day in d["downloads"]:
        months[day["day"][:7]] = months.get(day["day"][:7], 0) + day["downloads"]
    return months


def contributions():
    q = ('{ user(login:"%s"){ contributionsCollection { totalCommitContributions '
         'totalPullRequestContributions restrictedContributionsCount contributionCalendar '
         '{ totalContributions weeks { contributionDays { date contributionCount } } } } } }') % USER
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        d = get_json("https://api.github.com/graphql", json.dumps({"query": q}).encode(),
                     {"Authorization": f"bearer {token}", "User-Agent": "profile-data-cards"})
    else:
        d = json.loads(subprocess.run(["gh", "api", "graphql", "-f", f"query={q}"],
                                      capture_output=True, text=True, check=True).stdout)
    return d["data"]["user"]["contributionsCollection"]


def frame(w, h, title, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-labelledby="t"><title id="t">{title}</title>'
            f'<rect x="8" y="8" width="{w - 16}" height="{h - 16}" rx="24" fill="{SURFACE}"/>'
            f'<rect x="8.5" y="8.5" width="{w - 17}" height="{h - 17}" rx="23.5" fill="none" stroke="#FFFFFF" stroke-opacity="0.1"/>'
            f'{body}</svg>\n')


def text(x, y, s, size=14, fill=INK2, weight=400, anchor="start", font=SANS, extra=""):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{font}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}"{extra}>{s}</text>')


def col(x, y, w, h, fill, round_top):
    """Column from a baseline at y+h; 4px rounded data-end on top only."""
    if h <= 0:
        return ""
    r = min(4, h, w / 2) if round_top else 0
    return (f'<path d="M{x:.1f} {y + h:.1f}V{y + r:.1f}'
            f'{f"Q{x:.1f} {y:.1f} {x + r:.1f} {y:.1f}H{x + w - r:.1f}Q{x + w:.1f} {y:.1f} {x + w:.1f} {y + r:.1f}" if r else f"H{x + w:.1f}"}'
            f'V{y + h:.1f}Z" fill="{fill}"/>')


def hbar(x, y, w, h, fill):
    """Horizontal bar from a baseline at x; 4px rounded data-end on the right."""
    w = max(w, 3)
    r = min(4, w, h / 2)
    return (f'<path d="M{x:.1f} {y:.1f}H{x + w - r:.1f}Q{x + w:.1f} {y:.1f} {x + w:.1f} {y + r:.1f}'
            f'V{y + h - r:.1f}Q{x + w:.1f} {y + h:.1f} {x + w - r:.1f} {y + h:.1f}H{x:.1f}Z" fill="{fill}"/>')


def fmt(n):
    return f"{n:,}"


# ------------------------------------------------------------------ npm
def npm_card(today):
    end = today.isoformat()
    start = (today - dt.timedelta(days=540)).isoformat()  # npm caps a range at 18 months
    series = {p: npm_monthly(p, start, end) for p, _ in PACKAGES}
    this_month = today.strftime("%Y-%m")
    months = [m for m in next(iter(series.values())) if m != this_month]
    # start at the first month with any downloads
    while months and sum(series[p].get(months[0], 0) for p, _ in PACKAGES) == 0:
        months.pop(0)
    totals = {p: sum(series[p].values()) for p, _ in PACKAGES}
    grand = sum(totals.values())

    W, H = 1280, 420
    x0, x1, top, base = 96, 1232, 196, 356
    peak = max(sum(series[p].get(m, 0) for p, _ in PACKAGES) for m in months)
    step = 1000 if peak <= 6000 else 2000
    ymax = -(-peak // step) * step
    k = (base - top) / ymax
    slot = (x1 - x0) / len(months)
    cw = min(24, slot * 0.5)

    b = [text(40, 52, "NPM DOWNLOADS", 12, MUTED, font=MONO, extra=' letter-spacing="1.5"'),
         text(40, 112, fmt(grand), 52, INK, 800, extra=' letter-spacing="-1.5"'),
         text(40 + len(fmt(grand)) * 29 + 14, 110, f"all-time, across 3 packages · to {today:%-d %b %Y}", 15, MUTED)]
    lx = 40
    for p, c in PACKAGES:
        b.append(f'<rect x="{lx}" y="141" width="10" height="10" rx="2" fill="{c}"/>')
        label = f"{p} · {fmt(totals[p])}"
        b.append(text(lx + 18, 150.5, label, 14, INK2))
        lx += 18 + len(label) * 7.6 + 28
    for v in range(0, ymax + 1, step):
        y = base - v * k
        b.append(f'<path d="M{x0} {y:.1f}H{x1}" stroke="{BASE if v == 0 else GRID}" stroke-width="1"/>')
        b.append(text(x0 - 12, y + 4, f"{v // 1000}K" if v else "0", 12, MUTED, anchor="end", extra=' font-variant-numeric="tabular-nums"'))
    best = max(months, key=lambda m: sum(series[p].get(m, 0) for p, _ in PACKAGES))
    for i, m in enumerate(months):
        cx = x0 + slot * (i + 0.5)
        y = base
        vals = [(series[p].get(m, 0), c) for p, c in PACKAGES]
        drawn = [(v, c) for v, c in vals if v * k >= 1]
        for j, (v, c) in enumerate(drawn):
            h = v * k
            last = j == len(drawn) - 1
            gap = 0 if last else 2
            b.append(col(cx - cw / 2, y - h, cw, h - gap, c, last))
            y -= h
        mon = dt.date(int(m[:4]), int(m[5:]), 1)
        b.append(text(cx, base + 20, mon.strftime("%b"), 12, MUTED, anchor="middle"))
        if i == 0 or mon.month == 1:
            b.append(text(cx, base + 37, str(mon.year), 12, INK2, 600, anchor="middle"))
        total = sum(v for v, _ in vals)
        if m == best or m == months[-1]:
            b.append(text(cx, y - 10, fmt(total), 13, INK, 600, anchor="middle"))
    title = (f"npm downloads by month. {fmt(grand)} all-time across rn-rich-text-editor ({fmt(totals[PACKAGES[0][0]])}), "
             f"react-native-board-view ({fmt(totals[PACKAGES[1][0]])}) and react-native-geocodex ({fmt(totals[PACKAGES[2][0]])}).")
    (ASSETS / "card-npm.svg").write_text(frame(W, H, title, "".join(b)))
    return series, months, totals


# ------------------------------------------------------------ activity
def activity_card(cc):
    W, H = 640, 330
    cal = cc["contributionCalendar"]
    weeks = cal["weeks"]
    total = cal["totalContributions"]

    def level(n):
        return 0 if n == 0 else 1 if n <= 2 else 2 if n <= 5 else 3 if n <= 10 else 4

    pitch, cell, gx, gy = 10.6, 8, 36, 146
    b = [text(36, 52, "GITHUB · LAST 12 MONTHS", 12, MUTED, font=MONO, extra=' letter-spacing="1.5"'),
         text(36, 100, fmt(total), 44, INK, 800, extra=' letter-spacing="-1.2"'),
         text(36 + len(fmt(total)) * 25 + 12, 99, "contributions", 18, INK2, 600)]
    last_month = None
    for wi, wk in enumerate(weeks):
        for day in wk["contributionDays"]:
            d = dt.date.fromisoformat(day["date"])
            di = (d.weekday() + 1) % 7  # Sunday first, like GitHub
            b.append(f'<rect x="{gx + wi * pitch:.1f}" y="{gy + di * pitch:.1f}" width="{cell}" height="{cell}" rx="2" fill="{HEAT[level(day["contributionCount"])]}"/>')
        first = dt.date.fromisoformat(wk["contributionDays"][0]["date"])
        if first.month != last_month and first.day <= 7 and wi < len(weeks) - 2:
            b.append(text(gx + wi * pitch, gy - 8, first.strftime("%b"), 11, MUTED))
            last_month = first.month
    ly = gy + 7 * pitch + 22
    b.append(text(604 - 5 * 12 - 40, ly, "Less", 11, MUTED, anchor="end"))
    for i, c in enumerate(HEAT):
        b.append(f'<rect x="{604 - 5 * 12 - 32 + i * 12}" y="{ly - 8}" width="{cell}" height="{cell}" rx="2" fill="{c}"/>')
    b.append(text(604, ly, "More", 11, MUTED, anchor="end"))
    stats = [(cc["totalCommitContributions"], "commits"), (cc["totalPullRequestContributions"], "pull requests"),
             (cc["restrictedContributionsCount"], "in private repos")]
    sx = 36
    for n, label in stats:
        b.append(text(sx, 298, fmt(n), 20, INK, 700))
        b.append(text(sx + len(fmt(n)) * 12 + 6, 298, label, 14, MUTED))
        sx += len(fmt(n)) * 12 + 6 + len(label) * 6.8 + 26
    title = (f"{total} GitHub contributions in the last 12 months: {cc['totalCommitContributions']} commits, "
             f"{cc['totalPullRequestContributions']} pull requests, {cc['restrictedContributionsCount']} in private repositories.")
    (ASSETS / "card-activity.svg").write_text(frame(W, H, title, "".join(b)))


# --------------------------------------------------------------- bench
BENCH = [  # from react-native-board-view docs/benchmarks.md
    ("Janky frames, auto-scroll on a 500-card column", 45, "42–45%", 0.4, "0.4%"),
    ("Card renders per drop, 20 × 6 swimlanes", 480, "480", 4, "4"),
    ("Move sheet, tap to first frame", 450, "450 ms", 100, "100 ms"),
]
BEFORE, AFTER = "#6B6B76", "#d95926"


def bench_card():
    W, H = 640, 330
    b = [text(36, 52, "REACT-NATIVE-BOARD-VIEW · MEASURED", 12, MUTED, font=MONO, extra=' letter-spacing="1.5"'),
         text(36, 90, "Before and after", 24, INK, 700, extra=' letter-spacing="-0.4"'),
         f'<rect x="458" y="80" width="10" height="10" rx="2" fill="{BEFORE}"/>', text(474, 89.5, "before", 13, INK2),
         f'<rect x="530" y="80" width="10" height="10" rx="2" fill="{AFTER}"/>', text(546, 89.5, "after", 13, INK2)]
    y, span = 128, 470
    for label, before, bl, after, al in BENCH:
        b.append(text(36, y, label, 14, INK, 600))
        wb, wa = span, span * after / before
        b.append(hbar(36, y + 10, wb, 10, BEFORE))
        b.append(text(36 + wb + 8, y + 19, bl, 12, INK2))
        b.append(hbar(36, y + 24, wa, 10, AFTER))
        b.append(text(36 + max(wa, 3) + 8, y + 33, al, 12, INK, 700))
        y += 60
    b.append(text(36, 304, "0.5.0 on a Pixel 9 Pro emulator; 0.8.1 on a vivo V2158 phone. Release builds.", 12, MUTED))
    title = ("react-native-board-view, before and after: janky frames 42–45% to 0.4%; card renders per drop 480 to 4; "
             "Move sheet tap to first frame 450 ms to 100 ms.")
    (ASSETS / "card-bench.svg").write_text(frame(W, H, title, "".join(b)))


if __name__ == "__main__":
    today = dt.date.today()
    series, months, totals = npm_card(today)
    activity_card(contributions())
    bench_card()
    names = [p for p, _ in PACKAGES]
    print("| Month | " + " | ".join(names) + " | Total |")
    print("|---|" + "---:|" * (len(names) + 1))
    for m in months:
        vals = [series[p].get(m, 0) for p in names]
        print(f"| {dt.date(int(m[:4]), int(m[5:]), 1):%b %Y} | " + " | ".join(fmt(v) for v in vals) + f" | {fmt(sum(vals))} |")
    print(f"| **All-time to {today:%-d %b %Y}** | " + " | ".join(fmt(totals[p]) for p in names) + f" | **{fmt(sum(totals.values()))}** |")
