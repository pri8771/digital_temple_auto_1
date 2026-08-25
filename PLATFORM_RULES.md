# Platform Rules Register

No platform is activated merely because it is listed here. Rules must be reviewed again immediately before credentials are connected or automation is enabled.

## GitHub

- Status: active infrastructure platform after workflow verification
- Allowed use: public repository, Issues, pull requests, static files, and GitHub Actions
- Automation method: repository-scoped GitHub Actions using the standard hosted runner and the repository `GITHUB_TOKEN`
- Restrictions: repository stars, watchers, forks, issue participants, and feed users are not social followers and are reported separately
- Outreach rule: no unsolicited repetitive issue creation in third-party repositories
- Cost control: standard hosted runners only; no larger runners, paid services, packages, or billable storage

## Bluesky

- Status: blocked pending account creation, current rule review, and authorization
- Planned method: official AT Protocol interfaces only
- No browser automation or credential handling has been authorized
- No follows, posts, replies, or metrics may be claimed before external verification

## Mastodon

- Status: blocked pending selection of an instance whose local rules permit disclosed bots
- Planned method: official instance API
- Instance-specific bot disclosure, posting, rate, and content rules are authoritative
- No account may be created on an instance without reviewing its current local rules
