# %%
import requests
import time
import os
import re
from datetime import datetime
import html
import csv
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# %%

USER_AGENT = "ECLIPSE-Lab/1.0 (mailto:philipp.pelz@fau.de)"
ACTIVE_PEOPLE_DIRS = {"staff", "bsc", "msc", "ras", "admins"}


def normalize_doi(doi):
    """Normalize DOI values for deduplication and URL generation."""
    if not doi:
        return ""
    doi = str(doi).strip()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
    doi = re.sub(r"^doi:\s*", "", doi, flags=re.IGNORECASE)
    return doi.strip().lower()


def normalize_title(title):
    """Normalize titles enough to merge DOI-free records from multiple sources."""
    if not title:
        return ""
    title = html.unescape(str(title)).lower()
    title = title.replace("å", "a").replace("ä", "a").replace("ö", "o").replace("ü", "u")
    title = re.sub(r"[^a-z0-9]+", " ", title)
    return re.sub(r"\s+", " ", title).strip()


def request_json(url, params=None, headers=None, timeout=30):
    """GET JSON from an API, returning None on non-fatal failures."""
    request_headers = {"User-Agent": USER_AGENT}
    if headers:
        request_headers.update(headers)
    try:
        response = requests.get(url, params=params, headers=request_headers, timeout=timeout)
        if response.status_code == 404:
            return None
        if response.status_code == 429:
            print(f"Rate limited by {url}; skipping this request")
            return None
        if response.status_code >= 400:
            print(f"API error for {url}: {response.status_code}")
            return None
        return response.json()
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None


def extract_front_matter(text):
    """Return the YAML front matter block as text without requiring PyYAML."""
    if not text.startswith("---"):
        return ""
    match = re.match(r"^---\s*\n(.*?)\n---", text, flags=re.DOTALL)
    return match.group(1) if match else ""


def extract_scalar(front_matter, key):
    match = re.search(rf"^{re.escape(key)}:\s*['\"]?(.+?)['\"]?\s*$", front_matter, flags=re.MULTILINE)
    if not match:
        return ""
    return match.group(1).strip().strip("'\"")


def extract_uncommented_hrefs(front_matter):
    hrefs = []
    for line in front_matter.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = re.match(r"href:\s*(.+?)\s*$", stripped)
        if match:
            hrefs.append(match.group(1).strip().strip("'\""))
    return hrefs


def extract_profile_ids(urls):
    ids = {}
    for url in urls:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        path = parsed.path
        query = parse_qs(parsed.query)

        orcid_match = re.search(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]", url, flags=re.IGNORECASE)
        if "orcid.org" in host and orcid_match:
            ids["orcid"] = orcid_match.group(0).upper()

        if "scholar.google" in host and query.get("user"):
            ids["google_scholar"] = query["user"][0]

        if "scopus.com" in host and query.get("authorId"):
            ids["scopus"] = query["authorId"][0]

        wos_match = re.search(r"/wos/author/record/([^/?#\s]+)", path)
        if "webofscience.com" in host and wos_match:
            ids["webofscience"] = wos_match.group(1)
    return ids


def discover_people_profiles(people_dir="people"):
    """Discover active non-alumni people with publication profile identifiers."""
    people_path = Path(people_dir)
    profiles = []
    for qmd_path in sorted(people_path.glob("*/*.qmd")):
        group = qmd_path.parent.name
        if group == "alumni" or group not in ACTIVE_PEOPLE_DIRS:
            continue
        front_matter = extract_front_matter(qmd_path.read_text(encoding="utf-8"))
        if not front_matter:
            continue
        ids = extract_profile_ids(extract_uncommented_hrefs(front_matter))
        if not ids:
            continue
        profiles.append({
            "name": extract_scalar(front_matter, "title") or qmd_path.stem,
            "path": str(qmd_path),
            "group": group,
            "ids": ids,
        })
    return profiles


