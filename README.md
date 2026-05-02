# ECLIPSE Lab Website

This repository contains the Quarto source for https://pelzlab.science.

## Styling

- Canonical custom stylesheet: `styles.css`
- Legacy `style.css` was removed to avoid duplicate/dead CSS paths.

## Image optimization

Responsive AVIF/WebP assets can be regenerated with:

```bash
./tools/optimize-images.sh
```

Generated files are written to `img/optimized/` and consumed on the homepage via `<picture>` fallbacks.

## Publications/news refresh (local)

```bash
python3 generate_publications.py
quarto render
```

The publication refresh scans active people pages under `people/` and excludes `people/alumni/`. ORCID-backed profiles are fetched from ORCID, Crossref, and OpenAlex, including arXiv preprints exposed as arXiv external IDs or `10.48550/arxiv.*` DOIs, then enriched through Crossref and Semantic Scholar. Scopus and Web of Science IDs are detected from profile links; Scopus can be queried when `SCOPUS_API_KEY` is set, and Web of Science is skipped unless `WOS_API_KEY` is available.

The same flow runs automatically in GitHub Actions on a weekly schedule and can open a PR with regenerated `publications/` + `docs/` output when content changes.
