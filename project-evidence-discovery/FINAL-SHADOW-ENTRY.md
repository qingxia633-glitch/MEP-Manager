# Final Shadow entry contract

Contract: stable binding identity identifies one relation; canonical content
determines duplicate versus conflict. Provenance is retained but never distinguishes
duplicates. Same identity with differing semantic/geometric content must not remain
supported. Conflicts propagate to evidence, summaries and propagation roots.

Invariants: at most one canonical binding per ID; exact duplicates deduplicate;
conflicting variants preserve both sources; leader identity cannot silently carry
different geometry. IDs retain the preceding path/manifest independence.

Shadow entry requires an explicit nonblank string project_id and verified report
bytes. Integrity and acquisition eligibility are separate. Non-top-level reports
are non-evaluable, not proof of absent evidence. Zero bindings expose stable reasons.
Integrity is not authentication: changing report bytes and regenerating a manifest
can pass integrity verification; no reviewer/source authenticity is established.

Shadow observation fields are `report_integrity`, `acquisition_scope_status`
(`eligible` / `not_eligible`), `shadow_evaluable`, `binding_count` (all returned
candidates, not approved semantics), and nullable `zero_binding_reason`.
For zero candidates, reason priority is:

1. `acquisition_scope_not_top_level`: verified header is not the supported scope;
2. `ambiguous_or_conflicting_evidence`: observed conflicting annotation evidence;
3. `no_target_match`: a validated, relevant leader has no binding target;
4. `no_supported_leader_evidence`: no relevant validated leader chain available.

Nonzero ambiguous/conflicting candidates retain their individual statuses; a
nonzero count is not an admission decision. Generic research behavior is unchanged.

Failure: conflicting binding content, conflicting leader geometry, missing project,
or unsupported acquisition scope cannot produce a positive Shadow conclusion.
Generic research discovery project identity behavior is unchanged.

Acceptance matrix: duplicate associations with different geometry; duplicate leader
handle with different arrows; exact duplicates and provenance-only duplicates;
path/manifest/unrelated-entity stability; project/drawing/object identity controls;
missing/None/blank project; verified non-top-level; valid zero target/no-leader;
legacy failure ID plus normalized reason verification, including unknown failures
and unexpected passes. Existing green tests and all requested frozen regressions
are rerun. No historical test/fixture modification, Shadow sample, or review pack.

Out of scope: electrical approval, quantity, MLEADER expansion, ATTRIB text layering,
arbitrary raw/decoded derivation, additional exporter escapes, Chinese sentinel,
indexing/summary optimization and generic research-mode markers. Performance will
be measured in a real Shadow Run, not optimized speculatively here.