def source_candidate(source, profile, title, doi="", year="", journal_title="", work_type="", publication_date=None, authors=None, extra=None):
    title = html.unescape(str(title or "")).strip()
    if not title:
        return None
    candidate = {
        "title": title,
        "doi": normalize_doi(doi),
        "year": str(year or ""),
        "journal_title": journal_title or "",
        "work_type": work_type or "",
        "publication_date": publication_date or {"year": str(year or ""), "month": None, "day": None},
        "authors": authors or [],
        "source": source,
        "matched_people": [profile["name"]],
    }
    if extra:
        candidate.update(extra)
    return candidate


def is_preprint_doi(doi):
    return normalize_doi(doi).startswith("10.48550/arxiv.")


def arxiv_id_to_doi(arxiv_id):
    if not arxiv_id:
        return ""
    arxiv_id = str(arxiv_id).strip()
    arxiv_id = re.sub(r"^arxiv:\s*", "", arxiv_id, flags=re.IGNORECASE)
    return f"10.48550/arxiv.{arxiv_id.lower()}"


def is_repository_artifact(candidate):
    title = normalize_title(candidate.get("title", ""))
    doi = normalize_doi(candidate.get("doi"))
    work_type = str(candidate.get("work_type") or "").lower()
    journal_title = normalize_title(candidate.get("journal_title", ""))

    if title.startswith(("data for ", "codes for ", "code for ", "datasets acquired ", "dataset ")):
        return True
    if doi.startswith("10.5281/zenodo."):
        return True
    if work_type in {"dataset", "data-set", "software", "other"}:
        return True
    if not doi and any(marker in journal_title for marker in ["repository", "publication server", "elib"]):
        return True
    return False


def filter_publication_candidates(candidates):
    """Keep paper-like records and drop raw repository artifacts/noisy DOI-free records."""
    filtered = []
    for candidate in candidates:
        if not candidate:
            continue
        if is_repository_artifact(candidate):
            continue
        if not normalize_doi(candidate.get("doi")):
            continue
        filtered.append(candidate)
    return filtered


def merge_candidate_fields(target, candidate):
    doi = normalize_doi(candidate.get("doi"))
    if doi and (not target.get("doi") or (is_preprint_doi(target.get("doi")) and not is_preprint_doi(doi))):
        target["doi"] = doi
        for field in ["title", "year", "journal_title", "work_type", "publication_date", "authors"]:
            if candidate.get(field):
                target[field] = candidate[field]
    else:
        for field in ["year", "journal_title", "work_type"]:
            if not target.get(field) and candidate.get(field):
                target[field] = candidate[field]
        if not target.get("authors") and candidate.get("authors"):
            target["authors"] = candidate["authors"]
        if candidate.get("publication_date") and not target.get("publication_date"):
            target["publication_date"] = candidate["publication_date"]
    target["sources"] = sorted(set(target.get("sources", [])) | ({candidate.get("source", "")} - {""}))
    target["matched_people"] = sorted(set(target.get("matched_people", [])) | set(candidate.get("matched_people", [])))


def merge_publication_candidates(candidates):
    """Merge records by DOI first, falling back to a normalized title key."""
    merged = {}
    order = []
    for candidate in candidates:
        if not candidate or not candidate.get("title"):
            continue
        doi = normalize_doi(candidate.get("doi"))
        title_key = normalize_title(candidate.get("title"))
        key = f"doi:{doi}" if doi else f"title:{title_key}"
        if not title_key:
            continue
        if key not in merged:
            item = dict(candidate)
            item["doi"] = doi
            item["sources"] = sorted({candidate.get("source", "")} - {""})
            item["matched_people"] = sorted(set(candidate.get("matched_people", [])))
            merged[key] = item
            order.append(key)
            continue

        item = merged[key]
        merge_candidate_fields(item, candidate)

    collapsed = {}
    collapsed_order = []
    for key in order:
        item = merged[key]
        title_key = normalize_title(item.get("title"))
        if title_key not in collapsed:
            collapsed[title_key] = item
            collapsed_order.append(title_key)
            continue
        merge_candidate_fields(collapsed[title_key], item)
    return [collapsed[key] for key in collapsed_order]


