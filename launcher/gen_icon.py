# -*- coding: utf-8 -*-
"""生成 Bot 图标 bot.ico（可选，已生成可直接删除本脚本）。"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
OUT = HERE / "bot.ico"

size = 512
img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
# 圆角渐变底
for y in range(size):
    t = y / size
    r = int(255 - 40 * t)
    g = int(138 - 60 * t)
    b = int(61 - 20 * t)
    d.line([(0, y), (size, y)], fill=(r, g, b, 255))
mask = Image.new("L", (size, size), 0)
md = ImageDraw.Draw(mask)
md.rounded_rectangle((0, 0, size - 1, size - 1), radius=110, fill=255)
img.putalpha(mask)

font = None
for fp in (r"C:\Windows\Fonts\msyhbd.ttc", r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"):
    try:
        font = ImageFont.truetype(fp, 300)
        break
    except Exception:
        pass
if font:
    text = "课"
    bbox = d.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((size - tw) / 2 - bbox[0], (size - th) / 2 - bbox[1]), text, font=font, fill=(255, 245, 235, 255))
else:
    d.ellipse((150, 150, 362, 362), fill=(255, 245, 235, 255))

img.save(OUT, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("saved", OUT, OUT.stat().st_size, "bytes")
