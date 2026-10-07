# ProjectEvidenceDiscovery v0.1

Offline discovery of annotation, binding and propagation-root **candidates**. No project
semantic approval, new project rules, circuit inference, or quantity generation.

## Entry points

```powershell
python project-evidence-discovery/resolve.py --snapshot REPORT.txt --xy-tolerance 0.001 --nearby-distance 1000 --output NEW.json
python -m unittest discover -s project-evidence-discovery/tests -v
```

`--context normalized.json` accepts an already exported WCS context instead of a report.
Outputs use UTF-8, `ensure_ascii=False`, and exclusive creation: existing files are not
overwritten. Distances/tolerances are drawing units. The context radius is navigation only.

API: `annotations.load_report(path)` → normalized context;
`discovery.discover(context, xy_tolerance, nearby_distance)` → structured result.

## What is discovered

- TEXT/MTEXT and exported dimension text, with exact raw text and separate normalization.
- Attached ATTRIB ownership from the actual parent INSERT and attribute handle.
- Lexical S/S+D, specification, system, region, default-note and “余同” candidates.
- Annotation → explicitly associated leader → explicit arrow → real straight edge geometry.
- Supplied, independently evidenced object associations and bounded group witnesses.
- Typed device/edge/annotation regional observations, always membership candidates.
- Per-edge evidence completeness counts; no probability or predicted pass rate.

An S token is a lexical observation. It can occur on a symbol or in a table and does not
automatically identify an electrical line. ATTRIB ownership binds the text to its INSERT,
not to nearby lines. Device membership never becomes edge membership.

## Geometry and source contract

Normalized contexts contain `drawing_ref`, `annotations`, `targets`, `leaders`,
`object_associations`, `bounded_groups`, `memberships`, and `provenance`.

- Annotation: `handle`, `type`, `raw_text`, optional `position_wcs`, `bounds`, `parent_path`, provenance.
- Target: `id`, `target_type`, optional straight `geometry` with `type`, `vertices_wcs`,
  `closed`, `bulges`, `complete`, provenance. INSERT does not imply any electrical role.
- Leader: `handle`, `annotation_handle`, `association_status=explicit`, `arrow_wcs`,
  `vertices_wcs`, provenance. The explicit arrow must belong to the exported geometry.
- Object association: exact annotation/target ids, supported source association and provenance.
- Group: exact annotation/root target, explicit typed `bounded_set`, `scope_boundary`,
  `propagation_relation`, `termination_condition`, supported source evidence and provenance.
  These are geometric/document witnesses, not approvals of electrical semantics.

Points and targets must already be in WCS. This adapter does not infer nested transforms
from local text coordinates. It reuses `GeometryConnectionResolver._nearest_segment`
for LINE and straight LWPOLYLINE geometry; it does not implement another connection engine.
LWPOLYLINE requires an explicit bulge value for every vertex; absent values are not assumed zero.
Curved bulges are not replaced with chords. Width envelopes, arbitrary arcs/splines and
missing geometry remain unsupported. Exact XY candidate contact preserves XYZ distance
and `z_semantics=unresolved`; CAD Z is not interpreted as installation height.

MEPFULLREAD fields supported for leaders: `AnnotationHandle`/`TextHandle`, `Arrow_WCS`,
`LeaderVertex_WCS`. Classic LEADER can also use exported Raw_DXF vertices 10, explicit
arrowhead flag 71 and a **stable quoted handle** 340. Runtime enames are not handles.
MLeader nested DXF context decoding is not implemented; explicitly exported WCS fields
are supported. No arrow endpoint is inferred from nearest text or a nearby LINE.

## Evidence strength and status

`direct_object_binding`, `leader_binding`, `bounded_group_binding`,
`region_membership_candidate`, `nearby_context`, `unbound_text` are exposed separately.
`binding_status=supported` means the candidate's source association/geometry is supported;
it does **not** mean approved electrical identity. Ambiguous arrow hits remain partial.
Conflicting S/S+D candidate bindings are reported in the per-edge selection status.

“余同” with an unknown root stays unresolved. A known root with unknown bounds produces
`discovery_status=partial` and `propagation_boundary_unknown`. No global propagation occurs.
No root can be found using text distance alone. Nearby context cannot be submitted by this
module as Gate evidence; there is deliberately no automatic Gate adapter.

## Known limits and exporter diagnostics

The report adapter reads top-level ModelSpace objects and attached instance attributes.
It does not expand Xrefs/nested blocks, inspect layouts, OCR, recover proxy semantics,
infer exploded LINE/CIRCLE annotation groups, or map system diagrams to plan circuits.
Region geometry is not newly solved here: independently supplied typed observations remain
candidates. Propagation boundary discovery is a future capability, not a default assumption.

Gaps include `leader_geometry_unavailable`, `root_target_unknown`,
`propagation_boundary_unknown`, `region_or_system_scope_not_established`, and missing WCS.
No LEADER record in a snapshot does not prove the drawing has no leader expression.
The result lists required exporter fields: annotation association, stable handles, arrow
orientation/endpoint, vertices, landing/branches, full parent transform, and boundary references.

## Unicode and historical references

Snapshot drawing names are read from the Unicode DWG header, never invented from filenames.
Corrupt names are rejected unless `corrected_reference` receives an approved CorrectionEvidence
for the exact historical object id. The existing Golden correction remains scoped to its two
eligibility objects; it is not broadened to all historical files. Raw historical content is
never rewritten. Real new evidence uses the uncorrupted source snapshot drawing reference.

## Project validation

External fixture configuration: `fixtures/project-sources.json`. Three saved project reports
are inventoried independently; no cross-drawing bindings are inferred. Investigated edges:
13C9D/13CC7/13CC9 and Golden reference 13CF5. Negative fixtures: 51B44/51AA5/518D4.

Golden's reviewed project-rule/human authorization can be located as a reference source,
but is not rediscovered as a TEXT→leader binding. No Golden handle is encoded in the generic
discovery algorithm. A missing new binding never overwrites its historical approved evidence.