def date_from_orcid(publication_date):
    if not publication_date:
        return {"year": "", "month": None, "day": None}
    def value(part):
        part_value = publication_date.get(part) or {}
        return str(part_value.get("value", "") or "") or None
    return {
        "year": value("year") or "",
        "month": value("month"),
        "day": value("day"),
    }


def date_from_crossref(item):
    date_obj = (
        item.get("published-print")
        or item.get("published-online")
        or item.get("published")
        or item.get("issued")
        or {}
    )
    parts = date_obj.get("date-parts", [[]])[0] if date_obj else []
    return {
        "year": str(parts[0]) if len(parts) > 0 else "",
        "month": str(parts[1]).zfill(2) if len(parts) > 1 else None,
        "day": str(parts[2]).zfill(2) if len(parts) > 2 else None,
    }


def date_from_openalex(work):
    date_value = str(work.get("publication_date") or "")
    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_value):
        year, month, day = date_value.split("-")
        return {"year": year, "month": month, "day": day}
    year = work.get("publication_year")
    return {"year": str(year or ""), "month": None, "day": None}


def authors_from_crossref(item):
    authors = []
    for author in item.get("author", []) or []:
        if author.get("given") and author.get("family"):
            authors.append(f"{author['given']} {author['family']}")
        elif author.get("family"):
            authors.append(author["family"])
        elif author.get("name"):
            authors.append(author["name"])
    return authors


def authors_from_openalex(work):
    authors = []
    for authorship in work.get("authorships", []) or []:
        author = authorship.get("author", {}) or {}
        if author.get("display_name"):
            authors.append(author["display_name"])
    return authors


def candidate_from_orcid_summary(summary, profile):
    title = summary.get("title", {}).get("title", {}).get("value", "")
    doi = ""
    arxiv_id = ""
    for external_id in summary.get("external-ids", {}).get("external-id", []) or []:
        external_type = str(external_id.get("external-id-type", "")).lower()
        if external_type == "doi":
            doi = external_id.get("external-id-value", "")
            break
        if external_type == "arxiv":
            arxiv_id = external_id.get("external-id-value", "")
    if not doi and arxiv_id:
        doi = arxiv_id_to_doi(arxiv_id)
    pub_date = date_from_orcid(summary.get("publication-date"))
    journal_title = ""
    if summary.get("journal-title"):
        journal_title = summary["journal-title"].get("value", "")
    return source_candidate(
        "orcid",
        profile,
        title=title,
        doi=doi,
        year=pub_date["year"],
        journal_title=journal_title,
        work_type=summary.get("type", ""),
        publication_date=pub_date,
    )


def candidate_from_crossref_item(item, profile):
    titles = item.get("title") or []
    containers = item.get("container-title") or []
    pub_date = date_from_crossref(item)
    return source_candidate(
        "crossref",
        profile,
        title=titles[0] if titles else "",
        doi=item.get("DOI", ""),
        year=pub_date["year"],
        journal_title=containers[0] if containers else "",
        work_type=item.get("type", ""),
        publication_date=pub_date,
        authors=authors_from_crossref(item),
    )


def candidate_from_openalex_work(work, profile):
    source = (work.get("primary_location") or {}).get("source") or {}
    pub_date = date_from_openalex(work)
    return source_candidate(
        "openalex",
        profile,
        title=work.get("display_name") or work.get("title", ""),
        doi=work.get("doi") or (work.get("ids") or {}).get("doi", ""),
        year=pub_date["year"],
        journal_title=source.get("display_name", ""),
        work_type=work.get("type", ""),
        publication_date=pub_date,
        authors=authors_from_openalex(work),
    )


def collect_orcid_candidates(profile):
    orcid_id = profile["ids"].get("orcid")
    if not orcid_id:
        return []
    url = f"https://pub.orcid.org/v3.0/{orcid_id}/works"
    data = request_json(url, headers={"Accept": "application/orcid+json"})
    candidates = []
    for group in (data or {}).get("group", []) or []:
        for summary in group.get("work-summary", []) or []:
            candidate = candidate_from_orcid_summary(summary, profile)
            if candidate:
                candidates.append(candidate)
    print(f"  ORCID: {len(candidates)} candidates for {profile['name']}")
    return candidates


