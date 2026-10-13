# Shadow Benchmark Ledger

Post-Leader, non-Golden ProjectEvidenceDiscovery benchmark; this is not an engineering rule library.

- [v0.1](shadow-ledger-v0.1.json): initial two-case baseline (true-unresolved and true-supported). Preserved unchanged.
- [v0.2](shadow-ledger-v0.2.json): adds SHADOW-003, object ownership plus Discovery semantic boundary.

Discovery semantic boundary only; full CandidateSemantic / ProjectRule / Gate pipeline not validated by this case.

- Contract: ledger entries reference existing frozen blind results and separate post-blind adjudications by logical path and SHA-256. Private source files are required for reference verification.
- Invariants: never rewrite source results or feed adjudication back into blind inputs. Object ownership does not approve engineering semantics or quantities.
- Evaluation: PASS requires unresolved/true_unresolved, supported/true_supported, or conflicting/correctly_conflicting. False-supported and false-unresolved adjudications are FAIL. Error counts are observations within the documented scope, not proof about all DWG content.
- Semantic-boundary acceptance: supported ownership must agree with true_supported adjudication, and the separately adjudicated semantic boundary must be preserved without overreach.
- Failure: missing references, hash mismatches, inconsistent identities or status pairs invalidate ledger verification; do not infer a replacement result.
- Acceptance: validate required fields, types, unique case IDs, source hashes, status pairing and summary counts. No conflict candidate found is not a case; conflict handling remains unbenchmarked here.

Only ledger/document validation applies. Discovery and downstream stages were not rerun; full regression not rerun. No commit or push.
