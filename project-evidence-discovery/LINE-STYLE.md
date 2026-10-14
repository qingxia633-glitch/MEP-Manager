# Line Style Evidence Acquisition v0.1

## Contract

Exporter `2.5-line-style-evidence-v1`, independent `StyleEvidenceVersion="1"`.
ModelSpace top-level only. LINE, LWPOLYLINE, POLYLINE, ARC, SPLINE and other
entities retain separate entity/layer raw records. No style-based binding.
Each `Style.<field>` has `.Status`, `.Value` (only when read), and `.Source`.
States: read / missing / unavailable / unsupported. Raw DXF is retained alongside
getter-derived values; absent DXF is not replaced with a fabricated default.
Getter failure is unavailable. Layer lookup failure cannot use another layer.

## Invariants

- Entity ByLayer/ByBlock remains raw; layer evidence is a separate object.
- No final effective style. Per-property hints only: direct, bylayer_candidate,
  unresolved_byblock, unresolved. ByLayer on Layer 0 and unknown scope remain unresolved.
- New style fields require both the new exporter and style contract marker.
  Old reports have missing style fields, but existing width/flag raw records can
  be retained without pretending they were newly acquired.
- No semantic inference, new target geometry, Gate, quantities or proxy children.
- Viewport/plot style is unresolved_out_of_scope. No global PLINEGEN substitution.

## Failure / acceptance matrix

| Input | Required result |
|---|---|
| Explicit ACI/RGB/name/scale/weight | Value and original source preserved |
| ByLayer / ByBlock | Mode retained; never rewritten to explicit |
| Separate layer color/linetype/state | Separate evidence with layer identity |
| Missing/invalid/duplicate field or source | Non-read state; no usable value |
| Missing/foreign layer identity | No bylayer_candidate |
| Old/unknown version | No new-style claim; legacy widths retained |
| Polyline widths/flags | Ordered raw vertices; generation from object flags only |
| Proxy/custom | Class and marker only; no child lines |
| Adapter JSON round trip | Exact structured evidence retained |
| Style perturbation | Existing Discovery decisions unchanged |

Unit fixtures validate software only. Isolated AutoCAD acquisition must separately
validate LINE/LWPOLYLINE/ARC through exporter and adapter. Existing real batch must
remain 3 PASS with zero FP/FN/semantic overreach. Existing legacy failures remain
separately classified; historical inputs/expected/frozen files are immutable.

## Structured fields

`load_report()` adds `style_evidence[]`, one independent record per exported
entity, carrying project/drawing/report hash/handle/parent path provenance.
`discover()` does not consume this collection.

- Entity: `entity_color_mode`, `entity_aci`, `entity_truecolor_rgb`,
  `entity_colorbook_name`, `entity_linetype`, `entity_linetype_mode`,
  `entity_linetype_scale`, `entity_lineweight`, `entity_lineweight_mode`,
  `entity_visibility`.
- Layer: `layer_name`, `layer_color_mode`, `layer_aci`, `layer_truecolor_rgb`,
  `layer_colorbook_name`, `layer_linetype`, `layer_lineweight`, `layer_on`,
  `layer_frozen`, `layer_locked`, `layer_plottable`, `layer_transparency`.
- Polyline: constant width (LWPOLYLINE DXF 43), ordered start/end vertex widths,
  raw flags, generation hint from flag 128. Old POLYLINE has distinct header
  default widths, not an invented constant-width field. 3D/mesh/polyface
  generation interpretation is unsupported. Missing widths are not zero-filled.

Lineweight values remain native DXF/COM integer values, including inheritance
sentinels; no unit conversion or final display/plot width is supplied. Encoded
layer transparency DXF 440 is preserved raw when present; decoded transparency
is explicitly unsupported. Resolution hints are per property, not a final
entity effective style. Malformed/contradictory values cannot yield direct or
bylayer_candidate hints. Partial acquisition retains raw fields but no direct
resolution hint. No LTYPE pattern, MLINESTYLE or proxy-graphics interpretation.

## Runtime validation scope

`tests/validate-line-style-acquisition.lsp` requires an empty, unmodified isolated
CAD document. It creates synthetic LINE/LWPOLYLINE/ARC entities and calls the
production `mep2:details` exporter. It never saves a DWG. This validates actual
AutoCAD object access, not a real project benchmark or manual MEPFULLREAD dialog.
The wrapper names its report drawing as an isolated validation artifact.

AutoCAD 2021 Core Console was exercised during this change. DXF entity and layer
fields, RGB decoding, and polyline flags/width records reached the adapter.
COM object access was unavailable in that host: properties absent from DXF stay
missing; full desktop/compatible-host getters remain unverified. The first emitted
LWPOLYLINE widths were zero after CAD normalization and were preserved as zero.
A second isolated run omitted the constant-width override and verified actual
nonzero vertex widths 1/2 and 2/3, explicit ACI 4 and lineweight 50.
POLYLINE/SPLINE/proxy-specific real-host cases remain unverified; software
contract tests do not promote them to verified project acquisition.

Reports are immutable inputs. Generate manifest v2 only after file completion,
using the observed encoding and exact report bytes (no self-referential hash).
Existing 2.4 reports and their manifests remain valid legacy inputs with missing
new styles. The benchmark runner's current input-version policy is unchanged;
this change does not admit 2.5 benchmark inputs or new semantic bindings.
