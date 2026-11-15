#!/bin/sh
# Build the deck from pipeline outputs, apply the theme colours, validate, export the PDF and render previews.
# Requires: node (pptxgenjs installed here with `bun install`), the pptx skill helpers (PPTX_SKILL), LibreOffice flatpak.
set -e
cd "$(dirname "$0")"
SKILL="${PPTX_SKILL:-/home/ansonlo/.claude/skills/synced/ca0cd509-1879-4449-ae90-fb58c6488a03_22c1b2f4-d404-45d5-8e2d-ef96962a742e/pptx}"
(cd ../.. && uv run --no-project --with pillow python -c "from PIL import Image; im=Image.open('reports/screenshots/web-1440-overview.png'); im.crop((0,0,1440,1000)).save('presentation/assets/demo_overview.png')")
node build_deck.js
NODE_PATH="$PWD/node_modules" node "$SKILL/scripts/apply_theme.js" ../HashAtlas.pptx theme.json
(cd ../.. && uv run --with python-pptx --with defusedxml --with lxml python "$SKILL/scripts/office/validate.py" presentation/HashAtlas.pptx)
./soffice.sh --convert-to pdf --outdir "$(cd .. && pwd)" "$(cd .. && pwd)/HashAtlas.pptx" >/dev/null 2>&1
rm -rf render && mkdir -p render && pdftoppm -jpeg -r 70 ../HashAtlas.pdf render/slide
echo "pages: $(pdfinfo ../HashAtlas.pdf | awk '/Pages/{print $2}')"
