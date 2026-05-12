#!/usr/bin/env python3
"""cast_to_svg.py — minimal asciicast v2 → animated SVG converter (pure Python, no deps).

Renders a self-contained SVG with `<animate>` tags that replay the terminal session.
Designed for the claude-cortex demo, but generic enough for other asciicasts.

Trade-offs vs svg-term-cli (recommended for production demos):
  - Pure stdlib, no Node/npm needed
  - Simpler ANSI handling (foreground colors only — bold/underline ignored)
  - Single text element animated via opacity, not per-character animation
  - Sufficient for demos where readability > stylistic fidelity

Usage:
    python docs/demo/cast_to_svg.py docs/demo/demo.cast > docs/demo/demo.svg

Then embed in README:
    ![demo](docs/demo/demo.svg)

The SVG renders fine on GitHub markdown (animation plays in browsers, static frame
in IDE preview). File size ~10-30 KB for a 45s demo.
"""
import json
import re
import sys
from pathlib import Path

# Minimal ANSI → CSS color map (xterm-256color subset that the demo uses)
ANSI_FG = {
    "30": "#000", "31": "#cc0000", "32": "#4e9a06", "33": "#c4a000",
    "34": "#3465a4", "35": "#75507b", "36": "#06989a", "37": "#d3d7cf",
    "90": "#555", "91": "#ef2929", "92": "#8ae234", "93": "#fce94f",
    "94": "#729fcf", "95": "#ad7fa8", "96": "#34e2e2", "97": "#eeeeec",
}

# ANSI escape sequence pattern : \x1b[<codes>m
ANSI_RE = re.compile(r"\x1b\[([0-9;]*)m")


def strip_ansi(text: str) -> str:
    """Remove all ANSI escape sequences."""
    return ANSI_RE.sub("", text)


def ansi_to_spans(text: str) -> list[tuple[str, str | None]]:
    """Convert text with ANSI escapes to a list of (text_chunk, color_or_None) tuples."""
    spans: list[tuple[str, str | None]] = []
    pos = 0
    current_color: str | None = None
    for match in ANSI_RE.finditer(text):
        if match.start() > pos:
            spans.append((text[pos:match.start()], current_color))
        codes = match.group(1).split(";")
        for code in codes:
            if code == "0" or code == "":
                current_color = None
            elif code in ANSI_FG:
                current_color = ANSI_FG[code]
            # bold (1) / underline (4) etc. ignored for simplicity
        pos = match.end()
    if pos < len(text):
        spans.append((text[pos:], current_color))
    return spans