def collect_crossref_candidates(profile, max_pages=10):
    orcid_id = profile["ids"].get("orcid")
    if not orcid_id:
        return []
    candidates = []
    cursor = "*"
    for _ in range(max_pages):
        data = request_json(
            "https://api.crossref.org/works",
            params={
                "filter": f"orcid:{orcid_id}",
                "rows": 100,
                "cursor": cursor,
                "mailto": "philipp.pelz@fau.de",
            },
        )
        message = (data or {}).get("message", {})
        items = message.get("items", []) or []
        for item in items:
            candidate = candidate_from_crossref_item(item, profile)
            if candidate:
                candidates.append(candidate)
        next_cursor = message.get("next-cursor")
        if not items or not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor
        time.sleep(0.1)
    print(f"  Crossref ORCID filter: {len(candidates)} candidates for {profile['name']}")
    return candidates


def collect_openalex_candidates(profile, max_pages=10):
    orcid_id = profile["ids"].get("orcid")
    if not orcid_id:
        return []
    author = request_json(
        f"https://api.openalex.org/authors/https://orcid.org/{orcid_id}",
        params={"mailto": "philipp.pelz@fau.de"},
    )
    if not author or not author.get("id"):
        print(f"  OpenAlex: no author match for {profile['name']}")
        return []

    candidates = []
    cursor = "*"
    for _ in range(max_pages):
        data = request_json(
            "https://api.openalex.org/works",
            params={
                "filter": f"authorships.author.id:{author['id']}",
                "per-page": 200,
                "cursor": cursor,
                "mailto": "philipp.pelz@fau.de",
            },
        )
        results = (data or {}).get("results", []) or []
        for work in results:
            candidate = candidate_from_openalex_work(work, profile)
            if candidate:
                candidates.append(candidate)
        next_cursor = ((data or {}).get("meta") or {}).get("next_cursor")
        if not results or not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor
        time.sleep(0.1)
    print(f"  OpenAlex: {len(candidates)} candidates for {profile['name']}")
    return candidates


def collect_scopus_candidates(profile, max_pages=5):
    scopus_id = profile["ids"].get("scopus")
    api_key = os.environ.get("SCOPUS_API_KEY")
    if not scopus_id:
        return []
    if not api_key:
        print(f"  Scopus ID found for {profile['name']}, but SCOPUS_API_KEY is not set; skipping Scopus API")
        return []

    candidates = []
    start = 0
    for _ in range(max_pages):
        data = request_json(
            "https://api.elsevier.com/content/search/scopus",
            params={
                "query": f"AU-ID({scopus_id})",
                "start": start,
                "count": 25,
                "field": "dc:title,prism:doi,prism:coverDate,prism:publicationName,subtypeDescription,dc:creator",
                "httpAccept": "application/json",
            },
            headers={"X-ELS-APIKey": api_key, "Accept": "application/json"},
        )
        entries = ((data or {}).get("search-results") or {}).get("entry", []) or []
        for entry in entries:
            cover_date = entry.get("prism:coverDate", "")
            year = cover_date[:4] if cover_date else ""
            pub_date = {"year": year, "month": cover_date[5:7] if len(cover_date) >= 7 else None, "day": cover_date[8:10] if len(cover_date) >= 10 else None}
            candidate = source_candidate(
                "scopus",
                profile,
                title=entry.get("dc:title", ""),
                doi=entry.get("prism:doi", ""),
                year=year,
                journal_title=entry.get("prism:publicationName", ""),
                work_type=entry.get("subtypeDescription", ""),
                publication_date=pub_date,
                authors=[entry["dc:creator"]] if entry.get("dc:creator") else [],
            )
            if candidate:
                candidates.append(candidate)
        if len(entries) < 25:
            break
        start += 25
        time.sleep(0.2)
    print(f"  Scopus: {len(candidates)} candidates for {profile['name']}")
    return candidates


