"""Hand-built pixel icons and their per-theme colours.

Each sprite is a list of equal-length strings. Role letters, mapped by `catalogue(t)`:
  o outline  m main  s shade  h highlight  w paper  k dark fill  a accent (gold)
  r/g/b arc tones (ring)  f skin  e eye  c cord  p trousers  t tyre  i icon body

One rule keeps the set calm: icon bodies are the theme's neutral blue-grey, and the single accent
(Catppuccin yellow, "gold") marks the one detail that matters on each icon.
"""

from __future__ import annotations

import math

from pixelkit import mix


class G:
    """Tiny raster canvas for geometric icons."""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.g = [['.'] * w for _ in range(h)]

    def put(self, x, y, ch):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.g[y][x] = ch

    def rect(self, x, y, w, h, ch):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.put(xx, yy, ch)

    def line(self, x0, y0, x1, y1, ch):
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            self.put(x0, y0, ch)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def disc(self, cx, cy, r, ch):
        for y in range(self.h):
            for x in range(self.w):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    self.put(x, y, ch)

    def ring(self, cx, cy, r_out, r_in, ch):
        for y in range(self.h):
            for x in range(self.w):
                d2 = (x - cx) ** 2 + (y - cy) ** 2
                if r_in * r_in < d2 <= r_out * r_out:
                    self.put(x, y, ch)

    def outline(self, ch='o', only=None):
        """Wrap the current non-empty cells with an outline ring (4-neighbourhood)."""
        src = [row[:] for row in self.g]
        for y in range(self.h):
            for x in range(self.w):
                if src[y][x] != '.':
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.w and 0 <= ny < self.h and src[ny][nx] != '.':
                        if only is None or src[ny][nx] in only:
                            self.g[y][x] = ch
                            break

    def rows(self):
        return [''.join(r) for r in self.g]


def check(name, rows):
    w = {len(r) for r in rows}
    assert len(w) == 1, f'{name}: ragged rows {sorted(w)}'
    return rows


# --------------------------------------------------------------------------------------
# Sprites
# --------------------------------------------------------------------------------------

PLAYER = check('player', [
    "...oooooo...",
    "..okkkkkko..",
    ".okkkkkkkko.",
    ".okkkkkkkko.",
    ".okkffffkko.",
    ".ofeffffefo.",
    ".offffffffo.",
    "..ooffffoo..",
    "..obbbbbbo..",
    ".obbbccbbbo.",
    "obbbbccbbbbo",
    "obbbbbbbbbbo",
    "offbbbbbbffo",
    "..opppppppo.",
    "..oppooppo..",
    "..ooo..ooo..",
])


def ring16():
    """Three tonal arcs around a gold core: a pixel nod to a browser, in the page's own colours."""
    g = G(16, 16)
    cx = cy = 7.5
    for y in range(16):
        for x in range(16):
            dx, dy = x - cx, y - cy
            d = math.hypot(dx, dy)
            if d > 8.0:
                continue
            ang = math.degrees(math.atan2(dy, dx))
            if d > 4.7:
                ch = 'r' if -150 <= ang < -30 else ('a' if -30 <= ang < 90 else 'g')
                g.put(x, y, ch)
            elif d > 3.3:
                g.put(x, y, 'w')
            else:
                g.put(x, y, 'b')
    return g.rows()


RING = ring16()

GLASSES = check('glasses', [
    "................",
    "................",
    "................",
    ".iiiiiiiiiiiiii.",
    "ikkkkkiiiikkkkki",
    "ikwwkkiiiikwwkki",
    "ikkkkkiiiikkkkki",
    "ikkkkkiiiikkkkki",
    ".ikkkkiiiikkkki.",
    "..iiiii..iiiii..",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
])


def motorcycle():
    """Side-on bike facing right (18 x 14): a bright silhouette with a gold tank, so it reads on dark and light."""
    g = G(18, 14)
    for cx in (4.5, 13.5):
        g.ring(cx, 9.0, 4.6, 2.5, 'i')          # open wheels
        g.put(round(cx - .5), 9, 'a')           # hub
    g.rect(2, 3, 6, 2, 'i')                     # seat
    g.rect(7, 2, 5, 3, 'a')                     # tank
    g.rect(7, 2, 5, 1, 'h')
    g.rect(7, 5, 5, 4, 'i')                     # engine block
    g.rect(8, 6, 3, 2, 'k')
    g.line(4, 9, 7, 7, 'i')                     # swing arm
    g.line(13, 9, 12, 2, 'i')                   # fork
    g.line(14, 9, 13, 2, 'i')
    g.rect(11, 1, 4, 1, 'h')                    # bars
    g.put(15, 3, 'a')                           # headlight
    g.put(15, 4, 'a')
    return g.rows()


MOTORCYCLE = motorcycle()


def mocap():
    """A mannequin in a motion-capture suit: gold markers on head, shoulders, hands, hips and feet."""
    g = G(16, 16)
    g.rect(6, 0, 4, 4, 'i')                     # head
    g.put(6, 0, '.'); g.put(9, 0, '.')
    g.rect(5, 5, 6, 5, 'i')                     # torso
    g.rect(3, 5, 2, 6, 'i')                     # arms
    g.rect(11, 5, 2, 6, 'i')
    g.rect(5, 11, 2, 5, 'i')                    # legs
    g.rect(9, 11, 2, 5, 'i')
    g.outline('o', only='i')
    for x, y, w, h in ((7, 1, 2, 1), (7, 6, 2, 2), (3, 9, 2, 2), (11, 9, 2, 2), (5, 14, 2, 2), (9, 14, 2, 2)):
        g.rect(x, y, w, h, 'a')
    return g.rows()


