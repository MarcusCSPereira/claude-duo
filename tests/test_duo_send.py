"""duo-send with a fake claude in a temporary HOME.

The fake claude answers like `claude -p --output-format stream-json`, like
`claude --bg` and like `claude agents|logs|stop`; FAKE_MODE picks a failure.
Nothing reaches a real account.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "duo/duo-send.py"

FAKE_CLAUDE = r'''
import json, os, sys

args = sys.argv[1:]
request = "" if "--bg" in args or args[:1] in (["agents"], ["logs"], ["stop"]) else sys.stdin.read()
leaked = sorted(k for k in os.environ if k.startswith(("CLAUDE", "ANTHROPIC_")) and k != "CLAUDE_CONFIG_DIR")
with open(os.environ["FAKE_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps({"args": args, "request": request, "cwd": os.getcwd(),
                          "folder": os.environ.get("CLAUDE_CONFIG_DIR"), "leaked": leaked}, ensure_ascii=False) + "\n")
mode = os.environ.get("FAKE_MODE", "ok")

if args[:1] == ["agents"]:
    print(json.dumps([{"id": "4a79120f", "status": "busy", "title": "duo task"}]))
elif args[:1] in (["logs"], ["stop"]):
    print(f"{args[0]} {args[1]}")
elif "--bg" in args:
    if mode == "fail":
        print("error: not logged in", file=sys.stderr)
        sys.exit(1)
    print("backgrounded · 4a79120f\n  claude agents             list sessions")
else:
    session = args[args.index("--resume") + 1] if "--resume" in args else "sess-duo-0001"
    ok = mode != "fail"
    text = "Done: read the README." if ok else "Exceeded USD budget"
    for event in [
        {"type": "system", "subtype": "init", "session_id": session},
        {"type": "assistant", "message": {"id": "m1", "content": [
            {"type": "tool_use", "id": "t1", "name": "Read", "input": {"file_path": "README.md"}},
            {"type": "text", "text": text}]}},
        {"type": "result", "subtype": "success" if ok else "error_max_budget_usd", "is_error": not ok,
         "result": text, "session_id": session, "total_cost_usd": 0.02},
    ]:
        print(json.dumps(event, ensure_ascii=False), flush=True)
'''


class DuoSendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="duo-send-")
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name).resolve()
        self.home, self.bin, self.log = root / "home", root / "bin", root / "fake.jsonl"
        for folder in (self.home / ".claude", self.home / ".claude-duo", self.bin):
            folder.mkdir(parents=True)
        (self.bin / "claude").write_text(f"#!{sys.executable}\n{FAKE_CLAUDE}")
        (self.bin / "claude").chmod(0o755)
        self.repo = self.home / "project"
        self.repo.mkdir()
        self.env = {"HOME": str(self.home), "PATH": f"{self.bin}:/usr/bin:/bin", "FAKE_LOG": str(self.log),
                    # What a Desktop session of the original leaves in the environment and must not leak:
                    "CLAUDECODE": "1", "CLAUDE_CODE_ACCOUNT_UUID": "leaked", "ANTHROPIC_API_KEY": "leaked",
                    "CLAUDE_CONFIG_DIR": str(self.home / ".claude")}

    def send(self, *args, stdin=None, **env):
        return subprocess.run([sys.executable, "-I", str(SCRIPT), *args], capture_output=True, text=True,
                              input=stdin, env={**self.env, **env}, cwd=self.home, timeout=60)

    def send_json(self, *args, **kwargs):
        process = self.send("send", *args, "--json", **kwargs)
        return process, json.loads(process.stdout)

    def calls(self):
        lines = self.log.read_text().splitlines() if self.log.exists() else []
        return [json.loads(line) for line in lines]

    def test_sync_runs_on_the_duo_account_in_the_repo_and_returns_the_answer(self):
        process, end = self.send_json("read the README", "--repo", str(self.repo))
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual((end["ok"], end["mode"], end["answer"], end["session"]),
                         (True, "sync", "Done: read the README.", "sess-duo-0001"))
        self.assertAlmostEqual(end["cost_usd"], 0.02)
        [call] = self.calls()
        self.assertEqual(call["folder"], str(self.home / ".claude-duo"))
        self.assertEqual(call["leaked"], [])
        self.assertEqual(call["cwd"], str(self.repo))
        self.assertEqual(call["request"], "read the README")
        self.assertEqual(call["args"][:1], ["-p"])
        self.assertEqual(call["args"][call["args"].index("--permission-mode") + 1], "auto")
        self.assertIn("Claude Duo account", call["args"][call["args"].index("--append-system-prompt") + 1])
        self.assertNotIn("--disallowedTools", call["args"])

    def test_sync_plain_output_is_the_answer_and_stdin_carries_the_task(self):
        process = self.send("send", "-", "--repo", str(self.repo), stdin="a task with `backticks` and \"quotes\"")
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(process.stdout.strip(), "Done: read the README.")
        self.assertIn("duo Read: README.md", process.stderr)
        self.assertEqual(self.calls()[0]["request"], "a task with `backticks` and \"quotes\"")

    def test_sync_cost_ceiling_model_and_resume_reach_claude(self):
        process, end = self.send_json("go on", "--repo", str(self.repo), "--max-cost", "1.5", "--model", "sonnet",
                                      "--resume", "sess-duo-0042")
        self.assertEqual(process.returncode, 0, process.stderr)
        args = self.calls()[0]["args"]
        self.assertEqual(args[args.index("--max-budget-usd") + 1], "1.50")
        self.assertEqual(args[args.index("--model") + 1], "sonnet")
        self.assertEqual(args[args.index("--resume") + 1], "sess-duo-0042")
        self.assertEqual(end["session"], "sess-duo-0042")

    def test_sync_failure_is_reported_with_a_nonzero_exit(self):
        process, end = self.send_json("spend a lot", "--repo", str(self.repo), FAKE_MODE="fail")
        self.assertEqual(process.returncode, 1)
        self.assertFalse(end["ok"])
        self.assertIn("budget", end["error"])

    def test_bg_starts_a_background_session_on_the_duo_account(self):
        process, end = self.send_json("refactor the parser", "--repo", str(self.repo), "--bg", "--name", "parser")
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual((end["ok"], end["mode"], end["id"]), (True, "bg", "4a79120f"))
        [call] = self.calls()
        self.assertEqual(call["folder"], str(self.home / ".claude-duo"))
        self.assertEqual(call["leaked"], [])
        self.assertEqual(call["cwd"], str(self.repo))
        self.assertEqual(call["args"][0], "--bg")
        self.assertEqual(call["args"][-1], "refactor the parser")
        self.assertEqual(call["args"][call["args"].index("--name") + 1], "parser")
        self.assertNotIn("-p", call["args"])
        # The follow-up commands point at the Duo's session list, not the original's.
        self.assertEqual(end["commands"]["attach"],
                         f"CLAUDE_CONFIG_DIR={self.home / '.claude-duo'} claude attach 4a79120f")

    def test_bg_failure_is_reported(self):
        process, end = self.send_json("task", "--repo", str(self.repo), "--bg", FAKE_MODE="fail")
        self.assertEqual(process.returncode, 1)
        self.assertEqual((end["ok"], end["id"]), (False, None))
        self.assertIn("not logged in", end["error"])

    def test_follow_up_commands_run_on_the_duo_account(self):
        listed = self.send("agents")
        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertEqual(json.loads(listed.stdout)[0]["id"], "4a79120f")
        self.assertEqual(self.send("logs", "4a79120f").stdout.strip(), "logs 4a79120f")
        calls = self.calls()
        self.assertEqual([c["args"] for c in calls], [["agents", "--json"], ["logs", "4a79120f"]])
        self.assertTrue(all(c["folder"] == str(self.home / ".claude-duo") and c["leaked"] == [] for c in calls))

    def test_refusals_never_reach_claude(self):
        missing = self.home / "nowhere"
        cases = [
            (("send", "task", "--repo", str(missing), "--json"), "does not exist"),
            (("send", "   ", "--repo", str(self.repo), "--json"), "task is empty"),
            (("send", "task", "--repo", str(self.repo), "--bg", "--max-cost", "2", "--json"), "synchronous mode"),
            (("send", "task", "--repo", str(self.repo), "--name", "x", "--json"), "with --bg"),
            (("send", "task", "--repo", str(self.repo), "--max-cost", "0", "--json"), "above zero"),
            (("send", "task", "--repo", str(self.repo), "--model", "bad model;rm", "--json"), "invalid model"),
            (("send", "task", "--repo", str(self.repo), "--resume", "../x", "--json"), "invalid session id"),
        ]
        for args, message in cases:
            with self.subTest(args=args):
                process = self.send(*args)
                self.assertEqual(process.returncode, 1)
                self.assertIn(message, json.loads(process.stdout)["error"])
        self.assertIn("invalid choice", self.send("send", "t", "--permission", "bypassPermissions").stderr)
        self.assertEqual(self.calls(), [])

    def test_refuses_when_the_duo_account_has_no_code_folder(self):
        (self.home / ".claude-duo").rmdir()
        process = self.send("send", "task", "--repo", str(self.repo))
        self.assertEqual(process.returncode, 1)
        self.assertIn("no Code folder yet", process.stderr)
        self.assertEqual(self.calls(), [])

    def test_the_duo_folder_comes_from_the_installed_config(self):
        custom = self.home / "code-duo"
        custom.mkdir()
        config = self.home / ".config/claude-instances/claude-duo.conf"
        config.parent.mkdir(parents=True)
        config.write_text("Duo | io.github.x.claude-duo | ~/Library/Application Support/Claude-Duo | 212 | "
                          "CLAUDE_CONFIG_DIR=~/code-duo\n")
        pointer = self.home / ".local/share/claude-duo/config-path"
        pointer.parent.mkdir(parents=True)
        pointer.write_text(str(config))
        process, end = self.send_json("task", "--repo", str(self.repo))
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(self.calls()[0]["folder"], str(custom))


if __name__ == "__main__":
    unittest.main()
