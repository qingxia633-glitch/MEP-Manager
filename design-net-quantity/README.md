# DesignNetQuantityBuilder v0.1

Only executes QuantityBuildPlan v0.2. No CAD reads, semantic inference, ownership
decisions, upstream changes, procurement or pricing. The versioned schema is validated
in full by jsonschema Draft202012Validator; additional execution checks enforce
formula/component consistency, provenance, hashes and unit contracts.

Install `python -m pip install --target .builder-deps -r design-net-quantity/requirements.txt`.
Run `python -m unittest discover -s design-net-quantity/tests -v`.

## API and CLI

`build(plan, existing_quantities)` requires a complete normalized issued registry.
Omitting it blocks generation. An explicitly empty list asserts no issued objects.
Registry entries must include scope, quantity_kind, approved_semantic_role. Duplicate
keys block building. Caller must provide a complete registry and serialize concurrent
builds; this library does not provide a database transaction or issue quantities itself.

`replay_validate(plan, frozen_quantity)` evaluates without issuing. Native objects
require both numeric agreement and canonical semantic content/hash agreement,
including formula components, owners, devices, assumptions and evidence references.
The output distinguishes `numeric_match` from `evidence_contract_match`.
Legacy adapters with only value/specification fields cannot prove full replay:
they return `replay_value_matched_legacy_evidence_incomplete` when values agree.
They never receive `replay_matched`. Historical objects are not modified.

```
python design-net-quantity/resolve.py build plan.json --registry registry.json --output new-result.json
python design-net-quantity/resolve.py replay_validate plan.json --frozen normalized-frozen.json --output replay.json
```

Output files are exclusively created, never overwritten. Replay returns `issued=false`.
The result statuses are built, replay_matched, replay_mismatch,
replay_value_matched_legacy_evidence_incomplete, blocked, invalid_plan,
duplicate_detected and contract_violation. Schema admission is always checked before
evaluation; explicit failed eligibility is reported blocked with validation errors.

## Arithmetic and identity

Executes only the supplied multiply(add(base_path, all owned_adjustments), multiplier)
AST. No specification parsing. Decimal precision is read from the Plan. Inexact or
rounded intermediates reject execution. Reporting uses the approved policy's places
and ROUND_HALF_EVEN. Units m and mm are supported with explicit conversion contracts;
all source terms must use one source unit. Mixed source-unit plans reject. Historical
raw_geometry_conversion is audit-only and never an extra term.

All input evidence, assumptions and hashes are retained. Output content_hash uses a
canonical sorted JSON semantic projection excluding its own root content_hash, built_at, path and
source_build_plan_hash/source_decision_artifact_hash locators. These audit hashes remain
in the object. Nested evidence content hashes remain part of semantic content so a
correction with the same ID but different evidence cannot replay as a full match. All input hashes remain
in the object. Quantity identity uses canonical project/drawing/edge/segment/path
identity + kind + approved role, excluding scope comments and display metadata. Hashes prove integrity,
not source authority. CorrectionEvidence references are retained; corrected drawing_ref
must already be applied by upstream. Builder never rewrites historical evidence.

The hardened v0.2 schema and execution checks require complete nested bindings,
non-placeholder approved roles and provenance. Physical adjustment identities are
checked across all formula entries, not just within a category. Current physical keys
require owner scope, device and transition type; unrepresented identities fail closed.
No procurement-completeness gate is introduced.

The safety-hardening pass is not accepted until its regression gate passes. The two
unchanged legacy Golden replay assertions currently require an explicit contract
migration; the incomplete legacy status must not be disguised as a full match.
