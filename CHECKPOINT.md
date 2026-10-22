# CHECKPOINT

Last updated: 2026-10-22

## Done
- P0 (PR #4, merged): removed template placeholder sections, fixed manifest.json and HTML title/description.
- Portfolio content (PR #7): short bio on Home, trimmed Skills list, Projects page reviewed (dead links and a broken image fixed), Resume and LinkedIn links removed. Unfinished entries are not published.

## Merged since
- PR #5 (Lambda runtime), PR #9 (deploy on main), PR #6 (Kordis company section design doc, docs/ only, not linked from the site).

## Open items
- Add applied AI projects and skills once they exist.
- Add a Resume link back only with a public version of the CV.

## External cost and security review (2026-10-22)
- Findings 1 and 7 (PR #10, #11, merged): site bucket made private behind CloudFront OAC; CloudFront caches with a cache policy that follows upload Cache-Control headers (hashed `static/` assets 1 year, everything else 5 minutes). All four S3 public-access blocks are on (`RestrictPublicBuckets` was turned on in a follow-up PR after the OAC deploy, to avoid an outage).
- Findings 2, 3, 6, 9 (PR #12, merged; needed an inline `kordis-cloud-log-groups` policy on sam-user): counter API throttled (5 req/s, burst 10, stage-wide), each counter Lambda capped by reserved concurrency (`ReservedConcurrency` parameter, default 2; 0 turns it off), PUT counts a visitor (hashed IP + User-Agent) at most once per UTC day via a DynamoDB marker with TTL, CORS answers only https://kordis.cloud and https://www.kordis.cloud (preflight handled by the PUT Lambda), GET has only `GetItem` on the `visits` key and PUT only `GetItem` on `visits` plus `PutItem`/`UpdateItem` on the table (they run inside a transaction, where per-key conditions are not documented), Lambdas log to new log groups with 14-day retention and no longer log IPs or User-Agents, and a CI job deletes SAM packages the stack no longer references (older than 30 days) and adds a lifecycle rule expiring old versions after 7 days. The workflow now runs one deploy at a time (`concurrency: deploy-main`).
- Findings 8 and 10 (PR #13, merged): the footer counter uses the PUT response (falls back to GET only if PUT fails), and `npm run build` now fails (postbuild check) if any `build/profile/*.json` contains "TODO", because those files are published as-is even when React hides an entry. Neither main nor PR #7 has TODO entries now; the check keeps it that way. Switching the REST API to an HTTP API (optional part of finding 8) was not done.
- Finding 4 (PR #14, merged; AWS roles created by scripts/oidc-setup.sh; the exec role also needed CreateChangeSet on the SAM transform, added in a follow-up PR): workflow moves to GitHub OIDC. Unit, integration and e2e tests get no AWS credentials; `deploy-site` and the infra jobs assume separate roles; `sam deploy` hands CloudFormation its own execution role. AWS-side setup is in docs/github-oidc-plan.md and must be done by Nikos before that PR merges.
- Finding 5 (bio wording) is handled in PR #7.

## Remaining queue
1. SEO: meta/Open Graph link previews, no-JS fallback (currently only "You need to enable JavaScript"). Next up.
2. Dependency review (react-scripts 5, React 17) after PR #5.
3. Kordis company section: design doc merged (docs only); publishing is a separate decision.

## Notes
- After the OAC change the S3 origin is no longer publicly readable, so `curl https://kordis-cloud.s3.amazonaws.com/...` returns 403. Check live content through the site, or with `aws s3 cp s3://kordis-cloud/<key> -`.
- The old auto-created log groups `/aws/lambda/kordis-cloud-VisitorCount*` keep their history with no retention. Nikos can delete them or run `aws logs put-retention-policy --log-group-name <name> --retention-in-days 14` once.
- If the deploy fails on reserved concurrency (accounts with a 10-execution limit cannot reserve any), set `ReservedConcurrency=0` in samconfig.toml `parameter_overrides`.
- Deploys: the workflow now runs on every push to `main` (plus manual runs). It always syncs the site to S3 and runs `sam deploy` only when infra files change. The `dev` branch and the dev-to-main auto-merge are no longer used.
- dev-portfolio/README.md and LICENSE.md are upstream template files and still mention the template author; left untouched in P0.
- Local build needs `npm install --legacy-peer-deps` plus `ajv@8` (not saved) in this environment.
