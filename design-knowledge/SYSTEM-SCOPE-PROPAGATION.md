# System scope propagation — experimental

## Modules and contracts

- `model-core/SystemOntology.psm1`: versioned candidate aliases, independent of document titles, section numbers, handles and requirement IDs. Specific alarm, telephone, broadcast, alarm-power and security terms are recognized. Bare fire references, ordinary lighting and non-fire protection are not alarm identity. Unlisted terms remain unknown. Longest alarm-power wording is not counted twice as alarm and power.
- `SystemScopePropagation.psm1`: immutable overlay on automatic statements. Resolves exact section membership and original title/statement/paragraph terms into `SystemScopeCandidate`. Preserves matched raw term, UTF16 source offset/length, handle, snapshot, section/paragraph, inheritance evidence and conflicts. No statement type is changed. Only supplied section membership is used; no numbering-only parent inference or cross-column inheritance.
- `EvidenceAdmission.psm1`: preserves candidate arrays and status. Only a supported single-category candidate projects to the evidence category. It does not identify an installed network. Ambiguous/partial evidence keeps effective identity unknown. Reference child facets cannot adopt their host's system as the target's identity. All original admission and execution prohibitions remain.
- `SystemScopeInvestigation.psm1`: same registered project + same supported system-category candidate + relation/membership investigation + permitted evidence use. Only search directions and context support are produced. No device attributes, system membership, network IDs or connectivity are assigned.
- `EvidenceInvestigationAdapter.psm1`: routes scoped engineering questions through that gate; the old source-local path remains available and unknown is never a wildcard.

The runner supplies project registration from the already registered Golden project and records the user's same-project basis. This registration does **not** prove building/storey applicability. Same system category permits reviewing matching-system design/plan sources; it does not imply that two representations belong to the same installed network. Requirement status is never updated.

## Conservative interpretation

Explicit short titles are strongest. Direct statement terms can also support a topic candidate. A term only in another part of the same paragraph remains partial. Multiple categories, a switch against title context, or an unresolved reference with inherited scope stops simple inheritance. `23779` is a real alarm/broadcast example, used only in tests.

Search directions `system_drawing / plan_drawing` are derived from the missing relation/membership task. They are labeled task-derived navigation, **not** an explicit cross-drawing reference read from the statement. No concrete target file, sheet or region is selected. Relevance is system-topic relevance, not proof that each sentence answers the terminal relation question.

Known limitations: no inference from bare 'fire', no cross-fragment alias reconstruction, no unprovided ancestor/legend inference, partial paragraph context not admitted, ontology incomplete, no installed-system applicability evaluator. Ambiguous cross-system clauses remain blocked rather than merging networks.

## Running and results

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File design-knowledge/Read-SystemScopePropagation.ps1 -OutputDirectory <new-directory>
powershell -NoProfile -ExecutionPolicy Bypass -File design-knowledge/tests/Test-SystemScopePropagation.ps1
```

Final real outputs: `local_test_data/system-scope-propagation-validated-20260925/EW-0002.json` and `EW-0004.json`. Original snapshots and earlier candidate artifacts are retained. The runner records input SHA-256 and refuses an existing output directory.

EW-0004 still has 160 statements and 164 evidence records. Admission remains 124 supporting_candidate and 40 archived_only; no admissible or blocked main records are invented by the topic overlay.

| System candidate (single-category records) | supported_candidate | partial | Total |
|---|---:|---:|---:|
| fire_alarm | 13 | 7 | 20 |
| fire_phone | 4 | 0 | 4 |
| fire_broadcast | 7 | 14 | 21 |
| fire_alarm_power | 0 | 0 | 0 |

Separately: 9 multi-system ambiguous records; 110 unknown. Thus **54** records have scope evidence, but only **24** have a supported single-category projection. The effective category field is still unknown on 140 records, including partial and ambiguous cases. Zero power candidates is a result of this page and conservative aliases, not proof no power design text exists.

Primary source attribution (one strongest source per evidence): explicit section title 2; inherited section context 10; statement-local term 16; paragraph-only context 26; unknown 110. All supporting sources are retained, even when attribution selects one for counting.

| Fire requirement | Relevant | Not applicable | SearchScope | Support | Hint | Status unchanged |
|---|---:|---:|---:|---:|---:|---|
| phone_terminal_relation | 3 | 161 | 3 | 3 | 3 | missing |
| broadcast_relation | 6 | 158 | 6 | 6 | 6 | missing |
| logical_membership | 12 | 152 | 12 | 12 | 12 | partial |

Total 21 search scopes, 21 support candidates and 21 hints. Three supported category records are still archived-only due to unknown statement type. They receive no task permission. EW-0002 retains 89 unknown records and zero relevant pairs for all three fire tasks.

Scope review types on statements: system_scope_unknown 106, ontology_alias_unresolved 30, system_scope_ambiguous 9, multi_system_statement 9, inherited_scope_conflict 1 (overlapping reasons). Consumer mismatches use requirement_system_mismatch. Raw/normalized text remains unchanged.

Verdict: **useful_but_partial**. The knowledge now narrows system-category investigation, while actual diagram/plan evidence is still required for each Golden relation.

## Validation

All 35 offline regression suites passed. The final focused suite passed 558 checks, including a reproduced and fixed cross-section paragraph-context leak counterexample. Paragraph context is filtered by supplied section membership; it cannot import a neighboring section's system topic. The real page results were rerun after this guard and the counts above remained unchanged. No AutoCAD was invoked.
