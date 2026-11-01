"""MkDocs hook (mkdocs.yml hooks): the site's Material palette (#282) from the Mech's own colours, so the pictures and
the site share one source: the paper the pictures sit on (model/render/blender.py BG), the Milky Pink spool
(model/geometry.py SPOOLS) and the near-black Blender draws Absolute Black in (BLACK_LIFT). Light and dark schemes
(mkdocs.yml theme.palette, primary and accent custom); overrides/main.html puts the CSS in every page's head."""

import colorsys

from macros import constant
from model.geometry import SPOOLS

PAPER = constant("model/render/blender.py", "BG")
INK = constant("model/render/blender.py", "BLACK_LIFT")
PINK = SPOOLS["Milky Pink"]
AA = 4.5  # WCAG 2 AA, normal text


def contrast(a, b):
    """WCAG 2's contrast ratio of two #RRGGBB colours."""

    def luminance(c):
        rgb = [int(c[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        r, g, b = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in rgb]
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    hi, lo = sorted([luminance(a), luminance(b)], reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def darkest_needed(colour, on):
    """The colour's hue and saturation, darkened until text in it reads at AA on `on`: the pink spool's links."""
    h, lightness, s = colorsys.rgb_to_hls(*(int(colour[i : i + 2], 16) / 255 for i in (1, 3, 5)))
    while True:
        c = "#" + "".join(f"{round(x * 255):02X}" for x in colorsys.hls_to_rgb(h, lightness, s))
        if contrast(c, on) >= AA:
            return c
        lightness -= 0.01


LINK = darkest_needed(PINK, PAPER)
SCHEMES = {  # Material's scheme: page, text, links and hovers (a filled hover's text on it)
    "default": (PAPER, INK, LINK),
    "slate": (INK, PAPER, PINK),
}


def css():
    blocks = [
        f"""[data-md-color-scheme={scheme}] {{
  --md-default-bg-color: {bg}; --md-default-fg-color: {fg}; --md-typeset-color: {fg};
  --md-primary-fg-color: {PINK}; --md-primary-fg-color--light: {PINK}; --md-primary-fg-color--dark: {PINK};
  --md-primary-bg-color: {INK}; --md-primary-bg-color--light: {INK};
  --md-typeset-a-color: {link}; --md-accent-fg-color: {link}; --md-accent-fg-color--transparent: {link}1A;
  --md-accent-bg-color: {bg};
}}"""
        for scheme, (bg, fg, link) in SCHEMES.items()
    ]
    # Material draws a plain button's text and border in the header's pink, too light on paper: the links' colour
    # instead; :where keeps its weight, so a hovered button's own colours still win
    return "\n".join(
        [*blocks, ".md-typeset .md-button:where(:not(.md-button--primary)) { color: var(--md-typeset-a-color); }"]
    )


def on_config(config):
    config.extra["palette"] = css()
