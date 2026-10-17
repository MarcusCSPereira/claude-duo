# Local hardening changes

This revision supports the existing graphical workflow: open the Personal or
Enterprise/Trabalho application and use its Code tab. It does not require the
person using Claude to interact with the Claude Code CLI.

## Changed

- Share a data-only config parser across maintenance tools; no `eval` or shell
  evaluation of launcher contents. Verification compares the complete generated
  launcher, including environment values and executable.
- Validate instance names, identifiers, hues, environment keys and paths before
  mutations. Reject duplicates, path traversal, ambiguous dot components and
  shared Claude Code config directories. Resolve existing symlink aliases.
- Allow only `CLAUDE_CONFIG_DIR` in subscription-profile configuration. Start
  the child with a minimal environment; ignore inherited Bash startup files.
  Reject every caller argument and refuse inherited proxies rather than
  silently bypassing them. Hide env values in `--list`.
- Constrain data paths to the existing flat Claude layout or managed UUID
  locations inside home. Check every Desktop/Code pair for nesting or aliases.
  Reject non-ASCII legacy suffixes, root execution, foreign-owned paths,
  writable ancestors and custom allow ACLs (standard deny-delete ACLs allowed).
  Recheck paths and permissions before mutation and in generated launchers.
- Apply private-directory checks to icons/locks and watchdog logs. Refuse
  symlinked icon masters and symlinked/hardlinked watchdog logs.
- Verify the original and staged app against Anthropic's Developer ID team and
  bundle identifier. Require Gatekeeper acceptance of the source.
- Build and verify in a private directory on the destination volume. Publish
  with native `RENAME_SWAP` for a replacement or `RENAME_EXCL` for a first
  install, using directory descriptors and no-follow flags. There is no
  two-rename gap and no weaker `mv`/delete fallback.
- Write and sync an immutable, owner-only intention journal before publication;
  retain the prior bundle after a successful exchange. `--recover` checks inode
  identities and reports prepared/committed/unknown without replaying a swap,
  launching a bundle, restoring profiles or deleting anything.
- Hold a kernel `flock` across the worker and its children. It releases when
  the last holder exits, including after SIGKILL; the persistent lock file is
  not a stale-lock indicator. Legacy `.refresh-lock` directories still require
  inspection rather than being blindly removed.
- Fail closed if process enumeration fails. Stop cache cleanup if any observed
  Claude process shares the profile, including stock Claude using Personal.
- Create/restrict profile and Code config directories to mode 0700. Restrict
  the watchdog directory/log to 0700/0600. Status explicitly describes the
  limits of version comparison and local launcher/signature checks.
- Compare launchers in the watchdog and return failure for missing apps or
  unknown process state. Pass notification text as AppleScript arguments.
- Validate icon hue, including finite Swift numbers.

Copy **all** `bin/claude-*` files when installing: the entry script now needs
the shared library, `claude-build-worker.sh` and `claude-transaction.c` in the
same directory. Rebuild/recovery requires macOS 12+ and Xcode Command Line Tools;
the native helper is compiled locally in a private temporary directory, with
no downloaded binary or Python runtime dependency. Daily app launching does
not compile it. A normal rebuild is needed to
replace legacy launchers; `--verify` deliberately flags those until rebuilt.
Keep existing bundle IDs and profile directories to retain account identity and
history. Assign a unique `CLAUDE_CONFIG_DIR` to every additional Code account.

## Compatibility of the stricter policy

The existing Personal/Trabalho paths do not need to change. Arbitrary paths
such as `~/Documents` or `/etc` are now refused before creation/chmod/cleanup.
Legacy Desktop paths must be exactly `~/Library/Application Support/Claude`
or a flat `Claude-*` sibling; Code paths must be `~/.claude` or a flat
`.claude-*` sibling, with printable ASCII suffixes. New profiles can instead
use `~/Library/Application Support/Multi Claude Desktop/Profiles/<UUID>/desktop`
and `/code`. Generate a fresh UUID for each profile. Do not change paths on an
existing account without a separately reviewed, closed-app backup/migration.

The config must reside inside this user's home and cannot be a symlink.
It and its ancestors must be user-owned, without group/other write permissions
or custom allow ACLs. Data-directory ancestors have the same policy. Do not
blindly remove corporate ACLs or change permissions on shared folders to make
validation pass; use an approved private location or the official app.

