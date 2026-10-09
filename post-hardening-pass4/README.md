# Pass 4 — reviewed evidence admission

Baseline: a358fd454dcc3db0e0efea64f2e716a5a0cf761c.

## Contract / invariants

The common defect is accepting container shape and self-declared state in place
of relationships between authorization, its reviewed binding, and source records.
The shared executable validator enforces three independently versioned contracts:

- EvidenceAuthorizationContract/1: permitted direct project evidence vocabulary,
  nonempty reviewed bindings, exact bidirectional IDs, role/assertion and complete
  project/drawing/parent_path/handle/segment identity consistency.
- ProvenanceRecordContract/1: each source citation has source_id, sha256,
  status=verified, object_identity, evidence_ref (JSON pointer to the cited plan
  evidence), binding_ref=/binding, and pointer (location within the source).
  The indexed source must have the same ID/hash/identity, verified status, and
  explicitly list the evidence_ref. Verification is an acquisition/audit fact,
  not engineering approval or cryptographic reviewer authentication.
- AssumptionDependencyPolicy/1: assumptions are leaves. An assumptions_required
  key or nonempty assumption_refs anywhere inside an assumption is unsupported.

Plan v0.3 remains the unreleased executable envelope. These subcontracts tighten
its promised safety and are explicitly recorded in admission_contracts. Structured
source citations are a new input profile: historical fixtures are NOT edited or
silently upgraded. Missing source-backed fields block execution. Migration, if
possible, creates separate objects with real source references, never approvals.

## Failure rules

Missing/foreign/unresolved sources, generic evidence, absent/rejected bindings,
inconsistent references or unsupported dependencies fail before arithmetic. No
fallback to legacy evidence, no quantity issuance. Export and Builder independently
validate. Replay includes contract versions and the entire source/authorization
records. Physical SI conversion remains separate from reviewed CAD scale.

## Adversarial matrix / acceptance

Direct Builder tests: generic accepted evidence; missing/rejected binding;
bidirectional reference mismatch; empty provenance; foreign path; unresolved source;
unindexed hash; missing and existing nested dependencies. Positive synthetic
authorization, provenance coverage across all required roots, unchanged numeric
replay and changed-evidence replay are tested separately. Old expected remains.

Repository investigation: 357 parseable saved JSON files, 48 assumption records,
no assumption dependency declaration observed. This is bounded to saved evidence,
not a claim about all project drawings. No DAG is implemented.

Run current-contract, original Pass 3, source-backed/private checks, Test 15 and
historical hashes; report raw legacy failures separately. Tests never invent real
project approvals to restore green. No commit/push or official quantity authorized.
