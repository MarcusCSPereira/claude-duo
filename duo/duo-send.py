#!/usr/bin/env python3
"""duo-send: the original Claude Code hands a task to the Duo's account.

"duo" is the CLAUDE_CONFIG_DIR of the Duo line in the installed config (default
~/.claude-duo), the same account loop-duo uses. Two ways to send:

- synchronous (default): `claude -p` on the Duo's account, in the repository;
  waits and prints the answer, like a subagent on the other account.
- --bg: `claude --bg` on the Duo's account; returns at once with the id of a
  background session that `duo-send.py agents` lists and `attach` opens.

The account, its environment and the `claude -p` turn come from loop-duo.py,
so both scripts isolate the Duo the same way. Nothing here touches the apps.

Run with /usr/bin/python3 -I. See docs/DUO_SEND.md.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def _load_loop_duo():
    """loop-duo.py has a hyphen in its name, so it is loaded from its path (also under -I)."""
    spec = importlib.util.spec_from_file_location("loop_duo", HERE / "loop-duo.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


loop = _load_loop_duo()
Refused = loop.Refused

# bypassPermissions is left out, as in loop-duo: nobody watches a sent task.
PERMISSION_MODES = loop.PERMISSION_MODES
NAME = re.compile(r"^[\w .:/-]{1,60}$")
BACKGROUND_ID = re.compile(r"backgrounded\s*\S*\s*([0-9A-Za-z][0-9A-Za-z-]{5,80})")
FOLLOW_UP = ("agents", "logs", "attach", "stop")

ROLE_SYNC = """\
You are running on the Claude Duo account, the second Claude Code account of this Mac. The original account
sent you this task with duo-send and is waiting for your final answer, which goes back to it as a tool result.
- Nobody can answer you during this turn: there is no AskUserQuestion here. When the task needs a decision only
  a person can make (access, credentials, spending, something outside the repository), stop and say exactly
  what is missing in your final answer instead of guessing.
- Do not merge, push to the default branch or change settings and permissions.
- End with a short report: what you did, files touched, how you checked it and what is left.
"""

ROLE_BG = """\
You are running on the Claude Duo account, the second Claude Code account of this Mac. The original account
started you as a background session with duo-send. The user follows this session with `claude agents` and can
attach to it to answer questions.
- Do not merge, push to the default branch or change settings and permissions.
- End with a short report: what you did, files touched, how you checked it and what is left.
"""


def duo():
    acct = loop.account("duo")
    if not acct["folder"].is_dir():
        raise Refused(f"the Duo account has no Code folder yet ({acct['folder']}); open Code in Claude Duo once")
    return acct


def repository(folder):
    path = Path(folder).expanduser() if folder else Path.cwd()
    if not path.is_dir():
        raise Refused(f"the folder {path} does not exist")
    return path.resolve()


def check_options(task, *, model, name, session, cost_max):
    if not task.strip():
        raise Refused("the task is empty")
    if model and not loop.MODEL.match(model):
        raise Refused(f"invalid model: {model!r}")
    if name and not NAME.match(name):
        raise Refused(f"invalid name: {name!r}")
    if session is not None and not loop.SESSION_ID.match(session):
        raise Refused(f"invalid session id: {session!r}")
    if cost_max is not None and cost_max <= 0:
        raise Refused("--max-cost must be above zero")


def follow_up(acct, command, target=None):
    """The command line that reaches the Duo's session list from the user's terminal."""
    prefix = f"CLAUDE_CONFIG_DIR={shlex.quote(str(acct['folder']))} claude {command}"
    return f"{prefix} {shlex.quote(target)}" if target else prefix


def send_sync(task, *, folder=None, model=None, permission="auto", cost_max=None, session=None, say=print):
    """One `claude -p` turn on the Duo's account; returns {ok, session, cost_usd, answer, error}."""
    check_options(task, model=model, name=None, session=session, cost_max=cost_max)
    acct, where = duo(), repository(folder)
    extra = ["--max-budget-usd", f"{cost_max:.2f}"] if cost_max is not None else []
    end = loop.converse(acct, session, task, folder=where, role_prompt=ROLE_SYNC, reviewer=False, model=model,
                        permission=permission, extra=extra,
                        on_tool=lambda tool, data: say(f"  · duo {tool}: {loop.tool_summary(tool, data)}"))
    return {"mode": "sync", "account": "duo", "repo": str(where), **end}


