#!/bin/sh
# Run LibreOffice (user flatpak org.libreoffice.LibreOffice) headless with access to this repository.
# Usage: ./soffice.sh --convert-to pdf --outdir <dir> <file.pptx>
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
exec flatpak run --filesystem="$REPO" org.libreoffice.LibreOffice --headless --norestore "$@"
