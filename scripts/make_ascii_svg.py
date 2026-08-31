#!/usr/bin/env python3
"""
Convert portrait photo into an Andrew6rant-style monochrome ASCII portrait SVG.
Produces a crisp, high-density face rendering that types row-by-row.
Strictly escapes all XML text and validates XML before saving.
"""
import html
import os
import sys
import xml.etree.ElementTree as ET
import cv2
import numpy as np
from PIL import Image, ImageEnhance

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "source-photo.jpg")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "anass-ascii.svg")

img = cv2.imread(SRC)
if img is None:
    raise FileNotFoundError(f"Cannot read {SRC}")

h, w = img.shape[:2]
min_dim = min(h, w)
top = int((h - min_dim) * 0.15)
left = int((w - min_dim) * 0.5)
crop = img[top:top+min_dim, left:left+min_dim]

gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

# Apply CLAHE to extract face contours, eyes, nose, hair
clahe = cv2.createCLAHE(clipLimit=2.8, tileGridSize=(8, 8))
gray = clahe.apply(gray)

# Vignette outer background to white so outside subject maps to empty terminal spaces
ch, cw = gray.shape
center = (cw // 2, int(ch * 0.48))
mask = np.zeros((ch, cw), dtype=np.float32)
cv2.ellipse(mask, center, (int(cw * 0.44), int(ch * 0.50)), 0, 0, 360, 1.0, -1)
mask = cv2.GaussianBlur(mask, (45, 45), 0)
isolated = gray.astype(np.float32) * mask + 255.0 * (1.0 - mask)
isolated = np.clip(isolated, 0, 255).astype(np.uint8)

COLS = 84
ROWS = 46
CELL_W = 9.0
CELL_H = 16.0
RAMP = " .:-=+*cs#%@"

pil_im = Image.fromarray(isolated, mode="L")
pil_im = ImageEnhance.Contrast(pil_im).enhance(1.25)
pil_im = pil_im.resize((COLS, ROWS), Image.LANCZOS)
px = pil_im.load()

rows_txt = []
for y in range(ROWS):
    chars = []
    for x in range(COLS):
        val = px[x, y] / 255.0
        if val >= 0.93:
            chars.append(" ")
        else:
            idx = int((1.0 - val) * (len(RAMP) - 1))
            idx = max(0, min(len(RAMP) - 1, idx))
            chars.append(RAMP[idx])
    rows_txt.append("".join(chars))

PAD = 20
TITLEBAR_H = 30
STATUS_H = 30
ART_W = int(COLS * CELL_W)
ART_H = int(ROWS * CELL_H)
CANVAS_W = ART_W + PAD * 2
CANVAS_H = TITLEBAR_H + ART_H + STATUS_H + PAD

BG = "#0d1117"
BG2 = "#111722"
FRAME = "#30363d"
TITLE_TEXT = "#7d8590"
INK = "#c9d1d9"
CURSOR = "#c9d1d9"

ROW_DUR = 0.08
STAGGER = 0.08

parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_W}" height="{CANVAS_H}" '
    f'viewBox="0 0 {CANVAS_W} {CANVAS_H}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">',
    '<defs><linearGradient id="pbg" x1="0" y1="0" x2="0" y2="1">'
    f'<stop offset="0" stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/>'
    '</linearGradient></defs>',
    f'<rect width="{CANVAS_W}" height="{CANVAS_H}" rx="12" fill="url(#pbg)"/>',
    f'<rect x="0.5" y="0.5" width="{CANVAS_W-1}" height="{CANVAS_H-1}" rx="12" fill="none" stroke="{FRAME}" stroke-width="1"/>',
    f'<line x1="0" y1="{TITLEBAR_H}" x2="{CANVAS_W}" y2="{TITLEBAR_H}" stroke="{FRAME}"/>',
    f'<circle cx="{PAD}" cy="{TITLEBAR_H/2}" r="5" fill="#ff5f56"/>',
    f'<circle cx="{PAD+16}" cy="{TITLEBAR_H/2}" r="5" fill="#ffbd2e"/>',
    f'<circle cx="{PAD+32}" cy="{TITLEBAR_H/2}" r="5" fill="#27c93f"/>',
    f'<text x="{CANVAS_W/2}" y="{TITLEBAR_H/2 + 4}" fill="{TITLE_TEXT}" font-size="12" text-anchor="middle">anass@github: ~$ ./portrait.sh</text>'
]

art_top = TITLEBAR_H + PAD * 0.4
font_size = CELL_H * 0.88

for ry, line in enumerate(rows_txt):
    y = art_top + ry * CELL_H + CELL_H * 0.74
    row_y = art_top + ry * CELL_H
    delay = ry * STAGGER
    safe = html.escape(line)
    text = (f'<text xml:space="preserve" x="{PAD}" y="{y:.1f}" fill="{INK}" '
            f'font-size="{font_size:.1f}" textLength="{ART_W}" lengthAdjust="spacing">{safe}</text>')

    parts.append(
        f'<clipPath id="pr{ry}"><rect x="{PAD}" y="{row_y:.1f}" height="{CELL_H}" width="0">'
        f'<animate attributeName="width" from="0" to="{ART_W}" begin="{delay:.3f}s" '
        f'dur="{ROW_DUR:.2f}s" fill="freeze"/></rect></clipPath>'
    )
    parts.append(f'<g clip-path="url(#pr{ry})">{text}</g>')
    parts.append(
        f'<rect y="{row_y+1:.1f}" width="{CELL_W}" height="{CELL_H-2}" fill="{CURSOR}" opacity="0">'
        f'<animate attributeName="x" from="{PAD}" to="{PAD+ART_W}" begin="{delay:.3f}s" '
        f'dur="{ROW_DUR:.2f}s" fill="freeze"/>'
        f'<set attributeName="opacity" to="0.85" begin="{delay:.3f}s"/>'
        f'<set attributeName="opacity" to="0" begin="{delay+ROW_DUR:.3f}s"/></rect>'
    )

status_line_y = TITLEBAR_H + ART_H + PAD * 0.4
status_y = status_line_y + 20
parts.append(f'<line x1="0" y1="{status_line_y:.1f}" x2="{CANVAS_W}" y2="{status_line_y:.1f}" stroke="{FRAME}"/>')
parts.append(f'<text x="{PAD}" y="{status_y:.1f}" fill="{TITLE_TEXT}" font-size="13">'
             f'anass@github:~$ whoami <tspan fill="{INK}">Anass Agdi</tspan></text>')
parts.append(f'<rect x="{PAD+204}" y="{status_y-12:.1f}" width="8" height="14" fill="{INK}">'
             f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.51;1" '
             f'dur="1s" repeatCount="indefinite"/></rect>')

parts.append("</svg>")
svg = "".join(parts)

# XML Validation check
ET.fromstring(svg)

with open(OUT, "w", encoding="utf-8") as f:
    f.write(svg)
print(f"Validated and wrote {OUT} ({CANVAS_W}x{CANVAS_H}, {len(svg)} bytes)")
