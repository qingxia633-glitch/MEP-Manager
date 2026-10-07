# Routing termination and logical correspondence (experimental)

`RoutingCorrespondence.psm1` composes existing candidate evidence without changing
geometry, topology, instance roles, requirements or upstream reviews.
`Read-RoutingCorrespondence.ps1` checks the SHA-256 pins in
`tests/routing-correspondence-sources.json`, including the attachment's routing revision.

## Admission

- Supported representation geometry and supported endpoint attachment are required.
  Endpoint identity must agree with the actual routing edge; crossings and near-only
  relations are excluded even if their admission flag is incorrectly set.
- Endpoint counts are unique routing node references per device, not relation pairs.
  Every original open endpoint survives in `terminations` with `rawOpenEndpoint=true`.
- Other termination types require explicit, same-snapshot, same-system evidence.
  Unknown causes remain unresolved. Missing geometry is a hypothesis, not a repair request.
- A multi-endpoint device creates a partial continuation hypothesis with
  `internalContinuity=unresolved` and `bridgeAllowed=false`. No components are merged.
- Category membership gives partial instance/route correspondence. An unresolved
  system-diagram branch target gives only an unresolved logical-edge routing candidate.
  No candidate is inferred from distance, quantity equality or shared compartment.
- DZX evidence belongs to the system diagram. It is preserved as an upstream gap;
  it cannot classify an unrelated plan endpoint. Therefore the real plan currently
  has zero evidenced terminal-box terminations, not evidence of terminal-box absence.

## Scope and limitations

Only the two already admitted definition geometries are inputs; this module does not
read additional definitions or infer boundaries. The current adapter accepts fire_alarm
and matching compartment/source identity only. Logical-edge route admission remains
conservative: this first sample has no verified cross-drawing logical-edge route binding.
Category and instance correspondences do not establish a loop, circuit, signal direction,
physical port or installation quantity.

## Reproduce

Run with PowerShell 7:

```powershell
./model-core/tests/Test-RoutingCorrespondence.ps1 -OutputPath outputs/fire-alarm-routing/correspondence.json
./model-core/tests/Run-Regressions.ps1
```

The JSON includes all endpoint classifications, all device aggregations, individual
logical-edge assessments, the deterministic Golden chain, source hashes and open reviews.
