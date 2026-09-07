from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def front_matter(relative_path):
    text = (ROOT / relative_path).read_text(encoding="utf-8")
    _, yaml_text, _ = text.split("---", 2)
    return yaml.safe_load(yaml_text)


def test_confirmed_people_card_metadata():
    shengbo = front_matter("people/postdocs/02_shengbo_you.qmd")
    shengbo_links = shengbo["about"]["links"]
    assert any(
        link.get("href") == "https://orcid.org/0009-0008-0739-9903"
        for link in shengbo_links
    )

    yesim = front_matter("people/admins/yesim_tosun.qmd")
    yesim_links = yesim["about"]["links"]
    assert any(
        link.get("href") == "mailto:yesim.tosun@fau.de"
        for link in yesim_links
    )


def test_optional_card_copy_is_compact():
    paths = [
        "people/pi/00_pelz_philipp.qmd",
        "people/postdocs/02_shengbo_you.qmd",
        "people/phd/06_williams.qmd",
        "people/honorary/07_yan_mei.qmd",
    ]
    for path in paths:
        metadata = front_matter(path)
        copy = metadata.get("interests") or metadata.get("card-bio")
        assert copy
        assert len(copy) <= 220