def send_background(task, *, folder=None, model=None, permission="auto", name=None, session=None):
    """Starts a `claude --bg` session on the Duo's account; returns its id and the follow-up commands."""
    check_options(task, model=model, name=name, session=session, cost_max=None)
    acct, where = duo(), repository(folder)
    argv = [loop.claude_bin(), "--bg", *(["--resume", session] if session else []),
            *(["--name", name] if name else []), *(["--model", model] if model else []),
            "--permission-mode", permission, "--append-system-prompt", ROLE_BG, task]
    started = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace",
                             stdin=subprocess.DEVNULL, env=loop.environment(acct), cwd=where, timeout=120)
    output = (started.stdout or "") + (started.stderr or "")
    found = BACKGROUND_ID.search(output)
    if started.returncode != 0 or not found:
        return {"mode": "bg", "account": "duo", "repo": str(where), "ok": False, "id": None,
                "error": output.strip()[-400:] or f"exited with code {started.returncode}"}
    agent_id = found.group(1)
    return {"mode": "bg", "account": "duo", "repo": str(where), "ok": True, "id": agent_id, "error": None,
            "commands": {verb: follow_up(acct, verb, None if verb == "agents" else agent_id) for verb in FOLLOW_UP}}


def run_follow_up(verb, target=None, *, all_sessions=False):
    """`claude agents|logs|stop|attach` on the Duo's account: the original's would list its own sessions."""
    acct = duo()
    argv = [loop.claude_bin(), verb]
    if verb == "agents":
        argv += ["--json", *(["--all"] if all_sessions else [])]  # the plain list needs a terminal
    else:
        if not target or not NAME.match(target):
            raise Refused(f"invalid session id or name: {target!r}")
        argv.append(target)
    if verb == "attach":
        os.execve(argv[0], argv, loop.environment(acct))  # interactive: hands the terminal over
    done = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          stdin=subprocess.DEVNULL, env=loop.environment(acct), timeout=60)
    sys.stdout.write(done.stdout)
    sys.stderr.write(done.stderr)
    return done.returncode


def main(argv=None):
    if os.getuid() == 0:
        print("duo-send: run as your own user, not as root", file=sys.stderr)
        return 1
    os.umask(0o077)
    parser = argparse.ArgumentParser(prog="duo-send", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    send = commands.add_parser("send", help="hands a task to the Duo's account")
    send.add_argument("task", help='the task; "-" reads it from standard input')
    send.add_argument("--repo", help="the folder the Duo works in (default: the current folder)")
    send.add_argument("--bg", action="store_true", help="starts a background session and returns its id")
    send.add_argument("--resume", metavar="SESSION", help="continues a Duo session instead of starting one")
    send.add_argument("--name", help="display name of the background session (--bg)")
    send.add_argument("--model")
    send.add_argument("--permission", choices=PERMISSION_MODES, default="auto")
    send.add_argument("--max-cost", type=float, help="spending ceiling in US$ (synchronous mode only)")
    send.add_argument("--json", action="store_true")
    agents = commands.add_parser("agents", help="lists the Duo's background sessions (JSON)")
    agents.add_argument("--all", action="store_true", help="also the finished ones")
    for verb, text in (("logs", "prints a Duo background session's recent output"),
                       ("stop", "stops a Duo background session"),
                       ("attach", "opens a Duo background session in this terminal")):
        commands.add_parser(verb, help=text).add_argument("session", help="the id (or part of the name)")
    args = parser.parse_args(argv)

    try:
        if args.command != "send":
            return run_follow_up(args.command, getattr(args, "session", None), all_sessions=getattr(args, "all", False))
        task = sys.stdin.read() if args.task == "-" else args.task
        if args.bg:
            if args.max_cost is not None:
                raise Refused("--max-cost works only in the synchronous mode: claude enforces it with -p alone")
            result = send_background(task, folder=args.repo, model=args.model, permission=args.permission,
                                     name=args.name, session=args.resume)
        else:
            if args.name:
                raise Refused("--name names a background session; use it with --bg")
            say = (lambda text: None) if args.json else (lambda text: print(text, file=sys.stderr))
            result = send_sync(task, folder=args.repo, model=args.model, permission=args.permission,
                               cost_max=args.max_cost, session=args.resume, say=say)
    except Refused as error:
        if getattr(args, "json", False):
            print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        else:
            print(f"duo-send: {error}", file=sys.stderr)
        return 1
    except subprocess.TimeoutExpired:
        print("duo-send: claude did not answer in time", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif not result["ok"]:
        print(f"duo-send: the Duo account did not answer: {result['error']}", file=sys.stderr)
    elif result["mode"] == "bg":
        print(f"started on the Duo account · {result['id']} · {result['repo']}")
        for verb in FOLLOW_UP:
            print(f"  {result['commands'][verb]}")
    else:
        print(result["answer"])
        print(f"\n[duo · session {result['session']} · US$ {result['cost_usd'] or 0:.2f} estimated]", file=sys.stderr)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
