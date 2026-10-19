# Experiments to separate the secure storage name

On October 17, 2026, two disposable prototypes were prepared and opened without
signing in, with the user's authorization for each launch. **The installed Duo
was not replaced.** The release block from the [first trial](KEYCHAIN_FIRST_LAUNCH.md)
remains in place: the experiments do not approve two real accounts or graphical Code.

## Observed result

| Experiment | Changes | Result |
|---|---|---|
| Internal name and helpers | Own `CFBundleName`, four helpers renamed and re-signed | Opened, but still requested `Claude Safe Storage`; the user denied it. Hypothesis insufficient. There was also a Documents permission request. |
| Package product name | Own `package.json.productName` in the ASAR; original helpers preserved | Opened without permission prompts, according to the interface and the user's confirmation. An attributes-only query found an entry with the expected own name. The screen shown was the signed-out Desktop login (claude.ai/login in the app window), the same state as the old Duo; see the reopening below. |

Both prototypes were closed with ⌘Q. The native observer confirmed the Desktop
apps were stopped after each trial. No sign-in was performed, no secret value
was collected, and no Keychain access authorization was granted by the
automation. No Keychain entries or profile folders were deleted.
The second app may have created its own key as part of startup; that entry was
preserved. The absence of a prompt does not prove the absence of other silent
queries, nor separation of all authentication.

## Correction of the earlier hypothesis

