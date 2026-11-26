"""Replay a pinned legend-row / plan comparison into a new evidence file."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

from matching import compare_set, one, values

ROOT = Path(__file__).resolve().parents[1]
for folder in ("project-evidence-discovery", "targeted-native-probe"):
    sys.path.insert(0, str(ROOT / folder))
from annotations import field
from report_manifest import verify_manifest
from report_text import serialized_field, text_record
from verify import validate, validate_trace


# Several repository modules have a resolver.py. Bind to the Device Role source explicitly.
_role_spec = importlib.util.spec_from_file_location("legend_device_role", ROOT / "device-role/resolver.py")
_role = importlib.util.module_from_spec(_role_spec)
_role_spec.loader.exec_module(_role)
canonicalize = _role.canonicalize


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def load_probe(spec, project, drawing, dwg_sha):
    request = read(spec["request"])
    manifest = read(spec["manifest"])
    data = Path(spec["report"]).read_bytes()
    records = [json.loads(line) for line in data.decode("utf-8-sig").splitlines() if line.strip()]
    trace = Path(request["dbmod_trace_path"])
    probe_dwg = Path(request["drawing_path"])
    require(probe_dwg.name == drawing and request["project_id"] == project and
            digest(probe_dwg) == dwg_sha and request["collector_revision"] == 3,
            "probe/drawing version mismatch")
    validate(records, request, dwg_sha)
    validate_trace(trace.read_text(encoding="utf-8-sig"))
    expected = dict(manifest_version="2", report_format="TargetedNativeProbe/1", encoding="utf-8-sig",
                    hash_scope="exact completed report bytes", report_identity=records[0],
                    report_sha256=hashlib.sha256(data).hexdigest(), report_bytes=len(data),
                    request_sha256=digest(spec["request"]), dbmod_trace_sha256=digest(trace),
                    dwg_sha256_before=dwg_sha, dwg_sha256_after=dwg_sha)
    require(expected == manifest and expected["report_sha256"] == spec["sha256"]
            and records[0].get("collector_revision") == 3, "probe manifest mismatch")
    return records


def definition_coverage(records, definition, members, walk_ended):
    """Qualify only direct block-local geometry in a previously verified report."""
    btr = definition["block_record_handle"]
    nodes = {r["handle"]: r for r in records if r["kind"] == "node"}
    definitions = {}
    for record in records:
        if record["kind"] == "insert_definition":
            definitions.setdefault(record["insert"], []).append(record)
    reasons = []
    if not walk_ended:
        reasons.append("member walk not verified")
    if any(n["read_status"] != "read" for n in nodes.values()):
        reasons.append("unread object; ownership or dependencies not independently verified")
    if any(n["entity_type"] == "INSERT" for n in members):
        reasons.append("nested definition dependency unverified")
    subject = {n["handle"] for n in members} | {definition["insert"], definition["block_begin_handle"], btr}
    dependencies = []
    for ref in records:
        if ref["kind"] != "reference" or ref["source"] not in subject or ref["role"] == "owner":
            continue
        if ref["source"] == btr:
            # Backreferences to INSERTs and the BTR's own BLOCK marker do not
            # contribute symbol primitives. Preserve the records in the probe.
            if ref.get("section") == "{BLKREFS" and ref["code"] == 331:
                continue
            ungrouped = ref.get("section") is None and ref["role"] == "uninterpreted_reference"
            if ungrouped and ref["code"] == 360 and ref["target"] == definition["block_begin_handle"]:
                continue
            # Revision 3 serializes the null layout ID as a session token.
            target = ref.get("target")
            if (ungrouped and ref["code"] == 340 and isinstance(target, dict)
                    and target.get("reference_status") == "unresolved_not_dereferenced"
                    and target.get("session_token") in ("<图元名: 0>", "<Entity name: 0>")
                    and [g for g in definition.get("block_record_raw", []) if g[0] == 340]
                    == [[340, "ENAME", target]]):
                continue
        dependencies.append(ref)
    if dependencies:
        reasons.append("unverified dependency of current definition or INSERT")
    gaps = []
    for gap in (r for r in records if r["kind"] == "gap"):
        node = nodes.get(gap.get("handle"), {})
        path = node.get("traversal_path") or []
        owner = node.get("owner")
        defs = definitions.get(path[0], []) if path else []
        seed = nodes.get(path[0], {}) if path else {}
        localizable = (gap["reason"] == "unsupported_object_interpretation_raw_retained"
                       and node.get("read_status") == "read" and node.get("entity_type") == "SOLID"
                       and len(path) == 2 and owner and len(defs) == 1 and defs[0]["identity_status"] == "read"
                       and owner == path[1] == defs[0]["block_record_handle"]
                       and seed.get("entity_type") == "INSERT" and seed.get("parent_path") == []
                       and seed.get("parent_path_status") == "top_level_verified"
                       and values(seed.get("raw", []), 2) == [defs[0]["block_name"]]
                       and path[0] in records[0]["seeds"])
        disposition = "unattributed_or_nonlocal"
        if localizable:
            disposition = "local_raw_requires_field_validation" if owner == btr else "other_definition"
        else:
            reasons.append("unqualified gap: " + str(gap.get("handle")))
        gaps.append(dict(raw_gap=gap, owner=owner, path=path, disposition=disposition))
    return dict(report_integrity="verified", member_walk_verified=walk_ended,
                shared_dependency_status="unresolved" if dependencies or any(n["entity_type"] == "INSERT" for n in members)
                else "no_unverified_direct_geometry_dependency",
                entity_read_status={n["handle"]:n["read_status"] for n in members},
                gaps=gaps, unverified_dependencies=dependencies, blocking_reasons=reasons)


def attach_definition(symbol, records, probe_sha):
    h = symbol["identity"]["handle"]
    defs = [r for r in records if r["kind"] == "insert_definition" and r["insert"] == h]
    if not defs:
        return
    require(len(defs) == 1 and h in records[0]["seeds"], "ambiguous/non-seed definition")
    d = defs[0]
    if d["identity_status"] != "read":
        return
    nodes = [n for n in records if n["kind"] == "node"]
    seed = next(n for n in nodes if n["handle"] == h)
    require(seed["parent_path_status"] == "top_level_verified" and seed["parent_path"] == []
            and seed["entity_type"] == "INSERT" and seed["layout"] == "Model"
            and one(seed["raw"], 2) == d["block_name"] == symbol["name"]
            and d["effective_block_name"] == symbol["effective_name"], "probe/report INSERT mismatch")
    btr = d["block_record_handle"]
    members = sorted((n for n in nodes if n.get("owner") == btr and n["handle"] != d["block_begin_handle"]),
                     key=lambda n:n["handle"])
    traversals = {tuple(n.get("traversal_path") or []) for n in members}
    complete = False
    if len(traversals) == 1:
        path = next(iter(traversals))
        # The probe enumerates each block once; several seed INSERTs can share it.
        if len(path) == 2 and path[1] == btr:
            enumerator = path[0]
            same_definition = any(r.get("kind") == "insert_definition" and r["insert"] == enumerator
                                  and r["block_record_handle"] == btr for r in records)
            calls = [idx for idx,r in enumerate(records) if r.get("kind") == "dbmod_stage"
                     and r["target_context"] == enumerator and r["stage"] == "block_definition"
                     and r["call"] == "ENTNEXT"]
            enumerated_seed = next(n for n in nodes if n["handle"] == enumerator)
            # One additional ENTNEXT starts the attached ATTRIB walk (DXF 66).
            expected = len(members) + int(values(enumerated_seed["raw"], 66) == [1])
            if same_definition and len(calls) == expected and members:
                # Rev 3 calls ENTGET for each non-nil successor. A trailing ENTGET
                # without an emitted member cannot distinguish ENDBLK from read failure.
                after = records[calls[len(members)-1] + 1]
                complete = not (after.get("stage") == "entity_data" and after.get("call") == "ENTGET"
                                and after.get("target_context") == enumerator)
    coverage = definition_coverage(records, d, members, complete)
    attrs = sorted((n["handle"], one(n["raw"], 2), one(n["raw"], 1)) for n in nodes
                   if n.get("owner") == h and n["entity_type"] == "ATTRIB")
    require(attrs == sorted((a["handle"], a["tag"], a["value"]) for a in symbol["attributes"]),
            "full report / probe instance ATTRIB disagreement")
    definition = {k:symbol["identity"][k] for k in ("project_id","drawing","dwg_sha256")}
    definition.update(block_begin=d["block_begin_handle"], block_record=btr, probe_sha256=probe_sha)
    symbol.update(definition=definition, base=one(d["block_begin_raw"], 10),
                  enumeration_status="verified_member_walk_ended" if complete else "incomplete",
                  inventory_verified=not coverage["blocking_reasons"], definition_coverage=coverage,
                  transform=seed["raw"], members=members,
                  defaults=[dict(handle=n["handle"], tag=one(n["raw"],2), value=one(n["raw"],1))
                            for n in members if n["entity_type"] == "ATTDEF"])


def drawing_symbols(spec, project, handles):
    path = Path(spec["report"])
    data = path.read_bytes()
    verified = verify_manifest(data, path, "utf-8-sig", spec["manifest"])
    identity = verified["report_identity"]
    # Report headers serialize backslashes. Verify the actual source copy as well as the probe copy.
    dwg = Path(identity["drawing"].replace("\\\\", "\\"))
    require(dwg.resolve() == Path(spec["dwg"]).resolve() and digest(dwg) == spec["dwg_sha256"]
            and verified["report_sha256"] == spec["sha256"], "report drawing/version pin mismatch")
    require(identity["model_space_top_level"] == "included" and identity["nested_blocks"] == "not expanded"
            and identity["acquisition_mode"] == "ModelSpaceTopLevelAllLayers"
            and identity["extractor_version"] == "2.8-field-graph-evidence-v1",
            "unsupported full-report contract or scope")
    text = data.decode("utf-8-sig")
    header, *entities = re.split(r"(?m)(?=^EntityHandle=)", text)
    require(text.rstrip().splitlines()[-1].startswith("END_OF_REPORT:") and field(text, "ReadErrorCount") == "0"
            and (field(header, "AllLayers") or "").startswith("included")
            and field(text, "SelectedEntityTotal") == str(len(entities)),
            "incomplete report")
    records = load_probe(spec["probe"], project, dwg.name, spec["dwg_sha256"]) if spec.get("probe") else []
    wanted = set(handles)
    found = {}
    for rec in entities:
        h = field(rec, "EntityHandle")
        if h not in wanted:
            continue
        require(h not in found and field(rec,"DXF_Type") == "INSERT", "ambiguous/non-INSERT target")
        ident = dict(project_id=project, drawing=dwg.name, parent_path=[], handle=h,
                     snapshot_id=spec["sha256"], dwg_sha256=spec["dwg_sha256"])
        attrs = []
        for attr in re.split(r"(?m)(?=^AttributeTag=)", rec)[1:]:
            ah, owner = field(attr,"AttributeLayout.LayoutEntityHandle"), field(attr,"AttributeLayout.ParentINSERTHandle")
            require(ah and owner == h, "missing ATTRIB owner")
            value = text_record(serialized_field(attr,"AttributeText_RAW"))["decoded_text"]
            attrs.append(dict(handle=ah, owner=h, tag=field(attr,"AttributeTag"), value=value,
                              lexical_role=canonicalize(value)[0] if isinstance(value, str) else "unknown"))
        symbol = dict(identity=ident, name=field(rec,"BlockName"), attributes=attrs,
                      insertion_wcs_report_literal=field(rec, "Insertion_WCS"),
                      effective_name=field(rec,"EffectiveName_RAW") if field(rec,"EffectiveName_RAW_Status") == "read" else None,
                      dynamic=field(rec,"IsDynamicBlock") if field(rec,"IsDynamicBlock_Status") == "read" else None)
        if records:
            attach_definition(symbol, records, spec["probe"]["sha256"])
        found[h] = symbol
    require(set(found) == wanted, "requested instance missing in current report")
    return found


def membership(rows, symbol):
    found = []
    i = symbol["identity"]
    source = {k:i[k] for k in ("project_id", "drawing", "snapshot_id")}
    for region in rows["regions"]:
        require(region["provenance"] == source, "foreign legend region")
        for row in region["rows"]:
            cells = [c for c in row["cells"] if i["handle"] in c["members"]]
            if not cells:
                continue
            require(row["provenance"] == source, "foreign legend row")
            obj_id = region["objects"][i["handle"]]["identity"]
            require(obj_id == dict(project_id=i["project_id"], drawing_ref=i["drawing"],
                                   handle=i["handle"], snapshot_id=i["snapshot_id"], parent_path=[])
                    and region["objects"][i["handle"]]["kind"] == "INSERT", "legend symbol mismatch")
            texts, roles = [], []
            for h in sorted(set(row["original_members"] + row["row_only_candidates"])):
                obj = region["objects"][h]
                if obj.get("decoded_text"):
                    item = dict(handle=h, text=obj["decoded_text"],
                                membership="row_only" if h in row["row_only_candidates"] else "cell",
                                instance_applicability="not_established",
                                cell_ids=[c["cell_id"] for c in row["cells"] if h in c["members"]])
                    texts.append(item)
                    role, _ = canonicalize(item["text"])
                    if role != "unknown" and item["membership"] == "cell":
                        roles.append(dict(role=role, source_handle=h, basis="row lexical candidate"))
            statuses = {row["evidence_status"], *(c["evidence_status"] for c in cells)}
            if not statuses <= {"bounded", "ambiguous"}:
                status = "unresolved"
            elif len(cells) == 1 and statuses == {"bounded"}:
                status = "bounded"
            else:
                status = "ambiguous"
            found.append(dict(row_id=row["row_id"], status=status,
                              symbol_cells=[c["cell_id"] for c in cells], texts=texts, lexical_roles=roles,
                              column_role_candidates=row.get("column_role_candidates", []),
                              scope="observed legend region", provenance=source))
    return found or [dict(row_id=None, status="unresolved")]


def run(request):
    project = request["project_id"]
    require(isinstance(project,str) and project.strip(), "missing project")
    pairs = request["pairs"]
    ls = drawing_symbols(request["legend_drawing"], project, [a for a,_ in pairs])
    ps = drawing_symbols(request["plan_drawing"], project, [b for _,b in pairs])
    require(digest(request["rows_path"]) == request["rows_sha256"], "legend rows changed")
    rows = read(request["rows_path"])
    require(rows.get("NativeLegendRowEvidenceVersion") == 1, "legend version")
    comparisons = [(ls[a], ps[b], row) for a,b in pairs for row in membership(rows, ls[a])]
    return dict(DeviceLegendInstanceMatchVersion=1, symbols=dict(legend=ls, plan=ps),
                rows_sha256=request["rows_sha256"], matches=compare_set(comparisons))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request")
    parser.add_argument("output")
    args = parser.parse_args()
    result = run(read(args.request))
    with Path(args.output).open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, allow_nan=False, indent=2)
