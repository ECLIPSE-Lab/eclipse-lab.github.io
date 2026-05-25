"""Fetch citation/impact metrics from OpenAlex for every publication .qmd.

Run after generate_publications.py and before `quarto render`. Writes a
canonical `publication_metrics.json` and patches each publication's
front matter with an auto-managed metrics block that the EJS template
reads (cited_by_count, fwci, top-percentile flags, OA status, yearly
counts for the sparkline).
"""

# %%
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

USER_AGENT = "ECLIPSE-Lab/1.0 (mailto:philipp.pelz@fau.de)"
MAILTO = "philipp.pelz@fau.de"
ARTICLES_DIR = Path("publications/articles")
METRICS_JSON = Path("publication_metrics.json")
SUMMARY_INCLUDE = Path("_includes/pub-summary.qmd")
SPARKLINE_YEARS = 8
OPENALEX_BATCH_SIZE = 50

KEYWORD_MIN_SCORE = 0.5
KEYWORD_MAX_COUNT = 6
KEYWORD_DENYLIST = {
    "physics",
    "materials science",
    "computer science",
    "chemistry",
    "biology",
    "mathematics",
    "engineering",
    "science",
    "research",
    "technology",
}

METRICS_BEGIN = "# --- citation metrics (auto-managed; do not edit) ---"
METRICS_END = "# --- end citation metrics ---"

CAT_KW_BEGIN = "  # --- begin keyword categories (auto-managed) ---"
CAT_KW_END = "  # --- end keyword categories ---"


def normalize_doi(doi):
    if not doi:
        return ""
    doi = str(doi).strip()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
    doi = re.sub(r"^doi:\s*", "", doi, flags=re.IGNORECASE)
    return doi.strip().lower()


def request_json(url, params=None, headers=None, timeout=30, retries=2):
    request_headers = {"User-Agent": USER_AGENT}
    if headers:
        request_headers.update(headers)
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, params=params, headers=request_headers, timeout=timeout)
            if r.status_code == 429:
                print(f"  rate-limited by {url}; backing off")
                time.sleep(2 + attempt * 2)
                continue
            if r.status_code == 404:
                return None
            if r.status_code >= 400:
                print(f"  API error {r.status_code} for {url}")
                return None
            return r.json()
        except Exception as exc:
            print(f"  error fetching {url}: {exc}")
            if attempt < retries:
                time.sleep(1 + attempt)
    return None


# ---- frontmatter helpers (no PyYAML; match existing project style) ----

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def split_frontmatter(text):
    """Return (frontmatter_text, body) or (None, text) if no frontmatter."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None, text
    return m.group(1), text[m.end():]


def extract_doi_from_frontmatter(fm_text):
    if fm_text is None:
        return ""
    for line in fm_text.splitlines():
        m = re.match(r'^\s*doi:\s*"?([^"\n]+?)"?\s*$', line)
        if m:
            return normalize_doi(m.group(1))
    return ""


def strip_managed_block(fm_text):
    """Remove any prior auto-managed metrics block from the frontmatter."""
    pattern = re.compile(
        re.escape(METRICS_BEGIN) + r".*?" + re.escape(METRICS_END) + r"\n?",
        re.DOTALL,
    )
    return pattern.sub("", fm_text)


def render_managed_block(metrics):
    """Render the auto-managed YAML block for one publication's metrics."""
    lines = [METRICS_BEGIN]

    if metrics.get("cited_by_count") is not None:
        lines.append(f"cited_by_count: {int(metrics['cited_by_count'])}")

    fwci = metrics.get("fwci")
    if fwci is not None:
        lines.append(f"fwci: {float(fwci):.2f}")

    pct = metrics.get("citation_percentile")
    if pct is not None:
        lines.append(f"citation_percentile: {float(pct):.1f}")

    if metrics.get("is_top_1_percent"):
        lines.append("is_top_1_percent: true")
    if metrics.get("is_top_10_percent"):
        lines.append("is_top_10_percent: true")

    if metrics.get("is_oa"):
        lines.append("is_oa: true")
    oa_status = metrics.get("oa_status")
    if oa_status:
        lines.append(f"oa_status: {oa_status}")

    counts = metrics.get("counts_by_year_compact") or []
    if counts:
        lines.append("counts_by_year:")
        for year, count in counts:
            lines.append(f"  - [{int(year)}, {int(count)}]")

    keywords = metrics.get("keywords") or []
    if keywords:
        lines.append("keywords:")
        for kw in keywords:
            # quote to be safe with parens, hyphens, colons, etc.
            safe = str(kw).replace('"', '\\"')
            lines.append(f'  - "{safe}"')

    metrics_updated = metrics.get("metrics_updated")
    if metrics_updated:
        lines.append(f'metrics_updated: "{metrics_updated}"')

    lines.append(METRICS_END)
    return "\n".join(lines)