def render_svg(cast_path: Path) -> str:
    """Render an asciicast v2 file to an animated SVG."""
    lines = cast_path.read_text(encoding="utf-8").strip().split("\n")
    header = json.loads(lines[0])
    width = header.get("width", 80)
    height = header.get("height", 24)

    # Parse events : [time, "o", text]
    events = []
    for line in lines[1:]:
        if not line.strip():
            continue
        ev = json.loads(line)
        if len(ev) >= 3 and ev[1] == "o":
            events.append((ev[0], ev[2]))

    if not events:
        return "<svg xmlns='http://www.w3.org/2000/svg'/>"

    total_duration = events[-1][0] + 1.0  # 1s buffer at end

    # Build cumulative buffer per event : the complete terminal contents at time T
    # For SVG simplicity, we render N keyframes where each shows the full content up to that time.
    # To keep file size sane, sample at ~10 fps minimum, but keep an exact frame at each event boundary.
    keyframes: list[tuple[float, str]] = []
    buffer = ""
    for time, text in events:
        buffer += text
        keyframes.append((time, buffer))

    # SVG sizing : ~8px per char width, ~16px per line height
    char_w = 8
    line_h = 16
    px_w = width * char_w + 40  # padding
    px_h = height * line_h + 40

    # Explicit width/height attrs are required for GitHub markdown rendering.
    # Without them the browser uses CSS-default replaced-element size (300×150),
    # which makes the demo unreadable. We set the rendered size to the viewBox
    # native dims so the demo renders at full intended scale on GitHub README.
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {px_w} {px_h}" '
        f'width="{px_w}" height="{px_h}" '
        f'font-family="ui-monospace, Menlo, Consolas, monospace" font-size="13">',
        f'  <rect width="100%" height="100%" fill="#0c0c0c"/>',
        f'  <g transform="translate(20, 26)" fill="#d4d4d4">',
    ]

    # For each keyframe, emit a <g> animated via opacity. Only the last `height`
    # lines of the cumulative buffer are rendered (terminal-style scrolling) so
    # the viewport stays bounded — without this, the SVG accumulates all output
    # vertically and the lines also overflow horizontally for wide outputs.
    for idx, (time, content) in enumerate(keyframes):
        # Split content into lines (handles \r\n by splitting on \n; trailing \r is harmless in SVG)
        all_lines = content.split("\n")
        # Keep only the last `height` lines (scroll viewport)
        visible_lines = all_lines[-height:]
        # Truncate each line to `width` chars to prevent horizontal overflow
        # (real terminals wrap; we truncate as a simpler approximation)
        truncated_lines = [line[:width] for line in visible_lines]
        spans_per_line = [ansi_to_spans(line) for line in truncated_lines]

        # Build the <text> element with one <tspan> per line / per color span
        text_parts = [f'    <text x="0" y="0" xml:space="preserve">']
        for line_idx, spans in enumerate(spans_per_line):
            y = line_idx * line_h
            x = 0
            text_parts.append(f'      <tspan x="0" y="{y}">')
            for chunk, color in spans:
                # Escape XML
                chunk_esc = chunk.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                if color:
                    text_parts.append(f'<tspan fill="{color}">{chunk_esc}</tspan>')
                else:
                    text_parts.append(chunk_esc)
            text_parts.append("</tspan>")
        text_parts.append("    </text>")

        # Each frame uses an <animate> with values list spanning the FULL cycle.
        # Opacity stays 0 from 0→time, jumps to 1 from time→next_time, returns to 0
        # until the cycle ends. repeatCount="indefinite" makes the whole demo loop.
        # Trade-off vs <set>: slightly more verbose per frame, but each frame is
        # independently re-animated on every loop iteration (which <set> + syncbase
        # references could not deliver portably).
        next_time = keyframes[idx + 1][0] if idx + 1 < len(keyframes) else total_duration
        # Guard : keyTimes must be strictly increasing AND in [0,1]. Skip degenerate frames.
        kt1 = time / total_duration
        kt2 = next_time / total_duration
        if kt2 <= kt1:
            kt2 = min(kt1 + 0.001, 1.0)
        parts.append(f'    <g opacity="0">')
        parts.extend(text_parts)
        parts.append(
            f'      <animate attributeName="opacity" '
            f'values="0;0;1;1;0;0" '
            f'keyTimes="0;{kt1:.4f};{kt1:.4f};{kt2:.4f};{kt2:.4f};1" '
            f'dur="{total_duration:.2f}s" '
            f'repeatCount="indefinite"/>'
        )
        parts.append("    </g>")

    parts.append("  </g>")
    # Loop indicator
    parts.append(f'  <text x="20" y="{px_h - 10}" font-size="10" fill="#666">claude-cortex demo · {total_duration:.0f}s loop</text>')
    parts.append("</svg>")

    return "\n".join(parts)


def main():
    if len(sys.argv) != 2:
        print("Usage: python cast_to_svg.py <demo.cast>", file=sys.stderr)
        sys.exit(1)
    cast_path = Path(sys.argv[1])
    if not cast_path.exists():
        print(f"ERROR: file not found: {cast_path}", file=sys.stderr)
        sys.exit(1)
    print(render_svg(cast_path))


if __name__ == "__main__":
    main()
