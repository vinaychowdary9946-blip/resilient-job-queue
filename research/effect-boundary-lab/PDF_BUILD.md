# Optional PDF build

The experiment uses only the standard library. Rebuilding the supplied PDFs separately requires ReportLab 4.x and DejaVu Sans regular/bold TrueType fonts. These are document-build dependencies, not experiment dependencies.

```sh
python -m pip install "reportlab>=4,<5"
python build_pdf.py --font-dir /path/to/dejavu/fonts
```

The folder must contain DejaVuSans.ttf and DejaVuSans-Bold.ttf. Outputs are paper.pdf and research-brief.pdf beside the Markdown sources. The released PDFs were rendered and visually inspected. Font metrics affect pagination; inspect rebuilt documents before publishing.
