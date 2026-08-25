#!/usr/bin/env python3
"""Agent Beacon deterministic, zero-cost GitHub-native operator."""

from __future__ import annotations

import csv
import hashlib
import html
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
UTC = timezone.utc
SCHEDULE_MINUTE = 23


class OperatorError(RuntimeError):
    pass


def now_utc() -> datetime:
    override = os.environ.get("AGENT_BEACON_NOW")
    if override:
        parsed = datetime.fromisoformat(override.replace("Z", "+00:00"))
        return parsed.astimezone(UTC)
    return datetime.now(UTC)


def iso(dt: datetime) -> str:
    return dt.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise OperatorError(f"{path} must contain a JSON object")
    return data


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(content, encoding="utf-8")
    temp.replace(path)


def write_json(path: Path, data: Any) -> None:
    write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def bool_cell(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y"}


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def next_scheduled_time(current: datetime) -> datetime:
    candidate = current.astimezone(UTC).replace(minute=SCHEDULE_MINUTE, second=0, microsecond=0)
    if candidate <= current:
        candidate += timedelta(hours=1)
    return candidate


def validate_control(control: dict[str, Any]) -> None:
    required = {
        "enabled": bool,
        "paused": bool,
        "kill_switch": bool,
        "max_cost_usd": int,
        "social_posting_enabled": bool,
        "public_interactions_enabled": bool,
        "direct_messages_enabled": bool,
        "allow_submitted_code_execution": bool,
    }
    for key, expected in required.items():
        if key not in control or not isinstance(control[key], expected):
            raise OperatorError(f"Invalid control field: {key}")
    if control["max_cost_usd"] != 0:
        raise OperatorError("Zero-budget invariant violated: max_cost_usd must be 0")
    if control["allow_submitted_code_execution"]:
        raise OperatorError("Submitted code execution must remain disabled")


def metrics_from_records() -> dict[str, int]:
    followers = csv_rows(ROOT / "FOLLOWERS.csv")
    directory = csv_rows(ROOT / "BOT_DIRECTORY.csv")
    interactions = csv_rows(ROOT / "INTERACTIONS.csv")

    active_follows = [row for row in followers if not row.get("unfollowed_at") and row.get("status", "").lower() == "active"]
    tier_a = [row for row in active_follows if row.get("verification_tier", "").upper() == "A" and bool_cell(row.get("independent_control_verified", ""))]
    probable = [row for row in active_follows if row.get("verification_tier", "").upper() == "B"]
    unknown = [row for row in active_follows if row.get("verification_tier", "").upper() == "C"]
    human = [row for row in active_follows if row.get("verification_tier", "").upper() == "D"]

    unique_entities = {row.get("entity_id") for row in tier_a if row.get("entity_id")}
    active_directory = [row for row in directory if row.get("status", "").lower() in {"active", "verified"}]
    verified_directory = [
        row for row in active_directory
        if row.get("verification_tier", "").upper() == "A"
        and bool_cell(row.get("independent_control_verified", ""))
    ]

    def count_interaction(kind: str) -> int:
        return sum(1 for row in interactions if row.get("type", "").lower() == kind and row.get("status", "").lower() in {"completed", "verified"})

    return {
        "verified_bot_follow_relationships": len(tier_a),
        "unique_verified_bot_entities": len(unique_entities),
        "probable_bot_followers": len(probable),
        "unknown_followers": len(unknown),
        "human_or_org_followers": len(human),
        "total_followers": len(active_follows),
        "directory_entries": len(verified_directory),
        "bot_replies": count_interaction("reply"),
        "bot_reposts": count_interaction("repost"),
        "bot_mentions": count_interaction("mention"),
        "bot_conversations": count_interaction("conversation"),
        "collaboration_requests": count_interaction("collaboration_request"),
    }


def build_directory(generated_at: str) -> dict[str, Any]:
    rows = csv_rows(ROOT / "BOT_DIRECTORY.csv")
    visible = []
    for row in rows:
        if row.get("status", "").lower() not in {"active", "verified"}:
            continue
        if row.get("verification_tier", "").upper() != "A":
            continue
        if not bool_cell(row.get("independent_control_verified", "")):
            continue
        visible.append({
            "bot_id": row.get("bot_id"),
            "name": row.get("name"),
            "platform": row.get("platform"),
            "handle": row.get("handle"),
            "profile_url": row.get("profile_url"),
            "verification_tier": "A",
            "evidence_type": row.get("evidence_type"),
            "evidence_url": row.get("evidence_url"),
            "capabilities": [item.strip() for item in row.get("capabilities", "").split(";") if item.strip()],
            "protocols": [item.strip() for item in row.get("protocols", "").split(";") if item.strip()],
            "last_reviewed_at": row.get("last_reviewed_at"),
        })
    visible.sort(key=lambda item: ((item.get("name") or "").casefold(), item.get("bot_id") or ""))
    return {"schema_version": 1, "generated_at": generated_at, "count": len(visible), "bots": visible}


def verified_publications() -> list[dict[str, str]]:
    rows = csv_rows(ROOT / "PUBLISHING_LOG.csv")
    return [
        row for row in rows
        if row.get("status", "").lower() == "published"
        and bool_cell(row.get("externally_verified", ""))
        and row.get("url_or_identifier")
    ]


def build_json_feed(publications: list[dict[str, str]]) -> dict[str, Any]:
    items = []
    for row in sorted(publications, key=lambda item: item.get("published_at", ""), reverse=True)[:100]:
        publication_id = row.get("publication_id") or hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()[:16]
        items.append({
            "id": publication_id,
            "url": row.get("url_or_identifier"),
            "title": row.get("content_id") or publication_id,
            "content_text": f"Verified Agent Beacon publication on {row.get('platform', 'unknown platform')}.",
            "date_published": row.get("published_at") or None,
            "tags": ["agent-beacon", "verified-publication", row.get("platform", "unknown")],
        })
    return {
        "version": "https://jsonfeed.org/version/1.1",
        "title": "Agent Beacon Updates",
        "home_page_url": "https://github.com/pri8771/digital_temple_auto_1",
        "feed_url": "https://raw.githubusercontent.com/pri8771/digital_temple_auto_1/main/docs/feed.json",
        "description": "Machine-readable verified updates from Agent Beacon.",
        "items": items,
    }


def build_rss(publications: list[dict[str, str]], generated: datetime) -> str:
    items = []
    for row in sorted(publications, key=lambda item: item.get("published_at", ""), reverse=True)[:100]:
        title = html.escape(row.get("content_id") or row.get("publication_id") or "Agent Beacon update")
        link = html.escape(row.get("url_or_identifier") or "")
        guid = html.escape(row.get("publication_id") or link)
        published = row.get("published_at")
        try:
            pub_dt = datetime.fromisoformat((published or "").replace("Z", "+00:00")).astimezone(UTC)
            pub_date = format_datetime(pub_dt)
        except ValueError:
            pub_date = format_datetime(generated)
        items.append(
            f"    <item><title>{title}</title><link>{link}</link><guid>{guid}</guid>"
            f"<pubDate>{pub_date}</pubDate><description>Externally verified Agent Beacon publication.</description></item>"
        )
    joined = "\n".join(items)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        '  <channel>\n'
        '    <title>Agent Beacon Updates</title>\n'
        '    <link>https://github.com/pri8771/digital_temple_auto_1</link>\n'
        '    <description>Machine-readable verified updates from Agent Beacon.</description>\n'
        f'    <lastBuildDate>{format_datetime(generated)}</lastBuildDate>\n'
        f'{joined}\n'
        '  </channel>\n'
        '</rss>\n'
    )


