# Document target resolution - experimental

## Scope and files

`DocumentTargetResolver.psm1` consumes InformationRequirements, existing admitted SearchScopes and a registered document inventory. It does not access DWG files. `Read-DocumentTargets.ps1` reads these JSON inputs and optionally writes a new protected result. It does not change a requirement, choose/open a file, or resolve any design reference.

`reference/electrical-document-inventory-20260925.json` contains 44 file metadata records from the previously investigated electrical source directory. The old file roster was not persisted in this checkout, so names, paths, sizes and UTC modification times were refreshed by directory enumeration only. No new DWG bytes, header or graphics were read. The two registered snapshot sources were matched by their existing report headers; the partial fire Golden review and EW-0002/EW-0004 review do not mean the entire DWG has been understood. `not_registered_read` means absent from this bounded registry, not proof the file has never been opened by anyone.

## Contract

Each DocumentTargetCandidate preserves requirement/search/evidence references, the original inventory document record, filename type and system matches, expected evidence and gap type, read coverage, version-family candidates, supporting/contradicting signals, rank, status and full source SearchScope provenance down to statement/raw spans.

Type candidates: design_notes, legend, system_diagram, plan, riser/mainline_plan, detail, schedule, unknown. Composite filenames retain all matches. Their primary type is a conservative vocabulary choice; notes mentioning a system do not get promoted to system diagrams. No type is content-verified by its filename.

Broad fire/weak-current filename wording is a **document navigation lead**, not assignment of all those systems to file contents. SearchScopes must match the requirement's registered project and canonical system and retain raw spans. Unknown is not a wildcard. Missing source-directory registration leaves region applicability unresolved. Directory equality is only an investigation-scope candidate, never cross-DWG coordinate or building-position proof.

## Ranking policy

The experimental additive weights are inspectable heuristics, not probabilities or measured accuracy:

- Exact system wording or previously reviewed system evidence in a version family: +3; broad fire/weak-current wording: +1; adjacent explicit fire system: 0.
- Same source directory context: +2.
- Missing relation: system diagram +6, mainline/riser +3, plan/detail +2, schedule +1, notes/legend +0.
- Missing logical membership: system diagram +6, mainline/riser +4, plan +2, detail/schedule +1, notes/legend +0.
- A controlled physical-layout counterexample instead favors plan +6 and mainline +5 over system diagram +2. It only changes search priority; no route is generated.
- Type already suggested by SearchScope: +1.
- Unreviewed family: +1 as potential new evidence. A family with existing partial review: -1, because the requirement remains open. This penalty does not assert that an unread sibling has the same contents.

No date, file size, full drawing name, Handle, chapter, or task ID is a ranking key. Equal scores receive equal ranks. Display order within ties does not establish precedence. High score alone cannot promote an adjacent-system or broad weak-current lead beyond possible_candidate.

Trailing `_t<number>` tokens only form possible version families within the same directory. This neither orders revisions nor transfers content facts between files. Family coverage is used only to estimate review novelty and is explicitly sourced. Exact-file read status remains separate. Unresolved version peers prevent unique preferred_candidate selection. Even a preferred candidate would remain unverified and would not be opened automatically.

## Real Fire Golden result

Output: `local_test_data/fire-document-targets-20260925.json`. 44 documents x 3 independent requirements = 132 evaluated records: 12 supported_candidate, 18 possible_candidate, 102 unresolved, zero unique preferred_candidate. Each task has ten ranked files (five two-version families); the remaining 34 lack adequate scope/type/topic evidence.

Both `_t8` and `_t8_t3` stay tied for every family below:

| Document stem | Phone relation | Broadcast relation | Alarm membership |
|---|---:|---:|---:|
| EX-BX地下车库弱电消防系统图 | 1 (11) | 1 (11) | 1 (11) |
| EX-BX地下车库消防干线平面图 | 2 (8) | 2 (8) | 2 (9) |
| EX-BX地下车库火灾报警平面图 | 3 (7) | 4 (4) | 3 (7) |
| EX-BX地下车库弱电平面图 | 3 (7) | 3 (7) | 3 (7) |
| EX-BX地下车库说明及配电箱系统 | 4 (4) | 4 (4) | 4 (4) |

Parentheses contain heuristic scores. The common first choice is a **family**, not a resolved revision or reference target. Fire alarm plan registration has alarm/phone local evidence but does not establish broadcast coverage; this accounts for the lower broadcast ranking. The known design notes remain low-priority context, including their EW-0002/EW-0004 reviewed pages.

Expected investigation:

- Phone: endpoints, telephone system relationships and plan corroboration.
- Broadcast: broadcast control/zones/endpoints and their relationships, with plan corroboration; these are questions to investigate, not presumed file contents.
- Alarm membership: loop identity, system topology and device membership.

Requirement states remain missing / missing / partial. The three tasks remain independent even where targets coincide. No actual document is selected, no requirement is satisfied and no connection/network/quantity is produced.

ReviewItems: multiple_document_candidates 3; document_type_uncertain 3; version_relationship_unresolved 51 (17 inventory families independently associated with three tasks); candidate_not_yet_read 3. The wider inventory uncertainty is retained, not a request to manually inspect all those documents. The five ranked families are the actionable subset. `expected_evidence_type_uncertain` is supported for unrecognized task gaps.

## Reproduce

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File design-knowledge/Read-DocumentTargets.ps1 -OutputPath <new-json-path>
powershell -NoProfile -ExecutionPolicy Bypass -File design-knowledge/tests/Test-DocumentTargets.ps1
```

Verdict: **useful_but_partial**. Ranking narrows the next document family. Filename-only scope, opaque filenames, actual content and unresolved revisions prevent a unique verified target. No new DWG content was read.

## Validation

The final focused suite passes 700 checks: real inventory results, full raw provenance, independent requirements, unchanged states, revision/date/size neutrality, input order independence, arbitrary filename prefixes, exact ontology terms, type/gap-dependent ranking, unknown and mismatched systems, security isolation, foreign projects, missing spans, missing source registration and unrecognized evidence needs. A high score cannot promote an explicitly different system to a high-support target. The final code reproduces the saved targets, requirement summaries and reviews exactly.

All 36 offline regression suites passed. No AutoCAD was invoked. The existing readers, admission/consumption, system isolation, probes, geometry and first/second Golden model regressions passed alongside the new module.
