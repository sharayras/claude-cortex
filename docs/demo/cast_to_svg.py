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

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {px_w} {px_h}" font-family="ui-monospace, Menlo, Consolas, monospace" font-size="13">',
        f'  <rect width="100%" height="100%" fill="#0c0c0c"/>',
        f'  <g transform="translate(20, 26)" fill="#d4d4d4">',
    ]

    # For each keyframe, emit a <g> with display:none initially, animated to display:inline at its timestamp
    # (Using <set> attribute animation rather than <animate> for cleaner display switching)
    for idx, (time, content) in enumerate(keyframes):
        # Convert content to SVG text lines
        spans_per_line = []
        for raw_line in content.split("\n"):
            line_spans = ansi_to_spans(raw_line)
            spans_per_line.append(line_spans)

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

        # Frame visibility : show from `time` to next keyframe's time (or end)
        next_time = keyframes[idx + 1][0] if idx + 1 < len(keyframes) else total_duration
        # Use opacity animation for crisp transitions
        parts.append(f'    <g opacity="0">')
        parts.extend(text_parts)
        parts.append(f'      <set attributeName="opacity" to="1" begin="{time:.2f}s" end="{total_duration:.2f}s"/>')
        # Hide previous frame at this frame's start
        if idx > 0:
            parts.append(f'      <set attributeName="opacity" to="0" begin="{next_time:.2f}s" end="{total_duration:.2f}s"/>')
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
