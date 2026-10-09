# CategoryToPlanInstanceSet (experimental)

`CategoryMapping.psm1` exports `Resolve-CategoryToPlanInstanceSet`.

Inputs are candidate overlays, not rewritten RawEntity records:

- Category: `nodeRef`, reviewed canonical `roleCandidate`, `systemIdentity`,
  `compartmentRef`, optional `systemQuantityCandidate` and `quantityRef`.
- Compartment: `compartmentRef`, `polygonRef`, `boundaryStatus=supported`,
  `closed=true`, already projected `vertices`, `frameRef`, optional `holes`.
- Correspondence: `transformRef`, `status=supported`, `polygonRef`,
  `targetFrameRef`. The caller supplies an independently verified projection;
  this module does not fit a transform or infer coordinates from block names.
- Instances: unique `instanceRef`, insertion `position`, `frameRef`, optional
  independently established `compartmentRef`.
- Role candidates: `instanceRef`, `roleRef`, one canonical `roles` entry,
  `roleStatus` explicit/inherited_candidate, supported/partial `status`,
  `systemIdentity`, `sourceRefs`. Raw lexical compatibility remains upstream.

Algorithm: scope and provenance gates, validated simple closed polygon,
existing `MepSheet.Geometry.Point` XY membership, existing corrected
`Get-PolygonBoundaryDistanceXY`, separate tiered member references, then optional
system-quantity consistency comparison. No bounds-based membership. Holes and
invalid rings are blocked. XY membership does not establish storey membership.

Outputs contain source references, not copies of CAD entities. `assessments`
retain membership, distance, tolerance and role reference. Unknown/conflicting
roles do not enter supported members. Partial members are separate and excluded
from `roleSupportedExpressionCount`. Boundary points are never inside members.
Every input instance has one disposition; duplicate refs are rejected.

`complete_candidate` means no outstanding limitation within the supplied
candidate universe; it is not proof that the source drawing inventory is complete.
Inherited members, ambiguous members or a quantity mismatch keep completeness
partial. Quantity comparison never feeds back into selection. Missing quantity
does not prevent a spatial set. Reviews remain open and causes unresolved.

The reviewed fixture adapter pins three real categories, source Handles, semantic
compatibility and the previously verified polygon transform. These do not occur
in generic matching logic. The manual-call sample uses its alarm interface scope;
this does not remove its separate phone interface or merge systems.

No confirmed role/binding, Requirement mutation, network, routing or quantity
calculation is authorized. Counts are candidate membership audit only.
