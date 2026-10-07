# Scoped panel configuration evidence

This layer composes explicitly reviewed source selections. It does not discover
regions, infer revision priority, reopen AutoCAD, or modify any acquisition code.

```powershell
$model = & ./system-diagram/Read-PanelConfigurationFixture.ps1
# Optional new artifact; an existing file is never overwritten:
$model = & ./system-diagram/Read-PanelConfigurationFixture.ps1 -Output ./local_test_data/qwb1-panel-configuration-candidate.json
powershell -NoProfile -ExecutionPolicy Bypass -File system-diagram/tests/Test-PanelConfiguration.ps1
```

## Sources and scopes

`tests/panel-configuration-fixture.json` contains the selected Handles and expected
raw strings, the two report SHA-256 values, locally registered document/view/region
IDs, and the user's confirmations. These answers do not enter generic model code.
`Read-DiagramSnapshot` is reused for TEXT/INSERT/ATTRIB. A local adapter additionally
retains the two selected closed frames and three outgoing LWPOLYLINE records,
without constructing geometry topology. Changing a report fingerprint or reviewed
raw statement requires explicit re-review. Equal filenames or Handles never migrate
confirmations. DrawingSet completeness stays unknown.

The region confirmation applies only to the specified definition snapshot,
document, region, view and title/frame anchors. Visible text confirmation preserves
the user's literal excerpt: the package phrase does not human-confirm the adjoining
SC20 specification. Identical package text on other rows remains a separate drawing
fact, without propagated visibility confirmation. The plan endpoint is explicitly
selected by the current user instruction; its older hidden `直流配电箱` declaration
is preserved but receives no new human-confirmed classification or visibility.

## Output

- `PanelInstanceCandidate`: snapshot-scoped plan INSERT, attached identifier, and
  other unchanged raw attribute declarations. It is not a configuration definition.
- `PanelConfigurationCandidate`: project-local identifier, separate definition
  snapshot, title, outer boundary and device frame, candidate declarations and rows.
- `ConfigurationAttributeCandidate`: original Handle, rawText, source snapshot,
  statement/evidence references, parser basis and candidate status. Pe and Ijs are
  independently parsed decimal declarations with literal units, not calculated or
  validated electrical values. Their case-preserved names remain Pe and Ijs.
- `DiagramRowCandidate`: reviewed line/label selections WP1, WP2 and K1. Labels
  and raw vertices are retained, without inferring a final circuit or connection.
- `DrawingFact`, `HumanConfirmation`, `ProjectRule`: distinct evidence records.
  The same-name rule applies to panels in this project only and retains its human
  source. It neither merges instances nor proves electrical connectivity.
- `BindingHypothesis(relationType=usesConfiguration)`: supported only when the
  explicitly selected identifier strings agree and both endpoint confirmations
  and the project rule are present in matching scopes. Missing support gives
  candidate; differing identifiers retain both claims in a Conflict and give
  ambiguous. Invalid/migrated scope or changed snapshot is rejected.

The current real fixture produces one instance, one supported configuration,
one supported usesConfiguration hypothesis, 11 individually sourced candidate
attributes and three outgoing row candidates. Repeated cable statements are not
deduplicated. Upstream reference text remains unresolved. A supported relationship
does not automatically copy configuration properties onto all matching plan boxes.

No Circuit, actual device connection, center path or quantity output is generated.
Existing row/field candidate models, including unresolved power bindings, are left
unchanged. Definition evidence here comes from the verified t8_t3 snapshot; it does
not rewrite or reinterpret the previously surveyed t7 row model.
