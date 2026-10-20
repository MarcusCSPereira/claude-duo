# Opening a visible session in the Duo app (investigation)

Status: investigation only, nothing implemented. Evidence from Claude Desktop
2.42304.0 (`/Applications/Claude.app/Contents/Resources/app.asar`, main
process bundle) and this repository's builder, on 2026-10-20.

`duo-send.py` (see [DUO_SEND.md](DUO_SEND.md)) runs Claude Code on the Duo's
account, but the session lives in the Duo's Code profile, not in the Duo
window. The question here: what would it take for the original Claude to open
a session that appears in the **Claude Duo** app?

## What the Desktop accepts

- **Deep links handled by the main process.** `app.on("open-url")` hands every
  URL to one handler. It accepts only a fixed list of protocols, hard-coded in
  the bundle: `claude:`, `claude-dev:`, `claude-nest:`, `claude-nest-dev:`,
  `claude-nest-prod:`. Anything else is dropped with
  `claudeURLHandler: invalid protocol`.
- **Code links that exist today** (the host is `code`):
  - `claude://code/new?folder=<path>&q=<prompt>`: opens a new Code session
    with the folder chosen and the prompt filled in (`prompt` is accepted in
    place of `q`; also `file`, `environment`, `runner_pool`). The Finder
    service "New Claude Code Session Here" uses exactly this link. It fills the
    composer; nothing in the handler sends the prompt.
  - `claude://code/continue?session=last|local_<id>` and
    `claude://code/needs-input`: open an existing Desktop session. They are
    ignored when the "entry points" setting is off.
  - `claude://resume?session=<uuid>`: **imports a CLI session** by id
    (`importCliSession`) and opens it. The id must be a UUID, which is what
    `claude -p` and `claude --bg` print as `session_id`.
- **Enterprise policy** `authentication.disableDeepLinks` drops every link
  except sign-in ones.
- **Handoff** (`NSUserActivity` `com.anthropic.claude.code.session`) is only
  swallowed (`preventDefault`), not handled; not a way in.

So yes: the Desktop accepts a deep link that opens a Code session, both a new
one (`code/new`) and an existing CLI session (`resume`).

## Why the Duo has no link of its own

- `claude://` belongs to the official app. The builder deletes
  `CFBundleURLTypes` (and `NSUserActivityTypes`) from the Duo's `Info.plist`
  (`bin/claude-build-worker.sh`), so LaunchServices never routes a link to the
  Duo, and copies do not fight over `claude://` and `msauth://`.
- A `claude-duo://` scheme would need two changes:
  1. `CFBundleURLTypes` back in the Duo's `Info.plist`, which means changing
     the builder **and** the integrity record. The record regenerates the
     expected Duo from the signed source and requires byte-for-byte equality
     ([APP_INTEGRITY.md](APP_INTEGRITY.md)), so the generator, the verifier
     and their tests change together.
  2. `claude-duo:` in the protocol list inside `app.asar`. That is a second
     patch of the JavaScript bundle, beyond the same-size `productName` patch
     the Duo relies on today, redone at every Desktop update. Without it, the
     Desktop drops the link as an invalid protocol.

## Paths and cost

| Path | What changes | Cost | Viable |
|---|---|---|---|
| **A. `open -a` the Duo with a `claude://` link** | nothing in the app; `duo-send.py --open` | small: one flag, a fake `open` in the tests | **yes, if one check passes** (below) |
| B. `claude-dev://` in the Duo's `Info.plist` | builder, integrity generator and verifier, tests | medium, plus the risk of `claude-dev:` leaving future builds (it exists for Anthropic's dev builds) | yes, as a fallback |
| C. `claude-duo://` | B plus a JavaScript patch in `app.asar` at every update | high, and it breaks the "only `productName` changes" guarantee | no |
| D. Desktop shows CLI background sessions by itself | — | none, but nothing in 2.42304.0 does it | no |

### A: `open -a` with the app named (recommended)

```bash
# new session in the Duo, folder chosen and prompt filled in:
open -a "$HOME/Applications/Claude Duo.app" "claude://code/new?folder=$(python3 -c 'import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))' ~/repo)&q=..."
# a session duo-send already ran, imported into the Duo window:
open -a "$HOME/Applications/Claude Duo.app" "claude://resume?session=<session uuid>"
```

`open -a <app> <url>` sends the URL to the app named, not to the scheme's
registered handler, so the official app is not involved and the Duo's
`Info.plist` stays as it is. The Duo's own Code profile is
`CLAUDE_CONFIG_DIR=~/.claude-duo`, the same one `duo-send.py` writes to, so
`resume` finds the session there.

**The one check still open:** that macOS delivers the URL (Apple Event
`GetURL`) to an app that does not declare the scheme. It was not tested live
here, because it opens a session in the Duo window someone is using. To check,
with the Duo open:

```bash
open -a "$HOME/Applications/Claude Duo.app" "claude://code/new?folder=$HOME&source=duo-send-test"
```

A new Code session in your home folder means path A works. If nothing happens,
look for `claudeURLHandler` in the Duo's main log; no line means the URL never
arrived, and path B is the fallback.

What A would add to `duo-send.py`, if the check passes: `--open` on `send`
(after a synchronous run, or after `--bg`, import the session with `resume`),
and `open` as its own subcommand for `code/new`. A link that carries the prompt
is visible in process listings; long briefs should go through `duo-send`
itself, with `resume` only for the id. A `--bg` session still running would
be imported as a copy; import it once it is idle.

### B: `claude-dev://` in the Duo's `Info.plist`

Only if A fails. The builder would write `CFBundleURLTypes` with `claude-dev`
instead of deleting the key, and the integrity generator and verifier would
expect it. The Desktop already accepts `claude-dev:` links, so no JavaScript
changes. Costs: the builder and integrity changes with their tests, and a
dependency on a scheme meant for Anthropic's internal builds.

## Recommendation

Do A: a few lines in `duo-send.py`, nothing in the app, the builder or the
integrity record. First run the one-line check above with the Duo open. Keep B
as the fallback, and do not register `claude-duo://`.
