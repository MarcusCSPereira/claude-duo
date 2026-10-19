# GUI trial of the original Claude alongside Claude Duo

This script prepares the feasibility stage of the [roadmap](ROADMAP.md).
The maintenance code was tested with made-up data. **Login, simultaneous
accounts and Code in the copy still lack GUI validation.** A valid local
signature or a different icon does not prove the accounts are independent.

**Status on 10/17/2026:** the real preparation was completed and the user opened
the Duo. The app requested access to the preexisting `Claude Safe Storage`
entry; the user denied it. G01/G11 were left inconclusive and login is paused.
See the [account of the blocker and the criteria for resuming](KEYCHAIN_FIRST_LAUNCH.md)
and the [sanitized record](evidence/gui-first-launch.json). The remaining cases
have not been run yet.

Private destination selection went through eight new tests, within the
145-case suite, and through eight build/signature/content checks against the
real source, in a disposable folder. In the latter, processes were simulated and
Claude was not opened. [Evidence and hashes](evidence/gui-preparation.json).

## Chosen environment

Use **the user's usual macOS session**, per the user's decision. Do not create
another local user. The original keeps the existing default profile; the Duo
starts with new folders and made-up projects. Code tests continue to run in
disposable folders, without requiring login or changes to real profiles.

The GUI test of the original will involve its real profile. New Duo folders
reduce data mixing, but they do not isolate the Keychain, every global
configuration location, or files accessible to the same UID. Authentication
independence still has to be demonstrated. Do not change HOME or copy
credentials to simulate account separation. The preparation below was run with
a new configuration; it did not convert the legacy profiles. Personal and
Trabalho were moved to the Trash at the user's request, preserving their data.

## Preparation and user participation

1. Inventory paths, identifiers, shortcuts and configuration of the existing
   installation, without collecting account content. The legacy Personal copy
   may use the same default profile as the original; do not open both at once.
   Also check for legacy maintenance that could run during the trial.
2. Confirm the effective user and their home. All operations use this real
   session, without `sudo`, without changing HOME and without native test macros.
3. Check the reviewed package and its manifest against the candidate's
   independent reference. Install the full set with the
   [versioned installer](TOOLSET_INSTALLATION.md), preserving `~/bin`,
   legacy configuration and shortcuts until a reviewed transition.
4. Select the private destination `~/Applications`, which must be physical,
   owned by the user and have mode 0700. If missing, create the folder; if it
   exists and is incompatible, review the destination without changing other
   apps' permissions in order to proceed. `@apps user` only validates the
   folder, rejecting links, special permissions and granting ACLs; it does not
   create it or change its mode.
5. Create a trial configuration separate from the one in use, with the
   original + copy mode and a single Duo copy. Require a new app destination and
   new Desktop/Code folders; if they already contain data, review without
   overwriting or deleting. Do not import the whole default profile, tokens or
   Keychain.
6. Coordinate closing the apps for the build, without silently terminating
   tasks. Use only the configuration and maintenance chosen for the candidate,
   with no new LaunchAgent and no competing legacy maintenance.
7. Check the official source, build the Duo and verify content, configuration
   and signature before opening it. Do not replace process-observation errors
   with simulated results. Open the original only after checking the conflict
   with the Personal copy and the shortcut targets.

This preparation is done once by the technical owner. The trial and daily use
happen in the Claude interface; they do not require using the Claude Code CLI.
The trial and the intended daily use take place in the same usual session. This
does not automatically convert the legacy installation, nor does it prove that
the modified applications are compatible with your accounts.

## Lab topology

| Item | Location in the usual session |
|---|---|
| Original, official executable | `/Applications/Claude.app`, source/read-only for our tools |
| Duo | `~/Applications/Claude Duo.app` |
| Original's Desktop data | `~/Library/Application Support/Claude`, existing real profile |
| Original's Code configuration | `~/.claude` and other effective locations, preserving existing data |
| Duo's Desktop data | `~/Library/Application Support/Claude-Duo` |
| Code configuration requested for the Duo | `~/.claude-duo` via `CLAUDE_CONFIG_DIR` |
| Distinct made-up projects | `~/Claude Duo Lab/original` and `~/Claude Duo Lab/duo` |

Example of a separate configuration for a new trial copy, after reviewing the
destinations; do not replace the legacy configuration with this example:

```text
@mode original-copy
@apps user
Duo | com.guibrbs.claude-duo.lab | ~/Library/Application Support/Claude-Duo | 212 | CLAUDE_CONFIG_DIR=~/.claude-duo
```

The `.lab` identifier marks the test candidate; it does not migrate the
identifier of an installed copy. Changing identity, location or version after
the test requires revalidating whatever the change affects. The original stays
off the destination list. Folder selection does not change the
`/Applications/Claude.app` source.

