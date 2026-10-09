# Hierarchy / Paragraph bridge (experimental)

This is an additive, bounded second pass over an existing page Coverage result. It evaluates only gaps with a hierarchy source. General `body_role_unresolved` records are copied unchanged. It neither reruns the semantic parser nor modifies existing paragraphs, raw records, section numbering or section completeness.

Run offline:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File design-knowledge/Read-HierarchyParagraphBridge.ps1 -OutputPath local_test_data/new-bridge-result.json
```

The input defaults to the frozen EW-0002 coverage result. A different coverage result can be supplied with `-InputPath`. Output refuses overwrite and records the input SHA-256. This is a candidate overlay; it is not a formal Evidence import.

## Decision boundary

`HierarchyParagraphBridgeCandidate` retains raw reference/text, sheet, column, section/subitem references, neighboring texts, bbox, font, original reader decisions and earlier paragraph termination diagnostics. An absent direct rejection means the original Reader never reached that fragment; it is not an inferred per-fragment error.

Admission requires one compatible text column, hierarchy/column agreement, supported subitem/sibling structure or a conservatively bounded independent labelled sentence, spacing and font compatibility, and no grid/geometry separator. Multiline subitems are admitted together or remain unresolved. Geometry controls order, not Handle order.

Pure numbered structural labels with supported hierarchy/layout can retain `structural_fragment` and `paragraphNotRequired=true`. Other text is never excluded merely because it lacks a paragraph. Remaining body gaps use `hierarchy_paragraph_coverage_gap`.

The current implementation is conservative when bbox/font is unavailable, parents are multiple, a multiline item overlaps already-covered fragments, or an unfinished predecessor lies outside the allowed gap set. Such cases remain unresolved. Existing Reader fallback behavior is unchanged.

## Real page result

Source scope: EW-0002 from the v2.3 snapshot. Baseline: `ew0002-coverage-final-20260924.json`, SHA-256 `C6F3607FC976F298230344F64E89CD8A8E04E48CB363B83C60EF5E334F8F00B9`.

| Metric | Before | After |
|---|---:|---:|
| ParagraphCandidate | 38 | 46 |
| TEXT paragraph members | 97 | 106 |
| Original hierarchy gaps | 11 | 2 |
| General unresolved body gaps (unchanged) | 45 | 45 |
| Total coverage gaps | 56 | 47 |
| Sections without observed coverage gaps | 33/38 | 35/38 |
| Coverage ReviewItems, including four empty atomics | 60 | 51 |

Section coverage is not structural completeness. Hierarchy and its existing completeness assessments are unchanged. The 390 TEXT dispositions become 106 paragraph members, 11 structural section titles, 226 table records and 47 unresolved records. The 34 ATTRIB remain title-block metadata.

Nine fragments form eight additional paragraphs: `478C2`, `478C3`, `478C4`, `478C5 + 478C6`, `478C7`, `478BE`, `23406`, `23407`. No current gap was a pure structural label. `23405` still needs its unfinished predecessor `23363`, which is outside this stage. `236A4` remains independently reviewable prose with multiple section references (6.5 / 6.5.1); these nested references are not a semantic contradiction, but the conservative bridge does not resolve their ownership.

All original paragraphs and their atomic candidates are unchanged. New paragraphs have `semanticStatus=not_processed`, empty atomic/condition/reference arrays. No additional DesignStatement claim is made. Raw text and structural references remain available for the next bounded Paragraph / Hierarchy to DesignStatement stage.

See `HIERARCHY-BRIDGE-AUDIT.md` for the eleven-fragment audit and `local_test_data/ew0002-hierarchy-bridge-validated-20260924.json` for full provenance and layout evidence.

Verdict: `hierarchy_paragraph_bridge = useful_but_partial`. Stop expanding Paragraph recovery on this sample; preserve the two outstanding structural-body gaps and the untouched 45 general gaps for downstream requirements/review.

## Verification

All 31 offline regression suites passed. The final bridge implementation passed 106 dedicated checks, including immutable general dispositions and existing paragraphs, multiline subitem order, retained scope dependency, pure-number non-paragraph classification, hierarchy/column disagreement, font, separator, grid and ATTRIB rejection. No AutoCAD was invoked. Source snapshot and frozen coverage baseline hashes were rechecked unchanged. No observed regression in the protected golden paragraphs; this is bounded sample validation, not a general accuracy claim.
