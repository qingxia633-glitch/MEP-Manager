# Leader Evidence v0.1 external review hardening

## Contract / shared root cause
The adapter is not an authorization boundary for persisted contexts. Both
`load_report()` and `discover()` independently call the same pure, type/version
aware leader validator. State flags do not replace geometry and identity checks.
Only classic LEADER v1 is current; MLEADER binding remains unresolved. Legacy
records may be read but missing scope/path never means top-level identity.

## Invariants / failure
- Explicit top-level acquisition and an explicit empty path are required.
- Classic v1 arrow is the first WCS vertex; finite vertices and matching count
  are required. TEXT/MTEXT type must match the actual referenced annotation.
- False validation flags, unknown version, missing object, foreign identity,
  unsupported coordinates/type fail closed with named diagnostics.
- Report serialized text, decoded text, and normalized text remain separate.
  Only exporter-confirmed backslash, quote and control escapes are decoded.
- An optional sidecar is checked against exact bytes, length, encoding and
  report header/version identity. A computed hash alone is not verified integrity.
- Diagnostic distances never enlarge tolerance or resolve ambiguous targets.
- Output remains candidate evidence; no semantic/quantity modules are invoked.

## Adversarial matrix / acceptance
| Entry | Variant | Required result |
| --- | --- | --- |
| adapter + discovery | legacy unknown scope / missing path | unresolved scope/path, no binding |
| direct discovery | version 999 / false flags / last-vertex arrow | explicit failed condition, no binding |
| both | DIMENSION / mismatched type / missing annotation | annotation type/existence failure |
| both | NaN / OCS | geometry/coordinates failure |
| discovery | two targets at arrow | both partial, evidence partial |
| adapter | corrupted hash/length/encoding/header | explicit manifest failure |
| adapter | exporter escapes / Chinese CP936 / wrong encoding | exact raw preserved, correct decoding or failure |
| real verifier | optimized Python / absent manifest | checks still executed, refusal |

Run new adversaries, full Discovery (retain and classify legacy failures without
editing their expected values), acquisition/TextLayout, immutable real-report
verification, Test 15, historical file hashes. Rule Baseline is read-only context.
No .gitattributes change is needed for this narrowly scoped implementation;
canonical Git bytes may be used in an isolated regression copy, never rewriting
historical working fixtures. Review pack is local-only and UTF-8.

## Compatibility boundary

Historical tests and their expected values stay unchanged. Fourteen legacy
positive tests use unversioned/typeless leader contexts or a legacy MLEADER
association with no validated acquisition scope. They now fail their old positive
assertions. Report the full-suite raw failures separately from current v1 tests;
do not describe the historical suite as all green. Current synthetic v1 tests
independently cover selection, ambiguity, duplication, bounded/unbounded notes
and unresolved Z. They are not migrations of private project evidence.

## Exporter string evidence

`fixtures/exporter-string-escapes-v1.txt` is exact CP936 output from an isolated
AutoCAD 2021 Core Console invocation of the unchanged `mep2:val` formatter.
The companion metadata records its byte hash and formatter hash. This verifies
backslash, quote, newline, carriage-return, tab and Chinese string serialization,
not a project annotation binding. The file was closed by the script; the process
subsequently timed out during shutdown. No project DWG was opened or saved.

Current real-object acceptance revalidates the unchanged saved classic
LEADER-to-MTEXT report against a new separate v2 manifest. LEADER-to-TEXT remains
synthetic-only; MLEADER and project-level applicability remain unvalidated.