Changing only `CFBundleName` did not solve it. The distributed package declares
`productName: "Claude"`. The
[Electron 44.7.2 bootstrap](https://github.com/electron/electron/blob/v44.7.2/lib/browser/init.ts)
assigns that value to `app.name`. So the bundle metadata is not the only
relevant name source. The combination of the negative test, the definition in
the package and the positive test points to this mechanism; it is not a
complete reconstruction of every path in Anthropic's binary.

In the second sample, the helper names and `CFBundleName` stayed identical to
the source. The semantic change in the ASAR was limited to `productName` in
`package.json`. The size, the affected offsets and that member's hashes were
updated, along with the header hash in `ElectronAsarIntegrity`. No JavaScript
payload was changed. The main executable and the outer bundle were re-signed
locally, as the current build already does; the four helpers kept their
original files and signatures.

The confirmation query requested **attributes only** for the entry with the
exact name of the second sample. Returning secret data and references was
explicitly disabled; authentication interaction was configured to fail, with
no interactive fallback. The query confirmed existence, did not read the
value, did not edit ACLs and did not compare keys. This does not prove that all
secrets used by the application are separated.

## Build checks

- Official source verified by Anthropic identity, nested signature and
  Gatekeeper. Experiment versions pinned to Claude 2.42304.0 / Electron 44.7.2;
  different versions are refused pending a new review.
- Comparison of 4,964 source entries with the first sample, including the
  five executables before/after signing. Only the expected signature fields
  were normalized; unknown formats and layouts fail.
- In the second sample, comparison of all 508 ASAR members and the remaining
  source files. Only the `package.json.productName` semantics changed in the
  package; payloads outside that member stayed byte-for-byte identical. Helpers
  and their resources/signatures stayed identical to the source.
- The nested signature and content comparison of the second sample also passed
  after the graphical trial. Source content stayed unchanged during each
  preparation; no tool installed or replaced an app in use.
- 25 new offline tests passed: 12 on Mach-O/helper comparison and
  13 on ASAR limits and changes. The CI distribution now covers 170
  tests with no gaps or duplicates: 86 profiles/experiments, 59 storage and
  25 installer. The previous 145 tests remain evidence for implementation
  `b938c7d`; no new remote result is inferred from that history.

The first attempt to prepare the second sample refused deduplicated ASAR files
before creating the app. Inspection found 25 pairs that share exactly identical
ranges. The parser now accepts these aliases, with additional tests; it still
refuses partial overlaps and any alias of the `package.json` range. The refused
attempt was recorded, with no fallback to a less verified copy.

The Documents request in the first experiment coincided with the trial app and
data being inside that folder. The exact trigger was not demonstrated. The
second sample and its new data were kept outside Documents and did not request
the permission.

## Reopening and log comparison

On October 17, 2026, at 22:07, the same sample was reopened by the agent, at
the user's request, with the same disposable data folder and without signing
in. It showed the standard signed-out Desktop screen: the app's own window, the
Claude logo, “Continuar com o Google” (Continue with Google) and the cookie
notice, which was left unanswered. No Keychain prompt appeared, and the app
closed cleanly with ⌘Q.

The local logs (`main.log`) of the three test apps show the same signed-out
flow (`sign_in_cookie_present: false`), with the same Desktop routines
(Code, Cowork, `startup-sign-in`). The only difference is the Keychain:

| App | Stall until the login state | `safeStorage` |
|---|---|---|
| Old Duo (`b938c7d`) | 88.7 s (`event-loop-stall`) | `isEncryptionAvailable=false` after the denial |
| 1st prototype (helpers) | 41.0 s | `isEncryptionAvailable=false` after the denial |
| `productName` sample (2 launches) | ~1 s | no prompt |

The old Duo's record (G11) already described `claude.ai/login` after the denial.
Therefore, the “earlier Desktop introduction” was not a comparable state, and
the `productName` change did not change the entry screen. The User-Agent was not
measured. Real sign-in remains untested.

## Integration into the production builder

In `original-copy` mode (the Duo), the builder now gives the copy the
`productName` `<name> Claude`, for example `Duo Claude`. With that, Electron
looks for the `Duo Claude Safe Storage` key. Legacy mode does not change: old
installations keep the same key and are not signed out.

How it works, in C, with no Python in daily use:

- **Same size.** In `package.json`, `"Claude"` becomes `"Duo Claude"`, and the
  same number of bytes of insignificant whitespace, outside strings, is removed.
  The file keeps its size, no ASAR offset moves and the header keeps its
  length. Only that member's hashes (hash and blocks) change, plus, in
  `Info.plist`, the header's `ElectronAsarIntegrity` hash.
- **Writing only in staging.** `integrity product-name` writes to an
  exclusive file next to `app.asar` and swaps it in with an atomic `rename`. If
  it fails, the temporary file is deleted. A temporary file left over from an
  interrupted run causes the next build to be refused.
- **Verification that does not trust staging.** The integrity record
  **regenerates the expected file from the source** and requires byte-for-byte
  equality with the copy, with the `Info.plist` hash checked against the header.
  Before that, it refuses: a source `package.json` hash that diverges from
  any block; more than one top-level `package.json`; an entry layout
  different from the expected compact one (including `unpacked`); a payload
  shared with another member; a `productName` other than `"Claude"`, duplicated,
  nested or with an escaped key; insufficient insignificant whitespace; and a
  source `ElectronAsarIntegrity` that does not match the header. An
  independent semantic check compares the whitespace-free forms.
- **Already installed Duo.** The binding policy moved to
  `MCD_BUILD_CONFIG_ORIGINAL_COPY_3`. Any Duo built earlier fails
  verification and must be rebuilt to receive the fix.

Validation:

- 12 new offline tests (`tests/test_product_name.py`): copy with its own
  name, digests and size preserved; legacy byte-for-byte identical; post-build
  tampering with the JavaScript, the name or the `Info.plist` hash detected;
  tampering between writing and recording refused before publication; six
  packages and four unreviewed file layouts refused; multiple blocks
  re-sealed; a write interrupted by a size limit and a non-writable directory
  leave the file intact, with no temporary file; unvalidated names
  refused; and source update with rebuild.
- The C writer, applied to the real `app.asar` of Claude 2.42304.0, was accepted
  by the experiment's independent Python verifier: 508 members, only
  `productName` changed, same size and 167 differing bytes.
- Real disposable build with the new code: source identity, nesting and
  Gatekeeper; Duo build, verification and nested signature;
  reservation of the default profiles; and critical source files unchanged. No
  app was opened and no real profile was used.

The Duo installed in `~/Applications` **was not rebuilt**. That is a
change to your system and is left to your decision.

## Web interface after sign-in (correction of October 17, 2026)

The [reopening](#reopening-and-log-comparison) compared only the **signed-out**
screen, and the conclusion that the name did not affect the Desktop experience
was wrong. Signed in with `Claude Duo`, the app showed web-version notices
("Experimente o Claude Code no desktop" (Try Claude Code on desktop), "Código
no seu celular" (Code on your phone)) and the window buttons over the title.

Cause, checked in the code:

- Electron 44.7.2 builds the User-Agent with the app name **without spaces**
  (`BuildApplicationUserAgent`, `RemoveChars(name, " ")`) and names the key
  `<name> Safe Storage`, with spaces. It also trims the `productName` (`trim`).
- claude.ai enables the Desktop interface with `claudeAppBindings` **and** a
  `claude/` token in the User-Agent (`/claude(nest|gov)?\/([^ ]+)/i`,
  `indexOf("claude/")`). `Claude Duo` produced `ClaudeDuo/2.42304.0`, which fails.

Fix: the `productName` became `<name> Claude` (`Duo Claude`), with
the token `DuoClaude/2.42304.0`, accepted by those checks, and the key
`Duo Claude Safe Storage`. An `includes(" Claude/")` check in claude.ai,
used on mobile and in a printing path, still differs from the original.
Full parity would require a name that, without spaces, is exactly `Claude`,
that is, with a space in the middle (for example `Claud e`). That option was
discarded for readability. The final confirmation is the signed-in interface
without the web notices.

## What remains before integrating

1. ~~Preserve the Desktop experience~~ **dropped on October 17, 2026, 22:07.**
   The suspicion of a different web page was not confirmed (see
   [reopening](#reopening-and-log-comparison)).
2. ~~Integrate checks into the production builder~~ **done on October 17, 2026.**
   See [integration into the builder](#integration-into-the-production-builder).
3. **Repeat launch, shutdown and rebuild**, including another architecture
   when the corresponding source is available. The real trials in this round
   are arm64. Ad-hoc signatures may trigger new prompts after rebuilds.
4. **Resume G01–G11 with the user**, starting with email sign-in, return to the
   correct app and the effective identity of Code. Simultaneous accounts,
   signing out of one account without affecting the other, and continuity have
   not been tested yet.

The [sanitized results](evidence/keychain-namespace-experiments.json)
separate observed facts from hypotheses. There is no protection against a
malicious process from the same user, nor any absolute security guarantee.

## Experimental tools

The scripts below only prepare new copies; they do not open applications, do
not install into Applications and do not import profiles or access the Keychain:

- [Product name preparation](../scripts/prepare-product-name-probe.py), with
  [limited ASAR change and verification](../scripts/asar_product_name.py).
- [Earlier experiment](../scripts/prepare-namespace-probe.py), whose reproduction
  requires `--reproduce-helper-only-failure` because the separation failed in
  the interface.

They are not commands of the versioned production toolset. Any new launch of
modified software or any new sensitive permission is reviewed at the time of
the action.
