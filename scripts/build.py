#!/usr/bin/env python3
"""Build the profile: profile/*.svg and README.md.

    python3 scripts/build.py          # offline, from the committed snapshots in data/
    python3 scripts/build.py --live   # refresh Gerrit + contribution count first (falls back safely)

Stdlib only. Deterministic for a given data/ directory: two runs give byte-identical files.

README.md is generated, so copy edits belong in readme() below, not in the README itself.
"""

from __future__ import annotations

import json
import math
import re
import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import data as datamod  # noqa: E402
import sprites  # noqa: E402
from pixelkit import Doc, bayer, contrast, ensure_contrast, mix, notched, panel, read_text, text_w, write_text  # noqa: E402
from theme import THEMES  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / 'profile'
GLYPHS = json.loads(read_text(PROFILE / 'name-glyphs.json'))
V = 3  # cache-buster in README image URLs: bump when a design change must reach readers who cached an image

URL = dict(
    blog='https://techliker.com/',
    linkedin='https://www.linkedin.com/in/chenhaodiao/',
    gerrit='https://chromium-review.googlesource.com/q/owner:diaochenhao@gmail.com',
    gsoc='https://techliker.com/gsoc/',
    ar360='https://techliker.com/ar-panoramic-calling/',
    bike='https://techliker.com/smart-car-2021/',
    mocap='https://techliker.com/wearable-rehab-mocap/',
    skills='https://github.com/calvindiao/personal-codex-skills',
    snk='https://github.com/Platane/snk',
)

# The only motion in the page. Everything is switched off under prefers-reduced-motion and the still
# image is complete without it.
CSS = (
    '.qb{animation:qb 1.2s steps(1,end) infinite}@keyframes qb{50%{opacity:.3}}'
    '.qn{animation:qn 1s steps(1,end) infinite}@keyframes qn{50%{transform:translateX(4px)}}'
    '.qt{animation:qt 3.6s steps(1,end) infinite}@keyframes qt{0%,100%{opacity:1}50%{opacity:.35}}'
    '.qh{animation:qh 1.4s steps(1,end) infinite}@keyframes qh{50%{transform:translateY(-6px)}}'
    '@media (prefers-reduced-motion:reduce){.qb,.qn,.qt,.qh{animation:none}}'
)

SVG_OUT: dict[str, str] = {}
MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
ROUTE_MAX = 6    # stops drawn on the route banner (the newest ones)
CARD_W = 356     # project cards: two of them plus the space between fit the 720px modules (2 x 356 + ~4.5)
NB = '\u00a0'    # no-break space: binds the last words of a line so a wrapped line never ends in one orphan word
GAME_BUDGET = 58_000  # bytes for the animated mini-game (about 44,000 today); the workflow rejects any file over 60,000


def save(name, theme_key, svg):
    SVG_OUT[f'{name}-{theme_key}.svg'] = svg


def tw(s, u):
    return text_w(s) * u


def nb(s):
    """Bind the words of s together (no line break between them)."""
    return s.replace(' ', NB)


def progress(n_merged, n_open):
    """'3 merged and 1 in review'; a zero is never named."""
    return ' and '.join(p for p in (f'{n_merged} merged' if n_merged else '', f'{n_open} in review' if n_open else '') if p) \
        or 'no changes yet'


# ======================================================================================
# shared window chrome
# ======================================================================================


def window(d, t, w, h, tab=None, tab_right=None, fill=None, tab_u=2, border=None):
    """Notched, bevelled pixel window with a 4px drop shadow and an optional title bar."""
    wc, hr = (w - 4) // 4, (h - 4) // 4
    sh = d.pix(4)
    panel(sh, 1, 1, wc, hr, t['shadow'], t['shadow'])
    p = d.pix(4)
    panel(p, 0, 0, wc, hr, border or t['border'], fill or t['panel'], hi=t['bevel_hi'], lo=t['bevel_lo'])
    if tab is not None:
        rows = 8 if tab_u == 2 else 11
        ty = 13 if tab_u == 2 else 12
        p.rect(2, 1, wc - 4, 1, t['tab_bg'])
        p.rect(1, 2, wc - 2, rows - 1, t['tab_bg'])
        p.rect(1, rows + 1, wc - 2, 1, t['rule'])
        d.text(16, ty, tab, t['tab_fg'], tab_u)
        if tab_right:
            txt, col = tab_right if isinstance(tab_right, tuple) else (tab_right, t['tab_sub'])
            d.text(w - 16 - tw(txt, tab_u), ty, txt, col, tab_u)
    return wc, hr