Custom providers, API credentials, endpoint overrides and proxy overrides are
unsupported in this subscription mode. A required inherited proxy causes a
launch refusal. System proxy configuration and Claude's managed settings are
not edited. Arbitrary arguments, file opening and URL callback forwarding are
unsupported. This is deliberately narrower than a general Electron launcher.
The generated launcher requires pre-created profile/Code directories; rebuild
with the apps closed if those directories were deleted or moved.

The watchdog's own log moved to
`~/Library/Logs/claude-instances/watchdog.log`. Existing logs are not deleted;
the LaunchAgent's separate stdout/stderr paths remain as configured by macOS.

## Interrupted publication and retained bundles

Each prepared publication leaves
`/Applications/.claude-txn.XXXXXXXX/transaction.txt` (0600) inside a private
transaction directory (0700). It records root/stage/bundle device and inode
identities plus a validated instance name; it contains no environment or
credentials. After a replacement, `instance.app` inside that directory is the
previous bundle. After a first install, that slot is absent.

Inspect the transaction identifier printed by the builder:

```sh
claude-apps-refresh.sh --recover .claude-txn.XXXXXXXX
```

`PREPARED` means the recorded pre-publication layout is observed; `COMMITTED`
means the new bundle is at the destination and the previous slot matches the
record. Committed recovery also checks the generated launcher and local
signature. Unknown, partial, linked, foreign-owned or otherwise invalid records
fail closed. A later rebuild/updater can supersede an older journal's layout,
so old records may become unknown; they are never guessed or replayed. Staging
left before any journal exists also requires inspection and is not auto-deleted
on restart. Pre-journal failures with ordinary cleanup still remove their own
incomplete staging directory.

The record is not a signed provenance certificate or protection against a
malicious same-user process. Root and other administrators who can modify
`/Applications` are also outside this filesystem boundary. New bundles and
existing targets must be user-owned directories without group/other write
permissions or custom allow ACLs at the bundle root.

Previous bundles and journals are **not automatically pruned**. They retain old
blocks after updates, so disk use can grow; reviewed retention/cleanup remains
a follow-up. A previous bundle is not necessarily known-good. It is not a
backup of profiles, projects or Keychain credentials. There is no automatic
binary downgrade: a newer app may already have migrated profile data. A safe
restore needs a compatible closed-profile checkpoint and separate validation.

## Remaining limits

See [Residual limitations and improvement proposal](docs/LIMITATIONS_AND_ROADMAP.md)
for the deeper review, controlled evidence, release gates, and a proposed
unchanged-vendor-app launch mode. Environment/path restrictions above are now
implemented; the document labels the earlier findings and remaining proposals.

Copies still use ad-hoc signing and lose the original main executable's hardened
runtime/Team ID. These changes do not restore Anthropic notarization or make the
copies official. Signing the copies with a personal certificate would not grant
Anthropic's Team ID or entitlements either.

All profiles run as the same OS user. They organize accounts but are not an OS
security boundary. Users must still avoid stock Claude and Personal sharing the
same profile simultaneously. Process observation and a rebuild lock narrow
races but cannot prevent another program from starting or changing files after
a check. Atomic namespace publication and tested SIGKILL recovery do not prove
power-loss durability. The journal and parent metadata are synced, but the
helper does not recursively sync all app data or promise hardware cache flush.

Configuration separation does not prove that every GUI Code credential,
project setting, MCP server or environment source is separate. The minimal
parent environment does not control Code's later shell/local/project/managed
configuration layers. Profile path/permission observations are not descriptor-based
locks and cannot defeat a racing process of the same user. Bundle verification establishes local signature consistency
and an expected launcher, not an authenticated content manifest for all code.

Copies still need maintenance after Claude updates. In-app updates in copies
must be avoided. GUI Code authentication/SSO and session continuity should be
smoke-tested on the actual supported Claude version and accounts after a
reviewed installation; regression fixtures cannot establish those properties.

## Tests

On macOS with Python 3 installed for testing only:

```sh
python3 -m unittest discover -s tests -v
```

Production scripts do not add a Python dependency. Tests use temporary app and
profile fixtures, the macOS Bash/PlistBuddy/plutil, and simulated signature and
process commands. They never change the caller's HOME, contact a service, log in, or modify real
applications or histories. Native transaction tests compile the actual C
source and exercise real rename, lock, ACL and sync operations. Only their
test build enables failure/stop injection; production compilation ignores
those environment variables. Tests kill disposable helper processes before
and after exchange and inspect the resulting layouts. Real signatures must
be validated separately outside restricted execution environments.
