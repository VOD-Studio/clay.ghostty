"""Render scripts/preview.sh with a Clay theme into an SVG terminal mock-up.

Usage: python3 scripts/render.py themes/clay-dark assets/clay-dark.svg

The image also shows the Ghostty-side colors that ANSI output cannot reach:
the titlebar, a selection, search matches and the cursor.
"""

from __future__ import annotations

import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass, replace
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PREVIEW = ROOT / "scripts" / "preview.sh"

FONT = "'JetBrains Mono', 'SF Mono', Menlo, Consolas, 'DejaVu Sans Mono', monospace"
FONT_SIZE = 14
CELL_W = FONT_SIZE * 0.6
LINE_H = 20
PAD = 20
TITLE_H = 36
RADIUS = 10
FAINT_OPACITY = 0.5  # Ghostty default

SEARCH = "selection"  # term highlighted as search matches
SELECT = "listening on :8080"  # text highlighted as a selection
SGR = re.compile(r"\x1b\[([0-9;]*)m")


@dataclass(frozen=True)
class Style:
    fg: str | None = None  # None means the default foreground
    bg: str | None = None  # None means the default background
    bold: bool = False
    dim: bool = False
    italic: bool = False
    underline: bool = False
    reverse: bool = False


def parse_theme(path: Path) -> dict[str, str]:
    colors: dict[str, str] = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = (part.strip() for part in line.partition("="))
        if key == "palette":
            index, _, value = (part.strip() for part in value.partition("="))
            key = f"palette {int(index)}"
        colors[key] = value
    return colors


def apply_sgr(style: Style, params: str, theme: dict[str, str]) -> Style:
    codes = [int(p) for p in params.split(";") if p] or [0]
    for code in codes:
        if code == 0:
            style = Style()
        elif code == 1:
            style = replace(style, bold=True)
        elif code == 2:
            style = replace(style, dim=True)
        elif code == 3:
            style = replace(style, italic=True)
        elif code == 4:
            style = replace(style, underline=True)
        elif code == 7:
            style = replace(style, reverse=True)
        elif code == 22:
            style = replace(style, bold=False, dim=False)
        elif code == 23:
            style = replace(style, italic=False)
        elif code == 24:
            style = replace(style, underline=False)
        elif code == 27:
            style = replace(style, reverse=False)
        elif 30 <= code <= 37:
            style = replace(style, fg=theme[f"palette {code - 30}"])
        elif 90 <= code <= 97:
            style = replace(style, fg=theme[f"palette {code - 90 + 8}"])
        elif code == 39:
            style = replace(style, fg=None)
        elif 40 <= code <= 47:
            style = replace(style, bg=theme[f"palette {code - 40}"])
        elif 100 <= code <= 107:
            style = replace(style, bg=theme[f"palette {code - 100 + 8}"])
        elif code == 49:
            style = replace(style, bg=None)
    return style


def parse_ansi(text: str, theme: dict[str, str]) -> list[list[tuple[str, Style]]]:
    lines: list[list[tuple[str, Style]]] = [[]]
    style = Style()
    pos = 0
    for match in [*SGR.finditer(text), None]:
        end = match.start() if match else len(text)
        for ch in text[pos:end]:
            if ch == "\n":
                lines.append([])
            else:
                lines[-1].append((ch, style))
        if match:
            style = apply_sgr(style, match.group(1), theme)
            pos = match.end()
    while lines and not lines[-1]:
        lines.pop()
    while lines and not lines[0]:
        lines.pop(0)
    return lines


def overlay(line: list[tuple[str, Style]], start: int, length: int, fg: str, bg: str) -> None:
    for i in range(start, start + length):
        ch, style = line[i]
        line[i] = (ch, replace(style, fg=fg, bg=bg, dim=False, reverse=False))


def add_ghostty_ui(lines: list[list[tuple[str, Style]]], theme: dict[str, str]) -> None:
    """Paint search matches, a selection and a prompt with the cursor."""
    matches = []
    for row, line in enumerate(lines):
        text = "".join(ch for ch, _ in line)
        matches += [(row, m.start()) for m in re.finditer(re.escape(SEARCH), text)]
        col = text.find(SELECT)
        if col >= 0:
            overlay(line, col, len(SELECT), theme["selection-foreground"], theme["selection-background"])
    for n, (row, col) in enumerate(matches):
        current = n == len(matches) - 1
        prefix = "search-selected-" if current else "search-"
        overlay(lines[row], col, len(SEARCH), theme[prefix + "foreground"], theme[prefix + "background"])

    prompt = Style(fg=theme["palette 2"], bold=True)
    cursor = Style(fg=theme["cursor-text"], bg=theme["cursor-color"])
    lines += [[], [("❯", prompt), (" ", Style()), (" ", cursor)]]


