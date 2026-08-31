#!/usr/bin/env python3
import os
import html
import numpy as np
import cv2
from PIL import Image, ImageEnhance

HERE = os.path.dirname(os.path.abspath(__file__))
AVATAR = "/tmp/anass_headshot.png"
PREPPED_PATH = os.path.join(HERE, "..", "source-prepped.png")
OUT_SVG = os.path.join(HERE, "..", "anass-ascii.svg")

img = cv2.imread(AVATAR)
if img is None:
    raise ValueError(f"Could not load {AVATAR}")

# Convert to grayscale
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# Apply CLAHE to extract face features, eyes, hair highlights
clahe = cv2.createCLAHE(clipLimit=3.5, tileGridSize=(8, 8))
gray = clahe.apply(gray)
gray = cv2.normalize(gray, None, alpha=15, beta=245, norm_type=cv2.NORM_MINMAX)

prepped = Image.fromarray(gray, mode="L")
prepped.save(PREPPED_PATH)

COLS, ROWS, CELL_W, CELL_H = 100, 53, 8, 15
RAMP = " .`:-=+*cs#%@"

im = ImageEnhance.Contrast(ImageEnhance.Brightness(prepped).enhance(1.0)).enhance(1.25)
im = im.resize((COLS, ROWS), Image.LANCZOS)
px = im.load()

rows_txt = []
for y in range(ROWS):
    chars = []
    for x in range(COLS):
        lum = pow(px[x, y] / 255.0, 1.15)
        if lum >= 0.88:
            chars.append(" ")
        else:
            idx = int((1.0 - lum) * (len(RAMP) - 1) + 0.5)
            chars.append(RAMP[max(0, min(len(RAMP) - 1, idx))])
    rows_txt.append("".join(chars))

PAD, TITLEBAR_H, STATUS_H = 20, 30, 30
ART_W, ART_H = COLS * CELL_W, ROWS * CELL_H
CANVAS_W, CANVAS_H = ART_W + PAD * 2, TITLEBAR_H + ART_H + STATUS_H + PAD
BG, BG2, FRAME, TITLE_TEXT, INK, CURSOR = "#0d1117", "#111722", "#30363d", "#7d8590", "#c9d1d9", "#c9d1d9"
ROW_DUR, STAGGER = 0.11, 0.11

parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_W}" height="{CANVAS_H}" '
    f'viewBox="0 0 {CANVAS_W} {CANVAS_H}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">',
    '<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#111722"/><stop offset="1" stop-color="#0d1117"/>'
    '</linearGradient></defs>',
    f'<rect width="{CANVAS_W}" height="{CANVAS_H}" rx="12" fill="url(#bg)"/>',
    f'<rect x="0.5" y="0.5" width="{CANVAS_W-1}" height="{CANVAS_H-1}" rx="12" fill="none" stroke="#30363d" stroke-width="1"/>',
    f'<line x1="0" y1="30" x2="{CANVAS_W}" y2="30" stroke="#30363d"/>',
    '<circle cx="20" cy="15" r="5" fill="#ff5f56"/>',
    '<circle cx="36" cy="15" r="5" fill="#ffbd2e"/>',
    '<circle cx="52" cy="15" r="5" fill="#27c93f"/>',
    f'<text x="{CANVAS_W/2}" y="19" fill="#7d8590" font-size="12" text-anchor="middle">anass@github: ~$ ./portrait.sh</text>'
]

art_top = TITLEBAR_H + PAD * 0.35
font_size = CELL_H * 0.86

for ry, line in enumerate(rows_txt):
    y = art_top + ry * CELL_H + CELL_H * 0.74
    row_y = art_top + ry * CELL_H
    delay = ry * STAGGER
    safe = html.escape(line)
    text = (f'<text xml:space="preserve" x="{PAD}" y="{y:.1f}" fill="{INK}" '
            f'font-size="{font_size:.1f}" textLength="{ART_W}" lengthAdjust="spacing">{safe}</text>')

    parts.append(
        f'<clipPath id="r{ry}"><rect x="{PAD}" y="{row_y:.1f}" height="{CELL_H}" width="0">'
        f'<animate attributeName="width" from="0" to="{ART_W}" begin="{delay:.3f}s" '
        f'dur="{ROW_DUR:.2f}s" fill="freeze"/></rect></clipPath>'
    )
    parts.append(f'<g clip-path="url(#r{ry})">{text}</g>')
    parts.append(
        f'<rect y="{row_y+1:.1f}" width="{CELL_W}" height="{CELL_H-2}" fill="{CURSOR}" opacity="0">'
        f'<animate attributeName="x" from="{PAD}" to="{PAD+ART_W}" begin="{delay:.3f}s" '
        f'dur="{ROW_DUR:.2f}s" fill="freeze"/>'
        f'<set attributeName="opacity" to="0.85" begin="{delay:.3f}s"/>'
        f'<set attributeName="opacity" to="0" begin="{delay+ROW_DUR:.3f}s"/></rect>'
    )

status_line_y = TITLEBAR_H + ART_H + PAD * 0.35
status_y = status_line_y + 19
parts.append(f'<line x1="0" y1="{status_line_y:.1f}" x2="{CANVAS_W}" y2="{status_line_y:.1f}" stroke="{FRAME}"/>')
parts.append(f'<text x="{PAD}" y="{status_y:.1f}" fill="{TITLE_TEXT}" font-size="13">'
             f'anass@github:~$ whoami <tspan fill="{INK}">Anass Agdi</tspan></text>')
parts.append(f'<rect x="{PAD+204}" y="{status_y-12:.1f}" width="8" height="14" fill="{INK}">'
             f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.51;1" '
             f'dur="1s" repeatCount="indefinite"/></rect>')
parts.append("</svg>")

svg_out = "".join(parts)
with open(OUT_SVG, "w", encoding="utf-8") as f:
    f.write(svg_out)
print(f"Generated {OUT_SVG} ({len(svg_out)} bytes)")
