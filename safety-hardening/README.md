# Unified safety hardening audit

Baseline commit: `c838c6063a597b14effbce9f35e4f4e93d3d712e`.

The before-fix evidence and hash inventories are saved under
`outputs/unified-safety-hardening-20261008/`. Historical evidence, quantities and
project rule JSON are read-only. The executable v0.2 JSON Schema is the only
pre-existing JSON contract authorized for hardening.

## Reproduction

Run `python -B -m unittest discover -s safety-hardening -v`.
The adversarial assertions were established before implementation changes.
Before-fix failures are intentional evidence of the reviewed defects.

Pass 1 covers S1–S8. Pass 2 may start only after the first pass's specialty
tests, all 51 Test 15 suites and frozen hash checks pass. Each validation run
gets a separate output folder and uses exclusive file creation.

## Test input contracts

`fixtures.py` constructs an independent synthetic project, drawing, edge,
devices, adjustment owners and provenance. It imports no Golden fixture.
Any migration of legacy replay expectations must be explicitly approved and
documented; matching a historical numeric value is not a full evidence replay.

The explicitly approved S2 migration changes only the two legacy Golden replay
status assertions. Their old source and contract remain in `test-contract-baseline.json`;
the authorization, old/new expected states and unchanged frozen hashes are recorded
in `s2-legacy-replay-migration.json`. The legacy adapter is unchanged. Native replay
has independent full-contract positive and equal-value negative tests.

Pass 1 completed: Safety 24/24, native migration 4/4, eight specialties 224/224,
Test 15 51/51, 279 frozen JSON files unchanged. See `pass1-migrated-summary.json`.
Pass 2 began only after this complete gate. Its final report records its own results.

The test helpers for geometry and bounded propagation must provide actual source
edge geometry and independently supported structured propagation witnesses,
respectively. Supplying those missing inputs does not change their expected
connection or applicability outcomes. No historical project JSON is rewritten.

CandidateSemantic now requires explicit `evidence_identity` (project, drawing,
edge/target parent paths) on the item and both upstream outputs. The legacy test
adapter verifies source snapshot hashes and top-level handles before supplying
missing identity in memory; it never rewrites fixture JSON or expected outcomes.
