# CHECKPOINT

Last updated: 2026-10-22

## Done
- P0 (this PR): removed template placeholder sections (About, Education, Experience: data files, components, routes, nav links), fixed manifest.json and HTML title/description, headline changed from "Cloud Developer" to "Applied AI Developer".

## External cost and security review (2026-10-22)
- Findings 2, 3, 6, 9 (this PR): counter API throttled (5 req/s, burst 10, stage-wide), each counter Lambda capped by reserved concurrency (`ReservedConcurrency` parameter, default 2; 0 turns it off), PUT counts a visitor (hashed IP + User-Agent) at most once per UTC day via a DynamoDB marker with TTL, CORS answers only https://kordis.cloud and https://www.kordis.cloud (preflight handled by the PUT Lambda), GET has only `GetItem` on the `visits` key and PUT only `GetItem`/`UpdateItem` on `visits` plus `PutItem` on `visitor#*` keys, Lambdas log to new log groups with 14-day retention and no longer log IPs or User-Agents, and a CI job deletes SAM packages the stack no longer references (older than 30 days) and adds a lifecycle rule expiring old versions after 7 days.
- Still open in their own PRs: findings 1 and 7 (S3/CloudFront), 8 and 10 (frontend), 4 (GitHub OIDC). Finding 5 is handled in PR #7.

## Remaining queue
1. Lean portfolio: short bio, 3-4 selected projects, links (confirmed facts only; TODOs for anything unconfirmed). Also review the Skills page content and the Resume link.
2. Lambda runtime deprecation check (template.yaml currently pins python3.9 on two functions) and dependency review (frontend uses react-scripts 5, React 17).
3. SEO: meta/Open Graph link previews, no-JS fallback (currently only "You need to enable JavaScript").
4. Kordis company section: design only, not published.

## Notes
- The old auto-created log groups `/aws/lambda/kordis-cloud-VisitorCount*` keep their history with no retention. Nikos can delete them or run `aws logs put-retention-policy --log-group-name <name> --retention-in-days 14` once.
- If the deploy fails on reserved concurrency (accounts with a 10-execution limit cannot reserve any), set `ReservedConcurrency=0` in samconfig.toml `parameter_overrides`.
- Deploys: the workflow now runs on every push to `main` (plus manual runs). It always syncs the site to S3 and runs `sam deploy` only when infra files change. The `dev` branch and the dev-to-main auto-merge are no longer used.
- dev-portfolio/README.md and LICENSE.md are upstream template files and still mention the template author; left untouched in P0.
- Local build needs `npm install --legacy-peer-deps` plus `ajv@8` (not saved) in this environment.
