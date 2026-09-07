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
