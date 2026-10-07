# Project legend knowledge (experimental)

`Read-GarageLegendSemanticsFixture` enriches the pinned 51-row reviewed legend as
ProjectDesignKnowledge. `ConvertTo-SemanticLegendEntry` preserves all existing
raw fields and fragments and adds candidate properties. It does not mutate the
input or assign properties to engineering instances.

The actual columns are sequence, symbol, name, combined model/specification,
unit, and combined installation method/height. Overlapping headers and duplicate
TEXT remain source evidence. Model/specification is deliberately not silently
split. Unit is not a note. Mixed references such as “详见暖施” remain raw cell
content, not fabricated models. Installation alternatives remain partial.

Height candidates preserve raw fragments, source Handles, numeric value, unit,
datum and measurement meaning. Normalization to metres requires an explicit unit
and identifiable datum. Unitless values and H= alone retain uncertainty. Values
are not approved modelling Z coordinates or vertical cable lengths.

The real representation fixture compares ordinary row 14 with gas-extinguishing
row 48: the same base definition, external TEXT 23F42/QM in the reviewed symbol
cell, distinct legend names and raw model cells. Both rows specify bottom height
2.3m. This sample does NOT prove that QM changes the numerical height. The generic
pattern can carry separate role/type/model/specification/installation candidates.
Rows 28/29 separately show the same broadcast name with wall-mounted GRT3BM-01
versus ceiling GRT3XA-01(暗装)/GRT3XM-01(明装). Those model variants are preserved;
automatic model-option selection is not implemented.

Pattern resolution requires the exact scoped drawing and base definition.
Positive tokens also require independent association evidence. Default selection
requires an explicit project legend qualifier rule, full drawing coverage of
blocks/attributes/hidden items, zero matches, and no conflicts. Merely failing to
see a letter is insufficient. A cross-document application needs a separately
reviewed scope; identical block names cannot silently extend the legend scope.
Coverage inputs are evidence assertions from acquisition/human review, not a new
scanner or an automatic confirmation. A supported pattern is still a candidate.

Legend definition presence never asserts drawing instance presence. No network,
quantity, Requirement status or RawEntity updates are made.

Validation: `pwsh -NoProfile -File design-knowledge/tests/Test-LegendSemantics.ps1`.
