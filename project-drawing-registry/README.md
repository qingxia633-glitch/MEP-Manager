# Project Drawing Registry v1

Contract: local report input map -> verified acquisition instances -> candidate
aliases and exact lookup. No Discovery/Gate execution or cross-sheet links.
ReportVersion is independent of ProjectDrawingRegistryVersion=1.

Identity: SHA-256 of canonical project ID, full report DWG reference, optional
verified source DWG hash, and report hash. This is an acquisition instance, not
a logical drawing, formal revision or sheet. Repeated input deduplicates; distinct
snapshots remain separate. Identical file contents at different references retain
both instances. Report paths are not identity; the source reference in the report is.

Failure: missing project/drawing, bad manifest, unknown exporter, incomplete report,
duplicate header or source hash disagreement reject the input. Without a manifest,
integrity is computed_only and registry status partial. No DWG hash substitution.
Source hashes without source bytes are declared_unverified. Missing Layout evidence
means unresolved_out_of_scope, never no Layouts. Candidate extraction uses only
an explicit label/value within the same annotation or cell, or an explicitly named
ATTRIB tag/value with owner evidence; no proximity, Field
evaluation or title-block inference. All extracted labels remain partial.

Acceptance: identity/project/revision separation, deterministic dedup/order/hash,
ambiguous lookup, malformed inputs, candidate-only labels, heterogeneous reports,
and unchanged Discovery/SHADOW. No semantic or quantity output is produced.

CLI: `python -B project-drawing-registry/resolve.py --input-map <local.json> --output <new.json>`
Input map: `{"project_id":"P","inputs":[{"report_path":"...","manifest_path":"...",
"source_dwg_path":"...","source_dwg_sha256":"..."}]}`.
Manifest and DWG fields are optional; absent manifest requires explicit encoding.
Input map and real registry outputs are private, not committed. Output is exclusive-create.
Lookup: `lookup(registry, value, kind=None)` returns zero/one/multiple matches;
multiple is ambiguous and never selects a winner. Lookup is exact NFC/casefold,
not fuzzy matching and not evidence approval.
Inline labels may describe a directory entry or another sheet. They remain
observations contained in the source DWG with `identifies_current_drawing=unresolved`.
Lookup returns their evidence/status; even one match is not logical identity approval.
