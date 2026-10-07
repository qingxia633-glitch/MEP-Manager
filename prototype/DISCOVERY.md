# Local geometric discovery experiment

Run from the repository root (Windows PowerShell, no dependencies):

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File prototype\Run-Discovery.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File prototype\Test-Discovery.ps1
```

Run-Discovery reads only the report and discovery-window.json, then prints JSON. It never loads samples.json or discovery-expected.json. Test-Discovery completes discovery before reading the separate ground truth. It saves detailed results to ignored local_test_data/discovery-result.json. No DWG or AutoLISP is modified.

Window is manually supplied from the previously confirmed bend extent, expanded approximately 500 drawing units in XY; this is local discovery, not independent localization of a bend in a whole drawing. Layer, window, endpoint and angular tolerance, and bounded path-search depth are explicit configuration. The six answer handles appear only in the acceptance fixture. The test renames ALL report handles and checks discovery counts remain unchanged.

Process: read configured layer records; geometrically intersect segments with the window; retain original vertices and identity; build pairwise endpoint contacts using 3D numeric tolerance; enumerate simple paths of at most six edges; retain 90-degree or same-sign 45+45 turns, including collinear extensions; deduplicate reverse paths and remove contained paths of the same pattern. Pair disjoint chamfer/right-angle chains only when both oriented end runs are parallel, overlap inside the window, and have consistent nonzero signed spacing at the same elevation. No nearest-line pairing, no fixed width, no Handle hints.

The endpoint graph uses entity endpoints as vertices and pairwise tolerance contacts as connections. The reported 29 connections are contacts, not 29 distinct junction locations. Duplicate entities are retained and identified; tolerance contacts are not transitively merged into assumed physical junctions. An interior crossing alone creates no contact. Original segments intersecting the window are retained whole for provenance; pairing metrics are clipped to the window and traversal cannot continue through outside endpoints. No external geometry is searched.

Only open two-vertex LINE/LWPOLYLINE zero-bulge XY geometry is currently supported. Unsupported records are reported separately, including cases whose window membership cannot be established. Geometry cannot distinguish end caps from side edges or establish membership in other tray systems. Confidence is qualitative geometric support, not a probability. Depth limit is explicit and depthLimitHits reports truncated exploration.

Actual fixture: 14 candidates, 29 endpoint contacts, 20 maximal turn-pattern chains, one supported pair. All six gold handles are covered in order, but pair chains also contain three unconfirmed collinear extensions. This is coverage success, NOT exact segmentation or proof of system connectivity. Eight extra input candidates must not be described as eight proven false tray detections. Detailed lists and uncertainties remain in the JSON.
