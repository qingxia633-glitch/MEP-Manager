# Evidence investigation adapter — experimental

## Contract

`EvidenceInvestigationAdapter.psm1` consumes admitted evidence and task descriptors `{requirement, context}`. It emits `SearchScopeCandidate`, `RequirementSupportCandidate`, `InvestigationHint`, evaluations and grouped ReviewItems. It never calls the ModelCore requirement resolver or modifies a supplied requirement. Rule matching is an InvestigationHint with `ruleApplied=false`.

Every pair is checked for discipline, system, object, scope, permitted use, admission and conflict/provenance state. Failure is `not_applicable`, normally a filter result, **not proof that the underlying design statement is engineering-irrelevant**. Each check and reason is saved. No keyword, common discipline, page title or proximity can substitute for these checks.

Current external Golden requirements lack a validated semantic applicability mapping to EW-0002. All EW-0002 Evidence have unknown system identity and unresolved applicability. This version therefore does not generate external-task support. It does not manufacture known discipline/object/system metadata to make the tests pass.

## Source-local follow-ups

`New-SourceInvestigationTask` derives questions directly from existing references and qualitative-length conditions. These are not new manually invented installation cases. Source-local tasks bind one exact evidence ID, statement, snapshot and sheet and can ask only about that record's reference target or qualitative length threshold.

Unknown system is allowed here only as **no network inference**: the subject is the source record itself. It cannot act as a wildcard for a named system, building, other sheet, or equipment instance. The adapter preserves unknown identity and does not assign SystemIdentity. A local task disguised as fire_alarm is rejected.

Search scopes preserve requirement/evidence/statement/section/paragraph/sheet/raw span trace. Target documents/regions are unresolved candidates, target sheets are never inferred from filenames, and source sheet is not misrepresented as a resolved target sheet. Missing parameter directions may have no known target document type. Existing reference boundary uncertainty remains in blocking reasons.

Support types: `narrows_search`, `defines_expected_information`, `indicates_reference`, `indicates_condition`, `indicates_missing_parameter`, `conflicting_support`. Conflict support is a blocked diagnostic only, produces no search authorization, and never satisfies a requirement. Reviews group by requirement and reason; routine filtered pairs do not become automatic requests for human action.

## Entry point

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File design-knowledge/Read-EvidenceInvestigation.ps1 -OutputPath <new-file.json>
powershell -NoProfile -ExecutionPolicy Bypass -File design-knowledge/tests/Test-InvestigationAdapter.ps1
```

Input: `local_test_data/ew0002-evidence-admission-final-20260925.json`.
Input SHA-256: `BC9A8513AC5ACD488E3FDD550640B86359DB3609FC37D7F7E1E951FF20D20FE1`.
Output: `local_test_data/ew0002-evidence-investigation-20260925.json`.
The runner reads the existing GoldenSample and FireGoldenSample adapters and selects the six tasks specified by the user; it does not create new engineering relationships. Existing output paths are protected.

## Real results

| Population | Pair evaluations | task_relevant | not_applicable | Search scopes | Support candidates | Hints |
|---|---:|---:|---:|---:|---:|---:|
| 89 evidence x 6 existing Golden requirements | 534 | 0 | 534 | 0 | 0 | 0 |
| 89 evidence x 5 source-local follow-up tasks | 445 | 5 | 440 | 5 | 12 | 7 |

The five relevant pairs involve five distinct evidence records. No one of the 89 evidence records is currently permitted to support the six Golden requirements. Local results must not be presented as Golden-task improvement.

Golden statuses remain: individual_pump_mapping **missing**, physical_routing **missing**, procurement_boundary **missing**, phone_terminal_relation **missing**, broadcast_relation **missing**, logical_membership **partial**. No status is changed to satisfied.

Source-local results:

- `见表4.1` -> target-name candidate 表4.1; document type unresolved.
- `见系统图）` -> system_drawing candidate; raw target name remains 系统图）; boundary uncertain. No specific system drawing is selected.
- `详见表6.1` -> target-name candidate 表6.1; document type unresolved.
- 4.12.1 short/long line conditions -> two `length_classification_threshold` missing-parameter hints. No physical length comparison.
- The same two admitted requirements -> two rule-matching investigation hints, not rules applied to breakers.

Supports: 3 narrows_search + 3 indicates_reference + 2 defines_expected_information + 2 indicates_condition + 2 indicates_missing_parameter. Hints: 3 target-unresolved + 2 condition-definition + 2 rule-match. A real conflict is not present in this batch; counterexample tests verify the blocked conflicting_support path.

Verdict: **limited** for existing engineering tasks; useful bounded navigation within the source document. The next gap is traceable task-to-statement applicability and scope mapping. This must be resolved before connecting DeviceRole, SystemIdentity or instance tasks; broader keywords would not resolve it.

## Validation — 2026-09-25

- All **34 offline regression suites passed**, without AutoCAD.
- Final investigation-specific tests passed **44 checks**: real tasks, exact-source navigation, requirement/evidence immutability, denied admission, conflict diagnostics, foreign sheet, unknown-system isolation, multiple targets and threshold-kind filtering.
- Both saved result populations match a fresh run of the final adapter. The input evidence artifact SHA-256 remains unchanged.
- Output SHA-256: `690B007F442B4F12D87D9B1ADC871CAAD6E42077BD7427F0D0D8E206F9417DD3`.
