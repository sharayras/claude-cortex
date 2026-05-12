# Demo recording — claude-cortex

This folder contains the script and instructions to (re)record the README demo asset (GIF or SVG) showing the core claude-cortex workflow.

## Goal

A 30-60 second clip showing : grep frustration → vector.py top-k → verify.py drift → note.py anti-duplicate. Embedded in `README.md` to convert visitors who skim before deciding to clone.

## What to record

See `script.md` in this folder for the exact command sequence + expected timing. The script targets ~45s total runtime; trimming to 30s in post is fine.

## Recording tools (pick one)

### Option 1 — asciinema + svg-term-cli (recommended : SVG, sharp, small file)

```bash
# Install once
brew install asciinema    # or apt/dnf/winget equivalent
npm install -g svg-term-cli

# Record
asciinema rec docs/demo/demo.cast

# Convert to SVG (no GIF artifacts, scales crisply, ~50-200 KB)
svg-term --in docs/demo/demo.cast --out docs/demo/demo.svg --window
```

Pros : SVG renders perfectly on GitHub, file size 5-10× smaller than GIF, asciicast is editable later (re-trim, re-color).

### Option 2 — terminalizer (GIF directly)

```bash
npm install -g terminalizer
terminalizer record docs/demo/demo
terminalizer render docs/demo/demo -o docs/demo/demo.gif
```

Pros : direct GIF output, GitHub auto-renders. Cons : larger file, slight color banding.

### Option 3 — OS native screen recorder + ffmpeg

```bash
# Record any way (OBS, native macOS recorder, ScreenToGif on Windows)
# Then optimize :
ffmpeg -i raw.mp4 -vf "fps=15,scale=800:-1:flags=lanczos" -c:v gif docs/demo/demo.gif
gifsicle -O3 docs/demo/demo.gif -o docs/demo/demo.gif    # further compress
```

Pros : works without specialized tools. Cons : largest files, most post-work.

## Constraints

- **File size ≤ 2 MB** : GitHub auto-renders large files but lags on slow connections. Aim for 500 KB-1.5 MB.
- **Width 800-1000 px** : narrower than full-screen, fits well in README rendered width.
- **No personal info** : check the recording for usernames in paths, sensitive memory file names, etc.
- **Loop-friendly** : last frame should rest on a meaningful state (the `note.py` success message), not a blank prompt.

## After recording

1. Place the asset at `docs/demo/demo.gif` or `docs/demo/demo.svg`
2. Update README — replace the "🎬 demo asset placeholder" line with the actual `<img>` or `![demo](docs/demo/demo.gif)` markdown
3. Commit both the asset and the README change in the same PR
4. Close issue #5 with the PR

## Re-recording

If `claude-cortex` evolves and the demo becomes stale (new flags, different output formatting), re-run `script.md` against the current main and re-record. Asciicast is the editable source of truth — keep `demo.cast` committed alongside the rendered SVG/GIF.
