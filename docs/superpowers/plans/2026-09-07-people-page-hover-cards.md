# People Page Hover Cards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the active-member grids on the People page with accessible Stanford-inspired portrait cards and hover/tap information panels while keeping the Alumni table unchanged.

**Architecture:** A custom Quarto EJS listing template renders semantic card and panel markup directly from each profile's front matter. Page-scoped CSS controls the responsive grid and visual presentation, while a small dependency-free script adds single-panel state, touch and keyboard behavior, and viewport-aware alignment. Pytest and Playwright verify the rendered Quarto output and browser interactions.

**Tech Stack:** Quarto 1.7, EJS listing templates, HTML, CSS, vanilla JavaScript, Python 3, pytest, BeautifulSoup, Playwright, Google Chrome

---

## File Structure

- Create `_templates/people-card.ejs.md`: render one responsive grid for any active-member listing, including conditional panel fields and accessible attributes.
- Create `people-cards.css`: contain only People page grid, card, panel, breakpoint, focus, and reduced-motion rules.
- Create `people-cards.js`: manage open card state, keyboard/touch input, outside clicks, Escape, and viewport alignment.
- Create `tests/test_people_page.py`: render `people.qmd` and verify content, metadata, accessibility markup, and Alumni regression behavior.
- Create `tests/test_people_page_browser.py`: verify hover, keyboard, touch, single-open state, and viewport overflow in a real browser.
- Modify `people.qmd`: use the custom template for active-member listings, retain the Alumni table, and load the page-scoped assets.
- Modify `people/pi/00_pelz_philipp.qmd`: expose existing research interests as compact card metadata.
- Modify `people/postdocs/02_shengbo_you.qmd`: expose existing interests and add the confirmed ORCID link.
- Modify `people/phd/06_williams.qmd`: expose existing research interests as compact card metadata.
- Modify `people/honorary/07_yan_mei.qmd`: expose the existing one-sentence background as optional card biography metadata.
- Modify `people/admins/yesim_tosun.qmd`: correct the email and expose it as an email link.
- Update generated `docs/people.html` and copied page assets only after source and browser verification. Because generated files already contain unrelated user changes, inspect and stage their diff separately.

## Guardrails for the Existing Worktree

The worktree contains unrelated source and generated-site changes. Before every commit, run `git diff --cached --stat` and `git diff --cached`, and stage only files named by the current task. Never use `git add .`, `git commit -a`, checkout/reset commands, or broad formatting. Do not overwrite or revert existing changes in `_quarto.yml`, `styles.css`, `_includes/`, other profile files, or unrelated files under `docs/`.

### Task 1: Add the Card Metadata Contract

**Files:**
- Create: `tests/test_people_page.py`
- Modify: `people/pi/00_pelz_philipp.qmd:2-7`
- Modify: `people/postdocs/02_shengbo_you.qmd:2-8`
- Modify: `people/phd/06_williams.qmd:4-10`
- Modify: `people/honorary/07_yan_mei.qmd:2-9`
- Modify: `people/admins/yesim_tosun.qmd:2-15,46-48`

- [ ] **Step 1: Write failing source-metadata tests**

Add tests that parse YAML front matter and establish the approved metadata contract without requiring every optional field:

```python
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
```

- [ ] **Step 2: Run the focused tests and confirm the expected failure**

Run: `pytest tests/test_people_page.py -q`

Expected: FAIL because Shengbo's ORCID, Yesim's structured email link, and some compact card fields do not exist yet.

- [ ] **Step 3: Add only confirmed or already-published metadata**

Add compact `interests` strings to Philipp Pelz, Shengbo You, and Umah Chukwudi Williams using their existing Research Interests sections. Add this existing background sentence to Yan Mei's front matter:

```yaml
card-bio: "Doctoral researcher in the CorMic graduate school, co-supervised with Prof. Luca Ghiringhelli (KIT)."
```

Add an active link to Shengbo's existing `about` block:

```yaml
links:
  - icon: book-fill
    text: ORCID
    href: https://orcid.org/0009-0008-0739-9903
```

Add an active link to Yesim's existing `about` block:

```yaml
links:
  - icon: envelope
    text: Email
    href: mailto:yesim.tosun@fau.de
```

Replace the incorrect plain-text Yesim email in the profile body with `Email: yesim.tosun@fau.de`. Do not populate any other missing fields.