def get_publication_info_from_crossref(doi):
    """Fetch complete publication information from Crossref API using DOI"""
    doi = normalize_doi(doi)
    url = f"https://api.crossref.org/works/{doi}"
    try:
        response = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=30)
        if response.status_code == 200:
            data = response.json()
            work = data.get('message', {})
            
            # Extract authors
            authors = []
            if 'author' in work:
                for author in work['author']:
                    if 'given' in author and 'family' in author:
                        authors.append(f"{author['given']} {author['family']}")
                    elif 'family' in author:
                        authors.append(author['family'])
                    elif 'name' in author:
                        authors.append(author['name'])
            
            # Extract abstract
            abstract = ""
            if 'abstract' in work:
                abstract = work['abstract']
            
            # Extract volume and page information
            volume = work.get('volume', '')
            page = work.get('page', '')
            
            # Extract container title (journal name)
            container_title = ""
            if 'container-title' in work and work['container-title']:
                container_title = work['container-title'][0]
            
            # Extract keywords/subjects
            keywords = []
            if 'subject' in work:
                keywords.extend(work['subject'])
            if 'link' in work:
                for link in work['link']:
                    if link.get('content-type') == 'application/pdf':
                        # Sometimes keywords are in link descriptions
                        if 'title' in link and link['title']:
                            keywords.append(link['title'])
            
            return {
                'authors': authors,
                'abstract': abstract,
                'volume': volume,
                'page': page,
                'container_title': container_title,
                'keywords': keywords
            }
        else:
            print(f"Crossref API error for DOI {doi}: {response.status_code}")
            return {'authors': [], 'abstract': '', 'volume': '', 'page': '', 'container_title': '', 'keywords': []}
    except Exception as e:
        print(f"Error fetching publication info for DOI {doi}: {e}")
        return {'authors': [], 'abstract': '', 'volume': '', 'page': '', 'container_title': '', 'keywords': []}

def get_abstract_from_semantic_scholar(doi):
    """Fetch abstract from Semantic Scholar API as fallback"""
    doi = normalize_doi(doi)
    url = f"https://api.semanticscholar.org/graph/v1/paper/{doi}?fields=abstract"
    try:
        response = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return data.get('abstract', '')
        else:
            return ''
    except Exception as e:
        print(f"Semantic Scholar API error for DOI {doi}: {e}")
        return ''

def get_keywords_from_semantic_scholar(doi):
    """Fetch keywords from Semantic Scholar API"""
    doi = normalize_doi(doi)
    url = f"https://api.semanticscholar.org/graph/v1/paper/{doi}?fields=topics"
    try:
        response = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=30)
        if response.status_code == 200:
            data = response.json()
            topics = data.get('topics', [])
            keywords = []
            for topic in topics:
                if 'topic' in topic:
                    keywords.append(topic['topic'])
            return keywords
        else:
            return []
    except Exception as e:
        print(f"Semantic Scholar keywords API error for DOI {doi}: {e}")
        return []

def get_publication_info_with_fallback(doi):
    """Fetch publication info from Crossref, with Semantic Scholar as fallback for abstract and keywords"""
    crossref_info = get_publication_info_from_crossref(doi)
    
    # If no abstract from Crossref, try Semantic Scholar
    if not crossref_info['abstract']:
        print(f"  No abstract in Crossref, trying Semantic Scholar...")
        semantic_abstract = get_abstract_from_semantic_scholar(doi)
        if semantic_abstract:
            crossref_info['abstract'] = semantic_abstract
            print(f"  Found abstract in Semantic Scholar!")
        else:
            print(f"  No abstract found in Semantic Scholar either")
    
    # If no keywords from Crossref, try Semantic Scholar
    if not crossref_info['keywords']:
        print(f"  No keywords in Crossref, trying Semantic Scholar...")
        semantic_keywords = get_keywords_from_semantic_scholar(doi)
        if semantic_keywords:
            crossref_info['keywords'].extend(semantic_keywords)
            print(f"  Found {len(semantic_keywords)} keywords in Semantic Scholar!")
        else:
            print(f"  No keywords found in Semantic Scholar either")
    
    return crossref_info

