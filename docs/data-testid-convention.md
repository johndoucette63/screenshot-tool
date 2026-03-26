# `data-testid` Naming Convention

This document defines a consistent `data-testid` attribute convention for the Minneapolis Singles web application. These attributes serve as stable selectors for automated screenshot capture, end-to-end testing, and accessibility auditing.

## Why `data-testid`?

- **Decoupled from styling** — CSS classes change frequently; test IDs do not
- **Decoupled from content** — text-based selectors break with copy changes or i18n
- **Self-documenting** — reading a manifest or test immediately conveys intent
- **No runtime cost** — can be stripped in production builds if desired
- **Framework standard** — supported natively by Playwright, Testing Library, Cypress

## Naming Format

```
data-testid="{category}-{name}"
```

- Use **lowercase kebab-case** for all values
- Keep names **short but descriptive**
- Names should reflect **what the element is**, not how it looks

## Categories

### `nav-*` — Navigation elements

Top-level and sidebar navigation links.

```html
<a data-testid="nav-search">Search</a>
<a data-testid="nav-activity">Activity</a>
<a data-testid="nav-profile">My Profile</a>
<a data-testid="nav-logout">Logout</a>
<a data-testid="nav-logo">Minneapolis Singles</a>
<button data-testid="nav-mobile-menu">Menu</button>
<button data-testid="nav-back">Back</button>
```

### `action-*` — Buttons and interactive controls

Any clickable element that triggers a behavior (not navigation).

```html
<button data-testid="action-send-message">Send Message</button>
<button data-testid="action-save-member">Save</button>
<button data-testid="action-unsave-member">Unsave</button>
<button data-testid="action-filter-toggle">Filters</button>
<button data-testid="action-filter-apply">Apply Filters</button>
<button data-testid="action-filter-clear">Clear All</button>
<button data-testid="action-photo-next">Next Photo</button>
<button data-testid="action-photo-prev">Previous Photo</button>
<button data-testid="action-submit-login">Log In</button>
<button data-testid="action-load-more">Load More</button>
```

### `input-*` — Form fields and controls

Inputs, selects, textareas, and other form elements.

```html
<input data-testid="input-email" type="email" />
<input data-testid="input-password" type="password" />
<input data-testid="input-search" type="text" />
<select data-testid="input-age-min">...</select>
<select data-testid="input-age-max">...</select>
<select data-testid="input-distance">...</select>
<textarea data-testid="input-message-body">...</textarea>
<textarea data-testid="input-bio">...</textarea>
```

### `card-*` — Repeated content cards

Cards, list items, or tiles that represent a data entity.

```html
<button data-testid="card-member" data-member-id="...">
  <!-- member photo, name, age -->
</button>

<div data-testid="card-message" data-message-id="...">
  <!-- message preview -->
</div>

<div data-testid="card-activity" data-activity-id="...">
  <!-- activity item -->
</div>
```

For cards, also include a **data attribute with the entity ID** so selectors can target specific items when needed:

```css
[data-testid="card-member"][data-member-id="9200001"]
```

### `section-*` — Page sections and containers

Major content regions on a page.

```html
<div data-testid="section-featured-members">...</div>
<div data-testid="section-search-results">...</div>
<div data-testid="section-filter-panel">...</div>
<div data-testid="section-profile-header">...</div>
<div data-testid="section-profile-photos">...</div>
<div data-testid="section-profile-about">...</div>
<div data-testid="section-profile-details">...</div>
<div data-testid="section-message-thread">...</div>
```

### `modal-*` — Dialogs and overlays

```html
<div data-testid="modal-send-message">...</div>
<div data-testid="modal-confirm-action">...</div>
<div data-testid="modal-photo-viewer">...</div>
<button data-testid="modal-close">Close</button>
```

### `tab-*` — Tab controls

```html
<button data-testid="tab-photos">Photos</button>
<button data-testid="tab-about">About</button>
<button data-testid="tab-details">Details</button>
```

### `status-*` — State indicators

Elements that display status, counts, or feedback.

```html
<span data-testid="status-online">Online</span>
<span data-testid="status-member-count">24 members</span>
<div data-testid="status-empty-state">No results found</div>
<div data-testid="status-loading">Loading...</div>
<div data-testid="status-error">Something went wrong</div>
```

### `page-*` — Page-level wrapper (one per route)

A single wrapper on each page to confirm which view is rendered.

```html
<!-- /member/login -->
<div data-testid="page-member-login">...</div>

<!-- /member/search -->
<div data-testid="page-member-search">...</div>

<!-- /member/members/:id -->
<div data-testid="page-member-profile">...</div>

<!-- /member/activity -->
<div data-testid="page-member-activity">...</div>

<!-- /admin/login -->
<div data-testid="page-admin-login">...</div>

<!-- /admin/dashboard -->
<div data-testid="page-admin-dashboard">...</div>
```

## Rules

1. **Every interactive element gets a `data-testid`** — buttons, links, inputs, tabs
2. **Every repeated card gets a `data-testid` + entity ID attribute** — `data-member-id`, `data-message-id`, etc.
3. **Every page route gets a `page-*` wrapper** — confirms the correct view loaded
4. **Do not duplicate IDs on a page** — if multiple cards share `card-member`, that is fine (they are repeated), but singleton elements like `nav-search` must be unique
5. **Do not use `data-testid` for styling** — these are for testing and automation only
6. **Keep IDs stable across refactors** — renaming a component or changing layout should not change the `data-testid`

## Implementation Priority

### Phase 1 — Login and navigation (unblocks auth flows)
- `page-*` wrappers on all routes
- `input-email`, `input-password`, `action-submit-login`
- `nav-*` for all header/sidebar links

### Phase 2 — Search and member cards (unblocks search screenshots)
- `card-member` with `data-member-id`
- `section-featured-members`, `section-search-results`
- `action-filter-toggle`, `input-*` for filter controls

### Phase 3 — Profile and interactions (unblocks workflow screenshots)
- `section-profile-*` for profile sections
- `action-send-message`, `action-save-member`
- `modal-*` for dialogs
- `tab-*` if profile has tabs

### Phase 4 — Activity and messaging
- `card-activity`, `card-message`
- `section-message-thread`
- `input-message-body`

## Example: Screenshot manifest using `data-testid`

Once implemented, the captool manifests become clear and stable:

```yaml
pages:
  - id: member-login
    path: "/member/login"
    auth: none
    before_capture:
      - wait_for: "[data-testid='page-member-login']"

  - id: member-search
    path: "/member/search"
    auth: member
    before_capture:
      - wait_for: "[data-testid='section-search-results']"

  - id: member-profile
    path: "/member/search"
    auth: member
    before_capture:
      - wait_for: "[data-testid='card-member']"
      - click_and_navigate: "[data-testid='card-member']"
      - wait_for: "[data-testid='page-member-profile']"

  - id: member-search-filtered
    path: "/member/search"
    auth: member
    before_capture:
      - click: "[data-testid='action-filter-toggle']"
      - wait_for: "[data-testid='section-filter-panel']"
```
