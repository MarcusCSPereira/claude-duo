# Roadmap: two Claude accounts on Claude Desktop and Code

Plan updated on 10/17/2026, in
[PR #1 of your fork](https://github.com/guibrbs/multi-claude-desktop/pull/1), still
a draft. The previous base `2d37bf6` holds the historical evidence cited
below. The installer and the profile policy now have additional tests; the
real preparation has been completed. The first Duo opened by the user asked for access
to the preexisting `Claude Safe Storage` entry, and the user denied it. The account
run is blocked: [finding KC01](KEYCHAIN_FIRST_LAUNCH.md). The document
distinguishes disposable tests, real preparation and pending account validation.
The [later experiments](KEYCHAIN_NAMESPACE_EXPERIMENTS.md) found
a path to an entry with its own name, without changing the Desktop sign-in
screen. The production builder already applies this change to the Duo, with
regenerated source verification; the installed Duo has not been rebuilt yet and the accounts
have not been tested. The release block remains in place.

## The outcome we want

You use **the original Claude and a copy**, both with the interface of Claude
Desktop itself. The copy is called **Claude Duo**. You run tasks in Code with the matching account. For
example, the original serves the personal account and the copy the work account; the
assignment of accounts can be reversed. Daily use should be graphical. Each
profile has its own folders, and installation and updates must recognize failures
and preserve data.

The original keeps the official identity and updater. The current implementation
allows creating modified copies with their own names, identifiers and
launchers. Each copy replaces the external signature with a local signature;
Anthropic's identity and exclusive permissions remain a limitation
in that copy. Complete authentication separation between original and copy still
needs to be demonstrated in the interface. This preference replaces the
two-copy design for daily use. Personal and Trabalho were moved to the Trash
at the user's request; their data and the legacy configuration were preserved.

## Preferred topology and copy updates

| Application | Role | Data |
|---|---|---|
| `/Applications/Claude.app` | Daily use of one account; receives the official update | Default Desktop profile and default Code configuration |
| `/Applications/Claude Duo.app` | Daily use of the second account; rebuilt by our tools | Desktop and Code folders exclusive to the copy |

In this mode, reserve the default directories for the original. The managed configuration
must list only the copy; configuring the original as a rebuild target
remains prohibited. The explicit `@mode original-copy` policy already reserves both
default profiles and requires a single copy. Configurations without a header preserve the
legacy flow, in which a Personal copy can use the default. That legacy copy and
the original must not use that profile simultaneously. No configuration in
use has been converted automatically.

The intended update flow is:

1. The original Claude receives its official update normally.
2. A watcher detects a change in the source and identifies that the copy needs
   to be rebuilt. Comparing only version numbers neither proves the source nor
   detects every content change.
3. Wait for the original and the copy to close and confirm a verifiable,
   stable source. Do not end tasks automatically.
4. Build a new copy in private staging from the updated original,
   apply only the intended changes and verify signature and content.
   Refuse source changes or uncertain observations during the operation.
5. Publish the finished copy by atomic swap, preserving the previous one. The data
   and configuration of the second account stay outside the bundle and are not copied
   from the original's profile.
6. Report success or failure. Opening the new version and any migration of
   its data follow the compatibility tests; keeping the previous bundle
   does not prove that a downgrade is compatible.

Today the watchdog verifies and notifies; **automatic rebuilding is not yet
implemented**. The builder already prepares, verifies and publishes copies, and requires
the observed Desktop applications to be closed. The additional work is
orchestrating detection, waiting, selection of the single copy, rebuilding and reporting
of failures. Updating the original does not modify the copy's files by itself.

The model preserves the official identity in the application used by the first
account and reduces the number of modified bundles. The copy remains subject to the
signature and authentication limitations already documented.

Your priority remains **security first**. The prototype of a new
native manager is postponed. The current path must pass the tests before
we invest in another interface.

The user decided **not to create another macOS user**. The graphical run will be
in the usual session, with new folders for the Duo and the original's existing profile.
The [updated script](GUI_VALIDATION.md) starts with a review of legacy copies and
shortcuts to avoid simultaneous access to the same default profile. New
folders do not constitute isolation from the Keychain or from files of the same UID.

Additional requirement: reuse the original's preferences, MCPs and plugins in the Duo,
since it is the same person. The [selective import proposal](PROFILE_REUSE.md)
defines the original as the reference, preserves the Duo's own settings and keeps
login, sessions and credentials separate. Importer and sync are not yet
implemented. This does not mean copying the whole profile or sharing
the folders of the two accounts.

## Where we are

| Item | Proven status | Limit of the evidence |
|---|---|---|
| Configurations and folders | Validation of content, paths, permissions and folder separation implemented | Distinct folders do not isolate programs run by the same macOS user |
| Building the copies | Authenticated source, recorded content and atomic publication with an operation record | A local signature does not restore Anthropic's identity |
| Maintenance | Locking across tools, native process observation and restricted cache cleanup | Other programs can still start or write outside this coordination |
| Profile backup | Optional checkpoint of the Desktop/Code pair with content verification | No restore; restricted format; excludes Keychain and external projects; content not encrypted |
| Installer and original + Duo mode | Complete set verified, retained versions, atomic activation of the set and in-progress operation bound to its version | Integration with the legacy installation and maintenance interface pending |
| Current automated tests | 145 tests passing locally; remote results for this stage recorded in the PR | Tests with made-up data do not prove login, SSO or real use of Code |
| Two accounts in graphical Code | First Duo opened at the sign-in screen; login paused by finding KC01 in the Keychain | Effective account, email link return and continuity still need to be observed |
| Reuse of preferences, MCPs and plugins | Selective import proposal documented | Inventory, preview, application and sync not yet implemented |
| Automatic Duo rebuild | Flow planned; manual builder and verification watchdog available | Detection, waiting and automatic rebuild after an official update not yet implemented |
| Previous CI base | 106 tests passing on Apple Silicon and Intel at commit `2d37bf6` | Historical evidence, predating the installer |
| Claude Duo in a disposable folder | 8 real checks passing, now also in the private target: official source, build, content/signature and default profile reservation | Process observation simulated; application not opened; accounts not used |
| Real application on the previous base | 10 checks passing with Claude 2.42304.0, including detection of changes after a new local signature | The Claude executable was not opened and no account was used in these tests |
| Installation on your machine | Versioned set installed; Duo built and verified in a private target with real native observation | Personal/Trabalho in the Trash on request; legacy data preserved; candidate not released for real accounts |

References: [CI of the verified base](https://github.com/guibrbs/multi-claude-desktop/actions/runs/39061863713),
[evidence](evidence/integrity-maintenance.json) and
[technical limitations](LIMITATIONS_AND_ROADMAP.md).
The evidence for the installer base is in
[toolset-installation.json](evidence/toolset-installation.json). The lab
preparation stage, with the 145 tests and current hashes, is in
[gui-preparation.json](evidence/gui-preparation.json). The private target was
rehearsed in disposable folders. That historical record predates the decision to
use only the usual session. The real preparation and the block on the first
launch are recorded in [gui-first-launch.json](evidence/gui-first-launch.json);
no login or profile migration was performed.

## Order of execution

| Stage | Deliverable | When we will consider it done | Your participation |
|---|---|---|---|
| 1. Consistent installation | Implemented and tested in disposable folders; transition of the installation in use is missing | Interruption, tampering and concurrency do not activate an incomplete set | No login in the code tests |
| 2. Security review and preparation | Review the installer, file provenance and graphical test requirements | Evidence and limits recorded; disposable environment prepared | Confirm the account types and features you need |
| 3. Two accounts in the interface | Validate Desktop, Code and authentication in the original and in the copy | Graphical matrix approved for the declared account types | Do the logins directly in Claude |
| 4. Updates and recovery | Detect an update of the original and rebuild only the copy | Waiting for closed applications, failure scenarios and recovery rehearsed | End tasks for the agreed rehearsals |
| 5. Existing data | Offer compatible migration and restore, if you want to preserve current usage | Recovery rehearsed on copies; source preserved and exclusions documented | Choose to migrate or start with new profiles |
| 6. Graphical operation and distribution | Understandable installation, verification, updating and removal | Required flows executable through the interface, with no commands in daily use | Try out the usage flows |
| 7. Pilot and maintenance | Release an identified version and track changes | Release criteria met and tested versions recorded | Use the pilot and report problems without sending secrets |

Stage 3 is the feasibility condition: authentication failures or account switching
block the release. Stage 5 is required before migrating or replacing your
existing profiles; the first run can use new profiles. Public
distribution requires additional signing and review work described in stage 6.

## 1. Install the tools as a single version

Current problem: copying several scripts and helper files manually can
leave incompatible versions mixed together if the operation is interrupted.

- Prepare each complete version in a private folder, with an exact list of the
  expected files, their contents and permissions.
- Validate the package's source against a previously verified reference. A
  tampered manifest and tampered files together do not prove authenticity.
- Refuse missing files, extra files, links, unsafe destinations and incompatible
  packages; treat configuration and manifest as data.
- Prepare and verify the required components before activating the version.
  Define how the local compiler and its failures fit into this process.
- Activate the set by an atomic swap and keep the previous version of the
  tools for a controlled rollback.
- Ensure that an operation already started keeps using a single version,
  including its internal scripts, libraries and build files.
- Test concurrent installation, updating during an operation, lack of
  space, build failure, insufficient permissions and abrupt termination
  before/after activation. Refuse environments without the required atomic operation.
- Recognize incomplete installations after a restart without automatically deleting or promoting
  files of uncertain origin.
- Design the transition from the legacy installation without overwriting scripts in use
  before a reviewed change. Develop first in disposable folders.
- In original + copy mode, reserve the default Desktop and Code profile for the
  original and validate the configuration of the single copy. Keep the official source
  out of the publication targets.

**Output:** complete, identifiable set, tested activation, previous version
retained and failure inspection. Rolling back the tools does not mean rolling back
Claude or restoring your data. This deliverable is implemented in code and
tested in disposable folders. The dispatcher is published before the active
reference and must be compatible with the protocol of both versions; these are two
separate atomic operations. Details in
[TOOLSET_INSTALLATION.md](TOOLSET_INSTALLATION.md). Installing into your real
directories and converting the legacy shortcuts remain separate steps.

## 2. Review security and prepare the graphical run

- Maintain an inventory of the points that read configuration, create processes,
  write files, verify signatures, compile code and delete caches.
- Review the new components and expand adversarial tests at the limits of
  formats, sizes, permissions, concurrency and interrupted operations.
  Rerun static analysis and the appropriate suite on every change.
- Define when to check the installed content and how to report a change.
  Today the daily click does not perform full verification of the application.
- Separate in the diagnostics: official source, copy integrity, version,
  graphical compatibility and identity of the observed account. Each piece of information
  must state when it was verified or whether it remains unknown.
- Prepare the run of the original and one copy in the user's usual session,
  with new folders for the Duo and disposable projects. The original uses its existing
  real profile; do not delete it to get a first-run scenario.
  `@apps user` allows building the Duo in a private `~/Applications` without writing
  to the shared apps. The [graphical script](GUI_VALIDATION.md) starts
  with a review of the shortcuts and of the Personal copy that may share the default.
  Also check concurrent legacy maintenance, application registration and the Dock.
  Do not create another macOS user or change HOME.
- Record exact versions of macOS, architecture, Claude and tools.
  The helpers' macOS 12 minimum does not prove support for Claude itself.
- Confirm the required login types: personal, organization and SSO, if used;
  local Code and other features you actually intend to use.
  For the first run, the user confirmed login by email link, without
  SSO. The return of that link must work for the correct app and account.
- Document the loss of identity/permissions in the copies and check possible
  effects on the Keychain, macOS permissions, subprocesses and Code features.
- Distinguish the protections of our launcher from the effective configuration of the
  original, which is still launched through the official macOS flow.
- Define a continuity test between launch and maintenance. The current
  lock coordinates our tools; it does not yet coordinate all launches
  nor prevent an external program from opening the profile.

**Output:** identified candidate, test script and an explicit list of
supported, pending and refused features. No claim of a security
percentage. Known problems of unintended execution, data loss or use of the
wrong account must be resolved before the pilot.

## 3. Validate two accounts in Desktop and Code

You will do the logins inside Claude itself. The tests will use tasks without
private content and disposable folders. It will not be necessary to hand over passwords,
tokens, cookies, recovery codes or Keychain exports.
In the matrix below, A and B correspond to the original and the copy. The account assigned
to the original does not depend on whether it is the personal or the work one.

| Test | Behavior to observe |
|---|---|
| Sign in to A and then B; repeat in reverse order | Each window shows the expected account |
| Reopen both applications and restart macOS | Sessions and identification remain correct |
| Chat and open Code in both simultaneously | Each task uses the expected account and configuration |
| Resume tasks after closing and reopening | Correct continuity in the matching profile |
| Sign out and back in to B while A keeps running | A keeps its session and its tasks |
| Renew or revoke authentication | Effect limited to the expected profile, or limitation recorded and mode refused |
| Complete login through the browser and SSO, if needed | Return to the correct window and account |
| Open from the Dock, Finder and shortcuts | Correct target and profile, including with old copies retained |
| Open original and copy; try to start a legacy copy with the default profile | Original and main copy use distinct data; legacy conflict recognized; maintenance refused with applications running |
| Use local Code configuration | Shell, hooks, MCP and project settings do not cause unexpected mixing |
| Reuse selected preferences and extensions | Imported configuration works; the Duo's authentication and own settings preserved; importer still pending |
| Request permissions and use the declared features | Behavior recorded for each application identity |

The current launcher rejects all arguments, including URLs. The login
return flow needs to be observed: if it depends on a legitimate argument,
a restricted and tested solution will be required, preserving the protections against
arbitrary commands and parameters.

Icon name and color help distinguish windows; the effective account must be
confirmed in the interface and in the Code context. Use harmless markers and
separate projects to observe configurations, without collecting credentials or
publishing conversations. Separating projects also reduces human error; it still does not
create an access barrier between programs of the same user.

**Output:** report per version and account type, with results and limitations.
Any unexpected account switch or ambiguous identity halts the release.
If the modified copies are incompatible, record the blocker. An
investigation of the unmodified official app will be a separate decision;
the graphical prototype remains postponed until that need is demonstrated.

## 4. Update and recover without confusing applications and profiles

- Implement the detection, waiting and rebuild flow for the single copy described
  above, keeping the official updater in the original. Rehearse the update,
  rebuild and re-verification; require Desktop applications to be closed before
  maintenance, without silently ending tasks.
- Test original in use, copy in use and both open when the update
  is detected: show a pending update and wait. Coalesce repeated
  events and revalidate which official version is ready before rebuilding.
- Test a source update in the middle of the build, same version with different
  content, watcher failure, restart and concurrent installations. Refuse
  publication without verification and record an uncertain result for inspection.
- Observe the copies' internal updater and changes in identity,
  permissions or content. Define a supported flow without relying on private
  modifications to the updater or on disabling macOS checks.
- Repeat the essential login and Code matrix after the update.
- Rehearse signature failure, unavailable source, lack of space, incompatible
  version and interruption before/after the swap of each component.
- Show which components changed and distinguish an operation that is prepared,
  completed or in an uncertain state. An uncertain state requires inspection.
- Test the launch target with previous copies retained, including from the
  Dock and from the browser return. An old copy must not be launched as an
  improvised recovery.
- Define reviewed retention and removal for versions, records, temporary
  builds, checkpoints and quarantined caches. Protect sensitive data and
  avoid exhausting storage, including through partially completed copies.

**Output:** reproducible update and recovery with test data,
including clear instructions for failures. The atomic on-disk rename and the
process-termination rehearsals do not certify resilience to power
loss. A stored previous version does not authorize a downgrade over migrated data.

## 5. Preserve existing data, if there is a migration

The requested configuration reuse is a deliverable distinct from
account/history migration. Develop inventory and preview first, with
made-up data, according to [PROFILE_REUSE.md](PROFILE_REUSE.md).
Then rehearse selective import, conflicts and one-way sync;
repeat the authentication matrix. Do not copy secrets or account state through
a generic backup rule or to avoid a necessary reconnection.

- Choose between starting with empty profiles or reusing current data.
  The original keeps the default Desktop/Code pair; the copy uses an exclusive pair.
  Rehearse returning to the original data used by a legacy Personal copy,
  including history, permissions, authentication and Code features.
- Define how to deactivate the shortcuts and configuration of the legacy Personal copy
  to prevent it from opening the same profile as the original. Preserve files and
  data until a reviewed transition; do not remove applications automatically.
- Check the inventory of real metadata before copying. The current checkpoint
  refuses links, extended attributes and other objects; a refusal needs
  a reviewed format solution, without removing metadata from the original profile.
- With the applications closed, prepare a compatible copy in new destinations
  and check content, version and behavior. Preserve the source.
- Rehearse restoring into new folders with a compatible application/schema,
  verifying continuity of history, settings and Code tasks.
- Document what requires a new login and what is left out: Keychain, macOS
  permissions, external repositories and other data outside the two profiles.
- Define storage protection, appropriate encryption and disposal of
  checkpoints. Copied data may contain sessions and private code; restricted local
  permissions do not encrypt the content.
- Separate data restore, tool rollback and Claude downgrade;
  each operation requires its own compatibility validation.

**Output:** migration and recovery procedure rehearsed, source preserved
and result accepted by you before swapping the profiles in use. The existing
checkpoint is a partial prerequisite. Restore is not yet implemented.

## 6. Make operation graphical and prepare distribution

- Start with the official icon and that of the single copy. Assess the need for a
  small maintenance interface after the validations.
- Offer installation, status, updating, failure inspection and removal through
  understandable flows. State the affected profile and ask for tasks to be ended
  without silently ending them.
- Explain prerequisites, disk space, tested versions and incompatibilities
  before applying changes. Treat required proxies and corporate policies
  as compatibility requirements, preserving the organization's policy.
- Allow removing our tools while preserving the profiles. Deleting data
  must be a specific action, with visible target and consequence.
- Review the README and help to align promises with the evidence, including account,
  updating, APFS space and recovery. Make legacy guidance
  clearly distinguishable from the instructions of a released version.
- For public distribution, define verifiable packaging, signing and
  notarization of our own components, protection of publishing credentials
  and pinned dependencies. This may require an Apple Developer account; it is not
  needed to continue the current code and disposable-folder tests.
- Prepare version/tag, package manifest, release notes and an
  install/removal test in a clean environment. External review of the sensitive parts
  must precede public distribution.

**Output:** graphical usage flow validated for the announced scope. Signing our
installer grants neither it nor the copies Anthropic's identity. Building
the helpers still depends on the Command Line Tools; packaging
our own binaries would be another decision, with corresponding source validation.

## 7. Release a pilot and maintain compatibility

- First release an identified version for supervised use, with new
  profiles and projects without sensitive data.
- Record problems with minimal data: versions, stage, result and sanitized
  message. Without attaching profiles, checkpoints, process environment or tokens.
- Tie each release to a commit, verified package, CI and graphical report.
  Apple Silicon/Intel CI proves the automated tests on those machines;
  graphical support on each architecture requires a corresponding run.
- Review upstream changes and new Claude/macOS versions before declaring
  compatibility. Repeat account, signature, update and recovery tests
  when the affected behavior changes.
- Define how to suspend a problematic version and offer compatible
  recovery. Keep a history of limitations and support instructions.

**Output:** usable version within an explicit scope, with planned
maintenance. The work continues through new versions and concrete problems; a
growing test count does not represent progress toward 100% security.

## Criteria for releasing use

- Complete installation and updating without version mixing demonstrated.
- Automated tests and static analysis passing on the code to be released.
- Desktop and Code working with both accounts in the declared matrix.
- Login return, window identity and macOS routing validated.
- Original preserved, default profiles reserved and copy rebuild after an
  official update tested with applications running, closed and failing.
- Failures and recovery rehearsed; migration conditioned on compatible restore.
- Graphical routine and data-preserving removal verified.
- Evidence, artifact provenance and limitations available for review.
- No known outstanding issues of wrong-account use, unintended execution or
  data loss within the announced scope.

Both applications will continue to have the access of the same macOS user.
Isolation between accounts against a malicious local program requires an operating
system barrier and will not be certified by this roadmap. If a
signing, authentication or corporate policy limitation prevents the intended
use, the correct conclusion will be to keep that mode experimental or refuse it.

## How we will work

Each stage will have reviewable changes, commits in your fork, tests proportional
to what changed and an update to the PR. The PR stays a draft while the required
criteria are pending. Implementation, automated evidence and graphical
testing will be recorded separately.

We do not set dates before resolving graphical authentication. The installer has already been
developed and tested in a disposable environment; the greatest uncertainty is the behavior of the two accounts
and of the permissions in the modified copies. Your participation will be needed for the
logins and for evaluating the pilot. Development and automated tests use
made-up data. A future migration, if chosen, involves copying private
files and will follow the reviewed procedure of stage 5.
