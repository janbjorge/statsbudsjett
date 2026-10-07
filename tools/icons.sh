#!/usr/bin/env bash
# Render the PNG icons from src/adapters/web/static/icon.svg (needs rsvg-convert, from librsvg).
# icon-48.png is served as /favicon.ico for clients that skip the SVG; icon-180.png is the apple-touch-icon.
set -euo pipefail
STATIC="$(cd "$(dirname "$0")/.." && pwd)/src/adapters/web/static"
for size in 48 180; do
  rsvg-convert -w "$size" -h "$size" "$STATIC/icon.svg" -o "$STATIC/icon-$size.png"
done