- [ ] **Step 4: Run the focused tests**

Run: `pytest tests/test_people_page.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the metadata contract**

```bash
git add tests/test_people_page.py \
  people/pi/00_pelz_philipp.qmd \
  people/postdocs/02_shengbo_you.qmd \
  people/phd/06_williams.qmd \
  people/honorary/07_yan_mei.qmd \
  people/admins/yesim_tosun.qmd
git diff --cached
git commit -m "Add metadata for people hover cards"
```

### Task 2: Render Active Members with a Custom Quarto Template

**Files:**
- Create: `_templates/people-card.ejs.md`
- Modify: `people.qmd:1-79`
- Modify: `tests/test_people_page.py`

- [ ] **Step 1: Add failing rendered-markup tests**

Extend `tests/test_people_page.py` with a session fixture that renders the People page and parses it:

```python
import subprocess

import pytest
from bs4 import BeautifulSoup


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


def test_active_members_use_people_cards(people_page):
    cards = people_page.select(".people-card")
    assert len(cards) == 13
    for card in cards:
        trigger = card.select_one(".people-card__trigger")
        panel = card.select_one(".people-card__panel")
        image = card.select_one("img")
        assert trigger["aria-controls"] == panel["id"]
        assert trigger["aria-expanded"] == "false"
        assert image.get("alt") == card.select_one(".people-card__name").get_text(strip=True)
        assert panel.select_one(".people-card__profile-link")


def test_sparse_profiles_omit_optional_blocks(people_page):
    bardia = next(
        card for card in people_page.select(".people-card")
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
```

- [ ] **Step 2: Run the rendered-markup tests and confirm failure**

Run: `pytest tests/test_people_page.py -q`

Expected: FAIL because active listings still use Quarto's built-in grid cards.

- [ ] **Step 3: Create the reusable custom listing template**

Create `_templates/people-card.ejs.md`. Use `items`, `item.path`, standard fields, and custom metadata supplied by Quarto. The template must:

- emit one `.people-grid.list` wrapper;
- emit an `<article class="people-card">` for each item with `<%= metadataAttrs(item) %>`;
- derive a unique, HTML-safe panel ID from `item.path`;
- make the image/name/role block an anchor to `item.path` with class `.people-card__trigger`, `aria-expanded="false"`, and `aria-controls` pointing to the panel;
- render `item.image` with `alt` equal to `item.title` and `loading="lazy"`;
- render role and `started` only when present;
- choose `item.interests` first, then `item['card-bio']`, for the single optional summary block;
- render `item.about.links` only when the array exists and has entries, using `link.href` and `link.text`;
- append a `.people-card__profile-link` to `item.path`; and
- use escaped EJS output (`<%- value %>`) for profile metadata and URLs.

Implement the complete template as follows:

````ejs
```{=html}
<div class="people-grid list">
<% for (const item of items) {
     const key = String(item.path).replace(/[^a-zA-Z0-9_-]/g, "-");
     const panelId = `people-panel-${key}`;
     const summary = item.interests || item["card-bio"];
     const links = item.about && Array.isArray(item.about.links)
       ? item.about.links.filter(link => link && link.href)
       : [];
%>
  <article class="people-card" <%= metadataAttrs(item) %>>
    <a class="people-card__trigger" href="<%- item.path %>"
       aria-expanded="false" aria-controls="<%- panelId %>">
      <img class="people-card__portrait" src="<%- item.image %>"
           alt="<%- item.title %>" loading="lazy">
      <span class="people-card__name listing-title"><%- item.title %></span>
      <% if (item.subtitle) { %>
      <span class="people-card__role listing-subtitle"><%- item.subtitle %></span>
      <% } %>
    </a>
    <div class="people-card__panel" id="<%- panelId %>" aria-hidden="true">
      <% if (item.subtitle || item.started) { %>
      <div class="people-card__meta">
        <% if (item.subtitle) { %><strong><%- item.subtitle %></strong><% } %>
        <% if (item.started) { %><span>Since <%- item.started %></span><% } %>
      </div>
      <% } %>
      <% if (summary) { %>
      <div class="people-card__summary"><%- summary %></div>
      <% } %>
      <% if (links.length) { %>
      <div class="people-card__links">
        <% for (const link of links) { %>
        <a href="<%- link.href %>"><%- link.text || "Profile link" %></a>
        <% } %>
      </div>
      <% } %>
      <a class="people-card__profile-link" href="<%- item.path %>">View profile <span aria-hidden="true">→</span></a>
    </div>
  </article>
<% } %>
</div>
```
````

- [ ] **Step 4: Wire active listings to the template**

For listing IDs `pi`, `postdocs`, `phd-students`, `msc_students`, `research-assistants`, `admin-assistants`, and `honorary-members`, remove built-in grid-only options and set:

```yaml
template: _templates/people-card.ejs.md
sort: sortby
```

Keep the `alumni` configuration as `type: table` with its current sorting, filtering, fields, and display names. Do not reference the CSS or JavaScript yet; later tasks add each asset only after creating it.

- [ ] **Step 5: Run the rendered-markup tests**

Run: `pytest tests/test_people_page.py -q`

Expected: PASS, including 13 active cards, conditional omission for Bardia, confirmed links, and an intact Alumni table.

- [ ] **Step 6: Commit the semantic card rendering**

```bash
git add _templates/people-card.ejs.md people.qmd tests/test_people_page.py
git diff --cached
git commit -m "Render custom people profile cards"
```

### Task 3: Add the Responsive ECLIPSE Card Styling

**Files:**
- Create: `people-cards.css`
- Create: `tests/test_people_page_browser.py`
- Modify: `people.qmd:1-5`

- [ ] **Step 1: Write a failing browser layout test**

Create a test server fixture for `docs/` and a Playwright fixture using `/usr/bin/google-chrome`:

```python
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
```

- [ ] **Step 2: Run the layout test and confirm failure**

Run: `pytest tests/test_people_page_browser.py::test_people_grid_is_responsive -q`

Expected: FAIL because `people-cards.css` does not exist or the cards have no responsive grid rules.

- [ ] **Step 3: Implement page-scoped styles**

Create `people-cards.css` with rules scoped under `.people-grid` and `.people-card`. Include:

```css
.people-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1.5rem;
  align-items: start;
  margin: 1.25rem 0 3rem;
}

