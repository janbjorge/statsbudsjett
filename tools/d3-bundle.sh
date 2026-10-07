#!/usr/bin/env bash
# Rebuild src/adapters/web/static/d3.min.js with only the d3 parts the chart islands use.
# The full d3 v7.9.0 build was 280 KB; this one exposes the same global `d3` with fewer names.
# Add a name here when charts.js, flyt.js or d3-sankey.min.js starts using a new d3 function.
set -euo pipefail
OUT="$(cd "$(dirname "$0")/.." && pwd)/src/adapters/web/static/d3.min.js"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
cd "$TMP"
npm init -y >/dev/null
npm install --silent --no-audit --no-fund d3@7.9.0 esbuild@0.25.10
cat > entry.js <<'JS'
export { extent, group, max, min, sum } from "d3-array";
export { axisBottom, axisLeft } from "d3-axis";
export { format } from "d3-format";
export { hierarchy, treemap } from "d3-hierarchy";
export { scaleLinear, scaleLog } from "d3-scale";
export { create, pointer, select, selectAll } from "d3-selection";
export { line, linkHorizontal } from "d3-shape";
JS
{
  echo "// d3 v7.9.0 subset (https://d3js.org, ISC, Copyright 2010-2023 Mike Bostock). Built by tools/d3-bundle.sh."
  npx esbuild entry.js --bundle --minify --format=iife --global-name=d3 --legal-comments=none
} > "$OUT"
wc -c "$OUT"
