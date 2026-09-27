# People Page Hover Cards Design

## Goal

Redesign the active-member sections of the ECLIPSE Lab People page using the visual structure and interaction pattern of the Colin Ophus Lab People page: a clean portrait grid with a compact information panel that appears on hover, keyboard focus, or tap. The result must retain the ECLIPSE site's dark visual identity and continue to link to each person's full profile.

## Scope

The redesign applies to the Principal Investigator, Postdocs, PhD Students, MSc Students, Research Assistants, Honorary Members, and Administrative Assistants sections. The existing section headings and jump links remain. The empty BSc section remains as a short empty-state message.

The Alumni section remains the existing sortable and filterable table. Alumni do not receive portrait cards or hover panels in this change.

## Visual Design

The selected direction is “Stanford structure, ECLIPSE colors.” Active members appear in a responsive grid with:

- square, full-color portraits with a subtle corner radius;
- the person's name centered directly below the portrait;
- the person's role centered below the name;
- restrained spacing and decoration so the portraits remain the dominant visual element; and
- ECLIPSE typography, dark backgrounds, blue and violet accents, and existing page-level background effects.

The grid uses four columns on wide screens, three on laptops, two on tablets, and one on phones. Sections with fewer members do not stretch cards beyond the standard card width.

## Information Panel

Each active-member card can reveal a floating information panel anchored below the name and role. The panel uses a high-contrast dark surface, a fine border, a soft shadow, and compact typography consistent with the rest of the site.

Panel content appears only when available and follows this order:

1. role and start date;
2. one compact content block containing research interests, or a short biography when research interests are unavailable;
3. available contact and professional profile links; and
4. an explicit “View profile” link to the existing full profile page.

Empty values produce no label, separator, or placeholder. Long text is capped to keep the panel compact; the full profile page remains the destination for detailed biographies, experience, publications, and education.

## Interaction

On pointer devices, hovering over a card opens its panel. Moving the pointer from the card into the panel keeps it open, and leaving the combined card-panel region closes it after a brief delay.

Keyboard focus reveals the panel. Enter or Space toggles it, Escape closes it, and visible focus styling identifies the active card. The trigger exposes expanded/collapsed state and its relationship to the panel to assistive technology.

On touch devices, the first tap opens the panel. Links within the open panel work normally, including “View profile.” Tapping outside closes the panel. Opening one card closes any other open card.

The panel positions itself within the viewport, changing horizontal alignment for cards near the left or right edge. It must not cause horizontal page scrolling. Reduced-motion preferences disable nonessential transitions.

## Content and Data

The individual Quarto profile files remain the source of truth. A custom Quarto listing template will render the active-member cards from profile front matter, preserving automatic discovery and the existing `sortby` order. Optional metadata is rendered conditionally.

Existing metadata fields continue to provide `title`, `subtitle`, `image`, `started`, `interests`, and `about.links`. A concise description may be added to front matter when suitable text already exists in the profile body. Missing descriptions, interests, and external links remain optional and are omitted from the card.

This change includes two confirmed profile-data corrections:

- add Shengbo You's ORCID link: `https://orcid.org/0009-0008-0739-9903`;
- replace the incorrect email on Yesim Tosun's profile with `yesim.tosun@fau.de` and expose it as a usable email link.

No other missing biographies, pronouns, publications, photos, or external links will be invented or requested as part of this change. Existing placeholder portraits remain for members without a supplied photo.

## Components and Boundaries

The implementation has three focused parts:

1. A reusable custom Quarto listing template renders semantic card and panel markup from each profile item's metadata. It owns content ordering and conditional omission of unavailable fields.
2. People-page styles own the grid, portrait treatment, panel appearance, responsive breakpoints, focus presentation, and reduced-motion behavior. They are scoped so other Quarto listings and cards remain unchanged.
3. A small people-page interaction script owns open/close state, keyboard and touch behavior, outside-click handling, single-open-panel behavior, and viewport-aware alignment. The page remains readable and all profile links remain usable if JavaScript fails; hover and focus presentation can still be provided by CSS where supported.

The existing Quarto table listing continues to render the Alumni section, including its sorting and filtering controls.

## Accessibility

Every portrait uses the person's name as alternative text. The card trigger is keyboard reachable and communicates whether its panel is expanded. Panels do not trap focus. Links have descriptive accessible names, and the design does not rely on color alone to communicate state.

Text and interactive controls must retain sufficient contrast against the dark background. Touch targets must be comfortably sized. Information available on hover must also be available through focus and tap.

## Failure and Edge Cases

- Missing optional metadata: omit the corresponding content without leaving gaps.
- Missing supplied portrait: use the profile's existing placeholder image.
- Long names or roles: wrap without changing portrait dimensions.
- Long panel content: constrain panel height and allow internal scrolling only when necessary.
- Viewport edges: align or shift the panel to keep it on screen.
- JavaScript unavailable: preserve the portrait, name, role, and direct profile navigation.
- Empty group: preserve the existing textual empty state rather than rendering an empty grid.

## Verification

Render the site with Quarto and confirm there are no template or metadata errors. Inspect the generated People page at wide desktop, laptop, tablet, and phone widths. Verify all active-member groups, ordering, portrait paths, role labels, optional content, external links, and profile destinations.

Exercise hover transitions, movement into the panel, outside-click closing, single-open-panel behavior, keyboard traversal, Enter/Space activation, Escape closing, and touch tap behavior. Check the first and last card in each row for viewport overflow and confirm the page never gains horizontal scrolling.

Confirm that profiles with sparse metadata render cleanly, Shengbo You's ORCID is correct, Yesim Tosun's corrected email link works, reduced-motion behavior is respected, and the Alumni table still sorts and filters as before.
