# Runbook

## Operating cycle

The GitHub Actions workflow `.github/workflows/agent-beacon-operator.yml` runs on relevant code/configuration changes, manual dispatch, and hourly at minute 23 UTC.

Each cycle:

1. Checks out durable state.
2. Reads and validates `config/control.json`.
3. Fails closed if cost is nonzero or the kill switch is active.
4. Validates tests and record schemas.
5. Reconciles directory and follower metrics.
6. Starts the official clock if this is the first successful externally hosted cycle.
7. Rebuilds status, directory, JSON Feed, RSS, and the static hub.
8. Appends a timestamped metrics row and run receipt.
9. Commits only generated state files.
10. Leaves the next scheduled trigger active.

## Pause

Set `paused` to `true` in `config/control.json`. Monitoring and machine-output rebuilding continue, but adapters must not publish or initiate interactions.

## Stop

Set `enabled` to `false` or `kill_switch` to `true`. The operator records a safe stopped state and performs no external action.

## Recovery

After interruption, inspect the latest workflow run, `STATE.json`, `state/RUNS.jsonl`, generated outputs, and platform records. Reconcile external reality before posting or interacting.

## Social adapter activation gate

An adapter remains disabled until all are true:

- Current platform rules are recorded.
- An official project account exists.
- Required disclosure is present.
- Credentials are stored in repository secrets, not files.
- A read-only health check succeeds.
- A dry run produces no prohibited behavior.
- One externally verified test publication succeeds.