.people-card {
  position: relative;
  min-width: 0;
  text-align: center;
}

.people-card__trigger {
  display: flex;
  flex-direction: column;
  color: inherit;
  text-decoration: none;
  border-radius: 0.5rem;
}

.people-card__portrait {
  width: 100%;
  aspect-ratio: 1;
  object-fit: cover;
  border-radius: 0.25rem;
}

.people-card__panel {
  position: absolute;
  z-index: 20;
  top: calc(100% + 0.5rem);
  left: 50%;
  width: min(25rem, calc(100vw - 2rem));
  max-height: min(32rem, calc(100vh - 2rem));
  overflow-y: auto;
  transform: translateX(calc(-50% + var(--people-panel-shift, 0px))) translateY(-0.25rem);
  visibility: hidden;
  opacity: 0;
  pointer-events: none;
  text-align: left;
  background: #172033;
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 0.625rem;
  box-shadow: 0 1rem 2.5rem rgba(0, 0, 0, 0.45);
  transition: opacity 180ms ease, transform 180ms ease,
              visibility 0s linear 180ms;
}

.people-card:hover .people-card__panel,
html:not(.people-cards-enhanced) .people-card:focus-within .people-card__panel,
.people-card.is-open .people-card__panel {
  visibility: visible;
  opacity: 1;
  pointer-events: auto;
  transform: translateX(calc(-50% + var(--people-panel-shift, 0px))) translateY(0);
  transition-delay: 0s;
}

@media (max-width: 1199px) {
  .people-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}

@media (max-width: 767px) {
  .people-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 479px) {
  .people-grid { grid-template-columns: minmax(0, 1fr); }
}

@media (prefers-reduced-motion: reduce) {
  .people-card__panel { transition: none; }
}
```

Add explicit rules for `.people-card__name`, `.people-card__role`, `.people-card__meta`, `.people-card__summary`, `.people-card__links`, and `.people-card__profile-link`: use the existing Outfit heading font for names, Inter for supporting copy, `#f8fafc` for primary text, `#94a3b8` for secondary text, and `#93c5fd` for panel links. Separate nonempty panel sections with `rgba(148, 163, 184, 0.22)` borders, give the trigger a visible `#60a5fa` focus outline, and transition opacity, transform, portrait shadow, and delayed visibility over 180 ms. Keep the fixed four/three/two/one grid tracks above so sections with fewer cards occupy normal track widths rather than stretching.