def clean_filename(title):
    """Convert title to a clean filename"""
    # Remove special characters and replace spaces with underscores
    clean = re.sub(r'[^\w\s-]', '', title)
    clean = re.sub(r'[-\s]+', '_', clean)
    return clean.lower()[:50]  # Limit length

def format_authors_for_bibtex(authors):
    """Format authors list for bibtex-style author field"""
    if not authors:
        return ""
    
    # Convert full names to initials + last name format
    formatted_authors = []
    for author in authors:
        parts = author.split()
        if len(parts) >= 2:
            # Take first letter of each part except the last
            initials = " ".join([part[0] + "." for part in parts[:-1]])
            last_name = parts[-1]
            formatted_authors.append(f"{initials} {last_name}")
        else:
            formatted_authors.append(author)
    
    return ", ".join(formatted_authors)

def jats_to_markdown(jats_text):
    """Convert JATS XML tags in abstract to Markdown/HTML-compatible formatting."""
    if not jats_text:
        return ''
    # Remove <jats:title> tags entirely (including "Abstract" titles)
    jats_text = re.sub(r'<jats:title>.*?</jats:title>', '', jats_text, flags=re.DOTALL)
    # Remove <jats:p> tags, keep their content
    jats_text = re.sub(r'<jats:p>(.*?)</jats:p>', r'\1\n\n', jats_text, flags=re.DOTALL)
    # Convert <jats:sub>...</jats:sub> to <sub>...</sub>
    jats_text = re.sub(r'<jats:sub>(.*?)</jats:sub>', r'<sub>\1</sub>', jats_text)
    # Remove any other JATS tags (e.g., <jats:sup>, <jats:bold>, etc.) but keep their content
    jats_text = re.sub(r'<jats:[^>]+>(.*?)</jats:[^>]+>', r'\1', jats_text)
    # Unescape HTML entities
    jats_text = html.unescape(jats_text)
    # Remove leading/trailing whitespace and extra newlines
    jats_text = re.sub(r'\n\s*\n\s*\n', '\n\n', jats_text)  # Remove excessive newlines
    # Remove excessive tabs and normalize whitespace
    jats_text = re.sub(r'\t+', ' ', jats_text)  # Replace tabs with single spaces
    jats_text = re.sub(r' +', ' ', jats_text)   # Replace multiple spaces with single space
    return jats_text.strip()

def load_publication_links(csv_file="publication_links.csv"):
    """Load publication links from CSV file"""
    links = {}
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                doi = row['doi'].strip()
                links[doi] = {
                    'code_url': row['code_url'].strip() if row['code_url'].strip() else '',
                    'project_page_url': row['project_page_url'].strip() if row['project_page_url'].strip() else ''
                }
        print(f"Loaded {len(links)} publication links from {csv_file}")
    except FileNotFoundError:
        print(f"Warning: {csv_file} not found. No additional links will be added.")
    except Exception as e:
        print(f"Error reading {csv_file}: {e}")
    return links

