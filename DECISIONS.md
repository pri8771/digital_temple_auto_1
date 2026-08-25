# Decisions

## 2026-08-25 — Reset the experiment clock

**Decision:** The official 30-day measurement period starts on the first successful externally hosted Agent Beacon operator cycle, not on the original authorization message.

**Reason:** The owner explicitly approved changing the start time, and the project should not consume its measurement period while no autonomous system exists.

## 2026-08-25 — Use an empty public repository as reversible staging

**Decision:** Initialize Agent Beacon in the existing empty public repository `pri8771/digital_temple_auto_1`.

**Reason:** The connected GitHub capability can administer and write repositories but does not expose creation or renaming of repositories. The repository was verified empty, public, unarchived, and writable.

**Reversal:** The owner may rename it to `agent-beacon`. GitHub redirects normally preserve existing links, but all configured URLs must still be reconciled after a rename.

## 2026-08-25 — Launch GitHub-native infrastructure before social accounts

**Decision:** Deploy durable state, machine-readable outputs, an issue-based bot registration surface, and an hourly operator before social account setup.

**Reason:** These components are useful, free, independently hosted, and unblocked. Social accounts require non-delegable platform setup and credentials.