Add the stylesheet to `people.qmd` front matter after it exists:

```yaml
css: people-cards.css
```

- [ ] **Step 4: Render and rerun layout tests**

Run: `quarto render people.qmd && pytest tests/test_people_page_browser.py::test_people_grid_is_responsive -q`

Expected: PASS.

- [ ] **Step 5: Commit the responsive styling**

```bash
git add people-cards.css people.qmd tests/test_people_page_browser.py
git diff --cached
git commit -m "Style responsive people profile cards"
```

### Task 4: Implement Hover, Keyboard, and Touch Behavior

**Files:**
- Create: `people-cards.js`
- Modify: `people.qmd:1-5, end of file`
- Modify: `tests/test_people_page_browser.py`

- [ ] **Step 1: Write failing interaction tests**

Add Playwright tests that verify:

```python
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


def test_only_one_touch_panel_opens_and_links_still_work(browser, site_url):
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
    triggers.nth(1).tap()
    assert triggers.nth(0).get_attribute("aria-expanded") == "false"
    assert triggers.nth(1).get_attribute("aria-expanded") == "true"
    assert page.locator(".people-card.is-open").count() == 1
    context.close()


def test_open_panels_stay_inside_viewport(page, site_url):
    page.set_viewport_size({"width": 1024, "height": 800})
    page.goto(f"{site_url}/people.html")
    for card in page.locator("#phd-students .people-card").all():
        card.hover()
        rect = card.locator(".people-card__panel").bounding_box()
        assert rect["x"] >= 16
        assert rect["x"] + rect["width"] <= 1008
```

- [ ] **Step 2: Run interaction tests and confirm failure**

Run: `pytest tests/test_people_page_browser.py -q`

Expected: FAIL because ARIA state, single-open touch state, Escape handling, and panel edge shifting are not implemented.

- [ ] **Step 3: Implement the dependency-free controller**

Create `people-cards.js` with the complete dependency-free controller:

```javascript
(() => {
  document.documentElement.classList.add('people-cards-enhanced');
  const cards = [...document.querySelectorAll('.people-card')];
  if (!cards.length) return;

  const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)');
  let openCard = null;

  function setState(card, expanded) {
    const trigger = card.querySelector('.people-card__trigger');
    const panel = card.querySelector('.people-card__panel');
    card.classList.toggle('is-open', expanded);
    trigger.setAttribute('aria-expanded', String(expanded));
    panel.setAttribute('aria-hidden', String(!expanded));
    if (expanded) {
      openCard = card;
      requestAnimationFrame(() => keepPanelInViewport(card));
    } else if (openCard === card) {
      openCard = null;
      panel.style.removeProperty('--people-panel-shift');
    }
  }

  function closeCurrent(except = null) {
    if (openCard && openCard !== except) setState(openCard, false);
  }

  function keepPanelInViewport(card) {
    const panel = card.querySelector('.people-card__panel');
    panel.style.setProperty('--people-panel-shift', '0px');
    const rect = panel.getBoundingClientRect();
    const gutter = 16;
    let shift = 0;
    if (rect.left < gutter) shift += gutter - rect.left;
    if (rect.right > innerWidth - gutter) shift -= rect.right - (innerWidth - gutter);
    panel.style.setProperty('--people-panel-shift', `${shift}px`);
  }

  cards.forEach((card) => {
    const trigger = card.querySelector('.people-card__trigger');
    let coarseActivation = false;

    card.addEventListener('mouseenter', () => {
      closeCurrent(card);
      requestAnimationFrame(() => keepPanelInViewport(card));
    });

    trigger.addEventListener('pointerdown', (event) => {
      coarseActivation = event.pointerType === 'touch' || event.pointerType === 'pen';
    });

    trigger.addEventListener('focus', () => {
      if (coarseActivation) return;
      closeCurrent(card);
      setState(card, true);
    });

    trigger.addEventListener('click', (event) => {
      const isCoarseClick = coarseActivation || !finePointer.matches;
      coarseActivation = false;
      if (!isCoarseClick || card.classList.contains('is-open')) return;
      event.preventDefault();
      closeCurrent(card);
      setState(card, true);
    });

    trigger.addEventListener('keydown', (event) => {
      if (event.key !== 'Enter' && event.key !== ' ') return;
      event.preventDefault();
      const expanded = trigger.getAttribute('aria-expanded') === 'true';
      closeCurrent(card);
      setState(card, !expanded);
    });

    card.addEventListener('focusout', () => {
      requestAnimationFrame(() => {
        if (!card.contains(document.activeElement)) setState(card, false);
      });
    });
  });

  document.addEventListener('click', (event) => {
    if (openCard && !openCard.contains(event.target)) setState(openCard, false);
  });

  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape' || !openCard) return;
    const trigger = openCard.querySelector('.people-card__trigger');
    setState(openCard, false);
    trigger.focus();
  });

  window.addEventListener('resize', () => {
    if (openCard) requestAnimationFrame(() => keepPanelInViewport(openCard));
  });
})();
```

