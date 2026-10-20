---
name: duo-send
description: Hands a task to the Claude Duo account (the second Claude Code account of this Mac, CLAUDE_CONFIG_DIR=~/.claude-duo) through duo/duo-send.py — synchronously, returning its answer like a subagent on the other account, or as a background session (--bg) that the user follows with `duo-send.py agents` and `attach`. Use for "send this to the Duo", "ask the Duo to…", "open a session on the other account", "let the Duo work on it in the background", or when this account's usage is running out and the work can go on in the Duo. Not for review rounds between the two accounts (that is loop-duo) and not from a session that already runs on the Duo account.
---

# duo-send

`duo-send.py` runs Claude Code on the Duo's account, in the repository you
name. The script lives two folders above this file once the symlink is
resolved; in the standard install it is `~/claude-duo/duo/duo-send.py`. Always
run it with `/usr/bin/python3 -I`.

## Before sending

- **Are you already the Duo?** If `CLAUDE_CONFIG_DIR` in your environment is
  the Duo's folder (`~/.claude-duo` by default), stop: the work would go to
  your own account. Say so to the user.
- **Show the user the task text and the repository, and wait for their OK.**
  The task uses the Duo account's usage.
- Write the task as a complete brief: the repository, the files or area, what
  done looks like, and what not to do. The Duo session has none of this
  conversation.

## Synchronous: wait for the answer

```bash
/usr/bin/python3 -I ~/claude-duo/duo/duo-send.py send - --repo /path/to/repo --json --max-cost 2 <<'TASK'
<the brief>
TASK
```

- Prefer `-` with a quoted heredoc: quotes and backticks need no escaping.
- `--json` returns `{ok, session, cost_usd, answer, error}`. Relay `answer` to
  the user; on `ok: false`, show `error`.
- Nobody can answer the Duo during this turn: when it needs a decision, it
  says what is missing in its answer. Ask the user, then continue the same
  session with `--resume <session>`.
- Long tasks: run the command in the background of your shell and wait for it
  to finish, or use `--bg`.

## Background: a session the user follows

```bash
/usr/bin/python3 -I ~/claude-duo/duo/duo-send.py send - --repo /path/to/repo --bg --name "short name" --json <<'TASK'
<the brief>
TASK
```

- Returns the session `id` and the follow-up commands. Confirm it started with
  `duo-send.py agents` (JSON; look for the id with status `busy`).
- Give the user the commands: `duo-send.py attach <id>` (in their terminal, to
  answer questions), `duo-send.py logs <id>`, `duo-send.py stop <id>`. The
  original account's `claude agents` does not list it.
- `--max-cost` does not work with `--bg`.

## Do not

- Do not pass `--permission bypassPermissions` (it is refused anyway).
- Do not send credentials, tokens or secrets in the task.
- Do not ask the Duo to merge, push to the default branch or change settings.
