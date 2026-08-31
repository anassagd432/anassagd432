#!/usr/bin/env python3
"""
Generate an animated neofetch-style terminal info card SVG for Anass Agdi.
Uses pure SMIL animations (100% compliant with GitHub SVG rendering).
Strictly escapes all XML characters (&, <, >).
"""
import html
import os
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "info-card.svg")

CANVAS_W = 490
CANVAS_H = 432
PAD = 20
TITLEBAR_H = 30

BG = "#0d1117"
BG2 = "#111722"
FRAME = "#30363d"
TITLE_TEXT = "#7d8590"
MUTED = "#8b949e"
KEY_COLOR = "#58a6ff"
VAL_COLOR = "#c9d1d9"
ACCENT_GREEN = "#3fb950"
ACCENT_CYAN = "#38bdf8"

STAGGER = 0.08

info_lines = [
    {"type": "prompt", "user": "anass", "host": "agdi-ai", "cmd": "neofetch --short"},
    {"type": "separator"},
    {"key": "User", "val": "Anass Agdi", "hl": True},
    {"key": "Role", "val": "AI Engineer & Automation Architect"},
    {"key": "Company", "val": "Agdi AI (agdi.ai)"},
    {"key": "Location", "val": "Ibiza, Spain [ES]"},
    {"key": "Focus", "val": "AI Agents | Autonomous Systems | SaaS"},
    {"key": "Core Stack", "val": "Python, TypeScript, Next.js, FastAPI, Node"},
    {"key": "AI & Data", "val": "LLMs, PyTorch, LangChain, Vector DBs"},
    {"key": "DevOps", "val": "Docker, GitHub Actions, Playwright, Linux"},
    {"key": "Website", "val": "anassagdi.site"},
    {"key": "Status", "val": "> Building & Shipping AI systems", "status": True},
]

PALETTE = [
    "#ff5555", "#50fa7b", "#f1fa8c", "#bd93f9", "#ff79c6", "#8be9fd", "#f8f8f2",
    "#ff6e6e", "#69ff94", "#ffffa5", "#d6acff", "#ff92df", "#a4ffff", "#ffffff"
]

def render():
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_W}" height="{CANVAS_H}" '
        f'viewBox="0 0 {CANVAS_W} {CANVAS_H}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">',
        '<defs>',
        f'<linearGradient id="cbg" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/>'
        '</linearGradient>',
        '</defs>',
        f'<rect width="{CANVAS_W}" height="{CANVAS_H}" rx="12" fill="url(#cbg)"/>',
        f'<rect x="0.5" y="0.5" width="{CANVAS_W-1}" height="{CANVAS_H-1}" rx="12" fill="none" stroke="{FRAME}" stroke-width="1"/>',
        f'<line x1="0" y1="{TITLEBAR_H}" x2="{CANVAS_W}" y2="{TITLEBAR_H}" stroke="{FRAME}"/>',
    ]

    for i, dot in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        parts.append(f'<circle cx="{PAD + i*16}" cy="{TITLEBAR_H/2}" r="5" fill="{dot}"/>')
    parts.append(f'<text x="{CANVAS_W/2}" y="{TITLEBAR_H/2 + 4}" fill="{TITLE_TEXT}" '
                 f'font-size="12" text-anchor="middle">anass@github: ~/whoami</text>')

    start_y = TITLEBAR_H + 24
    line_h = 24

    for idx, item in enumerate(info_lines):
        y = start_y + idx * line_h
        delay = idx * STAGGER

        if item.get("type") == "prompt":
            u = html.escape(f"{item['user']}@{item['host']}")
            cmd = html.escape(item["cmd"])
            parts.append(
                f'<g opacity="0">'
                f'<set attributeName="opacity" to="1" begin="{delay:.2f}s"/>'
                f'<text x="{PAD}" y="{y}" font-size="13">'
                f'<tspan fill="{ACCENT_GREEN}" font-weight="700">{u}</tspan>'
                f'<tspan fill="{MUTED}">:$ </tspan>'
                f'<tspan fill="{VAL_COLOR}">{cmd}</tspan>'
                f'</text></g>'
            )
        elif item.get("type") == "separator":
            parts.append(
                f'<g opacity="0">'
                f'<set attributeName="opacity" to="1" begin="{delay:.2f}s"/>'
                f'<line x1="{PAD}" y1="{y-6}" x2="{CANVAS_W-PAD}" y2="{y-6}" stroke="{FRAME}" stroke-opacity="0.6"/>'
                f'</g>'
            )
        else:
            k = html.escape(f"{item['key']:<14}")
            v = html.escape(item["val"])
            val_fill = ACCENT_CYAN if item.get("hl") else (ACCENT_GREEN if item.get("status") else VAL_COLOR)
            font_weight = "bold" if item.get("hl") else "normal"
            parts.append(
                f'<g opacity="0">'
                f'<set attributeName="opacity" to="1" begin="{delay:.2f}s"/>'
                f'<text x="{PAD}" y="{y}" font-size="12">'
                f'<tspan fill="{KEY_COLOR}" font-weight="600">{k}</tspan>'
                f'<tspan fill="{MUTED}">: </tspan>'
                f'<tspan fill="{val_fill}" font-weight="{font_weight}">{v}</tspan>'
                f'</text></g>'
            )

    pal_y = start_y + len(info_lines) * line_h + 12
    delay = len(info_lines) * STAGGER
    
    parts.append(f'<g opacity="0"><set attributeName="opacity" to="1" begin="{delay:.2f}s"/>')
    parts.append(f'<line x1="{PAD}" y1="{pal_y-14}" x2="{CANVAS_W-PAD}" y2="{pal_y-14}" stroke="{FRAME}" stroke-opacity="0.4"/>')
    swatch_w = 22
    swatch_h = 10
    for i, col in enumerate(PALETTE):
        x = PAD + i * (swatch_w + 5)
        parts.append(f'<rect x="{x}" y="{pal_y}" width="{swatch_w}" height="{swatch_h}" rx="2" fill="{col}"/>')
    parts.append('</g>')

    parts.append('</svg>')
    svg_raw = "".join(parts)
    # Strict XML validation check
    ET.fromstring(svg_raw)
    return svg_raw


if __name__ == "__main__":
    svg = render()
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Validated and wrote {OUT} ({len(svg)} bytes)")
