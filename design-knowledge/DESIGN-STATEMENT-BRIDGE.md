# Automatic DesignStatement bridge — experimental

## Scope and modules

`ParagraphSemantics.psm1` is the existing Reader's semantic loop extracted to a shared entry point. Sentence splitting, offsets, conditions, exception/reference signals and Atomic generation rules are unchanged. `DesignStatementReader.psm1` calls that entry point. It also processes all 46 already accepted EW-0002 Paragraphs, including the eight hierarchy-bridge additions, without rerunning layout or admitting unresolved body fragments.

`DesignStatementBridge.psm1` converts nonempty atomics through the existing `New-DesignStatementCandidate` constructor. No fixture adapter is imported. Raw spans, paragraph, column, section/subitem candidate references, sheet identity and upstream SHA are retained. No statement is an EngineeringObject property, formal Evidence, RuleReference, QuantityRule or connection.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File design-knowledge/Read-DesignStatementBridge.ps1 -OutputPath local_test_data/new-statement-candidates.json
```

The input defaults to `ew0002-hierarchy-bridge-validated-20260924.json`; `-InputPath` accepts an equivalent candidate result. Existing outputs are protected. Canonical acceptance result for this stage: `local_test_data/ew0002-design-statements-reviewed-v2-20260924.json`.

## Trace and status contract

Every statement includes `sheetId`, `drawingNumber`, `columnScopeRef`, `sectionRef[]`, `subItemRef[]`, `paragraphRef`, `atomicRef`, `sourceSpanRefs[]`, `sourceEntityHandles[]`, exact `rawText`, `normalizedTextCandidate`, `statementType`, `statementStatus`, `semanticCompleteness`, `applicabilityScope`, and `qualityEvidence`. The output span registry validates UTF-16 offsets against upstream raw TEXT. The upstream file path/SHA and identity references permit reconstruction without copying or overwriting original CAD facts.

`columnScopeRef` preserves the actual upstream Coverage reference; `textColumnRef` is recorded separately. The eight bridge paragraphs currently carry local TextColumn references upstream, which are retained rather than fabricated into new Sheet ColumnScope identities. Body entity handles and inherited context spans stay distinguishable.

Section/subitem references are candidate sets, not forced choices. A unique section title may supply a bounded subject label before a colon. Context spans remain separate from body spans; inherited text is not inserted into rawText. Predicate-like or unbalanced-parenthesis title prefixes are not scope labels. Building/storey/system applicability remains unresolved, and automatic application is disabled for every statement.

Recognized Atomic types do not imply supported knowledge. Weak lexical signals such as the character for “set” inside the words for “design” or “construction” are retained in `atomicStatementTypeCandidate`, but the bridge leaves the DesignStatement type unknown. Unknown type, incomplete atomic termination, unresolved structural context or reading/coverage uncertainty prevent supported status. No conflict is fabricated from uncertainty or duplicate numbering.

## Clause boundary

- Conditions/exceptions/references must be wholly contained in one atomic source span. Syntactic condition guards can decline existing signals; the Atomic extractor itself is unchanged.
- Alternatives currently require bounded A and B around an explicit parenthesized “or”, plus a host statement and source spans. Verb/preposition-contaminated option boundaries are declined. Bare “or” remains a reviewed signal.
- Purpose requires explicit subject, connector and goal. This stage supports the observed bounded connector form, without inferring missing arguments.
- Exceptions need an existing recognized exception kind, a requirement host and compatible trigger references. No exception is forced into another sentence.
- References are navigation candidates only. Names/closing punctuation remain RAW-derived; target documents/regions are not resolved.

## EW-0002 acceptance result

| Metric | Result |
|---|---:|
| Paragraphs processed by shared pipeline | 46 |
| AtomicStatementCandidate | 95 |
| Nonempty Atomic | 86 |
| Empty Atomic, reviewed and blocked | 9 |
| DesignStatementCandidate | 86 |
| supported / partial / unresolved / conflicting | 0 / 54 / 32 / 0 |
| ApplicabilityCondition attachments | 8 |
| AlternativeClause | 1 |
| PurposeClause | 1 |
| ExceptionClause | 0 |
| CrossDrawingReference | 3 |

Types: requirement 54, unknown 28, reference_statement 2, installation_requirement 1, purpose_statement 1; definition/material_requirement/note 0. These are candidate labels, not engineering facts. The counts cover the accepted 46 paragraphs, not all text on the page.

The eight new paragraphs contribute eight nonempty atomics and five whitespace atomics. Existing 38 paragraphs retain their 78 nonempty and four blank atomics. The sentence splitter was not repaired to hide those empty cases.

All 46 paragraphs produce traceable DesignStatement candidates. The 45 general body gaps and two outstanding hierarchy/body gaps stay outside this semantic pass. Source snapshots, raw coverage dispositions, paragraph boundaries and hierarchy numbering are unchanged.

### 4.12.1 automatic Golden

`23428 → 23401 → 23402` produces three candidates without the fixture adapter:

1. Short-line protection requirement, qualitative condition with unresolved threshold.
2. Long-line protection and setting statement, with the explicit instantaneous/short-delay alternative. The Is1/Is2 bare-or phrase remains a reviewed signal. The setting text remains in the same raw atomic; the fixture's separate `additionalRequirements` field is **not** automatically reconstructed.
3. Short-delay trip device → “用以” → selectivity purpose.

All three receive the subject candidate “非消防负荷” from hierarchy source spans, never from the DWG filename. Applicability remains unresolved. The long-line wording produces both a qualitative condition and an overlapping general-predicate candidate from the existing extractor; these are not counted as independent engineering rules.

## Quality audit and unresolved issues

`DESIGN-STATEMENT-BRIDGE-AUDIT.md` records a fixed-seed (20260924) Fisher–Yates selection of ten partial and ten unresolved statements, sorted by statement ID before shuffling. There are no supported statements to sample. Audit comments distinguish exact Atomic text preservation from complete semantic understanding; no accuracy percentage is asserted.

Review records are grouped by root cause rather than presented as 270 separate manual requests:

| Root cause | Records |
|---|---:|
| Instance applicability unresolved | 86 |
| Atomic split remains a semantic candidate | 86 |
| Section completeness unresolved | 37 |
| Statement type unresolved | 28 |
| Weak Atomic type signal | 6 |
| Empty Atomic | 9 |
| Bare/insufficiently bounded alternative | 8 |
| Atomic termination unresolved | 4 |
| Section context unresolved | 4 |
| Declined condition predicate | 2 |

These root causes overlap. Nine existing semantic-reader review records are preserved separately. No new engineering conflicts were adjudicated. A mixed title-plus-subitem Atomic can retain a Section reference without a unique SubItem reference; the audit explicitly flags this limitation instead of inventing a child assignment. Multiple 6.5 / 6.5.1 references are also retained.

Verdict: `design_statement_bridge = useful_but_partial`.

The next bounded stage can be a candidate Evidence adapter with explicit status/application gates. It must not turn the 86 statements into automatically applicable rules: unknown types, mixed structural context, incomplete semantics and unresolved applicability remain reviewable. No further Paragraph recovery is required for that adapter experiment.

## Verification

All 32 offline regression suites passed. The final bridge suite independently passed 808 checks, covering source/column references, all 38 legacy paragraph semantic outputs, all eight new paragraphs, blank Atomic blocking, Golden automatic recovery, ambiguous clause guards, scoped inheritance, immutability, empty input and absence of fixture-specific code. No AutoCAD was invoked. The source snapshot and upstream hierarchy-bridge SHA-256 values remain unchanged. This is experimental sample validation, not general semantic accuracy.
