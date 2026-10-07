# Outgoing row candidates

Independent extension of the reviewed panel configuration artifact. The original
configuration and old diagram rows are not changed. No terminal search is run.

```powershell
$rows = & ./system-diagram/Read-OutgoingFixture.ps1
# Optional new artifact: existing files are protected with CreateNew.
$rows = & ./system-diagram/Read-OutgoingFixture.ps1 -Output ./local_test_data/qwb1-outgoing-row-candidates.json
powershell -NoProfile -ExecutionPolicy Bypass -File system-diagram/tests/Test-OutgoingRows.ps1
```

The fixture pins both the configuration artifact and CAD report SHA-256. Explicit
row selections and expected raw strings belong to the fixture, not the algorithm.
The adapter reuses Read-DiagramSnapshot and reads only selected direct LINE or
straight LWPOLYLINE geometry. This is not automatic row/field discovery.

Each OutgoingRowCandidate contains its configuration ID, snapshot, original row
label, geometry, raw target/power/package statements, literal conduit/method tokens,
boundary contact evidence, optional tail/gap evidence, normalized layout offsets,
shared context references, procurement-rule reference and missing information.
All statements retain Handle, rawText, Layer, coordinates and source snapshot;
geometry retains original records and coordinates with rawText=null.

The panelBoundaryContactEvidence refers specifically to the internal equipment
frame, not the outer regional border. It computes endpoint-to-frame-segment
distance in drawing-unit XYZ. Contact never establishes a real electrical port.
Endpoint reversal is supported, two contacting endpoints remain ambiguous, and a
missing contact is not snapped into place. No geometry is changed or gap filled.

Shared configuration statements are stored once at model level. Row fields contain
only their IDs: Pe/Ijs, standby arrangement and package protection claims are not
copied into row-confirmed attributes or inferred devices. This first fixture has
no observed individual switches or dynamic parameters; not_observed is limited to
the reviewed local evidence selection, not a claim of absence in all block content.

Conduit and installation methods are lexical tokens with exact spans and original
statement provenance. SC20/FC/WC are not interpreted as physical measurements or
final engineering properties. A changed/unsupported package-token layout requires
review rather than a guessed parse. The literal package clause produces one
Procurement/QuantityRuleCandidate per source: candidate/unresolved inclusion.
Neither cable nor conduit quantity is excluded.

WP1/WP2 remain independent despite repeated geometry/layout and equal power text.
K1 has null power with not_observed status, not zero and not inherited Pe. Target
names remain unbound to installed devices. No Circuit, terminal connection, center
path, quantity or procurement amount is emitted. CAD Z remains a raw coordinate.

The next read-only entry point is the already selected plan panel instance from the
upstream configuration model. Search for possible actual targets using plan-side
identifiers, symbols and local route/context evidence; do not bind by distance or
matching WP labels alone. This module does not perform that search.
