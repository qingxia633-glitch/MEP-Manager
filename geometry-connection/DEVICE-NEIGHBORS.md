# DeviceNetworkNeighborQueryVersion = 1

**Contract.** From a top-level open LINE or LWPOLYLINE and its named start/end, query native POINT contacts on the selected ModelSpace INSERT instances. Search the entire report for other open endpoints incident to those POINTs. An endpoint index and its original edge path identify the parent edge for future measurements. The query is one hop and never calls a routing or quantity builder.

**Identity and invariants.** Qualify the project and drawing instance through a pinned Registry v2. Verify the report, manifest, actual DWG and targeted Revision 3 probe. Each POINT belongs to one drawing version, instance path and block table record. Preserve both original geometries and the transformation. Compare native WCS XYZ using the drawing-unit tolerance from the pinned project contact rule. This is geometric evidence at the recorded elevation. Floor and engineering elevation require separate evidence.

**Failure.** Reject inconsistent sources. Missing definitions, incomplete walks, unsupported transforms and ambiguous point/device hits remain explicit. Retain independently observed contacts. Record every qualifying endpoint. Intersections, gaps, symbol envelopes and insertion positions cannot supply a POINT contact. There is no transitive traversal, including through another device or around a loop.

**Acceptance.** Exercise shared definitions, coincident devices, parallel candidate contacts, branches, interior crossings, gaps, stale pins and ordering. Replay the real source endpoints and a separate jump control. Compare the existing routing suites against their frozen Git bytes.

Run from the repository root with Python 3.11+:

```sh
python geometry-connection/neighbors.py request.json new-result.json
```

The request contains `project_id`, `registry` (path, sha256), `source` (the verified drawing_symbols input including one probe), `device_handles` (distinct top-level INSERT selectors), `contact_policy` (project rule file path, sha256 and rule_id), and `queries` (objects with edge and endpoint=start/end). Omit device_handles to search all top-level INSERT seeds from the verified probe. A supplied selection restricts device coverage. Other devices, nested POINTs, closed curves, line interiors, unacquired spaces and actual internal wiring remain outside this reverse lookup. Output is exclusive-create. Source errors return a diagnostic and a failing exit code.

## Proposed research · Design Network Continuity Evidence Research

Assess four claims separately. CAD geometry can locate a symbol connection point. Project design notes, system diagrams, legend conventions and bounded route topology may establish whether a designed network continues across the symbol. Physical terminal identity and internal electrical connectivity each need their own evidence, including applicable manufacturer documentation where necessary. Project evidence must establish any mapping between symbol points and physical terminals, including its cardinality. Cross-device design continuity remains unresolved until its project basis is verified.
