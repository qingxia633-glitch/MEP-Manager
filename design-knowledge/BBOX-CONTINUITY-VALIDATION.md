# TEXT bbox continuity: real snapshot comparison

Date: 2026-09-24. Same current reader for both runs; no AutoCAD invocation or semantic-model changes.

## Inputs

- B1: `system-t8t3-verified-snapshot-20260916`, SHA-256 `FC8E11D7678EDFFA06F5878155A577FC0E14EC8F932CA74AAE98ED4105C37C11`.
- B2: `system-t8t3-textlayout-snapshot-20260924`, SHA-256 `7360ADB34A4E0BACACD2768261FBB3E19835C07C65F9F4959F94BAE5751A249F`.
- Both are `MEP-full-entity-report.txt` under `local_test_data` and retain their original hashes.
- Run: `powershell -NoProfile -ExecutionPolicy Bypass -File design-knowledge/tests/Compare-BBoxContinuity.ps1`.

## Metrics

| Metric | B1 | B2 |
|---|---:|---:|
| Design text regions | 141 | 141 |
| Paragraph candidates | 368 | 369 |
| High-confidence reading orders | 243 | 249 |
| ReviewItems | 319 | 325 |
| Paragraphs evaluating available TEXT bbox evidence | 0 | 364 |
| Paragraphs accepting a bbox-based insertion-corridor extension | 0 | 10 |
| Accepted transitions across a detected separator | 0 | 0 |

Ten paragraphs changed membership (including one newly recovered candidate). Twelve changed membership or ending decisions in total. Qualitative assessment: ten `evidence_improved`; two `conservative_split` (more conservative boundary decisions, **no member removal**). No regression candidate was observed in the inspected changes; this is not an accuracy estimate.

Review reasons: paragraph boundary uncertainty 125 -> 120; bbox continuity review 0 -> 10; condition scope uncertainty 63 -> 64. Unchanged: region scope 105, numbering anomaly 4, multiple reference targets 6, remainder set 6, formatted text 9, rotation coverage 1.

## Known paragraphs

- `23428 -> 23401 -> 23402`: unchanged, high confidence.
- `23471 -> 23472 -> 23473 -> 23474 -> 23475`: unchanged, high confidence.
- `234DB`: B1 ends at `23772`; B2 yields `234DB -> 23771 -> 23772 -> 23773 -> 23774`.
- `23772 -> 23773`: overlap with both prior line and provisional column is 1, horizontal gap 0, compatible pitch/font, unfinished previous text, lexical continuation, no new section number or detected separator. The old insertion-X test fails; the added evidence permits continuation.
- The next independent numbered section is not swallowed. However, `23775` (subitem 3) remains excluded by the existing paragraph-boundary logic. This is **not** complete recovery of section 10.1.15; high confidence is the existing reading-order label, not section-completeness certification.

## Fixed-seed changed-paragraph inspection

Seed `20260924`, ten sampled changed-decision paragraphs; this run selected ten non-target paragraphs. Two have unchanged members but changed bbox-dependent separator decisions. The other changed member lists, including the known target, were also reviewed.

| Anchor | Observed change | Assessment |
|---|---|---|
| 234BF | Same members; spacing stop becomes separator stop | conservative_split; no text removed |
| 478BB | Restores 478BC between 478BB and 478BD | evidence_improved; restores missing LED sentence beginning |
| 234C7 | Adds 23768, 23769 | evidence_improved; continuation after unfinished text |
| 233A1 | Adds 23765 | evidence_improved; completes pump-stop statement |
| 234C8 | Adds 233DA | evidence_improved; completes shutter-control clause |
| 234D1 | Adds 23616 | evidence_improved; joins split word and continuation |
| 234C9 | Recovers 237F9, 237FA, 237FB beneath heading | evidence_improved; new paragraph candidate |
| 236E3 | Adds 237FD | evidence_improved; restores statement below heading |
| 233CE | Adds 233CF | evidence_improved; joins split word |
| 23416 | Same members; numbered stop becomes separator stop; high -> medium | conservative_split; no text removed |

The 23416 bbox-center transition intersects actual horizontal geometry, including `490C5`, `490C4`, `490D1`. No inspected accepted continuation crosses a detected table/column separator or admits an ATTRIB title-block fragment. Geometry coverage remains limited to the reader's supported boundaries.

## Limits and conclusion

Final validation: all 27 offline regression suites passed. The bbox continuity suite passed 20 checks, including the real target, both original golden paragraphs, rejected-extra-candidate boundary preservation, geometry/title/numbering counterexamples, missing-bbox fallback and transformed controlled input. These are offline checks, not new AutoCAD runtime acceptance.

`bbox_reader_value = useful_but_partial`.

TEXT bbox now affects actual decisions. MTEXT/ATTRIB bbox handling, semantic types, raw snapshots and engineering outputs are unchanged. Missing bbox retains the legacy position/spacing/numbering/separator path.

The principal remaining limitation is list/subitem paragraph boundaries and completeness: a recovered continuation does not prove that all subitems belong to or have been captured in the paragraph. Full-page automatic knowledge extraction is not yet justified by this experiment.
