# AGENTS.md

## Project
Single-file polar chart generator: `main.py` renders a "24-Hour Weekly Pricing Clock" for a given timezone using matplotlib. Output: `perfected_pricing_clock.png` (300 DPI). Defaults to the system timezone, with a list of common timezones to choose from.

## Running
```bash
source .venv/bin/activate   # Python 3.14.7 venv
python main.py              # interactive: pick timezone, save PNG, show window
```
Or without activating: `.venv/bin/python main.py`

CLI flags (all optional):
- `--tz America/Tijuana` — skip the interactive prompt
- `--animate` — render `pricing_clock.gif` (looping: day-ring highlight + current-time marker pulse)
- `--headless` — save output without opening a window (for scripts/CI)

## Dependencies
- `numpy`, `matplotlib` — listed in `requirements.txt`; already installed in `.venv`.
- GIF writing uses Pillow (`writer='pillow'`), also installed.

## Notes
- No tests, linting, typecheck, or build step exist for this project.
- The `.venv` is pre-created with Python 3.14; do not recreate unless needed.
- Output file `perfected_pricing_clock.png` is written to the repo root.
- **Commit messages** must follow the Conventional Commit spec as a one-liner (e.g., `feat: add peak hour highlight`).
