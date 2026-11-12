"""Check the Clay Ghostty themes against the Clay design rules.

Run from the repository root: python3 tests/check.py
Uses only the standard library. Ghostty validation is skipped when the
`ghostty` executable is not on PATH.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THEMES = {"dark": ROOT / "themes" / "clay-dark", "light": ROOT / "themes" / "clay-light"}

CLAY = "#d97757"
# Slots where Clay marks focus. Clay must not appear anywhere else.
CLAY_SLOTS = {"cursor-color", "search-selected-background", "palette 1", "palette 9"}
REQUIRED = {
    "background",
    "foreground",
    "cursor-color",
    "cursor-text",
    "selection-background",
    "selection-foreground",
    "search-background",
    "search-foreground",
    "search-selected-background",
    "search-selected-foreground",
    "split-divider-color",
    "unfocused-split-fill",
    "window-titlebar-background",
    "window-titlebar-foreground",
} | {f"palette {i}" for i in range(16)}
# Ghostty's default unfocused-split-opacity.
UNFOCUSED_OPACITY = 0.7
# Palette slots that hold the same text role in both variants. 0, 7 and 15
# differ by design (ANSI names are absolute), 1 and 9 are Clay.
MIRRORED_TEXT = ["foreground"] + [f"palette {i}" for i in (2, 3, 4, 5, 6, 8, 10, 11, 12, 13, 14)]
# Surfaces stack away from the background by the same L* distance in both
# variants, in opposite directions.
MIRRORED_SURFACES = [
    "selection-background",
    "search-background",
    "split-divider-color",
    "window-titlebar-background",
]
HEX = re.compile(r"^#[0-9a-f]{6}$")

results = {"pass": 0, "fail": 0, "skip": 0}


def report(status: str, name: str, detail: str = "") -> None:
    results[status] += 1
    line = f"{status.upper():4}  {name}"
    if detail:
        line += f"\n      {detail}"
    print(line)


def check(name: str, ok: bool, detail: str = "") -> None:
    report("pass" if ok else "fail", name, "" if ok else detail)


def parse(path: Path) -> dict[str, str]:
    colors: dict[str, str] = {}
    for number, raw in enumerate(path.read_text().splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = (part.strip() for part in line.partition("="))
        if not sep:
            raise ValueError(f"{path.name}:{number}: expected 'key = value'")
        if key == "palette":
            index, sep, value = (part.strip() for part in value.partition("="))
            if not sep:
                raise ValueError(f"{path.name}:{number}: expected 'palette = N=#rrggbb'")
            key = f"palette {int(index)}"
        if key in colors:
            raise ValueError(f"{path.name}:{number}: duplicate {key}")
        colors[key] = value
    return colors


def rgb(color: str) -> tuple[int, int, int]:
    return tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))  # type: ignore[return-value]


def luminance(color: str) -> float:
    def channel(value: int) -> float:
        c = value / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(v) for v in rgb(color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def lightness(color: str) -> float:
    """CIE L* of an sRGB color."""
    y = luminance(color)
    return 116 * y ** (1 / 3) - 16 if y > 216 / 24389 else y * 24389 / 27


def blend(top: str, bottom: str, alpha: float) -> str:
    """Composite `top` at `alpha` over `bottom`."""
    mixed = (round(t * alpha + b * (1 - alpha)) for t, b in zip(rgb(top), rgb(bottom)))
    return "#" + "".join(f"{v:02x}" for v in mixed)


def is_neutral(color: str) -> bool:
    r, g, b = rgb(color)
    return r == g == b


def check_variant(variant: str, c: dict[str, str]) -> None:
    prefix = f"{variant}: "
    bg, fg = c["background"], c["foreground"]

    missing = sorted(REQUIRED - c.keys())
    check(prefix + "defines every themed slot", not missing, f"missing {missing}")
    if missing:
        return
    extra = sorted(c.keys() - REQUIRED)
    check(prefix + "sets only known color slots", not extra, f"unexpected {extra}")

    bad_hex = sorted(k for k, v in c.items() if not HEX.match(v))
    check(prefix + "writes colors as lowercase #rrggbb", not bad_hex, f"bad values in {bad_hex}")
    if bad_hex:
        return

    tinted = sorted(k for k, v in c.items() if not is_neutral(v) and v != CLAY)
    check(prefix + "uses only neutral grays and Clay", not tinted, f"tinted slots {tinted}")

    clay_out = sorted(k for k, v in c.items() if v == CLAY and k not in CLAY_SLOTS)
    clay_missing = sorted(k for k in CLAY_SLOTS if c[k] != CLAY)
    check(
        prefix + "keeps Clay on focus slots only",
        not clay_out and not clay_missing,
        f"Clay outside focus slots {clay_out}; focus slots without Clay {clay_missing}",
    )

    ratio = contrast(fg, bg)
    check(prefix + "body text contrast >= 7", ratio >= 7, f"{fg} on {bg} is {ratio:.2f}")

    ratio = contrast(c["palette 8"], bg)
    check(prefix + "comment (bright black) contrast >= 4", ratio >= 4, f"{ratio:.2f}")

    if luminance(bg) < 0.5:
        ratio = contrast(CLAY, bg)
        check(prefix + "Clay text contrast >= 4.5 on dark", ratio >= 4.5, f"{ratio:.2f}")

    for slot in ("palette 1", "palette 2", "palette 9", "palette 10"):
        check(
            prefix + f"{slot} differs from body text",
            c[slot] != fg,
            f"{slot} equals foreground {fg}",
        )

    for dark, light in (("palette 0", "palette 7"), ("palette 8", "palette 15")):
        check(
            prefix + f"{dark} is darker than {light}",
            luminance(c[dark]) < luminance(c[light]),
            f"{c[dark]} vs {c[light]}",
        )

    check(
        prefix + "cursor and current match put the background on Clay",
        c["cursor-text"] == bg and c["search-selected-foreground"] == bg,
        "cursor-text and search-selected-foreground must equal background",
    )

    l_bg = lightness(bg)
    distance = {k: abs(lightness(c[k]) - l_bg) for k in MIRRORED_SURFACES}
    check(
        prefix + "search sits farther from the background than selection",
        0 < distance["selection-background"] < distance["search-background"],
        f"selection {distance['selection-background']:.1f}, search {distance['search-background']:.1f}",
    )
    check(
        prefix + "split divider is visible against the background",
        distance["split-divider-color"] >= 3,
        f"L* distance {distance['split-divider-color']:.1f}",
    )

    for text, surface in (
        ("selection-foreground", "selection-background"),
        ("search-foreground", "search-background"),
        ("window-titlebar-foreground", "window-titlebar-background"),
    ):
        ratio = contrast(c[text], c[surface])
        check(prefix + f"{text} contrast >= 4.5", ratio >= 4.5, f"{ratio:.2f}")

    fill = c["unfocused-split-fill"]
    dim_fg, dim_bg = blend(fg, fill, UNFOCUSED_OPACITY), blend(bg, fill, UNFOCUSED_OPACITY)
    ratio = contrast(dim_fg, dim_bg)
    check(
        prefix + "unfocused splits dim text but keep it readable",
        4 <= ratio < contrast(fg, bg),
        f"unfocused text {dim_fg} on {dim_bg} is {ratio:.2f}",
    )


def check_mirror(dark: dict[str, str], light: dict[str, str]) -> None:
    check(
        "variants define the same slots",
        dark.keys() == light.keys(),
        f"only in dark {sorted(dark.keys() - light.keys())}, "
        f"only in light {sorted(light.keys() - dark.keys())}",
    )
    if not REQUIRED <= dark.keys() or not REQUIRED <= light.keys():
        return

    for slot in MIRRORED_TEXT:
        d = contrast(dark[slot], dark["background"])
        l = contrast(light[slot], light["background"])
        check(f"mirror: {slot} contrast matches", abs(d - l) <= 0.2, f"dark {d:.2f}, light {l:.2f}")

    l_dark, l_light = lightness(dark["background"]), lightness(light["background"])
    for slot in MIRRORED_SURFACES:
        d = lightness(dark[slot]) - l_dark
        l = lightness(light[slot]) - l_light
        check(
            f"mirror: {slot} stacks the same distance the other way",
            abs(d + l) <= 1,
            f"dark {d:+.1f}, light {l:+.1f}",
        )


def check_ghostty() -> None:
    ghostty = shutil.which("ghostty")
    if not ghostty:
        report("skip", "ghostty +validate-config", "ghostty not found on PATH")
        return
    for variant, path in THEMES.items():
        proc = subprocess.run(
            [ghostty, "+validate-config", f"--config-file={path}"],
            capture_output=True,
            text=True,
        )
        check(
            f"{variant}: ghostty +validate-config",
            proc.returncode == 0,
            (proc.stdout + proc.stderr).strip(),
        )


def main() -> int:
    parsed: dict[str, dict[str, str]] = {}
    for variant, path in THEMES.items():
        try:
            parsed[variant] = parse(path)
        except (OSError, ValueError) as err:
            report("fail", f"{variant}: parse {path.name}", str(err))
            continue
        check_variant(variant, parsed[variant])
    if len(parsed) == len(THEMES):
        check_mirror(parsed["dark"], parsed["light"])
    check_ghostty()

    print(f"\n{results['pass']} passed, {results['fail']} failed, {results['skip']} skipped")
    return 1 if results["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
