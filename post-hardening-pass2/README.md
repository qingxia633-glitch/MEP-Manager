# Post-Hardening Review Fix Pass 2

Only the five reviewed findings are in scope. No quantity issuance or frozen-data migration.

## Before / after

The current starting commit already implements full-instance Gate identity and physical-unit
conversion checks. The first 18 new tests found 9 remaining failures/errors in height exemptions,
semantic-review replay retention and report owner scope; H1/H2 and the original missing-3D-evidence
and specification-provenance cases were already blocked. The extended suite has 24 tests.

## Contracts

- Existing schema mode names remain `converted_2d` and `approved_3d`. No schema rewrite.
- `approved_3d` or any physical adjustment requires supported identity-bound geometry and height.
- A planar exemption requires explicit `height_requirement=not_applicable` plus a height record
  with an approved/supported `measurement_rule`: rule_id, binding, provenance, measurement_mode,
  and height_requirement. A prose reason alone is insufficient.
- Eligibility retains this requirement and the complete semantic Gate record in its generated
  plan. The existing v0.2 exporter copies them without re-evaluating semantics.
- Native replay evidence contract v2 retains the semantic Gate record, approved semantic binding,
  height requirement and conversion contract in addition to previous formula/evidence records.
- Canonicalization sorts JSON object keys, preserves list order and every reviewed value.
  Only `path` in an explicitly hash-identified top-level source-map record is a machine locator.
  Arbitrary reviewed nested `path` fields remain significant. Replay stays independent of number
  equality; no historical frozen record receives backfilled fields.
- The report adapter establishes top-level INSERT scope only from the acquisition header:
  ModelSpaceTopLevelAllLayers / included / nested blocks not expanded.
- Unknown scope preserves raw attributes in `unresolved_attributes`, with null parent paths and
  unresolved association status. It cannot produce an explicit owner binding.
- Accepted attributes preserve attribute_handle, attribute_parent_path, owner_insert_handle,
  owner_parent_path, project/drawing and existing compatibility fields.

## Historical test treatment

`run_checks.py` runs the unchanged historical suites and retains every raw result. The prior 50
legacy contract mismatches remain classified (13 intentional rejections; 37 missing real sources).
Two old synthetic report fixtures lack an acquisition-scope declaration and now fail closed.
Their original assertions are rerun against a separately declared top-level synthetic report in
`current_contract_checks.py`. This is not fabricated project evidence or a historical fixture edit.

The old migration run's "all implementation Python hashes unchanged" check is retained but is not
the invariant for this authorized implementation-fix turn. Current frozen checks cover historical
JSON and historical test sources; authorized implementation diffs are separately disclosed.
No historical expected is modified to conceal a regression. Unexpected raw mismatches block completion.

Private Golden and actual report checks require excluded local data. Current-contract acceptance
combines recorded unaffected historical checks, migrated input tests, new adversarial tests and
the explicit current-boundary checks. The raw old suites are not reported as all green.
