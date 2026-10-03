"""pixelkit - tiny stdlib-only toolkit for crisp pixel-art SVGs.

Everything here draws on integer grids and merges same-colour cells into rectangles inside a
single <path> per colour, so edges stay crisp, neighbouring cells never show hairline seams when
the image is scaled, and files stay small.
"""

from __future__ import annotations

import re
from html import escape
from pathlib import Path

# --------------------------------------------------------------------------------------
# Colour helpers
# --------------------------------------------------------------------------------------


def rgb(h: str):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def hexc(t):
    return '#%02x%02x%02x' % tuple(max(0, min(255, round(v))) for v in t)


def mix(a: str, b: str, t: float) -> str:
    """Linear blend: t=0 -> a, t=1 -> b."""
    ra, rb = rgb(a), rgb(b)
    return hexc(tuple(x + (y - x) * t for x, y in zip(ra, rb)))


def luminance(h: str) -> float:
    def f(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (f(v) for v in rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    if la < lb:
        la, lb = lb, la
    return (la + 0.05) / (lb + 0.05)


def ensure_contrast(fg: str, bg: str, target: float = 4.6, toward: str = '#000000') -> str:
    """Darken (or lighten) fg toward `toward` until it reaches the target contrast on bg."""
    c = fg
    for i in range(0, 101):
        c = mix(fg, toward, i / 100)
        if contrast(c, bg) >= target:
            return c
    return c


# --------------------------------------------------------------------------------------
# Bitmap font (hand-built 5x7 caps, variable width)
# --------------------------------------------------------------------------------------

_F = {
    'A': ".###.|#...#|#...#|#####|#...#|#...#|#...#",
    'B': "####.|#...#|#...#|####.|#...#|#...#|####.",
    'C': ".####|#....|#....|#....|#....|#....|.####",
    'D': "####.|#...#|#...#|#...#|#...#|#...#|####.",
    'E': "#####|#....|#....|####.|#....|#....|#####",
    'F': "#####|#....|#....|####.|#....|#....|#....",
    'G': ".####|#....|#....|#.###|#...#|#...#|.###.",
    'H': "#...#|#...#|#...#|#####|#...#|#...#|#...#",
    'I': "###|.#.|.#.|.#.|.#.|.#.|###",
    'J': "..###|...#.|...#.|...#.|...#.|#..#.|.##..",
    'K': "#...#|#..#.|#.#..|##...|#.#..|#..#.|#...#",
    'L': "#....|#....|#....|#....|#....|#....|#####",
    'M': "#...#|##.##|#.#.#|#.#.#|#...#|#...#|#...#",
    'N': "#...#|##..#|#.#.#|#..##|#...#|#...#|#...#",
    'O': ".###.|#...#|#...#|#...#|#...#|#...#|.###.",
    'P': "####.|#...#|#...#|####.|#....|#....|#....",
    'Q': ".###.|#...#|#...#|#...#|#.#.#|#..#.|.##.#",
    'R': "####.|#...#|#...#|####.|#.#..|#..#.|#...#",
    'S': ".####|#....|#....|.###.|....#|....#|####.",
    'T': "#####|..#..|..#..|..#..|..#..|..#..|..#..",
    'U': "#...#|#...#|#...#|#...#|#...#|#...#|.###.",
    'V': "#...#|#...#|#...#|#...#|#...#|.#.#.|..#..",
    'W': "#...#|#...#|#...#|#.#.#|#.#.#|##.##|#...#",
    'X': "#...#|#...#|.#.#.|..#..|.#.#.|#...#|#...#",
    'Y': "#...#|#...#|.#.#.|..#..|..#..|..#..|..#..",
    'Z': "#####|....#|...#.|..#..|.#...|#....|#####",
    '0': ".###.|#...#|#..##|#.#.#|##..#|#...#|.###.",
    '1': "..#..|.##..|..#..|..#..|..#..|..#..|.###.",
    '2': ".###.|#...#|....#|...#.|..#..|.#...|#####",
    '3': "#####|...#.|..#..|...#.|....#|#...#|.###.",
    '4': "...#.|..##.|.#.#.|#..#.|#####|...#.|...#.",
    '5': "#####|#....|####.|....#|....#|#...#|.###.",
    '6': "..##.|.#...|#....|####.|#...#|#...#|.###.",
    '7': "#####|....#|...#.|..#..|.#...|.#...|.#...",
    '8': ".###.|#...#|#...#|.###.|#...#|#...#|.###.",
    '9': ".###.|#...#|#...#|.####|....#|...#.|.##..",
    ' ': "...|...|...|...|...|...|...",
    '.': ".|.|.|.|.|.|#",
    ',': "..|..|..|..|..|.#|#.",
    ':': ".|.|#|.|.|#|.",
    '-': "...|...|...|###|...|...|...",
    '+': ".....|.....|..#..|#####|..#..|.....|.....",
    '/': "....#|....#|...#.|..#..|.#...|#....|#....",
    '#': ".#.#.|.#.#.|#####|.#.#.|#####|.#.#.|.#.#.",
    '!': "#|#|#|#|#|.|#",
    '?': ".###.|#...#|....#|...#.|..#..|.....|..#..",
    "'": "#|#|.|.|.|.|.",
    '(': "..#|.#.|#..|#..|#..|.#.|..#",
    ')': "#..|.#.|..#|..#|..#|.#.|#..",
    '=': ".....|.....|#####|.....|#####|.....|.....",
    '>': "#..|.#.|..#|.#.|#..|...|...",
    '·': ".|.|.|#|.|.|.",
    '▶': "#...|##..|###.|####|###.|##..|#...",
    '✓': "......|.....#|....##|#..##.|##.##.|.###..|..#...",
    '→': "......|...#..|....#.|######|....#.|...#..|......",
    '×': ".....|.....|#...#|.#.#.|..#..|.#.#.|#...#",
    '_': ".....|.....|.....|.....|.....|.....|#####",
    '●': ".....|.###.|#####|#####|#####|.###.|.....",
    '…': ".....|.....|.....|.....|.....|.....|#.#.#",
}
FONT = {k: v.split('|') for k, v in _F.items()}
for _k, _rows in FONT.items():
    assert len(_rows) == 7, (_k, len(_rows))
    assert len({len(r) for r in _rows}) == 1, (_k, _rows)

CAP = 7  # glyph height in cells


def glyph(ch: str):
    """Rows of a glyph; characters the font lacks render as '?', never as a crash."""
    return FONT.get(ch) or FONT['?']


def glyph_w(ch: str) -> int:
    return len(glyph(ch)[0])


def text_w(s: str) -> int:
    """Width in cells (glyphs + 1-cell gaps)."""
    s = s.upper()
    return sum(glyph_w(c) for c in s) + max(0, len(s) - 1)


# --------------------------------------------------------------------------------------
# Pix layer
# --------------------------------------------------------------------------------------


def _merge(cells):
    """cells: iterable of (c, r) -> list of (c, r, w, h) rectangles."""
    rows = {}
    for c, r in cells:
        rows.setdefault(r, []).append(c)
    out = []
    active = {}  # (c0, w) -> r_start
    prev_r = None
    for r in sorted(rows):
        if prev_r is not None and r != prev_r + 1:
            for (c0, w), rs in active.items():
                out.append((c0, rs, w, prev_r + 1 - rs))
            active = {}
        cs = sorted(rows[r])
        runs = []
        start = prev = cs[0]
        for c in cs[1:]:
            if c == prev + 1:
                prev = c
                continue
            runs.append((start, prev - start + 1))
            start = prev = c
        runs.append((start, prev - start + 1))
        now = set(runs)
        for key in list(active):
            if key not in now:
                c0, w = key
                out.append((c0, active[key], w, r - active[key]))
                del active[key]
        for key in runs:
            if key not in active:
                active[key] = r
        prev_r = r
    for (c0, w), rs in active.items():
        out.append((c0, rs, w, prev_r + 1 - rs))
    return out


class Doc:
    """Ordered SVG assembly: strings and Pix layers are emitted in the order they were added."""

    def __init__(self, w, h, title, desc=None, css=''):
        self.w, self.h, self.title, self.desc, self.css = w, h, title, desc, css
        self.parts = []

    def add(self, s):
        self.parts.append(s)

    def pix(self, u=4, ox=0, oy=0, clip=None):
        p = Pix(u, ox, oy, clip)
        self.parts.append(p)
        return p

    def text(self, x, y, s, color, u=2):
        """Bitmap text with its top-left at pixel (x, y); returns its pixel width."""
        p = self.pix(u, x, y)
        return p.text(0, 0, s, color) * u

    def anim(self, pix, cls):
        """Wrap an existing layer in an animated group (class defined in the doc CSS)."""
        i = self.parts.index(pix)
        self.parts[i] = f'<g class="{cls}">{pix.emit()}</g>'

    def render(self):
        body = ''.join(p.emit() if isinstance(p, Pix) else p for p in self.parts)
        return svg_open(self.w, self.h, self.title, self.desc, self.css) + body + '\n</svg>\n'


class Pix:
    """A grid layer. Cell (c, r) covers pixels [ox + c*u, ox + (c+1)*u) x [oy + r*u, ...)."""

    def __init__(self, unit=4, ox=0, oy=0, clip=None):
        self.u, self.ox, self.oy = unit, ox, oy
        self.cells = {}
        self.clip = clip
        self.attrs = ''

    # --- drawing -----------------------------------------------------------------
    def px(self, c, r, color):
        if color is None:
            return
        if self.clip and not self.clip(self.ox + c * self.u, self.oy + r * self.u, self.u):
            return
        self.cells[(c, r)] = color

    def rect(self, c, r, w, h, color):
        for rr in range(r, r + h):
            for cc in range(c, c + w):
                self.px(cc, rr, color)

    def art(self, c, r, rows, pal, flip=False):
        for rr, line in enumerate(rows):
            if flip:
                line = line[::-1]
            for cc, ch in enumerate(line):
                if ch != '.' and ch in pal:
                    self.px(c + cc, r + rr, pal[ch])

    def text(self, c, r, s, color):
        """Draw bitmap text, return width in cells."""
        s = s.upper()
        x = c
        for i, ch in enumerate(s):
            g = glyph(ch)
            for rr, line in enumerate(g):
                for cc, v in enumerate(line):
                    if v == '#':
                        self.px(x + cc, r + rr, color)
            x += len(g[0]) + 1
        return x - 1 - c

    # --- output ------------------------------------------------------------------
    def emit(self, extra=''):
        by_color = {}
        for (c, r), col in self.cells.items():
            by_color.setdefault(col, []).append((c, r))
        out = []
        for col, cells in by_color.items():
            rects = sorted(_merge(cells), key=lambda t: (t[1], t[0]))
            u = self.u
            d = []
            px_, py_ = None, None
            for c, r, w, h in rects:
                x, y = self.ox + c * u, self.oy + r * u
                if px_ is None:
                    d.append(f'M{x} {y}')
                else:
                    d.append(f'm{x - px_} {y - py_}')
                d.append(f'h{w * u}v{h * u}h-{w * u}z')
                px_, py_ = x, y
            out.append(f'<path fill="{col}"{extra}{self.attrs} d="{"".join(d)}"/>')
        return ''.join(out)


# --------------------------------------------------------------------------------------
# Panels, dithering, misc helpers
# --------------------------------------------------------------------------------------

BAYER4 = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def bayer(c, r):
    return (BAYER4[r % 4][c % 4] + 0.5) / 16


def notched(x, y, w, h, n=4):
    """Clip factory: rectangle (x,y,w,h) with n-pixel notched corners."""
    def inside(px, py, u):
        if px < x or py < y or px + u > x + w or py + u > y + h:
            return False
        for cx, cy in ((x, y), (x + w - n, y), (x, y + h - n), (x + w - n, y + h - n)):
            if cx <= px < cx + n and cy <= py < cy + n:
                return False
        return True
    return inside


def panel(pix: Pix, c, r, w, h, border, fill=None, hi=None, lo=None):
    """Draw a notched-corner pixel window (cell units of `pix`).

    border ring 1 cell thick with the corner cells removed and a stepped inner corner; optional
    inner highlight (top/left) and lowlight (bottom/right) lines for a chunky bevel.
    """
    for rr in range(r, r + h):
        for cc in range(c, c + w):
            edge = rr in (r, r + h - 1) or cc in (c, c + w - 1)
            corner = (rr in (r, r + h - 1)) and (cc in (c, c + w - 1))
            if corner:
                continue
            if edge:
                pix.px(cc, rr, border)
            elif fill is not None:
                pix.px(cc, rr, fill)
    # stepped inner corners
    for cc, rr in ((c + 1, r + 1), (c + w - 2, r + 1), (c + 1, r + h - 2), (c + w - 2, r + h - 2)):
        pix.px(cc, rr, border)
    if hi:
        for cc in range(c + 2, c + w - 2):
            pix.px(cc, r + 1, hi)
        for rr in range(r + 2, r + h - 2):
            pix.px(c + 1, rr, hi)
    if lo:
        for cc in range(c + 2, c + w - 2):
            pix.px(cc, r + h - 2, lo)
        for rr in range(r + 2, r + h - 2):
            pix.px(c + w - 2, rr, lo)


def svg_open(w, h, title, desc=None, style=''):
    t = escape(title, quote=True)
    d = f'<desc>{escape(desc)}</desc>' if desc else ''
    st = f'<style>{style}</style>' if style else ''
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="{t}">\n<title>{escape(title)}</title>{d}{st}\n')


MONO = 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace'


def mono_text(x, y, s, size, fill, weight=400, anchor='start', adv=0.6):
    """System-mono line with a hard length so fallback fonts can never overflow."""
    s = clean(s)
    n = len(s)
    length = round(n * size * adv, 1)
    anc = f' text-anchor="{anchor}"' if anchor != 'start' else ''
    w = f' font-weight="{weight}"' if weight != 400 else ''
    return (f'<text x="{x}" y="{y}" fill="{fill}" font-family="{MONO}" font-size="{size}"{w}{anc} '
            f'textLength="{length}" lengthAdjust="spacingAndGlyphs">{escape(s)}</text>')


_BAD_XML = re.compile('[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]')


def clean(s) -> str:
    """Text from an API, made safe for SVG: no control characters or lone surrogates, collapsed whitespace."""
    return ' '.join(_BAD_XML.sub('', str(s)).split())


def read_text(path) -> str:
    """UTF-8 on every platform (the default encoding is cp1252 on Windows), newlines normalised to \\n."""
    return Path(path).read_text(encoding='utf-8')


def write_text(path, text: str) -> None:
    """UTF-8 with LF line endings on every platform, so a rebuild is byte-identical everywhere."""
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)


def fit_lines(s: str, max_w: float, size: float, max_lines: int, adv: float = 0.6):
    """Wrap system-mono text into at most `max_lines` lines no wider than `max_w` pixels.

    Width is measured, not guessed: mono_text() pins every line to len * size * adv pixels, so a line
    of n characters is exactly n * size * adv wide. Words longer than a line are broken, and when the
    text does not fit the last line is cut and ends in an ellipsis.
    """
    per = max(1, int(max_w // (size * adv)))
    words = clean(s).split(' ')
    lines, cur = [], ''
    i = 0
    while i < len(words):
        w = words[i]
        if len(w) > per:  # a single word wider than a line: break it
            if cur:
                lines.append(cur)
                cur = ''
            lines.append(w[:per])
            words[i] = w[per:]
            continue
        if not cur:
            cur = w
        elif len(cur) + 1 + len(w) <= per:
            cur += ' ' + w
        else:
            lines.append(cur)
            cur = w
        i += 1
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        lines[-1] = (last[:per - 1] if len(last) >= per else last).rstrip() + '…'
    return lines
