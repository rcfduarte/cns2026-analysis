# Dropping the paywalled JCN supplement PDFs (2022–2025)

These four CNS meeting supplements are Springer-paywalled (not in PMC). Download each via
UC's Springer access and save it under `data/pdfs/` with the **exact filename** below.

| Meeting | Springer article URL | Save as |
|---------|----------------------|---------|
| CNS*2022 | https://link.springer.com/article/10.1007/s10827-022-00841-9 | `data/pdfs/cns2022.pdf` |
| CNS*2023 | https://link.springer.com/article/10.1007/s10827-024-00871-5 | `data/pdfs/cns2023.pdf` |
| CNS*2024 | https://link.springer.com/article/10.1007/s10827-024-00889-9 | `data/pdfs/cns2024.pdf` |
| CNS*2025 | https://link.springer.com/article/10.1007/s10827-025-00915-4 | `data/pdfs/cns2025.pdf` |

Use the **"Download PDF"** button (the full supplement, not a single sub-article). The file
should be a few hundred pages.

## After dropping (even just one)

Tell me, and I'll:
1. Run `pdftotext` on it and inspect the real text layout (2-column journal PDFs need
   calibration — I won't guess the format blind).
2. Extend the Era C parser to PDF text (`parse_pdf.py`), reusing the flat `K1/F1/P###`
   segmentation already validated on the 2021 bundle.
3. Ingest all available years and rebuild the corpus to 2007–2025.

`data/pdfs/` is gitignored; the PDFs and the extracted Era C bodies (free-to-read, not
CC-BY) are never committed or redistributed.
