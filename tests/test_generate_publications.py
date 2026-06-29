from pathlib import Path

import generate_publications as gp


def write_qmd(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_discovers_active_people_profiles_and_ignores_alumni_and_commented_links(tmp_path):
    people_dir = tmp_path / "people"
    write_qmd(
        people_dir / "staff" / "active.qmd",
        """---
title: "Active Researcher"
about:
  links:
    - text: ORCID
      href: https://orcid.org/0000-0002-8009-4515
    - text: scholar
      href: https://scholar.google.com/citations?hl=en&user=d-lXKR8AAAAJ
    - text: Scopus ID
      href: https://www.scopus.com/authid/detail.uri?authorId=56005365900
    - text: Web of Science
      href: https://www.webofscience.com/wos/author/record/JZT-3950-2024
    # - text: ORCID
    #   href: https://orcid.org/1111-1111-1111-1111
---
""",
    )
    write_qmd(
        people_dir / "alumni" / "former.qmd",
        """---
title: "Former Researcher"
about:
  links:
    - text: ORCID
      href: https://orcid.org/2222-2222-2222-2222
---
""",
    )

    profiles = gp.discover_people_profiles(people_dir)

    assert [profile["name"] for profile in profiles] == ["Active Researcher"]
    assert profiles[0]["ids"] == {
        "orcid": "0000-0002-8009-4515",
        "google_scholar": "d-lXKR8AAAAJ",
        "scopus": "56005365900",
        "webofscience": "JZT-3950-2024",
    }


def test_merges_publication_candidates_by_doi_and_normalized_title():
    candidates = [
        {
            "title": "Near-isotropic sub-Angstrom 3D resolution",
            "doi": "https://doi.org/10.1234/ABC",
            "source": "orcid",
            "matched_people": ["A"],
        },
        {
            "title": "Near isotropic sub Angstrom 3D resolution",
            "doi": "10.1234/abc",
            "source": "openalex",
            "matched_people": ["B"],
        },
        {
            "title": "A DOI-free preprint title",
            "doi": "",
            "source": "semantic_scholar",
            "matched_people": ["A"],
        },
        {
            "title": "A doi free preprint title",
            "doi": None,
            "source": "openalex",
            "matched_people": ["B"],
        },
    ]

    merged = gp.merge_publication_candidates(candidates)

    assert len(merged) == 2
    by_title = {gp.normalize_title(pub["title"]): pub for pub in merged}
    doi_pub = by_title["near isotropic sub angstrom 3d resolution"]
    assert doi_pub["doi"] == "10.1234/abc"
    assert doi_pub["sources"] == ["openalex", "orcid"]
    assert doi_pub["matched_people"] == ["A", "B"]

    preprint_pub = by_title["a doi free preprint title"]
    assert preprint_pub["sources"] == ["openalex", "semantic_scholar"]
    assert preprint_pub["matched_people"] == ["A", "B"]


def test_parses_public_source_records_into_common_candidates():
    profile = {"name": "Active Researcher"}

    orcid_summary = {
        "title": {"title": {"value": "ORCID Work"}},
        "external-ids": {"external-id": [{"external-id-type": "doi", "external-id-value": "10.1000/orcid"}]},
        "journal-title": {"value": "ORCID Journal"},
        "publication-date": {"year": {"value": "2024"}, "month": {"value": "05"}, "day": {"value": "02"}},
        "type": "journal-article",
    }
    crossref_item = {
        "title": ["Crossref Work"],
        "DOI": "10.1000/crossref",
        "container-title": ["Crossref Journal"],
        "published-print": {"date-parts": [[2023, 4]]},
        "type": "journal-article",
        "author": [{"given": "Ada", "family": "Lovelace"}],
    }
    openalex_work = {
        "display_name": "OpenAlex Work",
        "doi": "https://doi.org/10.1000/openalex",
        "publication_year": 2022,
        "publication_date": "2022-03-01",
        "type": "article",
        "primary_location": {"source": {"display_name": "OpenAlex Journal"}},
        "authorships": [{"author": {"display_name": "Grace Hopper"}}],
    }

    assert gp.candidate_from_orcid_summary(orcid_summary, profile) == {
        "title": "ORCID Work",
        "doi": "10.1000/orcid",
        "year": "2024",
        "journal_title": "ORCID Journal",
        "work_type": "journal-article",
        "publication_date": {"year": "2024", "month": "05", "day": "02"},
        "authors": [],
        "source": "orcid",
        "matched_people": ["Active Researcher"],
    }

    crossref_candidate = gp.candidate_from_crossref_item(crossref_item, profile)
    assert crossref_candidate["title"] == "Crossref Work"
    assert crossref_candidate["doi"] == "10.1000/crossref"
    assert crossref_candidate["journal_title"] == "Crossref Journal"
    assert crossref_candidate["year"] == "2023"
    assert crossref_candidate["authors"] == ["Ada Lovelace"]

    openalex_candidate = gp.candidate_from_openalex_work(openalex_work, profile)
    assert openalex_candidate["title"] == "OpenAlex Work"
    assert openalex_candidate["doi"] == "10.1000/openalex"
    assert openalex_candidate["journal_title"] == "OpenAlex Journal"
    assert openalex_candidate["year"] == "2022"
    assert openalex_candidate["authors"] == ["Grace Hopper"]


def test_orcid_date_parser_handles_null_date_parts():
    assert gp.date_from_orcid({"year": {"value": "2024"}, "month": None, "day": None}) == {
        "year": "2024",
        "month": None,
        "day": None,
    }


def test_orcid_arxiv_external_id_is_converted_to_arxiv_doi():
    profile = {"name": "Active Researcher"}
    orcid_summary = {
        "title": {"title": {"value": "arXiv-only Work"}},
        "external-ids": {"external-id": [{"external-id-type": "arxiv", "external-id-value": "2501.01234"}]},
        "journal-title": {"value": "arXiv"},
        "publication-date": {"year": {"value": "2025"}},
        "type": "preprint",
    }

    candidate = gp.candidate_from_orcid_summary(orcid_summary, profile)

    assert candidate["doi"] == "10.48550/arxiv.2501.01234"
    assert gp.filter_publication_candidates([candidate]) == [candidate]


def test_filters_repository_artifacts_and_prefers_published_doi_over_preprint_duplicates():
    profile = {"name": "Active Researcher"}
    candidates = [
        gp.source_candidate("openalex", profile, "Same Paper", "10.48550/arxiv.1234.5678", "2024", "arXiv", "posted-content"),
        gp.source_candidate("crossref", profile, "Same Paper", "10.1038/example", "2025", "Nature", "journal-article"),
        gp.source_candidate("openalex", profile, "Same Paper", "", "2025", "ArXiv.org", "article"),
        gp.source_candidate("orcid", profile, "Data for: Same Paper", "10.5281/zenodo.12345", "2025", "Zenodo", "data-set"),
        gp.source_candidate("openalex", profile, "Patient to Room Assignments", "", "2025", "University Repository", "other"),
    ]

    merged = gp.merge_publication_candidates(gp.filter_publication_candidates(candidates))

    assert len(merged) == 1
    assert merged[0]["title"] == "Same Paper"
    assert merged[0]["doi"] == "10.1038/example"
    assert merged[0]["sources"] == ["crossref", "openalex"]