def inset(d, t, x, y, w, h, u=2, fill=None):
    """Inset item slot (small notched frame)."""
    p = d.pix(u, x, y)
    panel(p, 0, 0, w // u, h // u, t['slot_border'], fill or t['panel_deep'])
    return p


def sprite(d, t, name, x, y, u, box=None):
    """Draw a catalogue sprite at (x, y). With box=(w, h) in pixels its bounding box is centred there."""
    rows, pal = sprites.catalogue(t)[name]
    if box:
        cols = [c for r in rows for c, ch in enumerate(r) if ch != '.']
        rws = [i for i, r in enumerate(rows) if r.strip('.')]
        x += (box[0] - (max(cols) - min(cols) + 1) * u) // 2 - min(cols) * u
        y += (box[1] - (max(rws) - min(rws) + 1) * u) // 2 - min(rws) * u
    p = d.pix(u, x, y)
    p.art(0, 0, rows, pal)
    return p


def status_label(cl):
    return 'merged' if cl['status'] == 'MERGED' else 'in review'


# ======================================================================================
# HERO: title screen
# ======================================================================================


def sky_stops(t):
    if t['name'] == 'dark':
        return [t['crust'], mix(t['crust'], t['base'], .55), t['base'], mix(t['base'], t['blue'], .10),
                mix(t['base'], t['blue'], .20)]
    return [mix(t['base'], t['blue'], .30), mix(t['base'], t['blue'], .23), mix(t['base'], t['blue'], .16),
            mix(t['base'], t['blue'], .09), mix(t['base'], t['blue'], .03)]


def title_colors(t):
    """(name, near shadow, far shadow) of the hero title. The shadow steps are the title's neighbours, so the
    name has to hold 3:1 (large text) against them as well as against the sky: in the light theme the stock
    ink is darkened just enough for that."""
    dark = t['name'] == 'dark'
    far = mix(t['blue'], t['crust'], .80) if dark else mix(t['blue'], t['base'], .62)
    near = mix(t['blue'], t['crust'], .52) if dark else mix(t['blue'], t['base'], .22)
    name = t['text'] if dark else ensure_contrast(t['text'], near, 3.4, toward='#1e2030')
    return name, near, far


def hero(t):
    W, H = 720, 360
    R = H // 4
    dark = t['name'] == 'dark'
    desc = 'Pixel-art title screen: Calvin Diao, with a small player standing on a hill. The menu reads Less clicking, More tinkering.'
    d = Doc(W, H, 'Calvin Diao: Less clicking. More tinkering.', desc, CSS)
    inside = notched(0, 0, W, H, 4)

    # ---- sky: banded gradient with narrow Bayer-dithered seams --------------------
    stops = sky_stops(t)
    seams = [10, 19, 47, 64]
    sky = d.pix(4, clip=inside)
    for r in range(0, R):
        for c in range(0, 180):
            k = 0
            for b in seams:
                if r > b + 1.5:
                    k += 1
                elif r >= b - 1.5 and bayer(c, r) < (r - (b - 1.5)) / 3.0:
                    k += 1
            sky.px(c, r, stops[k])

    # ---- celestial: stars + moon (dark) / clouds + sun (light) --------------------
    if dark:
        st = d.pix(4)
        seed = 7
        spots = []

        def rnd():
            nonlocal seed
            seed = (seed * 1103515245 + 12345) & 0x7fffffff
            return seed / 0x7fffffff
        tries = 0
        while len(spots) < 30 and tries < 4000:
            tries += 1
            c, r = int(rnd() * 176) + 2, int(rnd() * 66) + 3
            x, y = c * 4, r * 4
            if 36 <= x <= 596 and 70 <= y <= 196:
                continue  # title block
            if 36 <= x <= 520 and 204 <= y <= 296:
                continue  # menu block
            if 604 <= x <= 704 and 64 <= y <= 168:
                continue  # moon
            if 496 <= x <= 548 and 212 <= y <= 290:
                continue  # radio mast
            if any(abs(c - c2) < 6 and abs(r - r2) < 5 for c2, r2 in spots):
                continue
            spots.append((c, r))
        bright = d.pix(4)
        twink = d.pix(4)
        for i, (c, r) in enumerate(spots):
            if i % 5 == 0:
                for dc, dr in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
                    twink.px(c + dc, r + dr, t['text'])
            elif i % 3 == 0:
                bright.px(c, r, t['text'])
            else:
                st.px(c, r, t['o1'])
        d.anim(twink, 'qt')
        rows, pal = sprites.catalogue(t)['moon']
        d.pix(6, 624, 76).art(0, 0, rows, pal)
    else:
        cl = d.pix(4)
        cloud = ["..####......", ".######.##..", "############", "############"]
        for (c0, r0) in ((6, 16), (148, 38), (66, 3)):
            for rr, line in enumerate(cloud):
                for cc, ch in enumerate(line):
                    if ch == '#':
                        cl.px(c0 + cc, r0 + rr, '#ffffff' if rr < 3 else mix('#ffffff', t['blue'], .12))
        rows, pal = sprites.catalogue(t)['sun']
        d.pix(4, 640, 80).art(0, 0, rows, pal)

    # ---- hills --------------------------------------------------------------------
    def smooth(x):
        x = max(0.0, min(1.0, x))
        return x * x * (3 - 2 * x)

    far_col = t['hill_far']
    near_col = t['mantle'] if dark else mix(t['base'], t['green'], .30)
    near_hi = mix(t['green'], t['crust'], .50) if dark else mix(t['base'], t['green'], .80)
    ground = t['crust'] if dark else mix(t['base'], t['green'], .45)

    def far_top(c):
        a = 0.25 + 0.75 * smooth((c - 60) / 70)
        return 71 - round(a * (4 + 3.2 * math.sin(c / 9 + .8) + 2 * math.sin(c / 3.7)))

    def near_top(c):
        return 75 if 142 <= c <= 170 else 76 - round(2.4 * math.sin(c / 7.3 + 2.2) + 1.4 * math.sin(c / 3.1))

    far = d.pix(4, clip=inside)
    for c in range(180):
        for r in range(far_top(c), R):
            far.px(c, r, far_col)

    # a radio mast on the far hill: the network, standing in the landscape
    mc = 129
    base = far_top(mc) + 2
    mast_col = mix(far_col, t['crust'], .55) if dark else mix(far_col, t['ink'], .6)
    mast = d.pix(4)
    shape = ["..#..", ".#.#.", ".###.", ".#.#.", "#####", "#...#", "#...#", "#...#"]
    for rr, line in enumerate(shape):
        for cc, ch in enumerate(line):
            if ch == '#':
                mast.px(mc - 2 + cc, base - len(shape) + rr, mast_col)
    beacon = d.pix(4)
    beacon.px(mc, base - len(shape) - 1, t['gold'])
    beacon.px(mc, base - len(shape) - 2, t['gold'])
    d.anim(beacon, 'qb')

    near = d.pix(4, clip=inside)
    for c in range(180):
        nt = near_top(c)
        for r in range(nt, R):
            near.px(c, r, near_col)
        near.px(c, nt, near_hi)
        if (c * 7 + nt) % 11 == 0:
            near.px(c, nt - 1, near_hi)
        for r in range(nt + 4, R):
            if r > nt + 5 or bayer(c, r) < .5:
                near.px(c, r, ground)

    deco = d.pix(4, clip=inside)
    for c in range(4, 176):
        nt = near_top(c)
        if c % 9 == 4 and not (96 <= c <= 112):
            col = (t['gold'], t['text'] if dark else '#ffffff')[(c // 9) % 2]
            deco.px(c, nt - 1, col)
            deco.px(c, nt - 2, near_hi)
        if c % 13 == 2:
            deco.px(c, nt + 3, mix(ground, t['o1'], .4) if dark else mix(ground, t['green'], .35))
            deco.px(c + 1, nt + 4, mix(ground, t['o1'], .25) if dark else mix(ground, t['green'], .35))

    # ---- player -------------------------------------------------------------------
    shadow = d.pix(6)
    for cc in range(99, 111):
        shadow.px(cc, 50, mix(near_col, t['crust'], .5) if dark else mix(near_col, t['ink'], .25))
    sprite(d, t, 'player', 600, 204, 6)

    # ---- title: face + two stepped blue shadows (plain paths, no <use>) -------------
    s = 96 / 1000
    ytop = 84
    paths = []
    x = 0.0
    for g in GLYPHS['glyphs']:
        tx = 48 - 28 * s + x * s
        ty = ytop + 787 * s
        paths.append(f'<path transform="translate({tx:.3f} {ty:.3f}) scale({s} {-s})" d="{g["path"]}"/>')
        x += g['advance']
    name_svg = ''.join(paths)
    name_col, mid_sh, far_sh = title_colors(t)
    d.add(f'<g transform="translate(12 12)" fill="{far_sh}">{name_svg}</g>'
          f'<g transform="translate(6 6)" fill="{mid_sh}">{name_svg}</g>'
          f'<g fill="{name_col}">{name_svg}</g>')

    # ---- menu (the tagline) --------------------------------------------------------
    d.text(76, 214, 'LESS CLICKING.', t['sub'], 4)
    d.text(76, 258, 'MORE TINKERING.', t['gold_m'], 4)
    cur = d.pix(4, 44, 258)
    cur.text(0, 0, '▶', t['gold_m'])
    d.anim(cur, 'qn')

    # ---- frame ---------------------------------------------------------------------
    fr = d.pix(4)
    for c in range(1, 179):
        for r in (0, R - 1):
            fr.px(c, r, t['border'])
    for r in range(1, R - 1):
        for c in (0, 179):
            fr.px(c, r, t['border'])
    for c, r in ((1, 1), (178, 1), (1, R - 2), (178, R - 2)):
        fr.px(c, r, t['border'])
    save('hero', t['key'], d.render())


# ======================================================================================
# CHROMIUM: the one banner that carries the credential
# ======================================================================================


def world(t, data):
    cls = data['cls']
    shown = cls[-ROUTE_MAX:]
    n = len(shown)
    n_merged = sum(c['status'] == 'MERGED' for c in cls)
    n_open = len(cls) - n_merged
    dark = t['name'] == 'dark'
    W, H = 720, 296
    desc = ('Chromium, net and DNS. '
            + (f'{progress(n_merged, n_open)}. Timeline: '
               + ', '.join(f"{status_label(c)} {c['when'][:7]}" for c in shown) + '.'
               if n else 'No changes yet.'))
    d = Doc(W, H, 'Chromium', desc, CSS)
    hr = window(d, t, W, H, fill=t['panel_deep'])[1]

    # ground band behind the route (dither seam + flat fill), with a few tufts
    gb = d.pix(4)
    gcol = mix(t['green'], t['panel'], .90 if dark else .86)
    tuft = mix(t['green'], t['panel'], .62 if dark else .60)
    for c in range(1, 178):
        for r in range(40, hr - 1):
            if r > 41 or bayer(c, r) < .5:
                gb.px(c, r, gcol)
    for c, r in ((8, 46), (22, 49), (40, 45), (68, 47), (95, 45), (112, 48), (134, 46), (150, 49), (172, 46), (14, 52), (166, 53)):
        gb.px(c, r, tuft)
        gb.px(c, r - 1, tuft)
        gb.px(c + 1, r, tuft)

    # ring + title block
    sprite(d, t, 'ring', 24, 24, 6)
    d.text(144, 28, 'CHROMIUM', t['text'], 6)
    d.text(144, 96, 'NET / DNS', t['sub'], 4)  # ends well left of the tally below, which starts right of x=476

    # tally: numerals share a column, labels share a column (a zero row is never drawn)
    rows_ = [(str(k), lab, col) for k, lab, col in ((n_merged, 'MERGED', t['green_c']), (n_open, 'IN REVIEW', t['gold_c'])) if k]
    if rows_:
        wnum = max(tw(a, 4) for a, _, _ in rows_)
        wall = wnum + 12 + max(tw(b_, 4) for _, b_, _ in rows_)
        x0 = 696 - wall
        y0 = 28 + (36 if len(rows_) == 1 else 0) // 2
        for i, (num, lab, col) in enumerate(rows_):
            d.text(x0, y0 + i * 36, num, col, 4)
            d.text(x0 + wnum + 12, y0 + i * 36, lab, t['text'], 4)

    if n:
        xs = [96 + round(i * (624 - 96) / max(1, n - 1)) for i in range(n)] if n > 1 else [360]
        yr = 200
        edge = t['border'] if dark else t['s2']
        last_done = max([i for i, c in enumerate(shown) if c['status'] == 'MERGED'], default=-1)
        rail = d.pix(4)
        for c in range(xs[0] // 4, xs[-1] // 4 + 1):
            rail.rect(c, yr // 4, 1, 2, edge)
        if last_done >= 0:
            prog = d.pix(4)
            for c in range(xs[0] // 4, xs[last_done] // 4 + 1):
                prog.rect(c, yr // 4, 1, 2, t['green'])
        if 0 <= last_done < n - 1:
            dash = d.pix(4)
            for c in range(xs[last_done] // 4 + 3, xs[-1] // 4 - 2):
                if (c // 3) % 2 == 0:
                    dash.rect(c, yr // 4, 1, 2, t['gold'])
        nodes = d.pix(4)
        blink = d.pix(4)
        check = [".....#", "....##", "#..##.", "##.##.", ".###..", "..#..."]
        ink = t['crust'] if dark else '#1e2030'
        for i, c in enumerate(shown):
            cx0, cy0 = (xs[i] - 20) // 4, (yr + 4 - 20) // 4
            if c['status'] == 'MERGED':
                panel(nodes, cx0, cy0, 10, 10, ink, t['green'])
                for rr, line in enumerate(check):
                    for cc, ch in enumerate(line):
                        if ch == '#':
                            nodes.px(cx0 + 2 + cc, cy0 + 2 + rr, ink)
            else:
                panel(nodes, cx0, cy0, 10, 10, t['gold'], t['panel_deep'])
                blink.rect(cx0 + 4, cy0 + 4, 2, 2, t['gold'])
        # month labels: drawn by priority (last, first, the rest); any that would collide is skipped
        placed = []
        for i in [n - 1] + ([0] if n > 1 else []) + list(range(1, n - 1)):
            c = shown[i]
            ym = MONTHS[int(c['when'][5:7]) - 1] + " '" + c['when'][2:4]
            wl = tw(ym, 4)
            x = xs[i] - wl // 2
            if any(x < px + pw + 16 and px < x + wl + 16 for px, pw in placed):
                continue
            placed.append((x, wl))
            d.text(x, 240, ym, t['text'] if c['status'] == 'MERGED' else t['gold_c'], 4)
        d.anim(blink, 'qb')

        # the player stands above the newest level still in review
        open_idx = [i for i, c in enumerate(shown) if c['status'] != 'MERGED']
        if open_idx:
            rows, pal = sprites.catalogue(t)['player']
            mk = d.pix(3, xs[open_idx[-1]] - 18, 132)
            mk.art(0, 0, rows, pal)
            d.anim(mk, 'qh')
    else:
        d.text(144, 180, 'NO CHANGES YET', t['sub'], 4)
    save('world', t['key'], d.render())


# ======================================================================================
# PROJECT CARDS: an icon, a name and one line. The whole card is the link.
# ======================================================================================


# Four cards, two by two. The motorcycle is the Smart Car competition entry; it won a National second prize.
# Everything a visitor needs beyond this one line is a click away (the blog post), and the alt text
# carries the detail for readers who cannot see the card.
PROJECTS = [
    dict(key='ar360', icon='glasses', title=['AR360'], line='PANORAMIC VIDEO CALLS', url='ar360',
         alt='AR360 panoramic calling, 2025: immersive video calls with Unity, Rokid AR glasses and an Insta360 '
             'panoramic camera. Read the blog post.'),
    dict(key='skills', icon='terminal', title=['CODEX SKILLS'], line='REUSABLE DEV WORKFLOWS', url='skills',
         alt='Personal Codex skills: Git-managed agent skills and shared AGENTS.md instructions for Mac, Windows and '
             'Linux, with CI. First skill: Evidence-led Engineering. Browse the repository.'),
    dict(key='bike', icon='bike', title=['SELF-BALANCING', 'MOTORCYCLE'], prize='NATIONAL 2ND PRIZE 2021', url='bike',
         alt='Self-balancing motorcycle, 2021: sensor fusion and fuzzy PID, built for the Smart Car competition. '
             'National second prize. Read the blog post.'),
    dict(key='mocap', icon='mocap', title=['WEARABLE', 'MOTION CAPTURE'], line='REHABILITATION ASSESSMENT', url='mocap',
         alt='Wearable motion capture and rehabilitation assessment system, 2022. Read the blog post.'),
]


def project_card(t, q):
    W, H = CARD_W, 132
    d = Doc(W, H, q['alt'].split(':')[0], q['alt'])
    window(d, t, W, H)
    inset(d, t, 16, 16, 68, 68)
    sprite(d, t, q['icon'], 18, 18, 3, box=(64, 64))
    n = len(q['title'])
    y = 16 + (68 - (n * 21 + (n - 1) * 8)) // 2  # the name, centred beside the icon
    for ln in q['title']:
        d.text(92, y, ln, t['text'], 3)
        y += 29
    if q.get('prize'):  # the one achievement: the medal and the prize, in gold
        rows, pal = sprites.catalogue(t)['medal']
        d.pix(1, 16, 97).art(0, 0, rows, pal)
        d.text(40, 98, q['prize'], t['gold_c'], 2)
    else:
        d.text(16, 98, q['line'], t['sub'], 2)
    d.text(W - 28, 98, '▶', t['gold_c'], 2)  # the menu cursor of the hero: this one opens
    return d


# ======================================================================================
# MENU BUTTONS
# ======================================================================================


def button(t, label, name):
    """A menu button: bevelled pixel window and one label. No cursor glyph, so the three of them
    (76 + 96 + 116 px, plus the two spaces between inline images) fit a 320px column without wrapping."""
    wtxt = tw(label, 2)
    W = 12 + wtxt + 12 + 4
    W += (-W) % 4
    H = 44
    d = Doc(W, H, name, f'Menu button: {name}')
    window(d, t, W, H)
    d.text((W - 4 - wtxt) // 4 * 2, 14, label, t['text'], 2)  # centred, on the 2px grid
    return d


# ======================================================================================
# MINI-GAME: the CI-generated snk file framed as a game window
# ======================================================================================


def snake_colors(t):
    """(snake, [empty, level1..level4]) for snk, derived from the theme: a gold ramp on the empty colour."""
    dark = t['name'] == 'dark'
    empty = t['s0']
    top = t['gold'] if dark else mix(t['gold'], t['ink'], .22)
    ramp = [empty] + [mix(empty, top, k) for k in (.38, .62, .84, 1.0)]
    return (t['text'] if dark else t['ink']), ramp


def snk_query(t):
    snake, ramp = snake_colors(t)
    return f'color_snake={snake}&color_dots={",".join(ramp)}'


RM_RULE = '@media (prefers-reduced-motion: reduce){.s,.c,.u{animation:none!important}}'


def prepare_snake(t):
    """The snk output for this theme, recoloured to the theme (a no-op when CI already passed these
    colours) and with reduced motion respected. Fails loudly if snk's variables ever change."""
    path = ROOT / 'data' / f'snake-{t["key"]}.svg'
    if not path.exists():
        raise SystemExit(f'{path.relative_to(ROOT)} is missing: run the snk step first')
    svg = read_text(path)
    snake, ramp = snake_colors(t)
    want = {'cs': snake, 'ce': ramp[0], 'c0': ramp[0], 'c1': ramp[1], 'c2': ramp[2], 'c3': ramp[3], 'c4': ramp[4]}
    for k, v in want.items():
        svg, n = re.subn(rf'(--{k}:)#[0-9a-fA-F]{{3,8}}(?=[;}}])', rf'\g<1>{v}', svg, count=1)
        if n != 1:
            raise SystemExit(f'{path.name}: CSS variable --{k} not found; snk changed its output')
        assert f'--{k}:{v}' in svg
    if RM_RULE not in svg:
        if '</style>' not in svg:
            raise SystemExit(f'{path.name}: no <style> block; snk changed its output')
        svg = svg.replace('</style>', RM_RULE + '</style>', 1)
    return svg


# snk draws the contribution graph as one <rect> per day on a 16px grid (2px margin, 12px cell). A day
# the snake eats carries an animation class (c0, c1, ...); a day without contributions has none. Only the
# still fallback below reads this; the animated file is embedded as snk wrote it.
CELL_RE = re.compile(r'<rect class="c(?: (c[0-9a-z]+))?" x="(\d+)" y="(\d+)" rx="2" ry="2"/>')
LEVEL_RE = re.compile(r'\.c\.(c[0-9a-z]+)\{fill:var\(--(c[0-4])\)')


def grid_cells(svg):
    """[(col, row, animation class or None)] for every day of the graph, or None when the markup is not
    the regular grid described above (the callers then leave the file alone)."""
    cells = []
    for cls, x, y in CELL_RE.findall(svg):
        x, y = int(x), int(y)
        if (x - 2) % 16 or (y - 2) % 16:
            return None
        cells.append(((x - 2) // 16, (y - 2) // 16, cls or None))
    return cells if len(cells) >= 28 else None


def still_grid(svg, t):
    """The contribution graph without the snake: every day in its level colour, no animation at all.
    The fallback when the animated file would not fit the size budget. None if the markup is unknown."""
    cells = grid_cells(svg)
    if not cells:
        return None
    level = dict(LEVEL_RE.findall(svg))  # animation class -> colour variable
    _, ramp = snake_colors(t)
    by = {}
    for col, row, cls in cells:
        by.setdefault(ramp[int(level[cls][1])] if cls in level else ramp[0], []).append((2 + 16 * col, 2 + 16 * row))
    return ''.join(f'<g fill="{color}">' + ''.join(f'<rect x="{x}" y="{y}" width="12" height="12" rx="2"/>' for x, y in xy) + '</g>'
                   for color, xy in sorted(by.items()))


GAME = {'still': False}  # set when the mini-game had to fall back to the still graph (the README wording follows)

VIEWBOX_RE = re.compile(r'^\s*<svg\b[^>]*?\sviewBox="\s*-?[\d.]+[\s,]+-?[\d.]+[\s,]+([\d.]+)[\s,]+[\d.]+\s*"')
SNK_WIDTH = 880  # snk's viewBox width for a 53-week graph: 16px margin + 53 columns x 16px + 16px margin


def snake_width(svg):
    """The width of snk's own viewBox. The graph is 53 week columns wide on most days and one column wider
    (896) on some, so the frame follows the file instead of assuming 53. Anything odd falls back to 880."""
    m = VIEWBOX_RE.match(svg)
    w = float(m.group(1)) if m else SNK_WIDTH
    return int(w) if w == int(w) and 400 <= w <= 1200 else SNK_WIDTH


def minigame(t, data, still=False):
    """The framed mini-game as SVG text: the snk animation, or (still=True) the graph without the snake."""
    W, H = 720, 212
    score = data['score']
    x, y, w, h = 16, 68, 688, 120
    svg = prepare_snake(t)
    if still:
        inner = still_grid(svg, t)
        if inner is None:
            return None
    else:
        inner = re.sub(r'</svg>\s*$', '', re.sub(r'^\s*<svg[^>]*>', '', svg.strip(), count=1))
    # snk's root viewBox is -16 -32 <W> 192; this one trims 10px at each side and 12px above, 30px below
    view = f'-6 -20 {snake_width(svg) - 20} 150'
    if still:
        tab, name = 'CONTRIBUTIONS', 'Contribution graph'
        desc = 'The contribution graph.'
    else:
        tab, name = 'MINI-GAME: SNAKE', 'Mini-game: snake'
        desc = 'Mini-game: a snake eats the contribution graph.'
    if score:
        desc += f' Score: {score} contributions in the last year.'
    d = Doc(W, H, name, desc)
    window(d, t, W, H, tab=tab, tab_right=(f'SCORE {score}', t['tab_fg']) if score else None, tab_u=4)
    fr = d.pix(2)
    panel(fr, x // 2 - 2, (y - 6) // 2, (w + 8) // 2, (h + 12) // 2, t['slot_border'], t['panel_deep'])
    d.add(f'<svg x="{x}" y="{y}" width="{w}" height="{h}" viewBox="{view}">{inner}</svg>')
    return d.render()


def minigames(data):
    """{theme key: svg}. The snake animation grows with the number of active days; when either theme's file
    would pass the size budget, both fall back to the still graph, so the job never fails on a busy year and
    the two themes always match."""
    games = {tk: minigame(t, data) for tk, t in THEMES.items()}
    biggest = max(len(g.encode('utf-8')) for g in games.values())
    if biggest > GAME_BUDGET:
        stills = {tk: minigame(t, data, still=True) for tk, t in THEMES.items()}
        if all(stills.values()):
            datamod.warn(f'the animated mini-game is {biggest} bytes, over the {GAME_BUDGET} budget; '
                         f'drawing the contribution graph without the snake')
            GAME['still'] = True
            return stills
    return games


# ======================================================================================
# README
# ======================================================================================


def pic(name, alt, width, link=None, v=V):
    alt = escape(alt, quote=True)
    p = (f'<picture><source media="(prefers-color-scheme: dark)" srcset="./profile/{name}-mocha.svg?v={v}">'
         f'<source media="(prefers-color-scheme: light)" srcset="./profile/{name}-latte.svg?v={v}">'
         f'<img src="./profile/{name}-mocha.svg?v={v}" width="{width}" alt="{alt}"></picture>')
    return f'<a href="{link}">{p}</a>' if link else p


def caption(media, text):
    """Images and their caption in ONE paragraph: the <br> keeps the caption attached to the images it
    describes, where a paragraph of its own would sit as far from them as from the next block. <sup> (small,
    raised half an em) rather than <sub> (small, lowered): it moves the text up toward the images and away
    from what follows, so the caption sits ~12px under its subject and ~25px above the next block."""
    return f'<p>\n{media}\n<br><sup>{text}</sup></p>' if media else f'<p><sup>{text}</sup></p>'


def readme(data, buttons):
    cls = data['cls']
    n_merged = sum(c['status'] == 'MERGED' for c in cls)
    n_open = len(cls) - n_merged
    score = data['score']
    when = data['last_save']
    # One image per idea, and nothing a click away (the Chromium changes themselves are on Gerrit, the
    # write-ups on the blog).
    out = ['<div align="center">', '']
    out.append('<p>' + pic('hero', 'Calvin Diao. Less clicking. More tinkering. A pixel-art title screen.', 720) + '</p>')
    out.append('')
    out.append("<p><b>From sensors and PID loops, through the browser's network stack, " + nb('to AR headsets.') + '</b><br>')
    out.append('<sub>Toronto, Canada · M.Eng, McMaster University</sub></p>')
    out.append('')
    out.append('<p>' + '\n'.join(pic(f'btn-{k}', f'{lab}: {desc}', w, URL[k]) for k, lab, desc, w in buttons) + '</p>')
    out.append('')
    world_alt = ('Chromium, net and DNS: ' + (f'{progress(n_merged, n_open)}.' if cls else 'no changes yet.')
                 + ' Open every change on Gerrit.')
    out.append(caption(pic('world', world_alt, 720, URL['gerrit']),
                       f'Google Summer of Code 2025: <a href="{URL["gsoc"]}">Structured DNS {nb("errors in Chromium")}</a>'))
    out.append('')
    cards = '\n'.join(pic(f'project-{q["key"]}', q['alt'], CARD_W, URL[q['url']]) for q in PROJECTS)
    out.append(f'<p>\n{cards}\n</p>')
    out.append('')
    still = GAME['still']
    game = ('Calvin Diao’s GitHub contribution graph.' if still else
            'Mini-game: a snake eats Calvin Diao’s GitHub contribution graph.') \
        + (f' Score: {score} contributions in the last year.' if score else '')
    out.append('<p>' + pic('minigame', game, 720) + '</p>')
    out.append('')
    out.append('<p><sub>' + (nb(f'Updated {when}.') + ' ' if when else '')
               + f'{nb("Colors from Catppuccin,")} snake{NB}by{NB}<a href="{URL["snk"]}">snk</a>, '
               + f'{nb("name set in DotGothic16 (SIL OFL).")}</sub></p>')
    out.append('')
    out.append('</div>')
    return '\n'.join(out) + '\n'


# ======================================================================================
# contrast audit and main
# ======================================================================================


def audit():
    """WCAG contrast for every text/background pair the design uses. Fails the build below 4.5:1."""
    bad = []
    for tk, t in THEMES.items():
        pairs = []
        for bg in (t['panel'], t['panel_deep']):
            for fg in ('text', 'sub', 'gold_c', 'green_c', 'red_c'):
                pairs.append((f'{tk}: {fg} on panel {bg}', t[fg], bg))
        for fg in ('tab_fg', 'tab_sub'):
            pairs.append((f'{tk}: {fg} on title bar', t[fg], t['tab_bg']))
        gcol = mix(t['green'], t['panel'], .90 if tk == 'mocha' else .86)
        for fg in ('text', 'sub', 'gold_c', 'green_c'):
            pairs.append((f'{tk}: {fg} on route ground', t[fg], gcol))
        name_col, near_sh, far_sh = title_colors(t)
        for label, sh in (('near', near_sh), ('far', far_sh)):
            # the title is large text (3:1 is the bar); its shadow steps touch every stroke edge
            if contrast(name_col, sh) < 3.0:
                bad.append(f'{tk}: hero title on its {label} shadow: {contrast(name_col, sh):.2f} < 3.0')
        for i, sc in enumerate(sky_stops(t)):
            pairs.append((f'{tk}: hero title on sky[{i}]', name_col, sc))
            if i >= 3:
                pairs.append((f'{tk}: hero menu gold on sky[{i}]', t['gold_m'], sc))
                pairs.append((f'{tk}: hero menu sub on sky[{i}]', t['sub'], sc))
        pairs.append((f'{tk}: hero menu gold on the far hills (the lower rows of the menu cross them)', t['gold_m'], t['hill_far']))
        for name, fg, bg in pairs:
            r = contrast(fg, bg)
            if r < 4.5:
                bad.append(f'{name}: {r:.2f} < 4.5')
    return bad


def check_workflow():
    """The snk colours in the workflow must match the theme (build.py recolours anyway, so drift is only a warning)."""
    wf = ROOT / '.github' / 'workflows' / 'profile-assets.yml'
    if not wf.exists():
        return
    text = read_text(wf)
    for tk, t in THEMES.items():
        line = f'data/snake-{tk}.svg?{snk_query(t)}'
        if line not in text:
            datamod.warn(f'profile-assets.yml snk colours are out of date, expected: {line}')


def main():
    live = '--live' in sys.argv
    data = datamod.load(live=live)
    BTN = [('blog', 'BLOG', 'Blog', 'read the blog'), ('gerrit', 'GERRIT', 'Gerrit', 'every Chromium change on Gerrit'),
           ('linkedin', 'LINKEDIN', 'LinkedIn', 'LinkedIn profile')]
    buttons = []
    for tk, t in THEMES.items():
        hero(t)
        world(t, data)
        for q in PROJECTS:
            save(f'project-{q["key"]}', tk, project_card(t, q).render())
        buttons = []
        for k, lab, name, desc in BTN:
            b = button(t, lab, name)
            save(f'btn-{k}', tk, b.render())
            buttons.append((k, lab, desc, b.w))
    for tk, svg in minigames(data).items():
        save('minigame', tk, svg)
    # Everything is rendered and checked in memory first; nothing is written unless all of it worked, so a
    # failure can never leave the tree half-built (new images, old README).
    files = {name: '\n'.join(line.rstrip() for line in svg.splitlines()).rstrip() + '\n' for name, svg in SVG_OUT.items()}
    readme_text = readme(data, buttons)
    check_workflow()
    bad = audit()
    print('contrast audit: ' + ('OK' if not bad else 'FAIL\n  ' + '\n  '.join(bad)))
    if bad:
        raise SystemExit(1)
    PROFILE.mkdir(exist_ok=True)
    for old in PROFILE.glob('*.svg'):  # prune images nothing refers to any more
        if old.name not in files:
            old.unlink()
    for name, svg in files.items():
        write_text(PROFILE / name, svg)
    write_text(ROOT / 'README.md', readme_text)
    if live:
        print('snk colours (keep in sync with .github/workflows/profile-assets.yml):')
        for tk, t in THEMES.items():
            print(f'  data/snake-{tk}.svg?{snk_query(t)}')
    total = sum(len(s) for s in files.values())
    big = sorted(((len(s), n) for n, s in files.items()), reverse=True)[:3]
    print(f'Wrote {len(files)} SVGs ({total // 1024} KB) + README.md; largest: ' + ', '.join(f'{n} {b // 1024}KB' for b, n in big))


if __name__ == '__main__':
    main()
