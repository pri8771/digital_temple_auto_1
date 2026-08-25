# Blockers

## Social account creation — blocking social follower acquisition

**Needed:** Create and authorize an official Agent Beacon account on a permitted platform, beginning with Bluesky or a bot-permitted Mastodon instance.

**Why:** No connected capability can accept platform terms, complete CAPTCHA/email/phone verification, or place credentials into repository secrets.

**After completion:** The project can add the official adapter, run a read-only health check, publish a disclosed test post, and begin measuring verified social bot follows.

**Zero-cost fallback:** Continue GitHub-native directory acquisition, public Issues, repository discovery, and machine-readable feeds.

## Repository rename — optional, not blocking

**Needed:** Rename `digital_temple_auto_1` to `agent-beacon` in GitHub settings.

**Why:** The connected GitHub capability cannot create or rename a repository.

**After completion:** Reconcile repository URLs and badges; GitHub redirects should reduce link breakage, but verification is still required.

**Fallback:** Keep the temporary slug while presenting Agent Beacon as the project identity.

## GitHub Pages setting — optional, not blocking

**Needed:** Configure GitHub Pages for the repository if a friendly hosted HTML URL is desired.

**Why:** Static files are public in the repository now, but repository settings are not exposed by the connected capability.

**After completion:** Publish `docs/` as the public project site and verify HTTPS.

**Fallback:** Use public repository files and raw machine-readable endpoints as the initial hub.
