# Independent block definition probe

## Generic one-level probe

APPLOAD `BlockDefinitionProbe.lsp`, then run `MEPONELEVELBLOCKPROBE`.
Enter any exact block definition name. Optionally enter its parent definition
and internal INSERT Handle; the command verifies both owner and referenced name.
Blank parent means definition-only provenance, never an inferred instance.
Save `block-definition-probe.txt` in a fresh directory; existing files are protected.

Each direct entity retains the definition path, internal Handle, raw DXF,
polyline closure flag and getter bounding box. Bounding boxes are labelled as
direct-definition getter results, not independently frame-verified or instance WCS.
Errors retain identity and unknown status and increase ReadErrorCount. Nested
INSERTs are recorded without expansion; duplicates are retained. No device
binding, engineering connection or quantity is produced. Parent INSERT raw DXF
preserves the transform for later analysis; no ModelSpace instance is inferred.

The K1-4 export inputs are target `PX-B-P01(-1F)-JSK$0$ERFER`, parent
`PX-B-P01(-1F)-JSK`, internal INSERT `835`. These are user inputs, not algorithm rules.
This export does not change the previous local report or its `830` unknown record.
Offline static contracts: `Test-OneLevel.ps1`; real AutoCAD acceptance remains separate.

## Target subblock pass

Reload the same LISP and run `MEPSUBBLOCKPROBE` to read ONLY `$element$00000576`
and `A$C705C5744`. This command does not inspect the four outer definitions.
Save `block-definition-probe.txt` in a fresh directory, for example
`local_test_data/subblock-probe-20260916/`. Direct geometry, text/ATTDEF, attached
attributes and layer/color records use the same format. Deeper INSERT references
are recorded without traversal. DefinitionIsDynamicBlock and its read/error status
are getter-only metadata; a failed query is not interpreted as false.

The previous report contains references to these blocks, not their internal
definitions. Their symbol details and replacement-line geometry remain pending
manual export. To compare replacement geometry later, use the definition base
point and the outer INSERT transform; do not compare local coordinates from
different frames directly. The source attribute `S="断路器"` remains an attribute
claim, separate from human composite-symbol confirmation.

`Test-RealProbe.ps1` runs the existing real outer-definition report through all
six pairs/four comparison modes. It fixes the zero/single-field PowerShell array
unwrapping regression and preserves the reviewed 81/81 vs 79/81 content results.
Style/visibility results compare independent multisets: identical counts do not
prove the same entities have the same visibility. Combined content differences
and source records must still be inspected for swaps. No prior report is rewritten.

APPLOAD BlockDefinitionProbe.lsp, then run MEPBLOCKPROBE in the system drawing.
The explicit diagnostic target list is *U401, *U402, *U403, *U404 only; no parameter
meaning or name-to-state rule is encoded. Select a fresh directory and save
block-definition-probe.txt. Existing paths are refused. The main extractor is not
loaded, called or modified. No block editing, exploding or visibility switching.

Reads direct block entities through the Blocks collection. Retains definition
header/base point, entity identities, raw non-binary DXF, layer records, raw color
and ByLayer/ByBlock source, linetype, lineweight, DXF60, local geometry, TEXT/MTEXT
DXF 1/3 strings, INSERT reference names. Owned POLYLINE vertices / ATTRIB are recorded
as subentities; INSERT definitions are not recursively traversed. Raw coordinates
may be OCS, and are never claimed to be transformed WCS. Layer 0/ByBlock styling
cannot be resolved to screen colors without the instance context.

Offline comparison (prints JSON, writes no output file):

```powershell
./block-probe/Compare-Blocks.ps1 -Report <path>/block-definition-probe.txt -Tolerance 0.00001
./block-probe/Test-Probe.ps1
```

Comparison preserves multiplicity using bipartite matching, ignores identities and
pointer fields, retains entity-field order, and compares geometry/style/visibility
and combined content separately. Definition headers/base points are compared too.
Tolerance is an absolute component tolerance for numeric geometry fields (angles
remain in radians). Reversed lines or alternate equivalent DXF encodings may be
reported different; this is conservative record comparison, not geometric proof.
Unsupported/binary data, extension dictionaries, XData and evaluated visibility are
not fully recovered. Error/incomplete/binary-omission reports are rejected by the
comparison reader. Identity/pointer differences are not content differences.

Entity membership alone does not prove visibility. Visibility comparison reports
DXF/layer-flag candidate differences only. Red wiring and green composite switch
roles require independent evidence, never assignment by raw color alone.

Human observation retained: at the inspected zoom, selected 20A/*U401 and 32A/*U402
instances had no obvious red-line or green composite-symbol shape difference.
This local observation does not override raw definition differences or propagate
to every instance. Real definition comparison is pending manual AutoCAD export.
