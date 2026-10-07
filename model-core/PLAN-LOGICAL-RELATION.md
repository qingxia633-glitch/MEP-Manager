# Plan logical relation (experimental)

`PlanLogicalRelation.psm1` adds a candidate overlay between system-diagram relations,
category membership and plan routing. It does not write either graph.

`logicalRelationStatus` remains unresolved even when `geometryStatus` is supported.
Category membership remains partial and inherited roles are referenced without promotion.
The relation levels distinguish membership, instance attachment, routed instance pair,
instance-set subgraph, system-branch relation and system-only relation.

The pinned sample contains two Golden selections and one selected category subgraph,
plus all 17 system edges. Fourteen bus/branch and one module-representation relation
remain plan-target-unresolved; two diagram line/line relations do not require a plan route.
Routing references include the artifact path because component/edge IDs are view-local.
The routed pair has no assigned source system edge, direction, control, causality or circuit.

Run `tests/Test-PlanLogicalRelation.ps1` or `Read-PlanLogicalRelation.ps1 -OutputPath ...`.
The reader pins source artifacts and uses source references rather than copying RawEntity.
Fixture handles are confined to the selection JSON and tests. The generic join never uses
quantity equality or proximity. This is not a general system-to-plan matching algorithm;
new system relation types require review. No new plan-instance pair enumeration is performed.
