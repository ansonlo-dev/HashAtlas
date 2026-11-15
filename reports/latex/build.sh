#!/bin/sh
# Build reports/technical_report.tex and its PDF from reports/technical_report.md (pandoc -> LuaLaTeX via latexmk).
set -e
cd "$(dirname "$0")/.."
TITLE="$(sed -n 's/^title: *"\(.*\)"$/\1/p' technical_report.md | head -1)"
pandoc technical_report.md -s -o technical_report.tex --template=latex/hashatlas-report.latex --lua-filter=latex/report.lua \
  -H latex/preamble.tex --number-sections --toc -V toc-depth=1 -V documentclass=article -V fontsize=11pt -V papersize=a4 \
  -V geometry=top=26mm -V geometry=bottom=24mm -V geometry=left=24mm -V geometry=right=24mm -V geometry=headheight=15pt \
  -V colorlinks=true -V linkcolor=ReportAccent -V urlcolor=ReportAccent -V shorttitle="HashAtlas · CDS3004 Group Project Report" \
  -V reportkind="CDS3004 Data Mining · Group Project Report" -M title-meta="$TITLE"
mkdir -p latex/build
latexmk -lualatex -interaction=nonstopmode -halt-on-error -outdir=latex/build technical_report.tex > latex/build/latexmk.out 2>&1 || {
  tail -40 latex/build/technical_report.log >&2; exit 1; }
if grep -Eq "undefined references|Reference .* undefined|Citation .* undefined" latex/build/technical_report.log; then
  echo "LaTeX build left undefined references; see reports/latex/build/technical_report.log" >&2; exit 1
fi
cp latex/build/technical_report.pdf technical_report.pdf
echo "built reports/technical_report.pdf ($(pdfinfo technical_report.pdf | awk '/Pages/{print $2}') pages, $(grep -c 'Overfull' latex/build/technical_report.log || true) overfull boxes)"
