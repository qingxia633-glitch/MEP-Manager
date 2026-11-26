# ProjectLegendBackedDeviceRoleVersion 1

**Contract.** This review-only overlay consumes a digest-pinned regional inventory, its two verified drawing snapshots, registry, native legend rows and a project-scoped source catalogue. The catalogue selects name-bearing ATTRIBs or legend symbol/name cells and optionally records a discipline hypothesis. It contains source selectors, never target handles, expected outcomes or quantities. Reviewed source selection is a trust input. A digest identifies the selected revision; it does not authenticate an engineer.

**Invariant.** Use the frozen DeviceRoleEvidence result, its priority and its recorded overrides verbatim. Read actual owner-qualified instance values again. Names must be recognized by the existing canonicalizer or independently qualified in the source catalogue. Keep same-literal names, scoped row correspondences, exact codes and canonical candidates separate. A known code requires an actual project legend anchor. Other observed usages of that code may introduce competition but cannot independently authorize it. Preserve original path, handle and snapshot per instance. Layer, proximity, name of a block and procurement discipline are never identity joins.

**Failure.** Reject global input hash, registry, owner and identity mismatches. Incomplete local row membership cannot authorize a correspondence. Ambiguous cell boundaries can support a conditional interpretation with the ambiguity attached. Different readings, conflicting roles or positive geometry indicating another type stay visible. Defaults remain inherited, including overridden values. Scope is the selected sources and current top-level snapshot.

**Acceptance.** Exercise foreign projects, owners, invalid cells, literal vs unknown names, empty and generic values, spelling direction, collisions, alternatives, geometry disagreements, instance priority, input order and preservation of old records. Replay every interior INSERT; count distinct instances separately from role hits and discipline candidates. The overlay cannot approve a role, installation attribute or material quantity.

Run from the repository root:

```text
python -B device-role/replay_project_legend.py --regional <frozen-directory> --inventory-sha256 <trusted-digest> --catalog <source-selectors.json> --catalog-sha256 <trusted-digest> --out <local-directory>
```

The CLI writes new prediction and comparison files exclusively. Use a fresh directory for each replay. The regional inventory retains the existing Device Role and geometry decisions. The catalogue must be prepared and frozen before showing predictions for a new assessment region.

### Source selection

A local catalogue records `project_id`, the legend drawing's `snapshot_id` (report SHA-256), and `sources`. A `legend_row` selector has a source INSERT `symbol`, native legend `region` ID, ordered `name_texts` handles in one qualified name cell, and an optional discipline hypothesis (`discipline` may be null). A `name_witness` selects an independently reviewed INSERT with a specific owner-qualified name in the source drawing. It supports the literal name only. Its row and cell membership remain null. Selectors require human review for the intended name column, fragment order and discipline. Matching verifies the selected text against the hashed native report.

A code must match the spelling of a selected legend display attribute. Competing usages are collected from top-level source-drawing INSERTs with that display tag. Where the plan supplies a specific name and a compatible polysemous display code, keep the explicit name and retain the display alternatives in `code_interpretations`. A conflicting name or geometry reading for the same selected symbol requires review. Unrelated rejected symbol comparisons remain available in the frozen inventory.

### Reading the replay

`role-candidates.json` contains one record per interior top-level INSERT. Inner `original_device_role_result` and geometry references preserve the frozen inputs. The outer status describes the review candidate. `regional-replay.json` separates single-candidate coverage, any-hypothesis coverage, overlapping type hits and discipline groups. The CSV contains the before/after review index. Independent assessment needs an unseen region, separately frozen predictions and an independently recorded human count.
