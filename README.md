# Claude Duo

[![Security regression](https://github.com/guibrbs/claude-duo/actions/workflows/security-regression.yml/badge.svg)](https://github.com/guibrbs/claude-duo/actions/workflows/security-regression.yml)

**Two Claude Desktop accounts on one Mac, side by side.** Keep the official
**Claude** app signed in to one account and run **Claude Duo**, a managed copy,
signed in to another: personal and work, two organizations, or two plans. Each
app has its own account, its own Claude Code profile and its own Keychain item,
and both can be open at the same time.

> ⚠️ **Experimental and unofficial.** This is an independent project, not
> affiliated with or endorsed by Anthropic. Claude Duo is a copy of the official
> app that is **signed locally**, without Anthropic's signature. Some scenarios
> are still being validated (see [Limitations](#limitations)). Use it at your own
> risk and follow the terms of use of each account and your organization's rules.

## Why

Claude Desktop holds one account at a time. Switching means signing out and in,
losing your place in Chat, Cowork and Code. Simply duplicating the app is not
enough either: the copy reuses the original's encrypted storage and asks for
your login Keychain password, and claude.ai treats a renamed copy as a web
browser. Claude Duo handles those details and keeps the copy up to date.

## Quick start

Requirements: macOS 12 or later, the official Claude in `/Applications`, and the
Xcode Command Line Tools (`xcode-select --install`).

```bash
git clone https://github.com/guibrbs/claude-duo.git ~/claude-duo
```

```bash
~/claude-duo/duo/install-duo.sh
```

The installer:

1. checks the requirements;
2. installs the versioned toolset (content-verified);
3. writes the config to `~/.config/claude-instances/claude-duo.conf`;
4. adds the **Update Claude Duo** app to `~/Applications`;
5. adds an hourly check that offers to update the Duo after Claude updates
   (skip it with `--no-auto-check`);
6. builds the Duo. It **asks before quitting Claude**, because building needs
   both apps closed, and reopens Claude at the end.

Then open **~/Applications/Claude Duo** and sign in with your second account.

## Everyday use

- **Open:** `Claude Duo` from the Dock, Launchpad or Spotlight. The original is
  still your usual `Claude`.
- **Update:** when the official Claude updates, a prompt asks *"Update now?"*.
  You can also open **Update Claude Duo** at any time. Either way, both apps
  quit, the Duo is rebuilt and verified, and whatever was open reopens.
  Prompts and notifications follow your macOS language (English or Portuguese).
- **Connectors (Google Drive, Slack…):** connect them in a private browser
  window signed in to the Duo's account (claude.ai → Settings → Connectors),
  then press ⌘R in the Duo. Connector sign-in started inside the Duo does not
  come back to it, because `claude://` links belong to the official app.
- **Same instructions, memories and skills in Code (optional):** with the Duo
  closed, run the command below. It links the Duo's `CLAUDE.md`, skills, output
  styles, tools, plugins and per-project memories to the original's, and copies
  `settings.json` once. Sign-in, sessions and history stay separate. Install
  plugins from the original. Details in [docs/PROFILE_REUSE.md](docs/PROFILE_REUSE.md).

```bash
/usr/bin/python3 -I ~/claude-duo/scripts/share-code-profile.py --apply --backup-existing
```

## How it works

- The Duo is a copy of the official `Claude.app` in `~/Applications` with its
  own bundle identifier, its own Desktop profile
  (`~/Library/Application Support/Claude-Duo`) and its own Code profile
  (`CLAUDE_CONFIG_DIR=~/.claude-duo`).
- **Its own Keychain item:** Electron names its encryption key
  `<productName> Safe Storage`. The builder changes only `productName` inside
  `app.asar` to `Duo Claude`, without changing the file size, and reseals the
  archive hashes. The Duo therefore never asks for the original's
  `Claude Safe Storage`. The name is `Duo Claude` rather than `Claude Duo`
  because the user agent drops spaces (`DuoClaude/…`) and claude.ai only enables
  the desktop UI for a `claude/` token.
- **Checks:** the source must carry Anthropic's signature and pass Gatekeeper.
  The integrity record **regenerates the expected result from the source** and
  requires byte-for-byte equality; any other difference is refused. Publishing
  is atomic and keeps the previous version for inspection.
- Details: [HARDENING.md](HARDENING.md), [docs/APP_INTEGRITY.md](docs/APP_INTEGRITY.md),
  [docs/KEYCHAIN_NAMESPACE_EXPERIMENTS.md](docs/KEYCHAIN_NAMESPACE_EXPERIMENTS.md)
  and [docs/TOOLSET_INSTALLATION.md](docs/TOOLSET_INSTALLATION.md).

## Limitations

- Local signature: the Duo loses Anthropic's identity, and macOS asks again for
  permissions such as folders, microphone or automation.
- It must be rebuilt after every official Claude update; don't use the Duo's
  own built-in updater.
- Still being validated: the effective Code account in each app, signing out of
  one account without affecting the other, and both apps open for long periods
  ([validation plan](docs/GUI_VALIDATION.md), [roadmap](docs/ROADMAP.md)).
- It does not protect against malicious software running as your user; the
  local records detect changes but are not a security boundary.

## Uninstall

1. Quit Claude Duo.
2. Remove the update check:

```bash
launchctl bootout gui/$(id -u)/io.github.guibrbs.claude-duo.update-check; rm -f ~/Library/LaunchAgents/io.github.guibrbs.claude-duo.update-check.plist
```

3. Move these to the Trash: `~/Applications/Claude Duo.app`,
   `~/Applications/Update Claude Duo.app` and `~/.local/share/claude-duo`.
4. The Duo account's data lives in `~/Library/Application Support/Claude-Duo`
   and `~/.claude-duo`. If you used Code sharing, the shared items inside
   `~/.claude-duo` are links: deleting them does not delete the originals in
   `~/.claude`.

## Development

```bash
python3 scripts/run-security-tests.py all
```

Tests run only in temporary folders with synthetic apps and accounts. CI runs
the same suite on arm64 and x86_64, plus the Clang static analyzer.
Contributions and issue reports are welcome.

## Credits and license

Based on [multi-claude-desktop](https://github.com/cgclark/multi-claude-desktop)
by Christopher Clark; its original technical documentation is in
[docs/MULTI_INSTANCE_REFERENCE.md](docs/MULTI_INSTANCE_REFERENCE.md).
MIT License ([LICENSE](LICENSE)). "Claude" is a trademark of Anthropic; this
project is not affiliated with or endorsed by Anthropic.
