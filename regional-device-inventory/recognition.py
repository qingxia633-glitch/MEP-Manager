"""Two independent readers of the same inventory. Evidence is joined only by native identity."""
import importlib.util
import re
import sys
from pathlib import Path

from inventory import identity, merge_evidence, reconcile
from survey import field, point

ROOT = Path(__file__).resolve().parents[1]
MATCHER = ROOT / "device-legend-instance-matching"
sys.path.insert(0, str(MATCHER))
spec = importlib.util.spec_from_file_location("regional_frozen_matcher", MATCHER / "resolve.py")
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


def load_symbols(source, project, requested):
    if native.digest(source["manifest"]) != source["manifest_sha256"]:
        raise ValueError("full-report manifest changed")
    probes = []
    handles = set(requested)
    for probe in source["probes"]:
        records = native.load_probe(probe, project, Path(source["dwg"]).name, source["dwg_sha256"])
        probes.append((probe, records))
        handles.update(r["insert"] for r in records if r["kind"] == "insert_definition")
    symbols = native.drawing_symbols(source, project, handles)
    for probe, records in probes:
        for h in sorted(set(records[0]["seeds"]) & symbols.keys()):
            native.attach_definition(symbols[h], records, probe["sha256"])
    return symbols


def instance_transform(record):
    if (field(record, "Style.entity_visibility.Status") != "read" or
            field(record, "Style.entity_visibility.Value") != "true"):
        return None
    raw = []
    for code, key in [(10,"Insertion_OCS"), (210,"Normal_DXF210")]:
        literal = field(record, key)
        if not point(literal):
            return None
        raw.append([code, "LIST", literal.strip("()").split()])
    groups = re.findall(r"(?m)^BlockTransform_or_Array_DXF=\((\d+) \. ([-+.\d]+)\)$", record)
    if any(sum(k == str(n) for k,_ in groups) != 1 for n in (41,42,43,50,70,71)):
        return None
    for k,v in groups:
        raw.append([int(k), "INT" if k in ("70","71") else "REAL", int(v) if k in ("70","71") else v])
    for k,v in re.findall(r'(?m)^StyleRawEntityDXF=\((8|6|62|420|370) \. (.+)\)$',record):
        raw.append([int(k), "STR" if k in ("8","6") else "INT",
                    v.strip('"') if k in ("8","6") else int(v)])
    return raw


def qualify_shared(symbol, donors, record):
    name = symbol["name"]
    if (not name or name.startswith("*") or symbol["dynamic"] != ":vlax-false"
            or symbol["effective_name"] != name or symbol["identity"]["parent_path"] != []):
        return
    candidates = [d for d in donors if d["name"] == d["effective_name"] == name
                  and d["dynamic"] == ":vlax-false"
                  and all(d["identity"][k] == symbol["identity"][k] for k in
                          ("project_id","drawing","dwg_sha256","snapshot_id"))]
    if len({d["definition"]["block_record"] for d in candidates}) != 1:
        return
    if not all(d.get("inventory_verified") for d in candidates):
        return
    donor = min(candidates,key=lambda d:d["identity"]["handle"])
    transform = instance_transform(record)
    if transform is None:
        return
    for k in ("definition","members","base","defaults","inventory_verified","definition_coverage"):
        symbol[k] = donor[k]
    symbol.update(transform=transform, definition_source_insert=donor["identity"]["handle"])


def role_context(symbols, project, source):
    instances = {}
    defs = {}
    def attributes(items):
        return [dict(handle=a["handle"],tag=a["tag"],raw_value=a["value"] or "") for a in items]
    for h,s in symbols.items():
        instances[h] = dict(handle=h,block_name=s["name"],effective_block_name=s["effective_name"],
                            parent_path=[],attributes=attributes(s["attributes"]))
        if s.get("inventory_verified") and s.get("definition") and not s.get("definition_source_insert"):
            entry = dict(defaults=attributes(s["defaults"]),children=[],complete=True,
                         source=s["definition"]["probe_sha256"])
            if s["name"] in defs and defs[s["name"]]["defaults"] != entry["defaults"]:
                raise ValueError("contradictory current block defaults")
            defs[s["name"]] = entry
    return native._role.RoleContext(Path(source["dwg"]).name,instances,defs,project_id=project,
                                     provenance=[dict(report_sha256=source["sha256"],
                                        donor_scope="regional top-level INSERTs and verified plan probe INSERTs")])