def detect_categories(title, keywords, work_type):
    """Detect categories based on title, keywords, and work type"""
    categories = []
    
    # Combine title and keywords for analysis
    text_to_analyze = title.lower()
    if keywords:
        text_to_analyze += " " + " ".join(keywords).lower()
    
    # Category detection based on keywords and title
    category_keywords = {
        "ptychography": ["ptychography", "ptychographic", "ptychogram"],
        "electron microscopy": ["electron microscopy", "stem", "tem", "scanning transmission", "transmission electron", "4d-stem", "4d stem"],
        "X-ray microscopy": ["x-ray", "xray", "synchrotron", "x-ray microscopy"],
        "tomography": ["tomography", "tomographic", "3d reconstruction", "tilt series"],
        "software": ["software", "algorithm", "py4dstem", "prismatic", "code", "implementation", "package"],
        "cryo-EM": ["cryo", "cryogenic", "cryo-em", "cryo em"],
        "atomic resolution": ["atomic", "ångstrom", "angstrom", "sub-angstrom", "atomic resolution"],
        "nanoparticles": ["nanoparticle", "nanoparticles", "nano", "quantum dot"],
        "materials science": ["materials", "crystal", "crystalline", "lattice", "defect"],
        "imaging": ["imaging", "microscopy", "microscope", "image reconstruction"],
        "computational": ["computational", "simulation", "modeling", "numerical", "algorithm"],
        "machine learning": ["machine learning", "deep learning", "neural network", "ai", "artificial intelligence"],
        "physics": ["physics", "physical", "scattering", "diffraction", "interference"],
        "chemistry": ["chemistry", "chemical", "molecular", "organic", "inorganic"],
        "biology": ["biology", "biological", "biomolecule", "protein", "cell"]
    }
    
    # Check each category
    for category, keywords_list in category_keywords.items():
        for keyword in keywords_list:
            if keyword in text_to_analyze:
                if category not in categories:
                    categories.append(category)
                break
    
    # Add work type category
    if work_type == "journal-article":
        if "journal article" not in categories:
            categories.append("journal article")
    elif work_type == "conference-paper":
        if "conference paper" not in categories:
            categories.append("conference paper")
    elif work_type == "book-chapter":
        if "book chapter" not in categories:
            categories.append("book chapter")
    
    # Ensure we have at least one category
    if not categories:
        categories.append("research")
    
    return categories

def generate_qmd_content(title, authors, year, journal_title, doi, work_type, publication_date, crossref_info, publication_links):
    """Generate the content for a qmd file"""
    
    # Use Crossref journal title if available, otherwise use ORCID data
    final_journal_title = crossref_info.get('container_title', journal_title) or journal_title
    
    # Get keywords from Crossref
    keywords = crossref_info.get('keywords', [])
    
    # Detect categories using improved algorithm
    categories = detect_categories(title, keywords, work_type)
    
    # Format publication string with volume and page info
    publication = final_journal_title
    volume = crossref_info.get('volume', '')
    page = crossref_info.get('page', '')
    
    if volume and page:
        publication += f" {volume}, {page}"
    elif volume:
        publication += f" {volume}"
    
    # Format authors for bibtex
    bibtex_authors = format_authors_for_bibtex(authors)
    
    # Generate filename
    filename = clean_filename(title)
    
    # Get abstract
    abstract = crossref_info.get('abstract', '')
    if abstract:
        abstract = jats_to_markdown(abstract)
    else:
        abstract = "[Abstract will be added manually]"
    
    # Get additional links from CSV
    links = publication_links.get(doi, {})
    code_url = links.get('code_url', '')
    project_page_url = links.get('project_page_url', '')
    
    # Create qmd content
    categories_str = "\n  - ".join(categories)
    qmd_content = f"""---
title: "{title}"
type: "article"
author: "{bibtex_authors}"
year: "{year}"
publication: "{publication}"
preprint: ""
doi: "{doi}"
materials: ""
code_url: "{code_url}"
project_page_url: "{project_page_url}"
toc: false
categories:
  - {categories_str}
---

## Citation (APA 7)

> {title}
{bibtex_authors}
{publication}


## Abstract

{abstract}


"""
    
    return filename, qmd_content

def empty_publication_info():
    return {'authors': [], 'abstract': '', 'volume': '', 'page': '', 'container_title': '', 'keywords': []}


def collect_candidates_for_profiles(profiles):
    candidates = []
    for profile in profiles:
        ids = ", ".join(f"{key}={value}" for key, value in sorted(profile["ids"].items()))
        print(f"\nCollecting publications for {profile['name']} ({ids})")
        candidates.extend(collect_orcid_candidates(profile))
        candidates.extend(collect_crossref_candidates(profile))
        candidates.extend(collect_openalex_candidates(profile))
        candidates.extend(collect_scopus_candidates(profile))
        if profile["ids"].get("webofscience") and not os.environ.get("WOS_API_KEY"):
            print(f"  Web of Science ID found for {profile['name']}, but WOS_API_KEY is not set; skipping WoS API")
        if profile["ids"].get("google_scholar"):
            print(f"  Google Scholar ID found for {profile['name']}; no stable official API is available, so it is not scraped")
    return candidates