CATEGORIES_BLOCK_RE = re.compile(
    r"^categories:[ \t]*\n((?:[ \t]+[-#][^\n]*\n|[ \t]*\n)*)",
    re.MULTILINE,
)


def parse_curated_categories(block_body):
    """Return curated category strings from a `categories:` body, ignoring any managed segment."""
    items = []
    in_managed = False
    for line in block_body.splitlines():
        stripped = line.strip()
        if stripped.startswith("# --- begin keyword categories"):
            in_managed = True
            continue
        if stripped.startswith("# --- end keyword categories"):
            in_managed = False
            continue
        if in_managed or not stripped.startswith("- "):
            continue
        value = stripped[2:].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        if value:
            items.append(value)
    return items


def render_categories_block(curated, keyword_extras):
    lines = ["categories:"]
    for c in curated:
        lines.append(f"  - {c}")
    if keyword_extras:
        lines.append(CAT_KW_BEGIN)
        for kw in keyword_extras:
            safe = str(kw).replace('"', '\\"')
            lines.append(f'  - "{safe}"')
        lines.append(CAT_KW_END)
    return "\n".join(lines) + "\n"


def patch_categories_in_frontmatter(fm_text, keywords):
    """Merge OpenAlex keywords into the `categories:` list, dedup'd against curated entries.

    Idempotent: each run strips the prior managed segment (between begin/end markers
    inside the categories list) and writes a fresh one. Curated entries are preserved.
    """
    match = CATEGORIES_BLOCK_RE.search(fm_text)
    if not match:
        return fm_text
    curated = parse_curated_categories(match.group(1))
    curated_lower = {c.lower() for c in curated}
    extras = []
    seen = set()
    for kw in keywords or []:
        kl = str(kw).lower()
        if kl in curated_lower or kl in seen:
            continue
        seen.add(kl)
        # Lowercase to match the curated style and prevent case-only duplicate
        # entries in the merged Quarto category sidebar (e.g. "Software" vs "software").
        extras.append(kl)
    new_block = render_categories_block(curated, extras)
    return fm_text[:match.start()] + new_block + fm_text[match.end():]


def patch_qmd_file(path, metrics):
    text = path.read_text(encoding="utf-8")
    fm_text, body = split_frontmatter(text)
    if fm_text is None:
        return False
    fm_clean = strip_managed_block(fm_text).rstrip() + "\n"
    fm_clean = patch_categories_in_frontmatter(fm_clean, (metrics or {}).get("keywords") or [])
    if metrics:
        fm_clean = fm_clean + render_managed_block(metrics) + "\n"
    new_text = f"---\n{fm_clean}---\n{body}"
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
        return True
    return False


# ---- OpenAlex ----

OPENALEX_SELECT = ",".join(
    [
        "doi",
        "cited_by_count",
        "counts_by_year",
        "fwci",
        "citation_normalized_percentile",
        "open_access",
        "keywords",
    ]
)


