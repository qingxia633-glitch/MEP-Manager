# MTEXT Structure Evidence v0.1

## Contract

An additive, read-only `mtext_structure` collection derived from the authoritative
MTEXT entity's exporter-decoded string. ReportVersion remains unchanged. The source
entity, serialized text, decoded text, layout and provenance are never replaced.
The entry point `structure_record(annotation, snapshot_id)` does not approve rules.
Adapter attaches the collection; Discovery exposes it separately from bindings.

Paragraph spans are zero-based, half-open **Unicode character offsets in the
entity's decoded_text**, not report byte offsets or serialized-string offsets.
`raw_fragment == decoded_text[start:end]`. Paragraph decoded_text is conservative:
formatting remains verbatim, rather than being stripped into purported display text.
Separators have their own spans. Joining fragments and separators recovers the source.
Identity includes project, drawing, full parent path, MTEXT handle, snapshot hash,
paragraph index and source span. Missing identity/decode evidence is unresolved.

## Invariants and support matrix

| Input | Structural result |
| --- | --- |
| Plain text | One paragraph; read |
| Explicit unescaped `\P` | Ordered paragraphs, including empty paragraphs |
| Width/bbox/visual wrapping | No extra paragraph |
| Escaped backslash/braces | Preserved atomically; partial display interpretation |
| Semicolon controls F/f/H/W/T/C/c/Q/A/p/S | Payload preserved, never split inside it; partial |
| Formatting groups, Unicode escapes, LF/CR | Preserved; partial, no inferred break |
| Unknown/truncated control or Field expression | Preserve remainder unsplit; partial |
| Failed exporter decoding or unknown/nested scope | Unresolved; no paragraphs |

Only paragraph boundaries are interpreted. Font, stacked text, color, width,
height, Unicode controls and formatting are not rendered. List-marker and heading
matches are lexical candidates only, at literal text starts; they create no hierarchy.

## Failure / fail-closed

No raw-text fallback on failed decoding. Unknown controls stop further boundary
recognition rather than guessing their payload extent. No paragraph feeds proximity,
binding admission, semantic approval or propagation. No paragraph bbox is fabricated.
No Gate, units, quantity or assumption execution exists in this contract.

## Acceptance / adversarial matrix

Plain and multi-paragraph order; escaped `\\P`; unknown/malformed controls;
format payload containing `\P`; formatting/raw span preservation; Unicode;
numbered/bullet/heading lexical matches; empty paragraphs; missing identity;
cross-parent/snapshot identity separation; original entity unchanged; adapter and
Discovery retain structure without new bindings/scope. Real report samples retain
independent raw slices. Historical current/legacy tests, batch and frozen hashes
remain independently checked. Synthetic fixtures are software tests, not project rules.
