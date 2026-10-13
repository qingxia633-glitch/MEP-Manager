# Batch Shadow Benchmark Runner v0.1

This is regression replay, not a new blind trial or an engineering rule library.

## Contract and boundaries

The orchestrator projects ledger metadata onto a strict input allowlist. A separate
Prediction process receives only case ID, project/drawing/target identity, pinned
report hash, acquisition scope and runtime report/manifest paths. It cannot accept
adjudication, historical result paths, PASS/FAIL or expected labels. It calls the
existing `discover_shadow()` on the whole report without injecting an association.
It exclusively writes the complete fresh machine output. All predictions finish
and their byte hashes are frozen before the scorer reads adjudications.

Scoring reads those files, validates their recorded hashes, and compares full
project/drawing/parent-path/handle identities and (for ownership cases) child
identity, direct binding method and relation. It never rewrites predictions.
The process boundary prevents accidental label passing, not malicious filesystem
access by arbitrary Python code; this is not an OS sandbox or signature system.

## Invariants / fail closed

- Ledger and frozen sources are read-only; output directory must not exist.
- Input paths come only from the local input-map, never the ledger's old paths.
- Missing input is SKIP; bad hash/manifest/drawing/project/scope/exporter is an
  input failure before Discovery, not a false negative.
- Unknown expectation shape, duplicate case IDs or malformed configuration abort.
- Wrong positive binding is a false positive; missing expected binding is a false
  negative. Conflicts are separately classified; partial is not supported.
- Lexical line codes and nearby geometry are not semantic approval. For boundary
  cases, extra line/system associations, propagation or explicit semantic approval
  are failures. Unknown output contracts fail closed, not implicit PASS.
- This tests Discovery only, not CandidateSemantic / ProjectRule / Gate.

## Acceptance matrix

Tests cover label leakage, input hash failure, absent inputs, positive/negative
agreement, false positives/negatives, wrong object/parent/project, conflict,
semantic overreach, lexical-only S, immutable scoring, duplicate IDs and unknown
adjudications. Synthetic inputs exercise runner software, not real benchmark cases.
Real acceptance replays the three ledger cases without changing Discovery.

## CLI

```powershell
python -B benchmarks/project-evidence-discovery/run_shadow_benchmark.py --ledger benchmarks/project-evidence-discovery/shadow-ledger-v0.2.json --input-map <local-map.json> --output-dir <new-local-output-directory>
python -B -m unittest discover -s benchmarks/project-evidence-discovery/tests -v
```

Local map shape: `{"cases":[{"case_id":"...","report_path":"...","manifest_path":"..."}]}`.
Relative input paths resolve relative to the map file, not the current directory.
Keep maps/reports/manifests/private evidence outside committed benchmark data.
Exit codes: 0 all PASS; 1 evaluation/input/execution failure; 2 invalid invocation;
3 otherwise successful run with unavailable-input SKIPs. Summary counters are
case counts; failure categories may overlap. Existing ledgers are not modified.
