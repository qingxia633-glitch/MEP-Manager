# Experimental section / subitem structure

`SectionHierarchy.psm1` adds a separate, reference-based structure overlay to an existing Layout Reader result. It does not edit ParagraphCandidate, raw TEXT or DesignStatement semantics.

## Use

```powershell
$result = ./design-knowledge/Read-Hierarchy.ps1 -ReportPath <snapshot-path>
$result.hierarchy
```

The entry point reads a snapshot and returns the existing reader result plus hierarchy in memory. It does not write an artifact or invoke AutoCAD. IDs reference the snapshot-scoped raw fragment, not a global CAD Handle.

## Contracts

- DocumentHierarchyCandidate: snapshot references, local sections, subitems, relations, reviews and unassigned fragment references. It is not a complete document tree.
- SectionCandidate: raw numbering, pattern/parts, title and fragment references, Paragraph references, direct subitem references, local source region and boundary candidate.
- SubItemCandidate: raw marker, ordinal candidate, source fragment and Paragraph references, sibling order and alternative parent candidates.
- ParentChildRelationCandidate: evidence for pattern/depth, indentation, bbox, height, spacing, sibling sequence, parent position, lead-in and observed geometry boundaries. Marker style alone cannot establish a parent.
- CompletenessCandidate: independent of reading-order confidence. Missing coverage or interrupted chains remain incomplete/unresolved. A bounded observed sequence may be likely_complete, never automatically complete.
- UnassignedStructureFragmentCandidate: references every raw text record absent from the supplied Paragraphs, including short headings and isolated markers. This is a preservation record, not automatic body admission.

Sections use dotted markers and observed local columns. List markers include closing/full parentheses, enumeration marks, numeric-space and single-dot forms. A nested list requires a lead-in and relative indentation; matching sibling styles return to the corresponding parent candidate. Duplicate numbers are preserved with reviews, not corrected. Horizontal lists, unproven parents, gaps, style changes and missing boundaries remain reviewable.

## Scope

The real fixture is **current snapshot / local design-text region**, not EW-0002. Page assignment is null until separately evidenced. Handles occur in test expectations only. No design semantics, electrical connectivity, circuits or quantities are generated.

This version supports near-horizontal top-level TEXT and the existing straight-line boundary evidence. Cross-column/page continuation, inline numbered lists, full page segmentation and more complex competing hierarchies are unresolved. A next numbered title is only a boundary candidate; it is not proof that all underlying CAD content has been observed.

Tests: `tests/Test-Hierarchy.ps1`; controlled cases can be run with `-ControlledOnly`.

## Real fixture result (2026-09-24)

Snapshot SHA-256: `7360ADB34A4E0BACACD2768261FBB3E19835C07C65F9F4959F94BAE5751A249F`.

- 10.1.15: eight direct subitems. Item 1 references 23772/23773; item 4 references 23776/2377B; items 5-8 reference 2377A, 23778, 23779, 23777 in layout order. Next same-level boundary is 23517/10.1.16. Section completeness is likely_complete while original paragraph coverage is incomplete.
- 4.10: ordinary fragments 2341E/2341F/23420, no list items.
- 478BF: numeric-space outer items 1-5; closing-parenthesis inner items 1-2 under outer item 1.
- 4.6.1-4.6.4 remain siblings, not parents of one another.
- Both raw 4.11 headings and both raw 6.2.1 headings survive as separate candidates with duplicate-numbering reviews.
- Dedicated full hierarchy test: 40 checks passed, including a prefix that must not cross an already closed parent section boundary and separate review source references/reasons. The final observation-boundary diagnostic was additionally checked with the 26-check controlled suite. Input Paragraph JSON remains identical before/after overlay creation. All 28 offline regression suites passed; no AutoCAD was invoked.

The complete supplied snapshot produces 423 section candidates, 113 subitem candidates and 342 hierarchy ReviewItems. These counts are experimental observations across the supplied snapshot, not an EW-0002 page inventory or validated coverage claim. Review increases from stricter parent-boundary checks preserve uncertainty; no numbering is repaired.
