# ProjectRuleApplicabilityResolver v0.1

Evaluates **provided, independently established** facts against external versioned project rules.
Produces an unapproved `RuleBindingProposal`; no geometry, device recognition, electrical
classification, quantity calculation, or historical file mutation.

## API and evidence contract

`resolver.resolve(rule_definition, request)` accepts JSON-compatible dictionaries.
`request` contains `target_object: {id, kind: edge|device|group}`, exact `context`
(`project_id`, `drawing_ref`), and witness lists:

- `object_facts`
- `region_memberships`, `system_memberships`, `local_group_memberships`
- `explicit_bindings`
- `propagation_sources`
- `exclusions`, `conflicting_evidence`
- `provenance`

Each ordinary witness needs exact `target_id`, `target_kind`, project/drawing context,
`key`, typed `value`, `status`, `evidence_strength`, and nonempty `provenance`.
Only supported witnesses with direct-object, direct-local, system-mapping,
project-rule, or drawing-fact strength can prove a condition. Conflicting/pending
direct witnesses remain blocking. Pattern/context/external/confidence evidence
cannot fill a missing condition. This module does not verify the truth of an
attestation against CAD; witness extraction and review are upstream responsibilities.

Rules contain `rule_id`, `rule_version`, `context`, `binding_scope`, required
`conditions`, optional `scope_conditions`, positive `exclusions`, effects, and provenance.
A condition is `{condition_id, channel, key, expected}`; exact equality only.
There is no executable Python/expression evaluation or inference between keys.
For example `semantic.line_code = S` is distinct from a specification fact.
System, region, drawing, compartment and local-group rules require corresponding
scope membership conditions. Witnesses for a device never prove membership of an edge.
An object rule may also constrain `target_ids`.

## Four-valued decisions

Missing, incomplete, weak or wrong-target evidence → `unknown`. Inconsistent peer
values or explicit conflict → `conflicting`. Otherwise typed equality → true/false.
Known false required condition or hit exclusion → `not_applicable`; otherwise conflict
→ `conflicting`; otherwise unknown → `unresolved`; all true and all exclusions false
→ `applicable`. A false requirement takes precedence over an independent conflict,
but the conflict remains recorded. Empty conditions do not vacuously succeed.
Unknown exclusions block applicability. No majority voting.

`may_submit_to_project_gate` is true only for applicable proposals. This is permission
to submit, not approval. Effects on specifications/materials do not authorize a bus identity.

## Bounded “余同”

`propagation_key` requires an independently supported propagation witness containing
`source_annotation`, typed `root_target`, `propagation_relation`, a typed explicit
`bounded_set`, `propagation_boundary`, and `termination_condition`. All must be known.
The target must be in the bounded set. There is no graph traversal, global rest default,
or region-to-system inference. A supported empty set excludes all targets.
The shared propagation witness is bound to its project/drawing and rule key; it need not
already carry an edge-specific target id. The explicit bounded set supplies target membership.

## Source rules and real fixtures

`fixtures/project-rules-v01.json` preserves all **18** audited rules verbatim under
`source_rule`, with source SHA256 and JSON pointer. Their prose predicates are external
named attestations, not automatically parsed facts. S/S+D have dedicated line-identity
selectors; all scope/exclusion witnesses remain required. Unavailable witnesses stay unknown.

One **additional object-binding template** references the already reviewed Golden Gate
bundle. It proves the existing 13CF5 authorization without weakening the 18 rules or
pretending Golden has a newly discovered S label. Its historical drawing key is preserved
as an opaque context identifier, not repaired or applied to another target.

13C9D and 13CC7 fixtures reference saved automatic results and audit hashes; device role
facts are retained at device scope. They have no proven edge S/S+D selection. The fixture
preparation script is project-specific evidence packaging, not a generic document parser.

`rules.load_rules(path, repository_root)` verifies declared source file hashes.
CLI output is exclusive-create, so an existing result is never overwritten:

```powershell
python project-rule-applicability/resolve.py --rules project-rule-applicability/fixtures/project-rules-v01.json --request project-rule-applicability/fixtures/13CF5.json --rule-id reviewed-golden-semantic-binding --output new-proposal.json
python -m unittest discover -s project-rule-applicability/tests -v
```

## Gate isolation

`to_gate_evidence(proposal)` converts only an applicable edge proposal with an explicit
semantic role. The Gate-compatible bundle is **pending review**, with unresolved evidence
status. It cannot approve itself. The unchanged Gate accepts it only after separate project
review supplies the existing reviewed/supported authorization contract. Test-only synthetic
review demonstrates interface compatibility; real Shadow Gate results are never changed.

## Limits

No CAD extraction, polygon membership computation, propagation discovery, natural-language
predicate parsing, rule-authority ranking, or review authority implementation. The v0.1 DSL
uses conjunction of explicit equality predicates; compound prose/alternative mappings need
independent attestation. Conflicts remain peer conflicts rather than automatically selecting
a “better” source. Downstream formal Gate integration is deliberately not installed.
