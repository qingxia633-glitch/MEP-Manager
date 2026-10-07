# EW-0002 coverage acceptance

Snapshot: `7360ADB34A4E0BACACD2768261FBB3E19835C07C65F9F4959F94BAE5751A249F`.
Input sheet: supported EW-0002 identity and actual frame polygon, not filename or fixed coordinates.
Result: `local_test_data/ew0002-coverage-final-20260924.json`.

Same-version baseline versus opt-in CoverageClosure:

| Metric | Before | After |
|---|---:|---:|
| Paragraphs | 34 | 38 |
| Raw TEXT paragraph members | 81 | 97 |
| Nonempty Atomic candidates | 71 | 78 |
| Reader review records | 26 | 24 |

After: 390 TEXT = 97 paragraph members + 11 structural titles + 226 grid candidates + 56 unresolved body candidates. All 34 attached title-block attributes remain metadata. No MTEXT in this page. No source is silently discarded.

38 sections: 33 covered by existing paragraphs, 5 with incomplete paragraph coverage. This metric is not section completeness. Nine subitems remain; the two Chinese major headings are no longer falsely treated as subitems. The earlier page-only audit had 35 sections and 11 subitem candidates; the two removed items were these headings.

Four targeted short suffixes recovered: 6066C, 23609, 2380B, 23436. They extend existing atoms, adding zero atom count. Four new body paragraphs account for seven additional nonempty atoms. The 23418/23419/2341A/23627 chain is now a paragraph. Golden 23428/23401/23402 and 2341E/2341F/23420 remain intact. 23471 and 234DB are excluded before Reader input.

56 gaps remain: 45 unresolved body roles and 11 hierarchy-referenced body fragments without paragraph coverage. Four empty Atomic candidates remain unchanged, each with an explicit quality review. There are 24 Reader, 32 hierarchy and 60 coverage review records; these categories overlap in root cause and are not an error rate.

## Fixed-seed non-fixture inspection

Seed 20260924. Population: previously non-paragraph fragments newly classified as paragraph members or structural titles. Exclude the explicitly requested suffix/4.8/Chinese-heading acceptance handles. Sort by handle, then PowerShell `Get-Random -SetSeed 20260924 -Count 10`; population 17.

| Handle | Classification | Observation |
|---|---|---|
| 23361 | evidence_improved | 4.1 title leads a bounded paragraph; later requirements still unresolved |
| 23408 | evidence_improved | 4.2 title and adjacent body recovered, not an assertion of complete section |
| 23806 | correct_structural_classification | 4.6 remains a title, no forced body paragraph |
| 6E168 | correct_structural_classification | isolated 1.2 title retained |
| 237FF | evidence_improved | short closing continuation of preceding text |
| 6E169 | correct_structural_classification | isolated 1.3 title retained |
| 23413 | correct_structural_classification | 4.5 title retained |
| 23362 | evidence_improved | paragraph body with preserved source and closing fragment |
| 2361D | evidence_improved | body below 4.2, continued by 2361E |
| 232F8 | correct_structural_classification | major heading remains separate |

Five evidence improvements and five structural classifications; no observed cross-column/grid/title-block merge in this sample. This is qualitative inspection, not accuracy. Remaining long-body omissions, conservative stops and hierarchy-to-paragraph gaps prevent a complete-page claim.

Verdict: `paragraph_coverage = useful_but_partial`. The next bounded target is remaining same-column hierarchy/body coverage, not cross-column reading or semantic expansion. All four coverage capabilities stay experimental.

## Verification

Final coverage suite: 31 checks passed (18 controlled, 13 real-page assertions). The complete regression runner passed all 30 offline suites; the final coverage suite was also rerun independently after the last coverage adjustments. Existing sheet (71), layout (21), bbox (20), hierarchy (41), reader (39), design statement (76), design knowledge (269), geometry (920), tray evidence (52), prototype (94) and Discovery checks passed. No AutoCAD invoked. The source snapshot SHA-256 remains unchanged. The regression runner restores the legacy Discovery output artifact after testing.
