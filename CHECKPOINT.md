# CHECKPOINT

Last updated: 2026-10-22

## Done
- P0 (this PR): removed template placeholder sections (About, Education, Experience: data files, components, routes, nav links), fixed manifest.json and HTML title/description, headline changed from "Cloud Developer" to "Applied AI Developer".

## External cost and security review (2026-10-22)
- Findings 1 and 7 (this PR): site bucket made private behind CloudFront OAC; CloudFront caches with a cache policy that follows upload Cache-Control headers (hashed `static/` assets 1 year, everything else 5 minutes). `RestrictPublicBuckets` stays false for this deploy only, so the old public policy keeps serving while CloudFront switches over; a one-line follow-up PR turns it on.
- Still open in their own PRs: findings 2, 3, 6, 9 (API and Lambda lockdown), 8 and 10 (frontend), 4 (GitHub OIDC). Finding 5 is handled in PR #7.

## Remaining queue
1. Lean portfolio: short bio, 3-4 selected projects, links (confirmed facts only; TODOs for anything unconfirmed). Also review the Skills page content and the Resume link.
2. Lambda runtime deprecation check (template.yaml currently pins python3.9 on two functions) and dependency review (frontend uses react-scripts 5, React 17).
3. SEO: meta/Open Graph link previews, no-JS fallback (currently only "You need to enable JavaScript").
4. Kordis company section: design only, not published.

## Notes
- After the OAC change the S3 origin is no longer publicly readable, so `curl https://kordis-cloud.s3.amazonaws.com/...` returns 403. Check live content through the site, or with `aws s3 cp s3://kordis-cloud/<key> -`.
- Deploys: the workflow now runs on every push to `main` (plus manual runs). It always syncs the site to S3 and runs `sam deploy` only when infra files change. The `dev` branch and the dev-to-main auto-merge are no longer used.
- dev-portfolio/README.md and LICENSE.md are upstream template files and still mention the template author; left untouched in P0.
- Local build needs `npm install --legacy-peer-deps` plus `ajv@8` (not saved) in this environment.
