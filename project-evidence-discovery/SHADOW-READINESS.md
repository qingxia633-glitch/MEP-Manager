# Leader Shadow readiness contract

Scope: report acquisition / adapter / Discovery candidates only. No semantic
authorization, quantity, new CAD acquisition, or MLEADER capability expansion.

## Contract and invariants

- Generic `resolve.py --snapshot` / `discover(context)` remain research paths.
  Caller-supplied JSON and its integrity labels are not authentication.
- Current `resolve.py --shadow --snapshot REPORT --manifest MANIFEST --project-id PROJECT` calls
  `discover_shadow`: only report paths, actual byte verification, then Discovery.
  Historical electrical Shadow scripts are frozen research artifacts, not this
  verified Leader entry and are not rewritten or executed.
- Manifest v2 hash_scope is exactly `exact completed report bytes`. SHA-256,
  byte length, strict encoding, extracted report identity, version and report
  basename must match. Filename strictness is intentional; a renamed report
  requires separately created metadata. Moving an unchanged basename is allowed.
  This is integrity checking, not signature or semantic authorization.
- Binding identity includes project, drawing, complete object paths and handles,
  method, annotation and target identity. Report paths/hash/verification state
  remain provenance and do not participate in binding IDs.
- Shared validation selects the same full annotation identity Discovery uses.
  Classic v1 requires explicit drawing/project/path keys, top-level scope,
  TEXT/MTEXT and decode status `read`. Generic research may explicitly use a null
  project; the verified Shadow entry requires a nonblank string project_id.
- Conflicting duplicates produce no supported binding, conflicting evidence/root,
  and `annotation_conflict`. MLEADER remains unresolved.

## Failure and acceptance

Missing/foreign identity, unsupported type/version/scope, unknown decoding,
conflicting annotations or invalid manifest fail closed at the relevant entry.
Tests directly exercise Discovery and the verified bytes entry. Prior tests and
fixtures remain unchanged. Raw historical failures are never counted as passes.
The ledger requires exactly the registered 14 failures; unexpected pass, skip,
missing test, or new failure blocks acceptance. Category C preserves its review
origin; the new explicit diagnostic regression test proves current remediation.
An old assertion indexing a binding that is correctly absent remains a raw error.
Current acceptance uses `legacy-failure-ledger-v2.json` and `check_current` / the
checker CLI: test IDs AND normalized reasons/categories must match. The v1 ledger
and ID-only helper remain historical compatibility artifacts, not current acceptance.
See [Final entry contract](FINAL-SHADOW-ENTRY.md) for collision and zero-result rules.

Acceptance also includes private project tests, exporter static checks, TextLayout,
CP936/escapes, saved real classic MTEXT chain, Test 15 and pinned hash inventories.
Original CRLF Test 15 and isolated Git-canonical fixture results are reported
separately. No historical fixture is normalized in place.

## Deferred backlog

- L4: non-top-level TEXT/MTEXT documentation.
- L5: ATTRIB raw/decoded/serialized model.
- L6: direct-context decoded/raw derivation validation.
- L7: further actual exporter escape samples.
- L8: Chinese encoding sentinel (ASCII bytes cannot establish intended encoding).
- L9: annotation-index profiling.
- L10: edge-summary profiling/complexity; no unmeasured refactor.
- L11: wider filename portability policy. Current strictness is documented above;
  hash_scope validation is implemented in this pass.

Real AutoCAD support is limited to the previously saved classic LEADER→MTEXT
sample; revalidation does not constitute a new AutoCAD run or project approval.
