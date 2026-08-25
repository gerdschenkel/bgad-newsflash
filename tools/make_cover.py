#!/usr/bin/env python3
"""
BGAD News Flash cover generator.

Produces two assets:

  public/assets/newsflash-banner.jpg   1600x884  art only, static, used as the
                                       in-page banner. Regenerated only if missing.
  public/assets/covers/YYYY-MM-DD.png  1200x630  dated social card, used as og:image.

Why this exists: the old issues embedded a 400x221 JPEG as a base64 data URI.
That made the in-page banner soft, and it made og:image unusable, because link
crawlers such as Flipboard, LinkedIn and Slack fetch og:image as a URL and
cannot read a data URI. Both assets are now real files served from public/.

Usage:
    python3 tools/make_cover.py 2026-08-14
    python3 tools/make_cover.py            # defaults to today in Australia/Sydney

Requires Pillow:  pip install --break-system-packages pillow
"""

import os
import sys
from datetime import datetime, timezone, timedelta

from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PUBLIC = os.path.join(ROOT, "public")
ASSETS = os.path.join(PUBLIC, "assets")
COVERS = os.path.join(ASSETS, "covers")

SOURCE_ART = os.path.join(HERE, "cover-source.png")
LOGO = os.path.join(HERE, "bgad-logo.png")

# BGAD palette
BLUE = (2, 110, 201)
DARK = (2, 78, 143)
LIGHT = (57, 145, 217)
WHITE = (255, 255, 255)

CARD_W, CARD_H = 1200, 630
BANNER_W, BANNER_H = 1600, 884

# Liberation Sans is metric compatible with Arial and Helvetica, which is what
# the issue HTML uses, so the card matches the page.
FONT_DIR = "/usr/share/fonts/truetype/liberation"
F_BOLD = os.path.join(FONT_DIR, "LiberationSans-Bold.ttf")
F_REG = os.path.join(FONT_DIR, "LiberationSans-Regular.ttf")
F_ITAL = os.path.join(FONT_DIR, "LiberationSans-Italic.ttf")

FALLBACK_DIR = "/usr/share/fonts/truetype/dejavu"
FALLBACKS = {
    F_BOLD: os.path.join(FALLBACK_DIR, "DejaVuSans-Bold.ttf"),
    F_REG: os.path.join(FALLBACK_DIR, "DejaVuSans.ttf"),
    F_ITAL: os.path.join(FALLBACK_DIR, "DejaVuSans-Oblique.ttf"),
}


def font(path, size):
    if os.path.exists(path):
        return ImageFont.truetype(path, size)
    fb = FALLBACKS.get(path)
    if fb and os.path.exists(fb):
        return ImageFont.truetype(fb, size)
    return ImageFont.load_default()


def sydney_today():
    # Australia/Sydney is UTC+10, or UTC+11 during daylight saving
    # (first Sunday in October to first Sunday in April).
    now_utc = datetime.now(timezone.utc)
    y = now_utc.year

    def first_sunday(year, month):
        d = datetime(year, month, 1, tzinfo=timezone.utc)
        return d + timedelta(days=(6 - d.weekday()) % 7)

    dst_start = first_sunday(y, 10).replace(hour=16)   # 2am AEST
    dst_end = first_sunday(y, 4).replace(hour=16)      # 3am AEDT
    offset = 11 if (now_utc >= dst_start or now_utc < dst_end) else 10
    return (now_utc + timedelta(hours=offset)).date()


def art_crop(target_w, target_h):
    """Centre crop of the brand artwork at the requested aspect ratio."""
    im = Image.open(SOURCE_ART).convert("RGB")
    w, h = im.size

    # The source has a caption band burned into the bottom ~15 percent.
    # Stay above it so no stray wording appears on the card.
    usable_h = int(h * 0.84)

    ratio = target_w / target_h
    crop_h = min(usable_h, int(w / ratio))
    crop_w = int(crop_h * ratio)

    left = (w - crop_w) // 2
    # Bias upward so the face sits in the upper third rather than dead centre.
    top = max(0, int((usable_h - crop_h) * 0.42))

    im = im.crop((left, top, left + crop_w, top + crop_h))
    return im.resize((target_w, target_h), Image.LANCZOS)


