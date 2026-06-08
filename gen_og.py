#!/usr/bin/env python3
"""Render og.png (1200x630) for The Prompt Index — riso/zine card. Pillow only; graceful fallback."""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def _font(paths, size):
    from PIL import ImageFont
    for p in paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def main() -> int:
    try:
        from PIL import Image, ImageDraw
    except Exception:
        print("Pillow not available — skipping og.png")
        return 0
    try:
        data = json.load(open(os.path.join(HERE, "data.json"), encoding="utf-8"))
        count, cats = data.get("count", 0), len(data.get("categories", []))
    except Exception:
        count, cats = 0, 0

    W, H = 1200, 630
    bg, ink, coral, muted = (246, 242, 233), (22, 19, 16), (255, 59, 47), (92, 85, 74)
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    # halftone dots
    for y in range(0, H, 14):
        for x in range(0, W, 14):
            d.ellipse([x, y, x + 2, y + 2], fill=(22, 19, 16))
    d.rectangle([0, 0, W, H], outline=None)
    # solid panel over dots
    d.rectangle([40, 40, W - 40, H - 40], fill=bg, outline=ink, width=4)

    bold = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/Library/Fonts/Arial Bold.ttf"]
    mono = ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            "/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/Monaco.ttf"]
    f_kick = _font(mono, 24)
    f_h1 = _font(bold, 84)
    f_stat = _font(mono, 28)

    d.rectangle([72, 80, 96, 104], fill=coral)
    d.text((112, 78), "THE PROMPT INDEX", font=f_kick, fill=ink)
    d.text((72, 180), "The best", font=f_h1, fill=ink)
    # coral block behind "prompts"
    pw = d.textlength("prompts", font=f_h1)
    d.rectangle([72, 285, 72 + pw + 24, 385], fill=coral)
    d.text((84, 278), "prompts", font=f_h1, fill=bg)
    d.text((72, 388), "are versioned.", font=f_h1, fill=ink)
    d.text((72, 510), f"{count} resources  ·  {cats} categories  ·  ranked daily by GitHub momentum",
           font=f_stat, fill=muted)
    img.save(os.path.join(HERE, "og.png"))
    print(f"wrote og.png ({count} resources)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
