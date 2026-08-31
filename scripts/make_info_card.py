#!/usr/bin/env python3
"""
Generate an animated neofetch-style terminal info card SVG for Anass Agdi.
Includes terminal title bar, user prompt, structured key-value stats,
and terminal ANSI color palette swatches.

Line-by-line staggered animation plays on load, then holds.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "info-card.svg")

STATIC = bool(os.environ.get("STATIC"))

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
ACCENT_YELLOW = "#e3b341"

LINE_DUR = 0.4
STAGGER = 0.12

info_lines = [
    {"type": "prompt", "user": "anass", "host": "agdi-ai", "cmd": "neofetch --short"},
    {"type": "separator"},
    {"key": "User", "val": "Anass Agdi", "hl": True},
    {"key": "Role", "val": "AI Engineer & Automation Architect"},
    {"key": "Company", "val": "Agdi AI (agdi.ai)"},
    {"key": "Location", "val": "Ibiza, Spain 🇪🇸"},
    {"key": "Focus", "val": "AI Agents · Autonomous Systems · Full-Stack SaaS"},
    {"key": "Core Stack", "val": "Python, TypeScript, Next.js, FastAPI, Node.js"},
    {"key": "AI & Data", "val": "LLMs, PyTorch, LangChain, Claude Code, Vector DBs"},
    {"key": "DevOps & Tools", "val": "Docker, GitHub Actions, Playwright, Linux, n8n"},
    {"key": "Website", "val": "anassagdi.site", "link": "https://anassagdi.site"},
    {"key": "Status", "val": "🚀 Shipping intelligent agents & high-impact software", "status": True},
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
        '<style>',
        '@keyframes fadeSlide {',
        '  0%   { opacity: 0; transform: translateY(6px); }',
        '  100% { opacity: 1; transform: translateY(0); }',
        '}',
        f'.line {{ opacity: 0; animation: fadeSlide {LINE_DUR:.2f}s cubic-bezier(.2,.8,.2,1) both; }}',
        '</style>' if not STATIC else '',
        f'<rect width="{CANVAS_W}" height="{CANVAS_H}" rx="12" fill="url(#cbg)"/>',
        f'<rect x="0.5" y="0.5" width="{CANVAS_W-1}" height="{CANVAS_H-1}" rx="12" '
        f'fill="none" stroke="{FRAME}" stroke-width="1"/>',
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
        anim_attr = f' class="line" style="animation-delay:{delay:.3f}s"' if not STATIC else ''

        if item.get("type") == "prompt":
            parts.append(
                f'<g{anim_attr}>'
                f'<text x="{PAD}" y="{y}" font-size="13">'
                f'<tspan fill="{ACCENT_GREEN}" font-weight="700">{item["user"]}@{item["host"]}</tspan>'
                f'<tspan fill="{MUTED}">:$ </tspan>'
                f'<tspan fill="{VAL_COLOR}">{item["cmd"]}</tspan>'
                f'</text></g>'
            )
        elif item.get("type") == "separator":
            parts.append(
                f'<g{anim_attr}>'
                f'<line x1="{PAD}" y1="{y-6}" x2="{CANVAS_W-PAD}" y2="{y-6}" stroke="{FRAME}" stroke-opacity="0.6"/>'
                f'</g>'
            )
        else:
            k = item["key"]
            v = item["val"]
            val_fill = ACCENT_CYAN if item.get("hl") else (ACCENT_GREEN if item.get("status") else VAL_COLOR)
            font_weight = "bold" if item.get("hl") else "normal"
            parts.append(
                f'<g{anim_attr}>'
                f'<text x="{PAD}" y="{y}" font-size="12">'
                f'<tspan fill="{KEY_COLOR}" font-weight="600">{k:<14}</tspan>'
                f'<tspan fill="{MUTED}">: </tspan>'
                f'<tspan fill="{val_fill}" font-weight="{font_weight}">{v}</tspan>'
                f'</text></g>'
            )

    # ANSI palette dots at bottom
    pal_y = start_y + len(info_lines) * line_h + 12
    delay = len(info_lines) * STAGGER
    anim_attr = f' class="line" style="animation-delay:{delay:.3f}s"' if not STATIC else ''
    
    parts.append(f'<g{anim_attr}>')
    parts.append(f'<line x1="{PAD}" y1="{pal_y-14}" x2="{CANVAS_W-PAD}" y2="{pal_y-14}" stroke="{FRAME}" stroke-opacity="0.4"/>')
    swatch_w = 22
    swatch_h = 10
    for i, col in enumerate(PALETTE):
        x = PAD + i * (swatch_w + 5)
        parts.append(f'<rect x="{x}" y="{pal_y}" width="{swatch_w}" height="{swatch_h}" rx="2" fill="{col}"/>')
    parts.append('</g>')

    parts.append('</svg>')
    return "".join(parts)


if __name__ == "__main__":
    svg = render()
    with open(OUT, "w") as f:
        f.write(svg)
    print(f"wrote {OUT} ({len(svg)} bytes)")