The maintenance lock is shared by rebuild, caches and checkpoints **within the
selected applications folder**. We do not coordinate two configurations that
pick different folders and reuse the same profiles. Use only the lab
configuration, with no old copies on top of this data. Changing `@apps` does not
migrate or disable old apps, and it changes the integrity binding.

## Checks before opening

Record macOS version and build, architecture, Claude version, package
commit/hash, and the Duo's identifier and exact path. Check the source's
Anthropic signature and Gatekeeper status, the copy's signature/content and the
launchers' targets. Record hashes of the source's critical files before/after
the build. These tests must not read profile content, process variables or the
Keychain.

Open the original by its full path and the Duo by its private path in Finder.
Check shortcuts/Dock before adding them. Do not open an app held in a
transaction, and do not look for a copy by name alone. Returns via the browser
must be observed; the current launcher rejects arguments and URLs.

The official app is shared on disk: an update by another process can change it.
If the source, version or signature changes during the trial, pause and identify
a new candidate. Do not grant administrator privileges, disable Gatekeeper or
work around organization policies to get a pass.

## Acceptance matrix

Flow declared by the user: **login via email link, no SSO**. G07 is mandatory
for that link; SSO is out of the initial scope and will not be treated as
tested.

When the matrix is opened, every item starts as **NOT RUN**; the actual results
go in the dated record above. Use only the labels A and B in the public report;
confirm email/organization privately in the interface. Declare the required
features. Re-authentication is done by the user inside Claude/the browser.
Signing out of account A, restarting and logging out of the macOS session are
arranged with the user; the trial does not force them over work in progress.
The scenario of an original with an empty profile was not tried under this
choice of environment. Record the coverage obtained without treating the real
profile as disposable.

| ID | Trial | Required evidence |
|---|---|---|
| G01 | Sign in to A in the original and B in the Duo | Expected identity in each app's interface |
| G02 | Reverse the opening order and, when the user re-authenticates, the login order | Do not switch the other app's account; do not delete the original profile to get fresh data |
| G03 | Open local Code in both at the same time | Effective Code account confirmed; tasks in the correct projects |
| G04 | Close, reopen, log out of the macOS session and restart | Resumption and identities preserved, without opening held versions |
| G05 | Sign out of and back in to B with A active | A's session/task remains correct |
| G06 | Login renewal and revocation of the test session in B | Impact observed; do not revoke usual sessions or all of the account's sessions |
| G07 | Email link/browser return | Return to the correct account and window; without bypassing the launcher |
| G08 | Finder, Dock and shortcuts | Correct paths, app identity and profile |
| G09 | Build and checkpoint with the original, the Duo or both open | Safe refusal, without terminating tasks to force maintenance |
| G10 | Made-up preferences and extensions | Reuse without transferring authentication, per the proposal below |
| G11 | Permissions and declared features | Works per identity; failures recorded |

Before G01, watch for Keychain access requests. An unexpected request for the
original's entry blocks login until reviewed. Deny the request; do not delete
entries or grant access to force the test. The current candidate hit this
blocker. A distinct folder, identifier or icon does not resolve it on its own.

Create distinct harmless markers in the projects and in the test instructions.
A response containing a marker shows that configuration was loaded; it does not
prove which account paid for/ran Code. Do not use that response as a substitute
for identifying the effective account; if it cannot be observed, mark
**INCONCLUSIVE**, keeping the feasibility requirement open.

The [reuse proposal](PROFILE_REUSE.md) adds the user's requirement without
sharing the whole profile. First validate basic authentication; then repeat the
essential cases with imported made-up configurations. The importer is not
implemented yet, so G10 remains pending. If the service does not allow limiting
a revocation to the trial session, keep that case pending without revoking
usual sessions. Do not use cache cleanup as a test of refusal without exit: the
current command may ask the selected app to close before cleaning up, which is
different behavior from build and checkpoint.

## Recording and wrap-up

For each case record date, candidate, A/B account type, result
(`PASSED`, `FAILED`, `INCONCLUSIVE`, `NOT RUN` or `NOT APPLICABLE`) and a
sanitized note. Excluding a feature from scope requires an explicit decision;
do not turn a pending test into a pass. Do not publish profiles, authentication
logs, conversations, callback URLs or screenshots containing private data.

An unexpected account switch, data loss or uncertain source halts the release.
At the end, close the apps and preserve sanitized results. Ending Duo sessions
or removing its trial folders are later actions, subject to review; preserve
the local account, the real profile and the legacy data. Do not delete profiles
automatically or assume that deleting files revokes sessions on the service. No
result authorizes replacing the real profiles or starting automatic updates
before the roadmap's other criteria are met.
