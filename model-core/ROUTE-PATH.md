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

## Approved crossing-gap path components v1

**Contract.** Read-RoutePath has an optional component mode. Its traversal request supplies
the full drawing scope, measurement item IDs and ordered native endpoint pairs. A reviewer
separately pins one accepted pair review by SHA-256. The review pins the project assumption,
unit authorization, manifest, report and DWG. The operator must obtain the review digest
from the accepted review, independently of the traversal request. This is local operator
authorization, not a signature. Paths are runtime inputs. The old graph and its pinned
fire-alarm scope cannot be substituted for the current drawing.

**Invariant.** A native step retains its vertices and native length. An observed visual gap
retains its geometry. Only a separately qualified gap yields a derived path component.
The two observations describe one distance. An item owns a set of component IDs;
reversing or repeating a traversal cannot add another occurrence. Separate items may
reference that ID. Neither the crossed line nor a device interior becomes a route step.

**Failure.** Missing authority, identity mismatch, inconsistent length, unsupported
geometry, competing endpoints or occupied geometry block the requested projection.
No partial approved list is returned. Legacy visual gaps remain unresolved. This v1
projection handles one reviewed pair per invocation, top-level ModelSpace straight
parents, and no device adjustments. It neither creates a plan nor changes the legacy
RoutePathCandidate version, output or ranking.

**Acceptance.** Independently measure the pinned source and replay the same endpoints
in both directions, with repeated and distinct item IDs. Challenge scope, crossing,
units, competition, native overlaps, evidence integrity and approval independently.

Use `Read-RoutePath.ps1 -ComponentRequest request.json -PairReview review.json
-ApprovedReviewSha256 <trusted-digest> -PythonExecutable <python>` (one command).
The request has keys `scope` (the exact verified_application identity), `files`
(assumption, unit, manifest, report, dwg paths) and `traversals` (each has
`item_id` and two ordered `endpoints` of the form [handle, parent_path, start/end]).
Relative paths resolve from the request file. A blocked response has no components.

QuantityBuildPlan v0.3 accepts a converted or approved 3D base and separately
owned device adjustments. Future consumption needs an explicit versioned base-path
composition with native and recovered source refs, item-level ownership, authorized
unit and per-component replay at Eligibility and Builder. Do not put a recovered gap
in a device adjustment or increase an original edge's raw length.
