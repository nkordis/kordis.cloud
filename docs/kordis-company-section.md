# Design: minimal "Kordis" company section

Status: **proposal, not implemented, not published.** No code in this PR.
Every `TODO(Nikos)` is a fact only Nikos can supply. Nothing below is a confirmed fact unless it is marked as such.

## 1. Goal

"Kordis" will be the umbrella (sole proprietorship) under which future product brands sit. The section should give startup programs, reviewers and collaborators a one-page answer to "what is Kordis, who is behind it, how do I reach it", without weakening the personal portfolio.

Non-goals: no product pages, no named product brands, no new contact details, no forms, no new AWS services, no DNS or certificate changes.

## 2. Confirmed facts available today

- Founder: Nikos Kordis, based in Copenhagen.
- Background: MSc Software Development, BA Sociology.
- Focus: applied AI, LLM applications, RAG and evaluation for computational social science.
- Kordis is intended as a sole proprietorship.

Everything else (legal name, CVR number, founding date, services, status) is unknown and stays a TODO.

## 3. How the current site is wired (relevant constraints)

- React 17 + `react-router-dom` v5. `MainApp.jsx` loads `profile/routes.json` at runtime and lazy-loads `components/<component>` for each entry. `NavBar.jsx` builds the menu from `profile/navbar.json`. Page content lives in `public/profile/*.json`, wired through `constants/endpoints.js`.
- CloudFront returns `/index.html` for 403 and 404 (`template.yaml`), so deep links like `/kordis` already reach the SPA.
- Consequence: a route can exist without a nav entry (reachable only by URL), and a nav entry or route is added purely by editing JSON.

## 4. Placement

Options:

| Option | Description | Verdict |
|---|---|---|
| A. New route `/kordis` | Own page, own nav item "Kordis" | **Recommended** |
| B. Section on Home | Block below the headline | Rejected: mixes the personal pitch with the company pitch |
| C. Separate domain or subdomain | | Rejected: needs DNS and certificate changes (out of bounds) |

Recommendation: option A. A stable URL (`https://kordis.cloud/kordis`) can be put in program applications. Nav item sits after Projects and before Resume.

## 5. Content outline

Keep it to one screen of text plus a small facts block.

1. **Header:** "Kordis"; one-line descriptor. `TODO(Nikos): tagline, e.g. what Kordis builds, in your words.`
2. **What Kordis is:** two or three sentences: sole proprietorship, umbrella for product brands, applied AI for computational social science. `TODO(Nikos): confirm the wording and whether "umbrella for product brands" should be public yet.`
3. **Focus areas:** applied AI, LLM applications, RAG, evaluation (from confirmed facts). `TODO(Nikos): add or remove areas.`
4. **Products / brands:** placeholder line only, e.g. "Products will be announced here." Names are **not** listed until Nikos approves. `TODO(Nikos): decide when and which brands to link.`
5. **About the founder:** two sentences linking back to the portfolio (Copenhagen, MSc Software Development, BA Sociology). No new facts.
6. **Company facts block (all optional):**
   - Legal form: sole proprietorship (intended) `TODO(Nikos): confirm once registered.`
   - Registered name and CVR number `TODO(Nikos)`
   - Founded `TODO(Nikos)`
   - Location: Copenhagen, Denmark
7. **Contact:** reuse links that already exist on the site (existing social links and the contact route already used by the portfolio). `TODO(Nikos): decide whether a company email is wanted. This design adds none.`

Writing rules: no metrics, customers, funding, team size or dates unless supplied; no superlatives.

## 6. Files to change later (implementation PR)

All under `dev-portfolio/`; none touched by this PR.

| File | Change |
|---|---|
| `public/profile/kordis.json` | New content file holding all copy above, with TODO placeholders rendered as empty (hidden) rather than shown |
| `src/constants/endpoints.js` | Add `kordis: 'profile/kordis.json'` |
| `src/components/Kordis.jsx` | New component modelled on `About.jsx` (fetch JSON, render with existing `Header`, `react-markdown`, theme) |
| `public/profile/routes.json` | Add `{ "component": "Kordis", "path": "/kordis", "headerTitle": "Kordis" }` |
| `public/profile/navbar.json` | Add `{ "title": "Kordis", "href": "/kordis" }` |
| `src/components/Kordis.test.js` | Render test: empty/TODO fields are not shown |
| `public/index.html` (optional) | Meta description tweak, coordinated with the SEO PR |

No backend, `template.yaml`, CI or infrastructure changes.

## 7. Keeping it hidden until approved

The site deploys on merge to `main`, and anything in `public/profile/*.json` or the JS bundle is publicly fetchable. "Hidden in the UI" is therefore not the same as "private". Layers:

1. **Default: do not merge.** The implementation lives in a draft PR (or a branch) until Nikos approves; the content never reaches `main`. This is the only truly private option.
2. **If it must be merged early (unlisted):** merge the component and route but leave out the `navbar.json` entry, and keep placeholder copy minimal. The page is then reachable by URL only and is discoverable via `routes.json` and the bundle, so only non-sensitive text may be in it. Add `<meta name="robots" content="noindex">` for that route while unlisted.
3. **Publishing:** a final small PR adds the nav entry, removes `noindex`, adds the page to any sitemap, and fills the TODOs.

Recommendation: layer 1 until copy is approved, then go straight to layer 3.

## 8. Risks and open questions

- Wording around "company" before registration: avoid implying a registered entity until it exists. `TODO(Nikos)`
- Whether the nav should say "Kordis" or "Company". Proposed: "Kordis".
- The Footer visitor counter and the single-page `noindex` interplay with the SEO work in a separate PR; coordinate before implementing.
- Overlap: the implementation touches `routes.json`, `navbar.json`, `endpoints.js`, which other open PRs may also touch; implement only after those merge.

## 9. Acceptance criteria for the later implementation

- `/kordis` renders with theme (light/dark) and mobile layout.
- No TODO text, brand names, or unconfirmed facts are visible.
- No new dependencies or AWS changes.
- Existing routes and tests unaffected.
