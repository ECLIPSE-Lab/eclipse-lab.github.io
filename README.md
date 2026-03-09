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

The same flow runs automatically in GitHub Actions on a weekly schedule and can open a PR with regenerated `publications/` + `docs/` output when content changes.
