"""Render the profile header from OFL-licensed DotGothic16 outlines.

The glyph outlines make the fine pixel type reliable in GitHub's SVG renderer.
Run from any directory: python3 scripts/render-header.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GLYPHS = json.loads((ROOT / "profile/name-glyphs.json").read_text())
THEMES = {
    "mocha": dict(base="#1e1e2e", mantle="#181825", edge="#313244", text="#cdd6f4",
                  sub="#bac2de", purple="#cba6f7", blue="#89b4fa", peach="#fab387"),
    "latte": dict(base="#eff1f5", mantle="#e6e9ef", edge="#ccd0da", text="#4c4f69",
                  sub="#5c5f77", purple="#8839ef", blue="#1e66f5", peach="#fe640b"),
}

for theme, c in THEMES.items():
    x, scale = 30.0, 80 / GLYPHS["units"]
    paths = []
    for glyph in GLYPHS["glyphs"]:
        gx, gy = x + glyph["xOffset"] * scale, 116 - glyph["yOffset"] * scale
        paths.append(f'<path transform="translate({gx:g} {gy:g}) scale({scale:g} {-scale:g})" d="{glyph["path"]}"/>')
        x += glyph["advance"] * scale
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="712" height="156" viewBox="0 0 712 156" role="img" aria-labelledby="title desc">
  <title id="title">Calvin Diao</title>
  <desc id="desc">Fine pixel lettering in Catppuccin {theme.title()}, inside a terminal window.</desc>
  <defs><clipPath id="window"><rect width="712" height="156" rx="10"/></clipPath></defs>
  <g clip-path="url(#window)">
    <rect width="712" height="156" fill="{c['base']}"/>
    <rect width="712" height="34" fill="{c['mantle']}"/>
    <path d="M0 34.5H712" stroke="{c['edge']}"/>
    <rect x="18" y="14" width="6" height="6" fill="{c['peach']}"/>
    <rect x="30" y="14" width="6" height="6" fill="{c['blue']}"/>
    <rect x="42" y="14" width="6" height="6" fill="{c['purple']}"/>
    <text x="62" y="21" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="12" fill="{c['sub']}">calvindiao / README</text>
    <g fill="{c['text']}">{''.join(paths)}</g>
    <rect x="{x + 7:g}" y="110" width="14" height="6" fill="{c['purple']}"/>
    <g fill="{c['edge']}">
      <rect x="624" y="65" width="6" height="6"/><rect x="634" y="65" width="6" height="6"/>
      <rect x="644" y="65" width="6" height="6"/><rect x="654" y="65" width="6" height="6"/>
      <rect x="624" y="75" width="6" height="6"/><rect x="654" y="75" width="6" height="6"/>
      <rect x="624" y="85" width="6" height="6"/><rect x="654" y="85" width="6" height="6"/>
      <rect x="624" y="95" width="6" height="6"/><rect x="634" y="95" width="6" height="6"/>
      <rect x="644" y="95" width="6" height="6"/><rect x="654" y="95" width="6" height="6"/>
    </g>
    <path d="M632 76H636V80H640V84H636V88H632" fill="none" stroke="{c['blue']}" stroke-width="2"/>
    <rect x="642" y="87" width="7" height="2" fill="{c['purple']}"/>
    <rect x="30" y="140" width="42" height="3" fill="{c['purple']}"/>
    <rect x="76" y="140" width="25" height="3" fill="{c['blue']}"/>
    <rect x="105" y="140" width="10" height="3" fill="{c['peach']}"/>
  </g>
</svg>
'''
    (ROOT / f"profile/header-{theme}.svg").write_text(svg)
    badge = f'''<svg xmlns="http://www.w3.org/2000/svg" width="244" height="30" viewBox="0 0 244 30" role="img" aria-label="Chromium contributor">
  <rect width="244" height="30" rx="6" fill="{c['base']}"/>
  <rect x="12" y="9" width="4" height="12" fill="{c['blue']}"/>
  <rect x="16" y="5" width="8" height="4" fill="{c['purple']}"/>
  <rect x="16" y="21" width="8" height="4" fill="{c['purple']}"/>
  <text x="36" y="20" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="14" fill="{c['purple']}">Chromium contributor</text>
</svg>
'''
    (ROOT / f"profile/chromium-{theme}.svg").write_text(badge)

print("Rendered Catppuccin Mocha and Latte header assets.")
