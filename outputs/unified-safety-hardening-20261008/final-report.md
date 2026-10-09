# Unified Safety Hardening — final report

**Unified Safety Hardening complete**

Pass 2 began only after the authorized S2 migration and the complete Pass 1 gate passed.
Historical audit records, test-contract baseline and legacy fixture adapter are preserved.

| Issue | Review | Severity | Reproduced | Root cause | Files changed | Regression | Before | After | Status |
|---|---|---|---|---|---|---|---|---|---|
| S1 | both | high | reproduced | Category-specific duplicate keys | quantity-eligibility/resolver.py; quantity-eligibility/quantity_contract.py | safety-hardening/test_adversarial.py | eligible with duplicate physical adjustment | Cross-category physical duplicate is blocked | passed |
| S2 | both | high | reproduced | Replay compared value/specification only | design-net-quantity/builder.py | safety-hardening/test_adversarial.py | replay_matched despite altered contract | Native contract/hash required; legacy value-only match explicitly incomplete | passed |
| S3 | both | high | reproduced | CLI write_text silently overwrote files | geometry-connection/resolve.py; device-role/resolve.py; candidate-semantic/resolve.py; project-evidence-gate/resolve.py; quantity-eligibility/resolve.py | safety-hardening/test_adversarial.py | existing output overwritten | Existing output/alias refused; exclusive creation | passed |
| S4 | local | high | reproduced | Nested scope/provenance and placeholder semantics not constrained | quantity-eligibility/schemas/quantity-build-plan-v02.schema.json; quantity-eligibility/quantity_contract.py; quantity-eligibility/resolver.py; design-net-quantity/builder.py | safety-hardening/test_adversarial.py | built with missing scope or unknown role | Incomplete or inconsistent contract blocked | passed |
| S5 | local | high | reproduced | Whole scope metadata dictionary used as identity | quantity-eligibility/quantity_contract.py; design-net-quantity/builder.py | safety-hardening/test_adversarial.py | built with scope metadata change | Metadata cannot bypass duplicate protection | passed |
| S6 | local | high | reproduced | Nonempty propagation objects treated as proof | project-rule-applicability/resolver.py | safety-hardening/test_adversarial.py | applicable with unresolved boundary | Required witnesses need supported status and provenance | passed |
| S7 | GitHub | high | reproduced | Caller coordinates were not checked against named edge | geometry-connection/resolver.py; geometry-connection/resolve.py | safety-hardening/test_adversarial.py | supported under wrong source edge | Readable source endpoint required with index and provenance | passed |
| S8 | GitHub | high | reproduced | Python string membership permitted substring match | project-rule-applicability/resolver.py | safety-hardening/test_adversarial.py | string target_ids accepted | Malformed target_ids raises contract error | passed |
| G1 | both | high | reproduced | Handle-only joins borrowed evidence across INSERT instances | project-evidence-discovery/discovery.py | safety-hardening/test_adversarial.py | second INSERT borrows first leader | Project/drawing/full parent-path/handle identity used for joins and summaries | passed |
| G2 | local | high | reproduced | Correction was required even for clean new provenance | quantity-eligibility/plan_v02.py | safety-hardening/test_adversarial.py | AttributeError without correction | Optional correction; provided corrections retain approval/hash/scope checks | passed |
| G3 | local | medium | reproduced | Conversion multiplication inherited ambient Decimal precision | quantity-eligibility/resolver.py | safety-hardening/test_adversarial.py | precision 28 conflicts; 80 eligible | Private operand-sized context; inexact/rounded conversion blocked | passed |
| G4 | local | medium | reproduced | Handle-only upstream evidence composition | candidate-semantic/resolver.py; geometry-connection/resolver.py; device-role/resolver.py; associated CLIs | safety-hardening/test_adversarial.py | candidate across different drawings | Explicit project/drawing/parent identity required; missing/mismatch unresolved | passed |
| G5 | GitHub | medium | reproduced | Project legend source filename embedded in generic resolver | device-role/resolver.py; device-role/resolve.py | safety-hardening/test_adversarial.py | approved other legend ignored | Versioned hashed approved source policy supplied by context; no built-in filename | passed |

## Validation

- Pass 1: Safety 24/24, S2 native replay guards 4/4, specialties 224/224, Test 15 51/51.
- Pass 2: safety/adversarial and boundary tests 42/42; Test 15 51/51.
- The only migrated expected statuses are the two explicitly approved legacy Golden replay assertions.
- Native full-contract replay still matches; equal numbers with changed ownership, provenance or assumptions do not.
- Shared review: S1/S2/S3/G1 all fixed. Local-only: S4/S5/S6/G2/G3/G4 all fixed. GitHub-only: S7/S8/G5 all fixed.
- No review false positive was found. Synthetic inputs no longer import Golden owners or evidence.

| Module | Tests | Result |
|---|---:|---|
| geometry-connection | 15 | passed |
| device-role | 17 | passed |
| candidate-semantic | 18 | passed |
| project-rule-applicability | 43 | passed |
| project-evidence-gate | 20 | passed |
| quantity-eligibility | 38 | passed |
| design-net-quantity | 27 | passed |
| project-evidence-discovery | 46 | passed |

Frozen JSON: 279 checked, 0 changed.
Golden formal quantity SHA-256: `d71dd9ca8f0e297711784d777efe1a0b0406576a78bb2e77fc04314f492aad77`.
The executable v0.2 JSON Schema is an authorized code contract change, excluded from frozen evidence inventory.

## Records

- `s2-legacy-replay-migration.json`: explicit limited migration and historical contract reference.
- `s2-migration-assertion-audit.json`: only two Builder test methods changed; legacy adapter unchanged.
- `pass1-migrated/results.json`, `pass2/results.json`: independent full test runs.
- `final-summary.json`: issue table, current eight-module hashes and frozen checks.

## Remaining limits

- Completion covers the 13 reviewed defects, not a guarantee against every possible defect
- Missing explicit upstream identity now stays unresolved; legacy evidence requires verified input adaptation
- Caller must supply the approved project legend policy; no policy means no legend admission
- No new project quantity, procurement/pay quantity, CAD write or publication was performed