def build_banner(force=False):
    """Art only wide banner for the top of the issue page."""
    out = os.path.join(ASSETS, "newsflash-banner.jpg")
    if os.path.exists(out) and not force:
        return out
    os.makedirs(ASSETS, exist_ok=True)
    art_crop(BANNER_W, BANNER_H).save(out, "JPEG", quality=88, optimize=True, progressive=True)
    return out


def build_card(date_str):
    """Dated 1200x630 social card: blue panel on the left, artwork on the right."""
    os.makedirs(COVERS, exist_ok=True)

    # Blue field across the whole card, with a gentle vertical lift, so the
    # artwork has something consistent to dissolve into and no seam shows.
    card = Image.new("RGB", (CARD_W, CARD_H), DARK)
    lift = Image.new("L", (1, CARD_H))
    for y in range(CARD_H):
        lift.putpixel((0, y), int(46 * (y / CARD_H)))
    card.paste(Image.new("RGB", (CARD_W, CARD_H), BLUE), (0, 0),
               lift.resize((CARD_W, CARD_H)))

    # Right hand artwork, faded in from the left over `seam` pixels
    art_w = 520
    seam = 210
    art = art_crop(art_w, CARD_H)
    mask = Image.new("L", (art_w, 1))
    for x in range(art_w):
        mask.putpixel((x, 0), 255 if x >= seam else int(255 * (x / seam) ** 1.4))
    card.paste(art, (CARD_W - art_w, 0), mask.resize((art_w, CARD_H)))

    d = ImageDraw.Draw(card)
    x = 64

    # Masthead: logo, wordmark, tagline
    y = 58
    if os.path.exists(LOGO):
        logo = Image.open(LOGO).convert("RGBA")
        lw = 92
        lh = int(logo.height * lw / logo.width)
        logo = logo.resize((lw, lh), Image.LANCZOS)
        # The extracted logo is on white, so drop the white to transparent
        px = logo.load()
        for iy in range(logo.height):
            for ix in range(logo.width):
                r, g, b, a = px[ix, iy]
                if r > 232 and g > 232 and b > 232:
                    px[ix, iy] = (r, g, b, 0)
        card.paste(logo, (x, y), logo)
        text_x = x + lw + 16
    else:
        text_x = x

    d.text((text_x, y + 6), "BGAD CONSULTING", font=font(F_BOLD, 25), fill=WHITE)
    d.text((text_x, y + 38), "STRATEGIES. DELIVERED.", font=font(F_BOLD, 16),
           fill=(178, 214, 246))

    # Rule
    d.rectangle([x, 152, x + 96, 156], fill=WHITE)

    # Masthead title
    d.text((x, 190), "BGAD", font=font(F_BOLD, 78), fill=WHITE)
    d.text((x, 272), "News Flash", font=font(F_BOLD, 78), fill=WHITE)

    # Subtitle
    d.text((x, 384), "Daily briefing: digital, tech and AI",
           font=font(F_ITAL, 29), fill=(196, 224, 249))

    # Date chip
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    pretty = f"{dt.day} {dt.strftime('%B %Y')}"
    f_date = font(F_BOLD, 27)
    tw = d.textlength(pretty, font=f_date)
    d.rounded_rectangle([x, 448, x + tw + 40, 504], radius=28, fill=WHITE)
    d.text((x + 20, 459), pretty, font=f_date, fill=DARK)

    out = os.path.join(COVERS, f"{date_str}.png")
    card.save(out, "PNG", optimize=True)
    return out


def main():
    date_str = sys.argv[1] if len(sys.argv) > 1 else sydney_today().isoformat()
    datetime.strptime(date_str, "%Y-%m-%d")  # validate

    banner = build_banner(force="--force-banner" in sys.argv)
    card = build_card(date_str)

    for p in (banner, card):
        print(f"{os.path.relpath(p, ROOT)}  {os.path.getsize(p) / 1024:.0f} KB  "
              f"{Image.open(p).size[0]}x{Image.open(p).size[1]}")


if __name__ == "__main__":
    main()
