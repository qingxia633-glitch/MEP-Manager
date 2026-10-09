# Paragraph coverage (experimental)

Run from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File design-knowledge/Read-ParagraphCoverage.ps1 -DrawingNumber EW-0002 -OutputPath <new-output.json>
```

The manifest pins the snapshot and supplied frame probes. The sheet must have a unique supported identity. Texts are clipped by the actual sheet polygon before either Reader run; bbox crossings remain exclusions, not majority-area assignments. Existing outputs are protected.

`Find-DesignStatementCandidates -LayoutAware -CoverageClosure` is opt-in. The default Reader and LegacySpacing behavior remain available for regression and same-code comparisons. The original long-text population estimates spacing; the coverage mode then admits short text and short numbered headings into the layout evaluation pool, excluding detected grids and attributes. A short continuation still needs spacing, column/indent compatibility, font height and style compatibility, unfinished previous text, closing punctuation, and no separator. Missing bbox falls back to insertion geometry; missing font evidence does not silently become known compatibility. Independent short headings remain structural fragments.

No new semantic splitting rules are used. Raw text, including drawing typos, stays unchanged. `empty_atomic_candidate` records the existing splitter's blank outputs without correcting them.

## Output

- `ParagraphCoverageCandidate`: complete raw-record accounting, not a claim of complete understanding.
- `RawTextDisposition`: one record per source text, with sheet, candidate column, paragraph/structure references, source text, evidence, status and reasons. An empty column list explicitly means unresolved column scope.
- `CoverageGapCandidate`: unresolved body role or hierarchy-referenced body with no paragraph.
- `Paragraph.termination`: reason, next candidate and rejection evidence. Rejected observations remain candidate evidence, not known document endings.
- Before/after Readers and per-column hierarchy are retained. No cross-column reading, formal Evidence admission, Circuit, or quantity is generated.

Table classification is a geometric candidate; it is not semantic cell extraction. MTEXT remains raw/unresolved for body interpretation. Legend disposition requires supplied legend evidence. Attached attributes are called title-block metadata only when their parent is the resolved title block. Other attributes remain excluded from body with a reason.

Current limitations include unfinished long-body coverage, conservative short suffix evidence requirements, ambiguous column scope, structural hierarchy completeness, and the existing atomic splitter. These capabilities remain experimental.
