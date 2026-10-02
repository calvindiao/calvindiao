"""Render the profile's Catppuccin artwork; the name uses licensed font outlines."""

import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GLYPHS = json.loads((ROOT / "profile/name-glyphs.json").read_text())
SANS = "-apple-system, BlinkMacSystemFont, Segoe UI, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
THEMES = {
    "mocha": dict(base="#1e1e2e", mantle="#181825", edge="#313244", text="#cdd6f4",
                  sub="#bac2de", purple="#cba6f7", blue="#89b4fa", peach="#fab387"),
    "latte": dict(base="#eff1f5", mantle="#e6e9ef", edge="#ccd0da", text="#4c4f69",
                  sub="#5c5f77", purple="#8839ef", blue="#1e66f5", peach="#fe640b"),
}


def text(x, y, value, color, size=16, weight=400, mono=False):
    family = MONO if mono else SANS
    return f'<text x="{x}" y="{y}" fill="{color}" font-family="{family}" font-size="{size}" font-weight="{weight}">{escape(value)}</text>'


def pixels(rows, x, y, size, colors):
    return ''.join(
        f'<rect x="{x + col * size}" y="{y + row * size}" width="{size}" height="{size}" fill="{colors[cell]}"/>'
        for row, line in enumerate(rows) for col, cell in enumerate(line) if cell in colors
    )


def save(name, theme, width, height, title, body):
    (ROOT / f"profile/{name}-{theme}.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title, quote=True)}">\n'
        f'<title>{escape(title)}</title>\n{body}\n</svg>\n'
    )


def frame(c, width=350, height=205):
    return f'<rect x=".5" y=".5" width="{width - 1}" height="{height - 1}" rx="12" fill="{c["base"]}" stroke="{c["edge"]}"/>'


for theme, c in THEMES.items():
    x, scale = 23.0, 60 / GLYPHS["units"]
    name = []
    for glyph in GLYPHS["glyphs"]:
        gx, gy = x + glyph["xOffset"] * scale, 73 - glyph["yOffset"] * scale
        name.append(f'<path transform="translate({gx:g} {gy:g}) scale({scale:g} {-scale:g})" d="{glyph["path"]}"/>')
        x += glyph["advance"] * scale
    header = frame(c, 712, 104)
    header += f'<g fill="{c["text"]}">{"".join(name)}</g><rect x="{x + 6:g}" y="69" width="12" height="5" fill="{c["purple"]}"/>'
    # A small pixel editor extends the terminal language without another title bar.
    header += f'<path d="M558 21H676V83H558Z" fill="{c["mantle"]}" stroke="{c["edge"]}"/>'
    header += pixels(["11..22..33", "11..22..33"], 570, 29, 2, {"1": c["peach"], "2": c["blue"], "3": c["purple"]})
    header += f'<path d="M570 47H602M610 47H640M582 57H624M632 57H662M582 67H612" stroke="{c["edge"]}" stroke-width="4"/>'
    header += f'<path d="M570 47H584M582 57H606M624 67H646" stroke="{c["blue"]}" stroke-width="4"/>'
    header += f'<path d="M648 47H662M612 57H624" stroke="{c["purple"]}" stroke-width="4"/>'
    header += f'<rect x="24" y="89" width="36" height="3" fill="{c["purple"]}"/><rect x="64" y="89" width="20" height="3" fill="{c["blue"]}"/><rect x="88" y="89" width="8" height="3" fill="{c["peach"]}"/>'
    save("header", theme, 712, 104, "Calvin Diao", header)

    chromium = frame(c, 712, 82)
    chromium += f'<rect x="1" y="1" width="710" height="80" rx="12" fill="{c["blue"]}" opacity=".07"/>'
    chromium += pixels([
        "..111111..", ".11....11.", "11......11", "11..22..11", "11.2332.11",
        "11.2332.11", "11..22..11", "11......11", ".11....11.", "..111111..",
    ], 23, 21, 4, {"1": c["blue"], "2": c["purple"], "3": c["text"]})
    chromium += text(84, 54, "Chromium contributor", c["blue"], 38, 600)
    chromium += pixels(["11.....", "111....", ".111...", "..111..", ".111...", "111....", "11....."], 664, 27, 4, {"1": c["blue"]})
    save("chromium", theme, 712, 82, "Chromium contributor — Google Summer of Code 2025", chromium)

    cards = [
        dict(name="ar360", title="AR360 panoramic calling", accent="blue", label="Immersive systems",
             heading=["AR360"], lines=["Panoramic video calls", "Unity / Rokid / Insta360"], footer="Explore the project",
             icon=["..111111111111..", ".11..........11.", "11..222..222..11", "11..2.2..2.2..11", "11..222..222..11", "11.....11.....11", ".111111..111111.", "...11......11...", "....11111111...."]),
        dict(name="motorcycle", title="Self-balancing motorcycle — National second prize, 2021", accent="peach", label="Embedded systems",
             heading=["Self-balancing", "motorcycle"], lines=["Sensor fusion + fuzzy PID"], footer="National 2nd prize · 2021",
             icon=[".........111....", "........11......", "....222211......", "...22...1111....", "..22...11..11...", ".111..11....111.", "11.1111....11.11", "11.11......11.11", ".111........111."]),
        dict(name="skills", title="Personal Codex skills — reusable development workflows", accent="purple", label="Developer tools",
             heading=["Codex skills"], lines=["Reusable development workflows", "macOS / Windows / Linux"], footer="Browse the repository",
             icon=["1111111111111111", "1..............1", "1.22.22.22.....1", "1..............1", "1..2...........1", "1...2..........1", "1..2..2222.....1", "1..............1", "1111111111111111"]),
    ]
    for card in cards:
        accent = c[card["accent"]]
        body = frame(c)
        body += text(22, 31, card["label"], accent, 13, 500)
        body += pixels(card["icon"], 269, 32, 3.5, {"1": accent, "2": c["text"]})
        for i, heading in enumerate(card["heading"]):
            body += text(22, 69 + i * 27, heading, c["text"], 24, 600)
        if len(card["heading"]) == 1:
            body += text(22, 111, card["lines"][0], c["text"], 16)
            body += text(22, 139, card["lines"][1], c["sub"], 14)
        else:
            body += text(22, 132, card["lines"][0], c["sub"], 16)
        body += f'<path d="M22 158.5H328" stroke="{c["edge"]}"/>'
        body += text(22, 184, card["footer"], accent, 14, 500)
        body += pixels(["..1..", "...1.", "11111", "...1.", "..1.."], 316, 174, 2, {"1": accent})
        save(card["name"], theme, 350, 205, card["title"], body)

print("Rendered profile header, Chromium feature, and three project cards in both themes.")
