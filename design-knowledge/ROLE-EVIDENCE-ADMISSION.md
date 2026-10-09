# Role evidence usage boundaries

`Get-RoleEvidenceAdmission` is exported by `EvidenceAdmission.psm1`. It is a
separate entry point for reviewed symbol/legend/instance evidence; it does not
change the existing design-statement admission policy or its consumers.

Input is a bounded evidence bundle containing resolved source references,
reviewed legend layout and context, symbol compatibility, instance code,
boundary hypotheses, system scopes, semantic declarations and requirements.
This is an admission policy, not an automatic legend or geometry discoverer.
The caller must provide trustworthy source resolution and scoped assessments.

The regression manifest `tests/role-admission-sample.json` pins four real report
hashes and the existing Golden requirement output. `Read-RoleFixture.ps1` reads
raw data in memory, checks definition references, verifies normalized rectangle
vertices/POINTs and the three boundary relationships. Only provenance references
enter the returned candidate records. Block names and Handles never select an
admission result. The fixture-specific geometry validation is not a reusable CAD
geometry engine. Attribute bbox failures remain in the original reports.

Policy requires the complete legend/code/compatibility/context chain for role
support. Separate supported sides with known systems are required for a
cross-system interface expression. Hidden/default semantic differences keep an
open review even when that contextual role is supported. Other unresolved
conflicts block admission. The reviewed dual-semantics case is not a general
waiver for all conflicting design evidence.

Eight use decisions are independent. `allowed` means candidate investigation
only; `partial` cannot pass `Test-RoleEvidenceUse`. Every consumer call must
supply the exact local scope and a known compatible system. No port-function or
physical-connection use is available, even if a caller supplies stronger input.
Cross-system direction, port mapping, internal conduction, control logic and
physical connection remain unresolved. The adapter emits no actual network,
connection, circuit or quantity, and never updates requirements or reviews in
its input. Review copies preserve all source references.

The sample emits separate support/search/hint candidates for `req:broadcast`
and `req:membership`, preserving missing/partial in the original source. It does
not identify a system-diagram symbol with a specific plan installation instance.

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File design-knowledge/tests/Test-RoleEvidenceAdmission.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File model-core/tests/Run-Regressions.ps1
```
