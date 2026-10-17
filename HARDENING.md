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
- Reject common shell/loader environment overrides. Hide env values in `--list`.
- Verify the original and staged app against Anthropic's Developer ID team and
  bundle identifier. Require Gatekeeper acceptance of the source.
- Build and verify in a private directory on the destination volume. Preserve
  the previous bundle until the replacement is ready; restore it if publishing
  fails. Return errors explicitly instead of relying on `set -e` in functions.
- Serialize rebuilds with an atomic directory lock. A lock left after SIGKILL or
  power loss requires inspection and manual removal; it is never blindly stolen.
- Fail closed if process enumeration fails. Stop cache cleanup if any observed
  Claude process shares the profile, including stock Claude using Personal.
- Create/restrict profile and Code config directories to mode 0700. Refuse
  launcher arguments overriding its configured profile.
- Compare launchers in the watchdog and return failure for missing apps or
  unknown process state. Pass notification text as AppleScript arguments.
- Validate icon hue, including finite Swift numbers.

Copy **all** `bin/claude-*` files when installing: the scripts now depend on
`claude-instances-common.sh` in the same directory. A normal rebuild is needed to
replace legacy launchers; `--verify` deliberately flags those until rebuilt.
Keep existing bundle IDs and profile directories to retain account identity and
history. Assign a unique `CLAUDE_CONFIG_DIR` to every additional Code account.

## Remaining limits

Copies still use ad-hoc signing and lose the original main executable's hardened
runtime/Team ID. These changes do not restore Anthropic notarization or make the
copies official. Signing the copies with a personal certificate would not grant
Anthropic's Team ID or entitlements either.

All profiles run as the same OS user. They organize accounts but are not an OS
security boundary. Users must still avoid stock Claude and Personal sharing the
same profile simultaneously. Process observation and a rebuild lock narrow
races but cannot prevent another program from starting or changing files after
a check. Replacing two directories is not an atomic exchange across both
renames; failure restoration preserves the old app in ordinary failure cases,
not every crash/power-loss scenario.

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
process commands. They never set HOME, contact a service, log in, or modify real
applications or histories. Real signatures must be validated separately outside
restricted execution environments.
