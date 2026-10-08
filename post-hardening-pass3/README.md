# Pass 3: Builder admission contract

Current executable input is QuantityBuildPlan **0.3**. Historical schema 0.2 and
its JSON inputs remain unchanged. Builder rejects version 0.2 with `blocked`
and `legacy_incomplete`; it never fills missing approvals or silently migrates.

`quantity-eligibility/plan_v03.py` exports only after calling the shared pure
`validate_executable_plan_contract`. Builder calls the same validator independently
before quantity arithmetic. The old v0.2 exporter remains available for historical
format compatibility only; its result is not admitted for execution.

## Admission

- Gate: explicit approved status and flags, approved role, complete object identity,
  accepted affirmative evidence and its provenance, bound context; no conflict.
- Raw geometry: exact decimal raw length, units and reviewed physical/CAD conversion,
  exact product, converted-2D/base equality, and identical raw execution audit record.
  An approved 3D path retains its separately reviewed height basis; no 3D recomputation.
- Assumptions: an explicit evidence registry recursively covers nested records such
  as exemption rules and accepted semantic evidence. Every required reference must
  resolve to an approved, sourced, same-identity assumption whose nonempty conditions
  match that particular evidence record. Missing conditions are never inferred.
- Version 0.3 adds required evidence fields without rewriting historical v0.2 required
  semantics. Native evidence replay and legacy numeric-only replay remain distinct.

## Tests and source boundary

`tests/test_admission.py` directly invokes Builder. Before implementation the first
22 tests recorded 24 failed assertions (subtests included); their raw result is retained
locally. Expanded tests include valid native replay, conversions and approved assumptions.

`current_checks.py` reruns the unchanged 24 Pass 2 assertions on NEW explicit synthetic
v0.3 inputs and a v0.3 exporter. Original v0.2 inputs and expectations remain frozen;
their raw outcomes are also run and reported separately, never counted as successes.

`migrate_inputs.py` writes new local Golden wrappers only. It copies the existing
full reviewed Gate, exact conversion-factor representation and already-bound slab
conditions with source paths, pointers and hashes for every delta. It neither approves
new facts nor rewrites old evidence. Frozen quantities are replayed, not issued.

Private Golden/report fixtures and output inventories are not publication artifacts.
Public synthetic checks run with Python unittest; private source validation requires
the original local evidence. Full regression runs retain raw legacy failures alongside
explicit classifications. No change to old expected is authorized.
