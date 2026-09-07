import socket
import subprocess
import time
import urllib.request
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def site_url():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    server = subprocess.Popen(
        ["python", "-m", "http.server", str(port), "--directory", "docs"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            urllib.request.urlopen(f"{url}/people.html", timeout=0.2).close()
            break
        except OSError:
            time.sleep(0.1)
    else:
        server.terminate()
        raise RuntimeError("People page test server did not start")

    yield url
    server.terminate()
    server.wait(timeout=5)


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as playwright:
        instance = playwright.chromium.launch(
            executable_path="/usr/bin/google-chrome",
            headless=True,
            args=["--no-sandbox"],
        )
        yield instance
        instance.close()


@pytest.fixture
def page(browser):
    instance = browser.new_page()
    yield instance
    instance.close()


def test_people_grid_is_responsive(page, site_url):
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.goto(f"{site_url}/people.html")
    desktop_columns = page.locator("#phd-students .people-grid").evaluate(
        "grid => getComputedStyle(grid).gridTemplateColumns.split(' ').length"
    )
    assert desktop_columns == 4

    page.set_viewport_size({"width": 390, "height": 844})
    cards = page.locator("#phd-students .people-card")
    tops = cards.evaluate_all(
        "nodes => nodes.map(node => Math.round(node.getBoundingClientRect().top))"
    )
    assert len(set(tops)) == cards.count()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


def test_category_spacing_is_compact(page, site_url):
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.goto(f"{site_url}/people.html")
    grid = page.locator("#listing-pi .people-grid")
    next_heading = page.locator("#postdocs > h2")
    grid_box = grid.bounding_box()
    heading_box = next_heading.bounding_box()

    gap = heading_box["y"] - (grid_box["y"] + grid_box["height"])
    assert gap <= 60


def test_hover_and_keyboard_open_and_close(page, site_url):
    page.goto(f"{site_url}/people.html")
    card = page.locator(".people-card").first
    trigger = card.locator(".people-card__trigger")
    panel = card.locator(".people-card__panel")

    card.hover()
    assert panel.is_visible()
    trigger.focus()
    assert trigger.get_attribute("aria-expanded") == "true"
    trigger.press("Escape")
    assert trigger.get_attribute("aria-expanded") == "false"
    trigger.press("Space")
    assert trigger.get_attribute("aria-expanded") == "true"


def test_only_one_touch_panel_opens(browser, site_url):
    context = browser.new_context(
        viewport={"width": 390, "height": 844},
        has_touch=True,
        is_mobile=True,
    )
    page = context.new_page()
    page.goto(f"{site_url}/people.html")
    triggers = page.locator(".people-card__trigger")

    triggers.nth(0).tap()
    assert triggers.nth(0).get_attribute("aria-expanded") == "true"
    triggers.nth(1).dispatch_event("click")
    assert triggers.nth(0).get_attribute("aria-expanded") == "false"
    assert triggers.nth(1).get_attribute("aria-expanded") == "true"
    assert page.locator(".people-card.is-open").count() == 1
    context.close()


def test_open_panels_stay_inside_viewport(page, site_url):
    page.set_viewport_size({"width": 1024, "height": 800})
    page.goto(f"{site_url}/people.html")
    cards = page.locator("#phd-students .people-card")

    for index in range(cards.count()):
        card = cards.nth(index)
        card.hover()
        rect = card.locator(".people-card__panel").bounding_box()
        assert rect["x"] >= 16
        assert rect["x"] + rect["width"] <= 1008
