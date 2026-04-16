#!/usr/bin/env bash
# Render a full 5-card Instagram carousel for a given post folder.
#
# Usage:
#   bash scripts/sns/render_carousel.sh <post-folder-name>
#
# Example:
#   bash scripts/sns/render_carousel.sh 001-018880-hanon-systems
#
# Requires:
#   sns/posts/<post>/hook.json
#
# Outputs:
#   sns/posts/<post>/carousel/0{1..5}-{hook,context,chart,insight,cta}.png

set -euo pipefail

POST="${1:-}"
if [[ -z "$POST" ]]; then
  echo "usage: $0 <post-folder-name>" >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
POST_DIR="$ROOT_DIR/sns/posts/$POST"
REMOTION_DIR="$ROOT_DIR/scripts/sns/remotion-sns"
PROPS_FILE="$POST_DIR/hook.json"
OUT_DIR="$POST_DIR/carousel"

if [[ ! -f "$PROPS_FILE" ]]; then
  echo "missing: $PROPS_FILE" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"

cd "$REMOTION_DIR"

render_card () {
  local comp="$1"
  local out_name="$2"
  echo "→ rendering $comp ..."
  npx remotion still src/index.ts "$comp" "$OUT_DIR/$out_name" \
    --props="$PROPS_FILE" \
    --image-format=png \
    --log=error
}

render_card HookCard    01-hook.png
render_card ContextCard 02-context.png
render_card ChartCard   03-chart.png
render_card InsightCard 04-insight.png
render_card CtaCard     05-cta.png

echo ""
echo "✔ 5 cards rendered to: $OUT_DIR"
ls -la "$OUT_DIR"
