# Confirmed-sample center-path prototype

Independent Windows PowerShell 5.1 prototype, with no additional dependencies.
It reads the local TXT report, never opens or writes a DWG, and does not call AutoCAD.

From the repository root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File prototype\Test-Prototype.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File prototype\Run-Prototype.ps1
```

Both commands print results; they do not save output files. To retain the JSON locally:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File prototype\Run-Prototype.ps1 | Out-File local_test_data\center-path-result.json -Encoding utf8
```

`samples.json` explicitly records the manually calibrated unit scale and user-confirmed handle pairs/chains. Layer names never establish pairing. `CenterPath.psm1` parses only those handle records, retains source vertices/bulges/layers and report SHA-256, checks chain endpoint coincidence, derives centerlines over actual projection overlap, and intersects perpendicular centerlines for strategy A. Numerical calculations remain in drawing units; mm and m are derived using the configured scale. Topology and length geometry are separate output objects. Logical connectivity uses the supplied manual confirmation, not proximity searches.

The real report is required for tests and remains under ignored `local_test_data`; it is not bundled. Tests check both sample outputs, each input's direction reversal, alternate unit scale, and rejection of a nonparallel pair. No new CAD reading capability is implemented.

Limitations: only the configured open, two-vertex, zero-bulge, coplanar XY samples; no full-drawing recognition, automatic pairing, arcs, variable-width transitions, T/cross junctions, proxy parsing, equipment routing, or final quantity takeoff. The turn uses only the supported local overlap; the unmatched continuation of 52905 is retained as evidence but excluded from length. A connection within the configured tolerance is reported with its gap, not silently treated as exact input identity. Unit calibration must be reviewed for any other drawing. JSON numeric display precision is the host serializer's responsibility; underlying computations use double precision and tests use absolute tolerance 0.00001 drawing units.