def width(ch: str) -> int:
    return 2 if unicodedata.east_asian_width(ch) in "WF" else 1


def resolve(style: Style, theme: dict[str, str]) -> tuple[str, str | None]:
    fg = style.fg or theme["foreground"]
    bg = style.bg
    if style.reverse:
        fg, bg = bg or theme["background"], fg
    if style.dim:
        fg = mix(fg, bg or theme["background"], FAINT_OPACITY)
    return fg, bg


def mix(top: str, bottom: str, alpha: float) -> str:
    a = [int(top[i : i + 2], 16) for i in (1, 3, 5)]
    b = [int(bottom[i : i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x * alpha + y * (1 - alpha)):02x}" for x, y in zip(a, b))


def render(theme_path: Path) -> str:
    theme = parse_theme(theme_path)
    ansi = subprocess.run([str(PREVIEW)], capture_output=True, text=True, check=True).stdout
    lines = parse_ansi(ansi, theme)
    add_ghostty_ui(lines, theme)

    cols = max(sum(width(ch) for ch, _ in line) for line in lines)
    w = round(cols * CELL_W + 2 * PAD)
    h = TITLE_H + len(lines) * LINE_H + 2 * PAD
    bg, title_bg = theme["background"], theme["window-titlebar-background"]
    name = theme_path.name

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'font-family="{escape(FONT)}" font-size="{FONT_SIZE}">',
        f"<title>{name}</title>",
        f'<clipPath id="window"><rect width="{w}" height="{h}" rx="{RADIUS}"/></clipPath>',
        '<g clip-path="url(#window)">',
        f'<rect width="{w}" height="{h}" fill="{bg}"/>',
        f'<rect width="{w}" height="{TITLE_H}" fill="{title_bg}"/>',
        f'<line x1="0" y1="{TITLE_H - 0.5}" x2="{w}" y2="{TITLE_H - 0.5}" '
        f'stroke="{theme["split-divider-color"]}"/>',
        f'<text x="{w / 2}" y="{TITLE_H / 2}" dominant-baseline="central" text-anchor="middle" '
        f'fill="{theme["window-titlebar-foreground"]}">{name}</text>',
    ]

    for row, line in enumerate(lines):
        y = TITLE_H + PAD + row * LINE_H
        col = 0
        runs: list[tuple[int, int, str, Style]] = []  # start col, cells, text, style
        for ch, style in line:
            cells = width(ch)
            if runs and runs[-1][3] == style and width(runs[-1][2][-1]) == cells:
                start, n, text, _ = runs[-1]
                runs[-1] = (start, n + cells, text + ch, style)
            else:
                runs.append((col, cells, ch, style))
            col += cells
        for start, cells, text, style in runs:
            fg, cell_bg = resolve(style, theme)
            x = PAD + start * CELL_W
            if cell_bg:
                out.append(
                    f'<rect x="{x:.1f}" y="{y}" width="{cells * CELL_W:.1f}" height="{LINE_H}" '
                    f'fill="{cell_bg}"/>'
                )
            if not text.strip():
                continue
            attrs = [f'x="{x:.1f}"', f'y="{y + LINE_H / 2}"', f'fill="{fg}"']
            attrs.append(f'textLength="{cells * CELL_W:.1f}" lengthAdjust="spacingAndGlyphs"')
            if style.bold:
                attrs.append('font-weight="bold"')
            if style.italic:
                attrs.append('font-style="italic"')
            if style.underline:
                attrs.append('text-decoration="underline"')
            out.append(
                f'<text {" ".join(attrs)} dominant-baseline="central" xml:space="preserve">'
                f"{escape(text)}</text>"
            )

    out += ["</g>", "</svg>", ""]
    return "\n".join(out)


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__.strip().splitlines()[2], file=sys.stderr)
        return 2
    Path(sys.argv[2]).write_text(render(Path(sys.argv[1])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
