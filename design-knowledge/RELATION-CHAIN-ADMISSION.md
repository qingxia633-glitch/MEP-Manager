# Local relation chain admission

`Get-RelationChainAdmission` consumes reference-backed endpoint role candidates,
two distinct boundary contact hypotheses, and reviewed local system context.
It does not recognize symbols or infer system identity from a raw layer.
The source-resolving fixture reuses the role admission result and verifies the
speaker segment/circle intersection using the actual INSERT transform.

The fixture manifest stores references and a snapshot hash, not RawEntity copies.
The previous role fixture supplies the system report, module definition, legend
definition and existing legend evidence. The new manifest adds the speaker probe.
The chain references all evidence without merging definition or instance identity.

With the complete reviewed chain, investigation, search, relation-candidate and
device-role support are allowed in candidate context only. Device role support
preserves each endpoint's original candidate status. System identity stays partial.
Port roles, physical connections, logical/routing edges and signal direction are
always blocked. Unknown is not a wildcard. An interior endpoint alone cannot
substitute for boundary-contact evidence. Other unresolved conflicts fail closed.

Raw layer and contextual scope remain separate references. Hidden-name dual
semantics stays open. Requirement status is never mutated. There is no automatic
network or routing construction. This is a bounded real-sample validation, not a
reusable symbol/connection recognizer.

Run `powershell -NoProfile -ExecutionPolicy Bypass -File design-knowledge/tests/Test-RelationChainAdmission.ps1`
or the offline regression runner `model-core/tests/Run-Regressions.ps1`.
