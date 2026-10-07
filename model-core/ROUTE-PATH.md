# Plan route path candidate

Uses pinned Routing, termination and VisualContinuity artifacts. It never mutates
them and never uses device-mediated continuation to join nodes. Shared original
geometry nodes remain shared; no device interior is bridged.

Components with branching are retained as branched_subgraph diagnostics and are
not linearized. Only a simple component with two supported device terminations is
eligible as the single Golden. Ranking favors fewer jumps, more explicit terminal
roles, more real segments, then stable handle ordering. No expected length is used.

Real edge lengths are verified from segment coordinates and summed separately
from visual gaps. INSUNITS=0; no metric conversion, heights, circuit or quantity.
Traversal start/end are deterministic labels, not signal direction. Logical status
remains unresolved regardless of geometric continuity. Existing PlanLogicalRelation
references use an artifact namespace and do not inherit control semantics.

Run tests/Test-RoutePath.ps1 or Read-RoutePath.ps1 -OutputPath ... .