def filter_openalex_keywords(raw_keywords):
    """Pick paper-specific keywords from OpenAlex output.

    OpenAlex returns ~10 keywords per paper with scores 0..1 and noisy entries
    like "Physics" or "Resolution (logic)" (a Wikidata mis-disambiguation).
    Keep only the strongest, drop generic single-domain terms and (logic)
    variants, dedupe case-insensitively, cap at KEYWORD_MAX_COUNT.
    """
    if not raw_keywords:
        return []
    seen = set()
    out = []
    for kw in raw_keywords:
        name = (kw.get("display_name") or "").strip()
        score = kw.get("score") or 0.0
        if not name or score < KEYWORD_MIN_SCORE:
            continue
        # OpenAlex uses Wikidata disambiguators ("Frame (networking)",
        # "Content (measure theory)", ...) that are usually wrong-context
        # for physics/microscopy papers. Drop any disambiguated entry.
        if "(" in name and ")" in name:
            continue
        if name.lower() in KEYWORD_DENYLIST:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(name)
        if len(out) >= KEYWORD_MAX_COUNT:
            break
    return out


def fetch_openalex_batch(dois):
    """Fetch metrics for a batch of DOIs from OpenAlex. Returns dict keyed by normalized DOI."""
    out = {}
    if not dois:
        return out
    filter_value = "doi:" + "|".join(dois)
    data = request_json(
        "https://api.openalex.org/works",
        params={
            "filter": filter_value,
            "per-page": len(dois),
            "select": OPENALEX_SELECT,
            "mailto": MAILTO,
        },
    )
    if not data:
        return out
    for work in data.get("results", []) or []:
        doi = normalize_doi(work.get("doi") or "")
        if not doi:
            continue
        cnp = work.get("citation_normalized_percentile") or {}
        oa = work.get("open_access") or {}
        pct_raw = cnp.get("value")
        out[doi] = {
            "cited_by_count": work.get("cited_by_count"),
            "fwci": work.get("fwci"),
            "citation_percentile": (pct_raw * 100) if isinstance(pct_raw, (int, float)) else None,
            "is_top_1_percent": bool(cnp.get("is_in_top_1_percent")),
            "is_top_10_percent": bool(cnp.get("is_in_top_10_percent")),
            "is_oa": bool(oa.get("is_oa")),
            "oa_status": oa.get("oa_status"),
            "counts_by_year": work.get("counts_by_year") or [],
            "keywords": filter_openalex_keywords(work.get("keywords") or []),
        }
    return out


def fetch_openalex_metrics(dois):
    metrics = {}
    unique = sorted(set(d for d in dois if d))
    for i in range(0, len(unique), OPENALEX_BATCH_SIZE):
        batch = unique[i : i + OPENALEX_BATCH_SIZE]
        print(f"OpenAlex batch {i // OPENALEX_BATCH_SIZE + 1}: {len(batch)} DOIs")
        metrics.update(fetch_openalex_batch(batch))
        time.sleep(0.2)
    return metrics


def compact_yearly_counts(counts_by_year, n=SPARKLINE_YEARS):
    """Return last n years (oldest→newest) as [(year, count), ...].

    OpenAlex returns recent-first; we emit a contiguous window so the sparkline
    renders even years with zero citations.
    """
    if not counts_by_year:
        return []
    by_year = {int(c["year"]): int(c.get("cited_by_count") or 0) for c in counts_by_year}
    if not by_year:
        return []
    end = max(by_year)
    start = end - n + 1
    return [(y, by_year.get(y, 0)) for y in range(start, end + 1)]


# ---- aggregate impact summary ----


def compute_summary(enriched):
    """Aggregate per-paper OpenAlex metrics into lab-wide impact figures."""
    cites = sorted((m.get("cited_by_count") or 0 for m in enriched.values()), reverse=True)
    n = len(enriched)
    return {
        "papers": n,
        "total_citations": sum(cites),
        "h_index": sum(1 for i, c in enumerate(cites) if c >= i + 1),
        "top_1_percent": sum(1 for m in enriched.values() if m.get("is_top_1_percent")),
        "top_10_percent": sum(1 for m in enriched.values() if m.get("is_top_10_percent")),
        "open_access": sum(1 for m in enriched.values() if m.get("is_oa")),
    }


