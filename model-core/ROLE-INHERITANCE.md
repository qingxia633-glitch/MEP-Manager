# DeviceRole inheritance (experimental)

`RoleInheritance.psm1` accepts a scoped definition and instance evidence records;
it does not read or modify CAD entities. `Resolve-DeviceRoleInheritance` returns
definition-role, instance-inheritance and open role-conflict candidates.

Evidence kinds remain separate: instance explicit, definition default, project
legend, sibling instance, human confirmation. Canonical role compatibility must
be supplied with a traceable `compatibilityRef`; this module does not infer roles
from block names, Handles, geometry, majority votes or free-text similarity.

Supported inheritance requires a supported local definition default, matching
document/definition/scope, static single-state definition and static instance,
no conflicts, and `roleAttributeState=absent_in_snapshot`. A present empty role
attribute is separately blocked. Own declarations remain explicit, including
when conflicting; defaults never replace them. Cross-DWG legends only supplement
local evidence and cannot establish a local default. Human confirmation is
retained as evidence, not an automatic conflict-resolution switch.

An inherited role is always `inherited_candidate`, never confirmed. Outputs are
for candidate investigation, not instance mutation, network construction or
quantity calculation. Snapshot references describe observed sources; downstream
callers must invalidate candidates when their source definition or scope changes.

## Real fixture

`tests/Read-SmokeRoleFixture.ps1` reads the existing plane, definition probe and
legend reports, retaining raw role text, source Handles, document and SHA-256.
The reviewed smoke-role compatibility is fixture data, not a generic parser rule.
The previously verified 52-vertex polygon transform is reused without refitting.
System quantity is read independently after spatial selection.

Expected: 80 explicit, 741 inherited candidates, zero conflicts/confirmed roles;
inside: 20 explicit + 88 inherited candidates. 108 vs 112 remains
`mismatch_candidate`, delta 4, cause unresolved.

Run: `pwsh -NoProfile -File model-core/tests/Test-RoleInheritance.ps1`.