def row_label(symbol, row, label_handle):
    items = [item for item in row.get("texts", []) if item["handle"] == label_handle]
    if len(items) != 1 or items[0]["membership"] != "cell":
        raise ValueError("legend label has no native row cell")
    raw = items[0]["text"]
    # The map selects a text carrier. A model, mounting instruction or arbitrary
    # cell in that same row cannot supply a role. Check the legend's name tag.
    names = {a["value"] for a in symbol["attributes"] + symbol.get("defaults", [])
             if a["tag"] == "A" and a.get("value")}
    if raw not in names:
        raise ValueError("legend cell has no corroborating legend name evidence")
    role = native.canonicalize(raw)[0]
    return dict(raw=raw, type=raw if role == "unknown" else role,
                source=items[0], row_id=row["row_id"])


def classify(rows, records, config):
    objects = {r["handle"]:r for r in rows if r["entity_type"]=="INSERT" and r["boundary_relation"]=="inside"}
    plan = load_symbols(config["plan"], config["project_id"], objects)
    legends = load_symbols(config["legend"], config["project_id"], config["labels"])
    donors = [s for s in plan.values() if s.get("definition")]
    for h,r in objects.items():
        s = plan[h]
        if not s.get("definition"):
            qualify_shared(s,donors,records[h])
        r["block_definition_identity"] = s.get("definition") or dict(name=s["name"], status="block_record_unverified")
        r["definition_source_insert"] = s.get("definition_source_insert")
        r["dynamic_status"] = s["dynamic"]
        r["cohort"] = "known_review" if h in config["known_plan_handles"] else "outside_fixed_development_pairs"
    if native.digest(config["rows_path"]) != config["rows_sha256"]:
        raise ValueError("legend evidence hash mismatch")
    legend_rows = native.read(config["rows_path"])
    if legend_rows.get("NativeLegendRowEvidenceVersion") != 1:
        raise ValueError("legend contract mismatch")
    triples = []
    labels = {}
    for legend_handle, label_handle in sorted(config["labels"].items()):
        s = legends[legend_handle]
        for row in native.membership(legend_rows,s):
            try:
                label = row_label(s,row,label_handle)
            except ValueError as error:
                label = dict(type=None, raw=None, source_handle=label_handle, reason=str(error))
            labels[legend_handle,row["row_id"]] = label
            triples.extend((s,plan[h],row) for h in sorted(objects))
    channels = []
    ctx = role_context(plan,config["project_id"],config["plan"])
    for h,obj in objects.items():
        channels.append((identity(obj),("role",native._role.resolve_device_role(h,ctx))))
    for m in native.compare_set(triples):
        h = m["instance_identity"]["handle"]
        m["regional_row_label"] = labels[m["legend_symbol_identity"]["handle"],m["legend_row_identity"]]
        channels.append((identity(objects[h]),("legend",m)))
    for key, entries in merge_evidence(channels).items():
        obj = objects[key[-1]]
        role = next(result for channel,result in entries if channel=="role")
        pairs = [result for channel,result in entries if channel=="legend"]
        viable = [m for m in pairs if m["match_status"] in ("candidate","ambiguous","supported")]
        geo = {m["regional_row_label"]["type"] for m in viable if m["regional_row_label"]["type"]}
        roles = {role["canonical_role"]} - {"unknown"}
        if role["role_status"] == "conflicting":
            roles.update(e["canonical_role"] for e in role["conflicting_evidence"] if e["canonical_role"]!="unknown")
        explicit_conflict = any("instance ATTRIB role differs from legend role candidate" in
                                m["conflicting_evidence"] for m in pairs)
        types,status = reconcile(roles,"conflicting" if explicit_conflict else role["role_status"],geo)
        obj.update(role_evidence=role,legend_comparisons=pairs,candidate_types=types,device_status=status,
                   role_types=sorted(roles),geometry_types=sorted(geo),
                   inventory_class="device_candidate" if types or status=="conflicting" else "unclassified")
