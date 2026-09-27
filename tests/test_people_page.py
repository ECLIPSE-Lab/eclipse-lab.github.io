from pathlib import Path
import subprocess

import pytest
import yaml
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]


def front_matter(relative_path):
    text = (ROOT / relative_path).read_text(encoding="utf-8")
    _, yaml_text, _ = text.split("---", 2)
    return yaml.safe_load(yaml_text)


@pytest.fixture(scope="session")
def people_page():
    result = subprocess.run(
        ["quarto", "render", "people.qmd"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return BeautifulSoup(
        (ROOT / "docs/people.html").read_text(encoding="utf-8"),
        "html.parser",
    )


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


def test_active_members_use_people_cards(people_page):
    cards = people_page.select(".people-card")
    assert len(cards) == 13
    for card in cards:
        trigger = card.select_one(".people-card__trigger")
        panel = card.select_one(".people-card__panel")
        image = card.select_one("img")
        assert trigger["aria-controls"] == panel["id"]
        assert trigger["aria-expanded"] == "false"
        assert image.get("alt") == card.select_one(
            ".people-card__name"
        ).get_text(strip=True)
        assert panel.select_one(".people-card__profile-link")


def test_sparse_profiles_omit_optional_blocks(people_page):
    bardia = next(
        card
        for card in people_page.select(".people-card")
        if "Bardia Nasiri Sharaf" in card.get_text(" ", strip=True)
    )
    assert bardia.select_one(".people-card__summary") is None
    assert bardia.select_one(".people-card__links") is None


def test_confirmed_links_render(people_page):
    assert people_page.select_one(
        'a[href="https://orcid.org/0009-0008-0739-9903"]'
    )
    assert people_page.select_one('a[href="mailto:yesim.tosun@fau.de"]')
    assert not people_page.select_one('a[href="mailto:jenny.wirth@fau.de"]')


def test_alumni_remain_a_table(people_page):
    alumni = people_page.select_one("#alumni")
    assert alumni.select_one("table")
    assert not alumni.select_one(".people-card")
