"""Catppuccin Mocha (dark) and Latte (light) roles.

The page uses one accent, Catppuccin yellow ("gold"): menu cursor, tab titles, the level in
progress, the sign-off. Everything else is the theme's blue-grey neutrals plus two meanings that
never change: green is merged / added, red is removed.

Fills use the stock colours. Anything that carries *text* uses the *_t / *_c / *_m variants, which
are the same hues darkened just enough to reach 4.7:1 on the surface they sit on (light theme only;
the dark theme's stock colours already pass).
"""

from pixelkit import ensure_contrast, luminance, mix

MOCHA = dict(
    name='dark',
    crust='#11111b', mantle='#181825', base='#1e1e2e',
    s0='#313244', s1='#45475a', s2='#585b70', o0='#6c7086', o1='#7f849c',
    sub='#a6adc8', text='#cdd6f4', white='#f5f7ff',
    gold='#f9e2af', green='#a6e3a1', blue='#89b4fa', red='#f38ba8',
    ink='#11111b', skin='#f2cdb0', hair='#585b70',
)
LATTE = dict(
    name='light',
    crust='#dce0e8', mantle='#e6e9ef', base='#eff1f5',
    s0='#ccd0da', s1='#bcc0cc', s2='#acb0be', o0='#9ca0b0', o1='#8c8fa1',
    sub='#5c5f77', text='#4c4f69', white='#ffffff',
    gold='#df8e1d', green='#40a02b', blue='#1e66f5', red='#d20f39',
    ink='#4c4f69', skin='#f2cdb0', hair='#4c4f69',
)

MIN_TEXT = 4.7  # design target; the audit in build.py fails below 4.5


def build(t: dict) -> dict:
    t = dict(t)
    dark = t['name'] == 'dark'
    toward = '#1e2030'
    # the darkest surface any text sits on in light mode: the tinted sky / route ground
    worst = mix(t['base'], t['blue'], .31)
    t['gold_t'] = t['gold'] if dark else ensure_contrast(t['gold'], worst, MIN_TEXT, toward=toward)
    if not dark:
        t['sub'] = ensure_contrast(t['sub'], worst, MIN_TEXT, toward=toward)
    # panel text (measured on the darker of mantle / route ground)
    ground = mix(t['green'], t['base'], .90 if dark else .86)
    pbg = min((t['mantle'], ground), key=luminance)
    for k in ('gold', 'green', 'red'):
        t[k + '_c'] = t[k] if dark else ensure_contrast(t[k], pbg, MIN_TEXT, toward=toward)
    # the far hills of the hero: the menu text sits on the sky and its lower rows cross these
    t['hill_far'] = mix(t['crust'], t['blue'], .12) if dark else mix(t['base'], t['blue'], .20)
    # menu text, measured on the darker of the pale sky band and those hills
    menu_bg = min((mix(t['base'], t['blue'], .09), t['hill_far']), key=luminance)
    t['gold_m'] = t['gold'] if dark else ensure_contrast(t['gold'], menu_bg, MIN_TEXT, toward=toward)
    t['panel'] = t['base']
    t['panel_deep'] = t['mantle']
    t['border'] = t['s1'] if dark else t['s2']
    t['slot_border'] = t['border'] if dark else t['s1']
    t['rule'] = t['s0'] if dark else t['s1']
    t['shadow'] = '#0b0b12' if dark else t['s0']
    # title bars: a dark bar with gold type in both themes
    t['tab_bg'] = t['s0'] if dark else '#4c4f69'
    t['tab_fg'] = '#f9e2af'
    t['tab_sub'] = t['sub'] if dark else '#cdd6f4'
    t['tab_green'] = '#a6e3a1'
    t['bevel_hi'] = t['s0'] if dark else t['white']
    t['bevel_lo'] = t['mantle'] if dark else t['s0']
    return t


DARK = build(MOCHA)
LIGHT = build(LATTE)
THEMES = {'mocha': DARK, 'latte': LIGHT}
for _k, _t in THEMES.items():
    _t['key'] = _k
