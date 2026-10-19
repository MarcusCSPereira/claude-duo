# First graphical trial: Keychain access blocked

On October 17, 2026, the real preparation was completed and the user opened
Claude Duo from the Finder. Before signing in, a request appeared for access to
the **Claude Safe Storage** Keychain entry, asking for the macOS password. The
user confirmed choosing **Deny**. The interface observed afterward was on the
Claude entry screen, with no account connected. The account trial was paused.

**The candidate is not yet cleared for use with real accounts.** The request
does not demonstrate data theft, nor does it prove that accounts were mixed. It
demonstrates a dependency on an existing entry that folder separation did not
resolve. There is no approved result for authentication independence.

**Investigation update:** the
[internal name and helpers experiment](KEYCHAIN_NAMESPACE_EXPERIMENTS.md)
did not resolve the prompt. A second sample, changing the product name in the
package, opened without permission prompts and produced an entry with its own
name, confirmed by attributes only. The Desktop experience and the accounts
remain pending; the prototype did not replace the installed Duo. The hypothesis
based only on `CFBundleName` was incomplete.

## What was observed

- Candidate built with implementation `b938c7dcd90d755aa1457c0118bb7884440a082c`,
  from official Claude 2.42304.0, on macOS arm64. The framework declares
  Electron 44.7.2.
- Versioned installer, build, nested signature and full content verification
  passed in the real preparation, using the production process observers. The
  critical source files and the legacy configuration were identical
  before/after this preparation.
- Duo installed at `~/Applications/Claude Duo.app`, with new Desktop and Code
  folders and a separate trial configuration. No additional macOS user.
- At the user's request, Personal and Trabalho were moved to the Trash. The
  profile data and the legacy configuration were preserved. This is not a
  migration of that data to the Duo.
- The first launch was performed by the user. The prompt text and the choice to
  deny are the user's reports; the entry screen was observed by the interface
  automation. No reading of Keychain contents was done by the audit.
- `CFBundleIdentifier` is distinct, but **`CFBundleName` is still `Claude` in
  both apps**. Only the display name was changed to `Claude Duo`.
- The ASAR of both apps has the same SHA-256. The four helpers still have
  the `Claude Helper` names, including the GPU, Renderer and Plugin variants.

The [sanitized data](evidence/gui-first-launch.json) identifies the candidate
without publishing profiles, conversations, emails, login links or secrets.

## Technical explanation and its limits

[Electron's safeStorage](https://www.electronjs.org/docs/latest/api/safe-storage)
uses the Keychain on macOS to protect encryption keys for local data.
The documentation also warns that signature changes can produce new access
requests. A local encryption key is not, by definition, the Anthropic account
password. Authorizing its use may broaden the application's access to the data
that key protects; it should not be treated as a cosmetic prompt.
The owner, contents and history of the pre-existing entry were not
inspected; it is not possible to attribute it exclusively to the original or to
a legacy copy based on the prompt text.

In the upstream code for the corresponding version, startup sets the service
as `app_name + " Safe Storage"` and the account as `app_name`:
[ElectronBrowserMainParts](https://github.com/electron/electron/blob/v44.7.2/shell/browser/electron_browser_main_parts.cc).
Without an overridden name, `Browser::GetName()` uses the executable name, which
on macOS comes from `CFBundleName`:
[Browser](https://github.com/electron/electron/blob/v44.7.2/shell/browser/browser.cc),
[ApplicationInfo](https://github.com/electron/electron/blob/v44.7.2/shell/common/application_info_mac.mm).
The preserved name is an explanation consistent with the observed prompt. The
upstream source and the metadata are not proof of every path in the binary
distributed by Anthropic, nor do they inventory the contents of the requested
entry.

There is a second dependency on that same name. The
[Electron subprocess launcher](https://github.com/electron/electron/blob/v44.7.2/shell/app/electron_main_delegate_mac.mm)
looks for helpers by the product name or the app name and aborts if it does not
find them. Therefore, **changing only `CFBundleName` is not a validated fix**.
The current builder preserves the signed helpers, and its integrity
verification refuses changes other than the expected ones. That isolated change
was not made to the installed application.

A static analysis with REA retained partial evidence from the ASAR. It hit
memory, time and semantic graph limits; it does not certify the entire
application. The hash declared in the ASAR for an unpacked native binding
differs from the distributed file. The observed file has the same bytes in the
original and in the Duo; the analysis continued while recording the
divergence, without treating it as content authenticated by the ASAR's internal
hash. The signatures verified during preparation are separate evidence, not an
automatic explanation of the divergence. The IDs and limits are in the
sanitized record.

## Next fix and criteria for resuming

A dedicated identity for secure storage must be designed and tested without
breaking helper discovery. A mechanism supported by this application that does
this while preserving the current packaging has not yet been demonstrated.
Changing helper names/paths/plists or injecting code into the ASAR would expand
the modifications and require a new analysis of signatures, integrity and
permissions. Do not apply these approaches directly to the installation in use.

1. Examine a solution in a disposable copy, without signing in, with an exact
   list of the changes and their consequences. Preserve the official source and
   the real profiles.
2. Confirm that the main process and helpers open on the covered architectures,
   that storage remains encrypted and that the copy no longer requests
   the original's entry. Any new sensitive permission is reviewed before
   authorizing it; do not read secret values to prove the separation.
3. Verify persistence after closing/reopening and rebuilding. The local
   signature may again trigger access requests after an update, even with its
   own name. A different name also does not create isolation between processes
   that can access the same user files.
4. Only then resume G01/G11 and, after that, return from the email link, the
   effective account in Code, simultaneous sessions and the remaining cases in
   the plan. The absence of a prompt, on its own, does not approve those cases.

Do not delete the original's entry, copy its key, grant permanent access,
disable encryption or modify Keychain policies to obtain an approved result.
Another macOS user was declined by the user and is not a prerequisite that can
be introduced silently. Until a solution is validated, use official Claude and
keep the Duo sign-in paused.
