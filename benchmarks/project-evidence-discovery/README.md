# Shadow Benchmark Ledger v0.1

Post-Leader, non-Golden ProjectEvidenceDiscovery benchmark; this is not an engineering rule library.

- Contract: ledger entries reference existing frozen blind results and separate post-blind adjudications by logical path and SHA-256. Private source files are required for reference verification.
- Invariants: never rewrite source results or feed adjudication back into blind inputs. Object ownership does not approve engineering semantics or quantities.
- Evaluation: PASS requires unresolved/true_unresolved, supported/true_supported, or conflicting/correctly_conflicting. False-supported and false-unresolved adjudications are FAIL. Error counts are observations within the documented scope, not proof about all DWG content.
- Failure: missing references, hash mismatches, inconsistent identities or status pairs invalidate ledger verification; do not infer a replacement result.
- Acceptance: validate required fields, types, unique case IDs, source hashes, status pairing and summary counts. No conflict candidate found is not a case; conflict handling remains unbenchmarked here.

Only ledger/document validation applies. Discovery and downstream stages were not rerun; full regression not rerun. No commit or push.
