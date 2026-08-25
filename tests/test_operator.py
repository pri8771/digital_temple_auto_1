import csv
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class OperatorTests(unittest.TestCase):
    def test_control_is_zero_cost_and_social_disabled(self):
        control = json.loads((ROOT / "config" / "control.json").read_text())
        self.assertEqual(control["max_cost_usd"], 0)
        self.assertFalse(control["social_posting_enabled"])
        self.assertFalse(control["allow_submitted_code_execution"])

    def test_required_record_headers_exist(self):
        required = {
            "BOT_DIRECTORY.csv": {"bot_id", "verification_tier", "evidence_url", "independent_control_verified"},
            "FOLLOWERS.csv": {"relationship_id", "entity_id", "platform", "verification_tier", "independent_control_verified"},
            "METRICS.csv": {"timestamp", "verified_bot_follow_relationships", "unique_verified_bot_entities", "cost_usd"},
        }
        for filename, expected in required.items():
            with (ROOT / filename).open(newline="", encoding="utf-8") as handle:
                headers = set(next(csv.reader(handle)))
            self.assertTrue(expected.issubset(headers), filename)

    def test_operator_runs_with_deterministic_time_in_isolation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = Path(temp_dir) / "repo"
            shutil.copytree(ROOT, sandbox, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            env = dict(os.environ)
            env.update({
                "AGENT_BEACON_NOW": "2026-08-25T15:00:00Z",
                "GITHUB_RUN_ID": "test-run",
                "GITHUB_EVENT_NAME": "test",
                "GITHUB_SHA": "test-sha",
            })
            result = subprocess.run(
                ["python3", str(sandbox / "operator" / "main.py")],
                cwd=sandbox,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            status = json.loads((sandbox / "docs" / "status.json").read_text())
            self.assertEqual(status["cost_usd"], 0)
            self.assertEqual(status["last_run_at"], "2026-08-25T15:00:00Z")
            self.assertIn("metrics", status)

if __name__ == "__main__":
    unittest.main()
