# CHECKPOINT

Last updated: 2026-10-20

## Done
- P0 (this PR): removed template placeholder sections (About, Education, Experience: data files, components, routes, nav links), fixed manifest.json and HTML title/description, headline changed from "Cloud Developer" to "Applied AI Developer".

## Remaining queue
1. Lean portfolio: short bio, 3-4 selected projects, links (confirmed facts only; TODOs for anything unconfirmed). Also review the Skills page content and the Resume link.
2. Lambda runtime deprecation check (template.yaml currently pins python3.9 on two functions) and dependency review (frontend uses react-scripts 5, React 17).
3. SEO: meta/Open Graph link previews, no-JS fallback (currently only "You need to enable JavaScript").
4. Kordis company section: design only, not published.

## Notes
- dev-portfolio/README.md and LICENSE.md are upstream template files and still mention the template author; left untouched in P0.
- Local build needs `npm install --legacy-peer-deps` plus `ajv@8` (not saved) in this environment.
