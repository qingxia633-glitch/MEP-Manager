# Local logical network candidates (experimental)

`LocalLogicalNetwork.psm1` organizes reviewed local representation evidence into
system-isolated `LocalLogicalNetworkCandidate`, `LogicalNodeCandidate`,
`LogicalEdgeCandidate`, `NetworkBoundaryCandidate` and `NetworkGapCandidate`.
It reuses ModelCore system scopes and candidate element admission. No actual
LogicalNetwork, RoutingNetwork, physical connection, Circuit or quantity is emitted.

An edge here means a **candidate relationship between drawing representations**.
It does not override `EvidenceAdmission` prohibitions on actual network edges,
port functions, physical connections or signal direction. Every edge has
`admissionStatus=candidate_only` and `formalNetworkAdmission=blocked`.

The bounded real sample adapter reads the existing system snapshot plus the
existing module/legend/speaker probe evidence. The fixture lists the reviewed
region, selected representations and context references. Selection is not a
general automatic system recognizer. Handles and coordinates do not participate
in the reusable admission policy. Whole source records stay in original reports;
the catalogue retains document, snapshot hash, Handle and source-span references.

## Geometry and scope

- Recompute same-system endpoint coincidence and endpoint-on-straight-segment
  contact from WCS coordinates with explicit drawing-unit tolerance.
- Interior segment crossings do not create edges. Parallel overlaps are unresolved.
- Curved polylines retain bulges. Only their endpoints are tested; no chord
  substitution, curve-interior intersection or geometry repair is performed.
- Existing probed module/speaker boundary evidence supports representation edges.
  Other device columns remain separate unresolved endpoint associations.
- Raw lines may extend outside the local observation window. Preserve those raw
  representations; emit window-exit boundaries and do not investigate other regions.
- `openEnds` counts in-window endpoints without an admitted candidate edge,
  including boundary-supported gap endpoints. Boundary contact alone does not
  remove these unresolved continuation records or assert disconnected wiring.
- `unresolvedRoles` counts nodes lacking even a role candidate. A candidate name
  is not confirmed device identity; all ports and actual memberships remain unresolved.

## Isolation and gaps

Shared device representations receive distinct system-qualified node IDs.
Cross-system associations reference those IDs without merging networks.
Terminal-box gaps are independent per system. The probable object and reason
remain candidates; neither proximity nor a declared supported edge can bridge a gap.
The verified DZX probe refines three gaps to terminal-box boundary relations;
their distances and unresolved internal continuity remain intact. See
[TERMINAL-BOUNDARY-REGRESSION.md](TERMINAL-BOUNDARY-REGRESSION.md).
Source/control-room text is navigation context, never a bound controller instance.
Completeness is partial, locally_supported or unresolved; never complete.
Requirements are copied with unchanged status and receive investigation support only.

## Reproduce

`powershell -NoProfile -ExecutionPolicy Bypass -File model-core/tests/Test-LocalLogicalNetwork.ps1`

`powershell -NoProfile -ExecutionPolicy Bypass -File model-core/Read-LocalFireNetwork.ps1 -OutputPath local_test_data/fire-local-networks-20260925.json`

The second command writes only the candidate inventory artifact. It does not read
new DWGs, call AutoCAD or modify the existing evidence reports.