def publication_from_candidate(candidate):
    doi = normalize_doi(candidate.get("doi"))
    if doi:
        print(f"\nProcessing: {candidate['title']}")
        crossref_info = get_publication_info_with_fallback(doi)
        time.sleep(0.2)
    else:
        print(f"\nProcessing DOI-free candidate: {candidate['title']}")
        crossref_info = empty_publication_info()

    if not crossref_info.get("authors") and candidate.get("authors"):
        crossref_info["authors"] = candidate["authors"]
    if not crossref_info.get("container_title") and candidate.get("journal_title"):
        crossref_info["container_title"] = candidate["journal_title"]

    keywords = crossref_info.get('keywords', [])
    if keywords:
        print(f"  Keywords found: {', '.join(keywords[:5])}")

    return {
        'title': candidate['title'],
        'authors': crossref_info.get('authors', []),
        'year': candidate.get('year') or candidate.get('publication_date', {}).get('year', ''),
        'journal_title': candidate.get('journal_title', ''),
        'doi': doi,
        'work_type': candidate.get('work_type', ''),
        'publication_date': candidate.get('publication_date') or {
            'year': candidate.get('year', ''),
            'month': None,
            'day': None,
        },
        'crossref_info': crossref_info,
        'sources': candidate.get('sources', [candidate.get('source', '')]),
        'matched_people': candidate.get('matched_people', []),
    }


def main(output_dir="publications/articles"):
    """Fetch active people publications and generate qmd files."""
    publication_links = load_publication_links()

    profiles = discover_people_profiles("people")
    print(f"Discovered {len(profiles)} active people profiles with publication IDs")
    if not profiles:
        print("No active people profiles with publication IDs found; nothing to generate.")
        return

    candidates = collect_candidates_for_profiles(profiles)
    paper_candidates = filter_publication_candidates(candidates)
    print(f"\nCollected {len(candidates)} raw candidates; kept {len(paper_candidates)} paper-like candidates")
    publications = [publication_from_candidate(candidate) for candidate in merge_publication_candidates(paper_candidates)]

    print(f"\nFound {len(publications)} publications to process after deduplication")

    # Sort publications from oldest to newest
    def pub_sort_key(pub):
        y = pub['year']
        m = pub['publication_date'].get('month')
        d = pub['publication_date'].get('day')
        # Use 0 for missing month/day so missing values sort as earliest
        return (
            int(y) if y and y.isdigit() else 0,
            int(m) if m and m.isdigit() else 0,
            int(d) if d and d.isdigit() else 0
        )
    publications.sort(key=pub_sort_key)
    
    # Generate qmd files
    os.makedirs(output_dir, exist_ok=True)
    for old_file in Path(output_dir).glob("*.qmd"):
        old_file.unlink()
    
    print(f"\nGenerating qmd files in {output_dir}...")
    for i, pub in enumerate(publications):
        filename, content = generate_qmd_content(
            pub['title'],
            pub['authors'],
            pub['year'],
            pub['journal_title'],
            pub['doi'],
            pub['work_type'],
            pub['publication_date'],
            pub['crossref_info'],
            publication_links
        )
        
        # Add index number to filename to ensure uniqueness
        qmd_filename = f"{i+1:02d}_{filename}.qmd"
        filepath = os.path.join(output_dir, qmd_filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Created: {qmd_filename}")
    
    print(f"\nSuccessfully generated {len(publications)} qmd files in {output_dir}")

if __name__ == "__main__":
    # For testing, use the test directory
    main("publications/articles")
    
    # Uncomment the line below to generate files in the actual publications folder
    # main("publications/articles") 
