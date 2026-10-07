# Sheet Scope real-snapshot validation — 2026-09-24

## Result and scope

39/39 ordinary frames resolved from closed probe geometry and composed INSERT transforms.
39/39 title blocks and drawing identities paired. Each row below has frame, title,
identity and WCS polygon resolved. No ordinary frame without title, title without
frame, duplicate drawing number, positive-area page overlap, or isolated-frame gap
above the documented diagnostic threshold was reported. This is not proof of
arbitrary drawing-layout coverage.

Source snapshot SHA-256:
`7360ADB34A4E0BACACD2768261FBB3E19835C07C65F9F4959F94BAE5751A249F`.
All four supplied probe hashes are pinned in `tests/sheet-scope-sample.json`.
All five source files were rechecked unchanged.

## Observed page identities

Region counts are supported associations across three overlapping conceptual levels,
not counts of unique text or complete design knowledge. Zero does not mean an empty page.

| Number | Observed title | Frame INSERT | Supported regions | Ambiguous regions |
|---|---|---|---:|---:|
| EW-0001 | 图纸目录 | 506D0 | 0 | 0 |
| EW-0002 | 电气施工图设计说明（一） | 50708 | 53 | 0 |
| EW-0003 | 电气施工图设计说明（二） | 50740 | 91 | 0 |
| EW-0004 | 电气施工图设计说明（三） | 50778 | 76 | 0 |
| EW-0005 | 电气施工图设计说明（四） | 507B0 | 85 | 0 |
| EW-0006 | 电气施工图设计说明（五） | 507E8 | 166 | 0 |
| EW-0007 | 图例表 | 50820 | 1 | 0 |
| EW-0008 | 线性表 | 50858 | 0 | 0 |
| EW-0009 | 人防设计说明（一） | 50890 | 92 | 0 |
| EW-0010 | 人防大样图（一） | 508C8 | 0 | 0 |
| EW-0011 | 人防大样图（二） | 50900 | 0 | 0 |
| EW-0012 | 人防大样图（三） | 50938 | 0 | 0 |
| EW-0013 | 强电干线系统图（一） | 50970 | 0 | 0 |
| EW-0014 | 强电干线系统图（二） | 5098C | 0 | 0 |
| EW-0015 | 配电箱系统图（一） | 509C4 | 0 | 0 |
| EW-0016 | 配电箱系统图（二） | 509FC | 0 | 0 |
| EW-0017 | 配电箱系统图（三） | 50A34 | 0 | 0 |
| EW-0018 | 配电箱系统图（四） | 50A6C | 0 | 0 |
| EW-0019 | 配电箱系统图（五） | 50AA4 | 0 | 0 |
| EW-0020 | 配电箱系统图（六） | 50ADC | 1 | 0 |
| EW-0021 | 配电箱系统图（七） | 50B28 | 0 | 0 |
| EW-0022 | 配电箱系统图（八） | 50B2F | 0 | 0 |
| EW-0023 | 配电箱系统图（九） | 50B36 | 0 | 0 |
| EW-0024 | 配电箱系统图（十） | 50B3D | 0 | 0 |
| EW-0025 | 配电箱系统图（十一） | 50B44 | 0 | 0 |
| EW-0026 | 配电箱系统图（十二） | 50B4B | 0 | 0 |
| EW-0027 | 配电箱系统图（十三） | 50B52 | 0 | 0 |
| EW-0028 | 配电箱系统图（十四） | 50B59 | 0 | 0 |
| EW-0029 | 配电箱系统图（十五） | 50B60 | 0 | 0 |
| EW-0030 | 配电箱系统图（十六） | 50B67 | 0 | 0 |
| EW-0031 | 配电箱系统图（十七） | 50B6E | 0 | 0 |
| EW-0032 | 配电箱系统图（十八） | 50B75 | 0 | 0 |
| EW-0033 | 配电箱系统图（十九） | 50B7C | 0 | 0 |
| EW-0034 | 配电箱系统图（二十） | 50B83 | 0 | 0 |
| EW-0035 | 配电箱系统图（二十一） | 50B8A | 0 | 0 |
| EW-0036 | 配电箱系统图（二十二） | 50B91 | 0 | 0 |
| EW-0037 | 配电箱系统图（二十三） | 50B98 | 0 | 0 |
| EW-0038 | 配电箱系统图（二十四） | 50B9F | 0 | 0 |
| EW-0039 | 配电箱系统图（二十五） | 50BA6 | 0 | 0 |

## Three acceptance pages

| Page | WCS bounds: minX, minY → maxX, maxY | Text acceptance | Column segments |
|---|---|---|---:|
| EW-0002 | (28912.216786,228819.528358) → (113012.216786,288219.528358) | 23428 / 4.12.1 supported | 10 |
| EW-0003 | (113012.216786,228819.528358) → (197112.216786,288219.528358) | 23471 / 8.3 supported; not EW-0002 | 17 |
| EW-0004 | (197112.216786,228819.528358) → (302212.216786,288219.528358) | 234DB / 10.1.15 and section fragments including item 8 supported | 20 |

These are actual transformed polygon bounds, not dimensions inferred from paper names.
Source paragraphs and hierarchy remain unchanged.

## Association counts

* DesignTextRegionCandidate: 141
* SectionCandidate: 423
* Reviewed LegendRegion: 1
* Combined: 565 supported, 0 partial, 0 ambiguous, 0 outside, 0 unresolved
* Raw text associations: 13,165 supported; 831 partial (fallback); 11 outside
* ColumnScopeCandidate: 141 existing column segments scoped to one page
* New sheet-layer ReviewItems: 0
* Cover 2413C: excluded/unresolved

No observed crossing was required to exist in this fixture. Synthetic tests verify
boundary contact and multi-page ambiguity. A zero new sheet-review count does not
clear upstream Reader/Hierarchy reviews or certify semantic correctness. The 831
partial text records remain in the output; fallback is not full bbox confirmation.
The 11 outside text records are not silently deleted.

Column segments are not physical-column counts. Split segments separated by tables,
spacing or other reader evidence are preserved; no automatic across-column sequencing.
The lone section candidate on EW-0020 is a spatial assignment, not confirmation that
the source reader correctly classified that text as design prose.

## Tests

* Final sheet suite: 71 checks passed (21 controlled plus 50 real-sample checks).
* Existing offline regression suites: 28/28 passed.
* Combined coverage: 29 suites including the new sheet suite.
* Existing key suites: geometry 920; evidence 52; context 63; prototype 94;
  Discovery passed; hierarchy 41; bbox continuity 20.
* No AutoCAD invoked. No source reports or DWGs changed. Existing Discovery artifact
  restored by the regression harness.

## Capability and next boundary

sheet_frame_resolution = validated_sample (39 instances, two definition paths).
sheet_identity_resolution / region_to_sheet_association / column_scope_resolution =
experimental. None promoted to reusable.

The spatial prerequisite for a first candidate-only EW-0002 page extraction is met.
Unattended complete-page learning is not established: physical-column consolidation,
reading across column segments, paragraph completeness and semantic review still need
explicit treatment. This run does not perform that extraction.

