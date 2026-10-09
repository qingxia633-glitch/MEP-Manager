# Functional control relation (experimental)

`FunctionalControl.psm1` consumes explicitly reviewed candidate references and
relation evidence. It does not discover controls from raw text or infer relationships
from matching counts. References must resolve within the supplied scope.

The five independent relation grains are function/control region, circuit/target,
module/function, circuit/IO and IO/target. Missing endpoints or evidence downgrade
only the affected relation. Supported means candidate support, never confirmation.
Cardinality requires explicit relation evidence; equal counts are not evidence.

The EW-0015 / ALZ1-B1 test pins the existing snapshot SHA-256 and resolves Handles
without copying RawEntity records into outputs. Its reviewed quantity candidate
retains rawQuantity=5 and IO module representation meaning. Physical object and
channel counts remain unresolved. The output references that quantity candidate.

Fixture result: seven partial relations, ten unresolved IO bindings, unresolved
cardinality. No individual IO identities are fabricated. The module-box and
terminal-box wording remains in the source, not normalized away. x12 is outside
this scope and is not an input to the resolver. No network, routing, requirement
mutation or physical-instance application is implemented.

Run `design-knowledge/tests/Test-FunctionalControl.ps1` for the real fixture and
negative checks, or `model-core/tests/Run-Regressions.ps1` for all offline suites.
