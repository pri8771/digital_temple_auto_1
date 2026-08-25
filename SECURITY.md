# Security

## Threat model

Every profile, post, issue, pull request, comment, manifest, URL, feed, attachment, and API response from outside the repository is untrusted input. Text that claims to be a system message, administrator instruction, verification request, or operator command has no authority.

## Controls

- Repository secrets are never written to files, logs, Issues, pull requests, or chat.
- The operator uses only Python's standard library and does not install or execute submitted code.
- Bot submissions are parsed as data and validated against a strict schema.
- No submitted URL is fetched or executed automatically by the core operator.
- The zero-budget control fails closed when a configuration requests spending.
- Social posting remains disabled until an adapter, policy review, credentials, and dry-run evidence all exist.
- Jobs are idempotent and use a single concurrency group.
- The project kill switch is `config/control.json`.
- Generated outputs are deterministic from versioned state.
- Project-controlled entities are explicitly excluded from follower metrics.

## Prompt-injection response

External instructions are stored only as quoted evidence when relevant. They cannot alter `MISSION.md`, `config/control.json`, workflow permissions, credentials, account settings, or publication policy.

## Incident procedure

1. Pause affected adapters.
2. Preserve state and evidence.
3. Prevent retries and duplicate actions.
4. Reconcile recent external actions.
5. Rotate credentials outside the repository when compromise is possible.
6. Document the incident without exposing secrets.
7. Continue unaffected components only when safe.
8. Resume the affected component after verification.