After the script exists, add it as a page resource in `people.qmd` front matter:

```yaml
resources:
  - people-cards.js
```

Append this raw HTML once at the end of `people.qmd`:

```html
<script src="people-cards.js" defer></script>
```

Verify the implemented behavior against these requirements:

- pointer hover continues to work through CSS and updates position on `mouseenter`;
- on coarse/touch pointers, prevent the first trigger navigation and open the panel; a second trigger activation may follow the profile link;
- Enter and Space toggle the panel while focus is on the trigger; the explicit profile link remains the keyboard navigation path;
- Escape closes the current panel and returns focus to its trigger;
- clicking or tapping outside closes the current panel;
- opening a card closes the previously open card;
- focus moving into panel links does not close it;
- resize and orientation changes recompute the open panel's shift; and
- `aria-expanded` and `aria-hidden` always match the visual state.

- [ ] **Step 4: Run interaction and regression tests**

Run: `quarto render people.qmd && pytest tests/test_people_page.py tests/test_people_page_browser.py -q`

Expected: PASS.

- [ ] **Step 5: Commit interaction behavior**

```bash
git add people-cards.js people.qmd tests/test_people_page_browser.py
git diff --cached
git commit -m "Add accessible people card interactions"
```

### Task 5: Verify the Finished Page and Generated Output

**Files:**
- Modify: `docs/people.html`
- Create or modify through Quarto: `docs/people-cards.css`, `docs/people-cards.js`

- [ ] **Step 1: Run all existing Python tests**

Run: `pytest -q`

Expected: all tests pass.

- [ ] **Step 2: Render the complete site**

Run: `quarto render`

Expected: exit code 0 with no EJS template, missing-resource, or YAML errors.

- [ ] **Step 3: Rerun the people-page browser suite against the final render**

Run: `pytest tests/test_people_page.py tests/test_people_page_browser.py -q`

Expected: all People page tests pass.

- [ ] **Step 4: Inspect desktop and mobile screenshots**

Use Playwright to capture the final page at 1440×1000 and 390×844 with a representative panel open. Confirm portrait crops, centered labels, panel contrast, row spacing, edge alignment, no horizontal scrolling, and the unchanged Alumni table. Also test one sparse card and the corrected Shengbo and Yesim links.

- [ ] **Step 5: Audit the final diff without absorbing unrelated work**

Run:

```bash
git status --short
git diff -- people.qmd _templates/people-card.ejs.md people-cards.css people-cards.js \
  people/pi/00_pelz_philipp.qmd people/postdocs/02_shengbo_you.qmd \
  people/phd/06_williams.qmd people/honorary/07_yan_mei.qmd \
  people/admins/yesim_tosun.qmd tests/test_people_page.py \
  tests/test_people_page_browser.py
```

Expected: only approved source, test, and metadata changes appear in this task's files. Review `docs/people.html` and copied assets separately because `docs/` already contained user-owned generated changes before this work.

- [ ] **Step 6: Commit only safely attributable generated output**

If the People page and copied assets can be staged without including unrelated pre-existing changes:

```bash
git add docs/people.html docs/people-cards.css docs/people-cards.js
git diff --cached
git commit -m "Build updated people page"
```

If `docs/people.html` still mixes unrelated pre-existing changes, leave the generated output unstaged and report that clearly; the verified source implementation remains complete, and the generated file can be committed with the owner's existing site-output update.
