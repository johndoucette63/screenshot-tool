# captool

Automated screenshot capture of web applications for design analysis. Reads a YAML manifest defining pages, viewports, and auth flows, then uses Playwright to capture every combination.

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
playwright install chromium
```

## Quick start

```bash
# Copy and fill in env vars
cp env.example .env

# Validate your manifest
capture validate manifests/example.yaml

# List defined pages
capture list manifests/example.yaml

# Capture all screenshots
capture run manifests/example.yaml

# Capture specific pages
capture run manifests/example.yaml --only admin-dashboard,member-search-default

# Capture only one viewport
capture run manifests/example.yaml --viewport desktop

# Compare two screenshot sets
capture diff ./screenshots/2026-03-25T14-30-00 ./screenshots/2026-03-26T10-00-00
```

## Manifest format

```yaml
base_url: "http://localhost:5173"
output_dir: "./screenshots"
timestamp_dirs: true  # creates ./screenshots/2026-03-26T14-30-00/

defaults:
  wait_until: "networkidle"  # Playwright load state
  wait_after: 500            # ms pause after load before capture
  format: "png"

viewports:
  desktop: { width: 1440, height: 900 }
  mobile:  { width: 390, height: 844, device_scale_factor: 2 }
  tablet:  { width: 768, height: 1024 }

auth_flows:
  admin:
    steps:
      - goto: "/admin/login"
      - fill: { selector: "input[type='email']", value: "${ADMIN_EMAIL}" }
      - fill: { selector: "input[type='password']", value: "${ADMIN_PASSWORD}" }
      - click: "button[type='submit']"
      - wait_for: "nav"

pages:
  - id: admin-dashboard
    path: "/admin/dashboard"
    auth: admin
    viewports: [desktop]
    full_page: false

  - id: public-landing
    path: "/"
    auth: none
    viewports: [desktop, mobile]
    full_page: true

  - id: search-filtered
    path: "/search"
    auth: admin
    viewports: [desktop]
    before_capture:
      - click: "button:has-text('Filters')"
      - wait_after: 300
    full_page: true
```

### Environment variables

Use `${VAR_NAME}` in manifests. Values are resolved from the environment or a `.env` file.

### Auth flows

Auth steps execute once per browser context, then the session is reused for all pages sharing that auth. Use `auth: none` (or omit) for public pages.

### Before-capture actions

Set up page state before the screenshot:

| Action | Example |
|---|---|
| `click` | `click: "button.submit"` |
| `fill` | `fill: { selector: "input.search", value: "query" }` |
| `scroll_to` | `scroll_to: "#section-3"` |
| `wait_for` | `wait_for: ".loaded"` |
| `wait_after` | `wait_after: 500` (ms) |
| `select_tab` | `select_tab: "Settings"` |

## Output

- Screenshots: `{output_dir}/{timestamp}/{page_id}-{viewport}.png`
- Gallery: `{output_dir}/{timestamp}/index.html` — grid of all captures
- Failed pages get an `-ERROR` suffix and the run continues

## Diff

Compares two screenshot directories by filename, reports pixel difference percentages, and generates a side-by-side HTML report.

```bash
capture diff ./screenshots/before ./screenshots/after
```

Images with >1% pixel change are flagged. Output goes to `{dir_b}/diff/`.