def render_summary_include(summary, generated_at):
    """Render the impact-summary banner as a Quarto include fragment (raw HTML block)."""
    n = summary["papers"]
    oa_pct = round(100 * summary["open_access"] / n) if n else 0
    updated = (generated_at or "")[:10]

    def stat(value, label):
        return (
            '  <div class="pub-stat">'
            f'<span class="pub-stat-value">{value}</span>'
            f'<span class="pub-stat-label">{label}</span></div>'
        )

    tiles = [
        stat(f"{n}", "Publications"),
        stat(f"{summary['total_citations']:,}", "Citations"),
        stat(f"{summary['h_index']}", "h-index"),
        stat(f"{summary['top_10_percent']}", "in world&rsquo;s top 10%"),
    ]
    if summary["top_1_percent"]:
        tiles.append(stat(f"{summary['top_1_percent']}", "in world&rsquo;s top 1%"))
    tiles.append(stat(f"{oa_pct}%", "Open access"))

    return (
        "<!-- AUTO-GENERATED by fetch_citation_metrics.py — do not edit by hand -->\n"
        "```{=html}\n"
        '<div class="pub-summary" role="group" aria-label="Publication impact summary">\n'
        + "\n".join(tiles)
        + "\n"
        f'  <div class="pub-summary-note">Source: <a href="https://openalex.org/">OpenAlex</a>'
        f" &middot; updated {updated}</div>\n"
        "</div>\n"
        "```\n"
    )


def write_publication_summary(enriched, generated_at):
    if not enriched:
        return
    summary = compute_summary(enriched)
    SUMMARY_INCLUDE.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_INCLUDE.write_text(render_summary_include(summary, generated_at), encoding="utf-8")
    print(
        f"Wrote {SUMMARY_INCLUDE} "
        f"(papers={summary['papers']}, citations={summary['total_citations']}, "
        f"h-index={summary['h_index']})"
    )


# ---- main ----


def collect_publication_dois():
    pairs = []
    if not ARTICLES_DIR.exists():
        print(f"Articles dir {ARTICLES_DIR} not found")
        return pairs
    for path in sorted(ARTICLES_DIR.glob("*.qmd")):
        text = path.read_text(encoding="utf-8")
        fm, _ = split_frontmatter(text)
        doi = extract_doi_from_frontmatter(fm)
        pairs.append((path, doi))
    return pairs


def main():
    pairs = collect_publication_dois()
    dois = [doi for _, doi in pairs if doi]
    print(f"Found {len(pairs)} publications, {len(dois)} with DOIs")
    if not dois:
        print("Nothing to fetch.")
        return 0

    raw = fetch_openalex_metrics(dois)
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    enriched = {}
    for doi, m in raw.items():
        m = dict(m)
        m["counts_by_year_compact"] = compact_yearly_counts(m.get("counts_by_year"))
        m["metrics_updated"] = now_iso
        enriched[doi] = m

    METRICS_JSON.write_text(
        json.dumps(
            {
                "generated_at": now_iso,
                "source": "openalex",
                "count": len(enriched),
                "metrics": enriched,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {METRICS_JSON} with {len(enriched)} entries")

    write_publication_summary(enriched, now_iso)

    patched = 0
    for path, doi in pairs:
        m = enriched.get(doi) if doi else None
        if patch_qmd_file(path, m):
            patched += 1
    print(f"Patched {patched} of {len(pairs)} publication files")
    missing = [doi for doi in dois if doi not in enriched]
    if missing:
        print(f"OpenAlex returned no metrics for {len(missing)} DOIs:")
        for d in missing[:10]:
            print(f"  - {d}")
        if len(missing) > 10:
            print(f"  ... and {len(missing) - 10} more")
    return 0


if __name__ == "__main__":
    sys.exit(main())
