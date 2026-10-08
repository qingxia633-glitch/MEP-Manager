# Post-Hardening Review Fix regression evidence

Scope: P1-1, P1-2, P1-3, P1-4, P2-1 from commit 6b937fd18834da02d2f2c848edaa83afac0a6e2e.

`test_findings.py` contains the five initial reproductions. Before-fix execution failed all five.
`test_contract_boundaries.py` adds independently complete synthetic contracts, positive admission,
identity separation, required evidence, unchanged-value replay mutation, and report adapter checks.
New synthetic inputs explicitly declare their ModelSpace path; no historical identity is inferred.
Historical fixtures, assertions, project JSON, and frozen quantities are not migrated by these tests.

## Tightened contracts

- Gate candidate and object context both provide project_id, drawing_ref, edge_handle,
  parent_path (explicit [] for a proven ModelSpace object), plus segment_id when applicable.
  scope_type must be explicit and consistent with segment presence.
- Gate object_identity and every accepted evidence object_identity must match the Eligibility
  measurement scope. A bare historical supported boolean is insufficient.
- Engineering length conversion contract engineering-length-units/1 supports mm/m only.
  CAD scaling requires its own approved, identity-bound, hashed scale contract.
- Measurement evidence contract measurement-evidence/1 requires supported sourced geometry.
  approved_3d and physical adjustments also require supported sourced height evidence.
  A pure converted_2d plan without adjustments may provide a sourced not_applicable height record.
- Native replay compares a dedicated execution evidence contract as well as numeric value.
  Missing native contract fields cannot prove full replay; historical objects are not backfilled.
- The report adapter records ATTRIB ownership independently of coordinates and instance text.

## Known migration boundary

Historical inputs lacking explicit instance paths are intentionally blocked. Historical synthetic
plans without the newly required evidence also no longer pass. This is not resolved by changing
expected values or by defaulting missing paths. Any sourced migration must be independently
reviewed and versioned; no such migration is included here.