MOCAP = mocap()

TERMINAL = check('term', [
    "................",
    "................",
    ".oooooooooooooo.",
    ".oiiiiiiiiiiiio.",
    ".oiiiiiiiiiiiio.",
    ".okkkkkkkkkkkko.",
    ".okakkkkkkkkkko.",
    ".okkakkkkkkkkko.",
    ".okkkakkkkkkkko.",
    ".okkakkkwwwkkko.",
    ".okakkkkkkkkkko.",
    ".okkkkkkkkkkkko.",
    ".oooooooooooooo.",
    "................",
    "................",
    "................",
])


def medal():
    g = G(16, 16)
    g.rect(4, 0, 3, 5, 'b')
    g.rect(9, 0, 3, 5, 'r')
    g.disc(7.5, 9.5, 5.2, 'm')
    g.ring(7.5, 9.5, 5.2, 3.6, 's')
    g.outline('o', only='msbr')
    two = ["###", "..#", "###", "#..", "###"]
    for ry, line in enumerate(two):
        for rx, ch in enumerate(line):
            if ch == '#':
                g.put(6 + rx, 7 + ry, 'k')
    return g.rows()


MEDAL = medal()


def sun():
    g = G(16, 16)
    g.disc(7.5, 7.5, 3.6, 'a')
    for ang in range(0, 360, 45):
        x = 7.5 + 6.4 * math.cos(math.radians(ang))
        y = 7.5 + 6.4 * math.sin(math.radians(ang))
        g.put(round(x - 0.5), round(y - 0.5), 'a')
        if ang % 90 == 0:
            x2 = 7.5 + 7.4 * math.cos(math.radians(ang))
            y2 = 7.5 + 7.4 * math.sin(math.radians(ang))
            g.put(round(x2 - 0.5), round(y2 - 0.5), 'a')
    return g.rows()


SUN = sun()


def floppy():
    g = G(16, 16)
    g.rect(1, 1, 14, 14, 'i')
    g.put(13, 1, '.'); g.put(14, 1, '.'); g.put(14, 2, '.')
    g.rect(4, 1, 8, 5, 'h')
    g.rect(8, 2, 2, 3, 'k')
    g.rect(3, 8, 10, 7, 'w')
    g.rect(4, 10, 8, 1, 's')
    g.rect(4, 12, 6, 1, 's')
    g.outline('o', only='ihw')
    return g.rows()


FLOPPY = floppy()


def moon():
    g = G(12, 12)
    g.disc(5.5, 5.5, 5.6, 'm')
    for (x, y) in ((3, 3), (4, 3), (3, 4), (7, 6), (8, 6), (7, 7), (5, 8), (6, 8)):
        g.put(x, y, 's')
    g.put(7, 2, 'h'); g.put(8, 3, 'h')
    return g.rows()


MOON = moon()


def palette(role_colors: dict, ink: str, tint: str):
    """char -> colour map. `tint` is the sprite's main colour; shade and highlight derive from it."""
    base = {'o': ink, 'm': tint, 's': mix(tint, ink, 0.38), 'h': mix(tint, '#ffffff', 0.35)}
    base.update(role_colors)
    return base


def catalogue(t):
    """name -> (rows, palette) for one theme."""
    ink = t['ink']
    dark = t['name'] == 'dark'
    body = t['sub'] if dark else '#6c6f85'          # neutral icon body
    lens = t['crust'] if dark else '#2b2d3f'
    paper = t['white'] if dark else '#ffffff'

    def pal(tint, **extra):
        return palette(extra, ink, tint)

    return {
        'player': (PLAYER, pal(t['blue'], b=t['blue'], k=t['hair'], f=t['skin'], e=ink, c=t['gold'],
                               p=mix(t['blue'], ink, 0.62))),
        'ring': (RING, pal(t['gold'], r=t['text'] if dark else ink, a=body, g=t['o0'] if dark else '#9ca0b0',
                           w=t['base'] if dark else '#eff1f5', b=t['gold'])),
        'glasses': (GLASSES, pal(body, i=body, k=lens, w=t['gold'])),
        'bike': (MOTORCYCLE, pal(body, i=body, a=t['gold'], k=lens, h=mix(t['gold'], '#ffffff', .45))),
        'mocap': (MOCAP, pal(body, i=body, a=t['gold'])),
        'terminal': (TERMINAL, pal(body, i=body, k=lens, a=t['gold'], w=paper)),
        'medal': (MEDAL, pal(t['gold'], b=t['blue'], r=t['red'], k=ink)),
        'sun': (SUN, pal(t['gold'], a=t['gold'])),
        'floppy': (FLOPPY, pal(body, i=body, k=lens, w=paper, h=t['gold'], s=t['s2'] if dark else '#9ca0b0')),
        'moon': (MOON, pal(t['text'] if dark else t['gold'], m=mix(t['text'], t['blue'], 0.25) if dark else t['gold'],
                           s=mix(t['text'], t['blue'], 0.55) if dark else t['gold'], h=t['white'])),
    }