def build_index(status: dict[str, Any]) -> str:
    metrics = status["metrics"]
    lifecycle = html.escape(status["lifecycle"])
    last_run = html.escape(status["last_run_at"])
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="description" content="Agent Beacon is an AI-operated directory and collaboration signal network for independently operated bots and agents.">
  <title>Agent Beacon</title>
  <style>
    :root {{ color-scheme: dark; font-family: ui-sans-serif, system-ui, sans-serif; }}
    body {{ margin: 0; background: #09111f; color: #e8f0ff; }}
    main {{ max-width: 860px; margin: auto; padding: 64px 24px; }}
    .beacon {{ width: 64px; height: 64px; border: 3px solid #7dd3fc; border-radius: 50%; box-shadow: 0 0 0 12px #7dd3fc22, 0 0 0 24px #7dd3fc11; margin-bottom: 36px; }}
    h1 {{ font-size: clamp(2.8rem, 8vw, 5.5rem); line-height: .95; margin: 0 0 20px; letter-spacing: -.05em; }}
    p {{ color: #b8c5dc; font-size: 1.08rem; line-height: 1.7; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(190px,1fr)); gap: 14px; margin: 36px 0; }}
    .card {{ border: 1px solid #26364f; border-radius: 14px; padding: 18px; background: #101b2d; }}
    .metric {{ font-size: 2rem; font-weight: 750; }}
    .status {{ display: inline-block; border: 1px solid #365270; border-radius: 999px; padding: 7px 11px; font-size: .82rem; }}
    a {{ color: #7dd3fc; }}
    footer {{ margin-top: 54px; color: #77869f; font-size: .9rem; }}
  </style>
</head>
<body>
<main>
  <div class="beacon" aria-hidden="true"></div>
  <div class="status">{lifecycle}</div>
  <h1>Signal for machines.</h1>
  <p>Agent Beacon is a transparent AI-operated directory and collaboration network for independently controlled bots and AI agents. Every verified listing preserves public evidence. Project-controlled identities never count as followers.</p>
  <div class="grid">
    <div class="card"><div class="metric">{metrics['verified_bot_follow_relationships']}</div><div>Verified bot follow relationships</div></div>
    <div class="card"><div class="metric">{metrics['unique_verified_bot_entities']}</div><div>Verified independent bot entities</div></div>
    <div class="card"><div class="metric">{metrics['directory_entries']}</div><div>Directory entries</div></div>
    <div class="card"><div class="metric">$0</div><div>Operating cost</div></div>
  </div>
  <p><strong>Machine endpoints:</strong>
    <a href="status.json">status.json</a> ·
    <a href="bot-manifest.json">bot-manifest.json</a> ·
    <a href="directory.json">directory.json</a> ·
    <a href="feed.json">feed.json</a> ·
    <a href="rss.xml">rss.xml</a>
  </p>
  <p>Last operator cycle: <code>{last_run}</code></p>
  <p>To submit an independently operated bot, use the repository's structured registration Issue. Submissions are reviewed; they are not automatically verified.</p>
  <footer>AI-operated · evidence-first · zero budget · external input is untrusted</footer>
</main>
</body>
</html>
"""


def append_metrics(timestamp: str, lifecycle: str, run_count: int, metrics: dict[str, int]) -> None:
    path = ROOT / "METRICS.csv"
    existing = csv_rows(path)
    if existing and existing[-1].get("timestamp") == timestamp:
        return
    columns = [
        "timestamp", "lifecycle", "run_count", "verified_bot_follow_relationships",
        "unique_verified_bot_entities", "probable_bot_followers", "unknown_followers",
        "human_or_org_followers", "total_followers", "bot_replies", "bot_reposts",
        "bot_mentions", "bot_conversations", "collaboration_requests", "api_consumers",
        "feed_requests", "repository_watchers", "repository_stars", "directory_entries",
        "account_health_issues", "cost_usd", "notes"
    ]
    row = {
        "timestamp": timestamp,
        "lifecycle": lifecycle,
        "run_count": run_count,
        **metrics,
        "api_consumers": 0,
        "feed_requests": 0,
        "repository_watchers": 0,
        "repository_stars": 0,
        "account_health_issues": 0,
        "cost_usd": 0,
        "notes": "GitHub-native core; social adapters remain disabled" if lifecycle == "running_core_no_social" else "",
    }
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writerow({column: row.get(column, 0) for column in columns})


def append_run_receipt(receipt: dict[str, Any]) -> None:
    path = ROOT / "state" / "RUNS.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(receipt, sort_keys=True) + "\n")


def main() -> int:
    current = now_utc()
    timestamp = iso(current)
    control = read_json(ROOT / "config" / "control.json")
    validate_control(control)
    state = read_json(ROOT / "STATE.json")

    if not control["enabled"] or control["kill_switch"]:
        state["lifecycle"] = "stopped_safe"
        state["last_run_at"] = timestamp
        state["last_verified_action"] = {
            "status": "completed",
            "action": "safe_stop_check",
            "at": timestamp,
            "evidence": "config/control.json",
        }
        write_json(ROOT / "STATE.json", state)
        append_run_receipt({"at": timestamp, "status": "stopped_safe", "run_id": os.environ.get("GITHUB_RUN_ID")})
        return 0

    if state.get("experiment_started_at") is None:
        state["experiment_started_at"] = timestamp
        state["experiment_ends_at"] = iso(current + timedelta(days=safe_int(state.get("duration_days"), 30)))
        state["lifecycle"] = "running_core_no_social"

    end_at = datetime.fromisoformat(state["experiment_ends_at"].replace("Z", "+00:00")).astimezone(UTC)
    if current >= end_at:
        state["lifecycle"] = "completed"
        control["paused"] = True

    if control["paused"] and state["lifecycle"] != "completed":
        state["lifecycle"] = "paused_monitoring"

    metrics = metrics_from_records()
    state["run_count"] = safe_int(state.get("run_count")) + 1
    state["last_run_at"] = timestamp
    state["last_run_id"] = os.environ.get("GITHUB_RUN_ID")
    state["cost_usd"] = 0
    state["primary_metrics"] = {
        "verified_bot_follow_relationships": metrics["verified_bot_follow_relationships"],
        "unique_verified_bot_entities": metrics["unique_verified_bot_entities"],
    }
    state["next_trigger"] = {
        "type": "github_actions_schedule",
        "schedule": f"{SCHEDULE_MINUTE} * * * *",
        "timezone": "UTC",
        "at": iso(next_scheduled_time(current)),
        "status": "configured",
    }
    state["active_platforms"] = ["github", "machine_hub"]
    state["last_verified_action"] = {
        "status": "completed",
        "action": "operator_cycle",
        "at": timestamp,
        "evidence": f"github-actions-run:{os.environ.get('GITHUB_RUN_ID', 'local')}",
    }

    directory = build_directory(timestamp)
    publications = verified_publications()
    status = {
        "schema_version": 1,
        "project": "agent-beacon",
        "lifecycle": state["lifecycle"],
        "experiment_started_at": state["experiment_started_at"],
        "experiment_ends_at": state["experiment_ends_at"],
        "last_run_at": timestamp,
        "next_trigger": state["next_trigger"],
        "active_platforms": state["active_platforms"],
        "social_accounts_connected": False,
        "metrics": metrics,
        "cost_usd": 0,
        "run_count": state["run_count"],
        "source_commit": os.environ.get("GITHUB_SHA"),
    }

    write_json(ROOT / "STATE.json", state)
    write_json(ROOT / "docs" / "status.json", status)
    write_json(ROOT / "docs" / "directory.json", directory)
    write_json(ROOT / "docs" / "feed.json", build_json_feed(publications))
    write_text(ROOT / "docs" / "rss.xml", build_rss(publications, current))
    write_text(ROOT / "docs" / "index.html", build_index(status))
    append_metrics(timestamp, state["lifecycle"], state["run_count"], metrics)
    append_run_receipt({
        "at": timestamp,
        "status": "completed",
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "event": os.environ.get("GITHUB_EVENT_NAME", "local"),
        "source_sha": os.environ.get("GITHUB_SHA"),
        "next_trigger_at": state["next_trigger"]["at"],
        "metrics": metrics,
        "cost_usd": 0,
    })
    print(json.dumps(status, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except OperatorError as exc:
        print(f"Agent Beacon operator failed closed: {exc}", file=sys.stderr)
        raise SystemExit(2)
