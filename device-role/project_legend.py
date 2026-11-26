"""Review-only projection of verified project symbols and frozen regional evidence."""
import json
import re

from resolver import canonicalize


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def key(text):
    role, _ = canonicalize(text)
    return role if role != "unknown" else text


def is_code(text):
    return bool(re.fullmatch(r"[A-Za-z0-9]+(?:[/+-][A-Za-z0-9]+)*", text))


def specific_name(value):
    """Source selection supplies specificity; reject category lists and bare classes."""
    return (isinstance(value,str) and bool(value.strip()) and not is_code(value)
            and not any(mark in value for mark in ("、","\n","；",";"))
            and value.strip() not in {"设备","装置","箱柜","equipment","device","unknown"})


def recover(obj, symbol, catalogue):
    """Inputs are qualified by replay_project_legend; keep resolver decisions intact."""
    ident = symbol["identity"]
    old = obj["role_evidence"]
    handle = obj["handle"]
    scope = dict(project_id=obj["project_id"], drawing_ref=ident["drawing"], parent_path=obj["parent_path"])
    require(old["device_handle"] == ident["handle"] == handle and scope == old["evidence_identity"]
            and obj["parent_path"] == ident["parent_path"] == [] and obj["snapshot"] == ident["snapshot_id"]
            and scope["project_id"] == ident["project_id"] and obj["block_name"] == symbol["name"]
            and obj["provenance"]["report_sha256"] == ident["snapshot_id"], "instance identity mismatch")
    attributes = sorted(symbol["attributes"], key=lambda a:a["handle"])
    require(all(a["owner"] == handle and a["handle"] for a in attributes)
            and len({a["handle"] for a in attributes}) == len(attributes), "invalid attribute owner or identity")
    direct = [e for e in old["evidence"] if e["evidence_type"] == "instance_attrib"]
    require(all(e["source_definition_path"] == [handle] and e["source"] == ident["drawing"] for e in direct)
            and sorted((e["source_handle"],e["attribute_tag"],e["raw_value"]) for e in direct)
            == sorted((a["handle"],a["tag"],a["value"]) for a in attributes), "resolver/source attribute mismatch")

    raw = sorted({a["value"] for a in attributes if a["tag"] == "A" and isinstance(a["value"],str)})
    codes = {v for v in raw if is_code(v)}
    codes.update(a["value"] for a in attributes if a["tag"] == "$TEXT$" and isinstance(a["value"],str)
                 and is_code(a["value"]))
    previous = set(obj["candidate_types"])
    names, interpretations, trades = set(), set(), set()
    matched, basis = [], set()
    unresolved_usages = []
    for value in raw:
        if canonicalize(value)[0] != "unknown":
            names.add(key(value))
            basis.add("owner_verified_instance_name")
    for entry in sorted(catalogue, key=lambda e:json.dumps(e,sort_keys=True,ensure_ascii=False)):
        require(entry["project_id"] == ident["project_id"], "foreign project catalogue")
        label = entry["label"]
        label_type = key(label)
        row = entry["kind"] == "legend_row"
        label_keys = {label_type, *(key(v) for v in entry["names"] if not is_code(v))}
        literal = {v for v in raw if specific_name(v) and v in {label,*entry["names"]}}
        # The row supplies a scoped spelling correspondence. It never rewrites the resolver.
        if literal:
            existing_alias = previous & {label_type} if not entry["codes"] else set()
            names.update(existing_alias or {key(v) for v in literal})
            basis.add("owner_verified_instance_name")
        anchored_codes = codes.intersection(entry["codes"]) if row else set()
        if anchored_codes:
            basis.add("project_legend_exact_code")
            interpretations.add(entry.get("label_type",label_type))
            interpretations.update(key(v) for v in entry["names"] if specific_name(v))
            for obs in entry["usages"]:
                if obs["code"] in anchored_codes:
                    if specific_name(obs["name"]):
                        interpretations.add(key(obs["name"]))
                    else:
                        unresolved_usages.append(obs)
        existing = row and bool(previous & label_keys)
        if not (literal or anchored_codes or existing):
            continue
        matched.append(dict(entry, correspondence=dict(literal=sorted(literal), code=sorted(anchored_codes),
                            existing_candidate=existing, block_name_equal=symbol["name"]==entry["symbol_block"])))
        if entry["discipline"]:
            trades.add(entry["discipline"])

    # A display code can be ambiguous in the project and still agree with an
    # explicit instance name. Preserve *all* readings of the display separately.
    code_alternatives = interpretations.copy()
    if names and names <= interpretations and not (codes & set(raw)):
        interpretations = names.copy()
    options = previous | names | interpretations
    conflicts = list(old["conflicting_evidence"])
    if old["role_status"] == "conflicting" or (obj.get("device_status") == "conflicting"):
        conflicts.append("existing evidence conflict")
    if (previous and (names | interpretations) - previous) or len(names) > 1:
        conflicts.append("independent role readings disagree")
    if len({v for v in raw if v.strip()}) > 1:
        conflicts.append("competing owner-qualified name values")
    if names and interpretations and not names.intersection(interpretations):
        conflicts.append("instance name and project code disagree")
    for comparison in obj["legend_comparisons"]:
        if comparison["match_status"] == "conflicting" and any(
            entry["row_id"] == comparison["legend_row_identity"]
            and entry["provenance"] == comparison["legend_symbol_identity"] for entry in matched
        ):
            conflicts.append(dict(reason="geometry disagrees with selected legend symbol",
                                  row_id=comparison["legend_row_identity"],
                                  geometry_status=comparison["geometry_comparison_status"]))
    if conflicts:
        status = "conflicting_evidence"
    elif len(options) > 1 or (unresolved_usages and not names):
        status = "competing_interpretations"
    elif previous:
        status = "retained_regional_candidate"
    elif names:
        status = "explicit_name_candidate"
    elif interpretations:
        status = "conditional_legend_candidate"
    else:
        status = "unresolved"
    missing = []
    if not options:
        missing.append("specific owner-qualified device name or project legend correspondence")
    if status in ("conditional_legend_candidate","competing_interpretations","conflicting_evidence"):
        missing.append("independent instance symbol or project-specific disambiguation")
    definition = obj["block_definition_identity"]
    if not definition.get("block_record"):
        missing.append("verified current block definition")
    if not trades:
        missing.append("independent discipline scope")
    return dict(stable_instance_identity=dict(ident,drawing_instance_id=obj["drawing_instance_id"]),
                original_device_role_result=old, previous_candidate_types=sorted(previous),
                raw_attribute_evidence=attributes, raw_device_names=raw, raw_codes=sorted(codes),
                normalized_name_candidates=sorted(names), project_legend_evidence=matched,
                role_candidates=sorted(options), candidate_basis=sorted(basis | ({"frozen_regional_evidence"} if previous else set())),
                candidate_status=status, discipline_candidates=sorted(trades),
                code_interpretations=sorted(code_alternatives), unresolved_code_uses=unresolved_usages,
                conflicting_evidence=conflicts, competing_interpretations=sorted(options) if len(options)>1 else [],
                missing_evidence=missing, geometry_status=dict(definition=definition,types=obj["geometry_types"],
                    comparisons=[dict(row_id=c["legend_row_identity"], status=c["match_status"],
                                      geometry=c["geometry_comparison_status"]) for c in obj["legend_comparisons"]]),
                engineering_approval_status="not_approved", discipline_approval_status="not_assessed",
                approved_device_quantity=None,
                propagated_properties=[], provenance=obj["provenance"])
