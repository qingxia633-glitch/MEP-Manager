"""Verify an exclusive manual-host capture against its pinned request and full report."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from line_style import style_evidence
from linetype_definition import associate, definition, record_identity, triples
from report_manifest import verify_manifest


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def clean(value):
    return type(value) is int and value == 0


def unpack(records, request, request_hash, source):
    names = request["names"]
    require(names and all(isinstance(n, str) and n for n in names)
            and len({n.upper() for n in names}) == len(names), "invalid requested names")
    head, *body, end = records
    require(head.get("kind") == "header" and type(head.get("LinetypeDefinitionEvidenceVersion")) is int
            and head["LinetypeDefinitionEvidenceVersion"] == 1
            and head.get("request_sha256") == request_hash and head.get("names") == names
            and Path(head["active_document"]).resolve() == Path(request["shadow"]).resolve()
            and clean(head.get("before_load")) and clean(head.get("after_load")), "invalid host header")
    require(end.get("kind") == "complete" and clean(end.get("dbmod")), "incomplete or dirty capture")
    styles, raws, missing, ids = {}, [], [], set()
    i = 0

    def take(kind):
        nonlocal i
        require(i < len(body) and body[i].get("kind") == kind, "missing or unexpected " + kind)
        item = body[i]
        i += 1
        return item

    def stage(key, call, name):
        s = take("dbmod_stage")
        require(s["stage"] == key and s["call"] == call and s["target_context"] == name
                and clean(s.get("before")) and clean(s.get("after")), "invalid acquisition stage")
        return s

    for name in names:
        s = stage("ltype_lookup", "TBLOBJNAME", name)
        require(s["argument_tokens"] == ['"LTYPE"', json.dumps(name, ensure_ascii=False)],
                "unexpected LTYPE lookup")
        have_read = i < len(body) and body[i].get("stage") == "ltype_read"
        if have_read:
            stage("ltype_read", "ENTGET", name)
        while i < len(body) and body[i].get("stage") == "style_read":
            stage("style_read", "ENTGET", name)
            if i < len(body) and body[i].get("kind") == "style":
                raw = triples(take("style")["raw"])
                _, handle = record_identity(raw, "STYLE")
                require(handle not in ids, "duplicate native handle")
                ids.add(handle)
                styles[handle] = raw
        if i < len(body) and body[i].get("kind") == "unavailable":
            require(take("unavailable")["requested"] == name, "missing name mismatch")
            missing.append(name)
            continue
        item = take("definition")
        got, handle = record_identity(triples(item["raw"]), "LTYPE")
        require(have_read and item["requested"] == name and got.upper() == name.upper()
                and handle not in ids, "definition identity mismatch")
        ids.add(handle)
        raws.append(item["raw"])
    require(i == len(body), "unexpected trailing record")
    referenced = {v for raw in raws for c, t, v in raw if c == 340 and t == "ENAME" and isinstance(v, str)}
    require(set(styles) <= referenced, "unrelated STYLE")
    return [definition(raw, styles, source) for raw in raws], styles, missing


def selected_styles(text, handles, source):
    records = re.split(r'(?m)(?=^EntityHandle=)', text)
    result = {}
    for record in records[1:]:
        match = re.match(r'^EntityHandle="([0-9A-Fa-f]+)"', record)
        if match and match[1] in handles:
            h = match[1]
            require(h not in result, "duplicate source entity")
            result[h] = style_evidence(record, records[0], dict(source, handle=h, parent_path=[]),
                                       {"snapshot": source["report_sha256"]})
    require(set(result) == set(handles), "missing source entity")
    return result


def verify(request_path, native_path):
    request_bytes = Path(request_path).read_bytes()
    q = json.loads(request_bytes)
    dwg_hash = q["dwg_sha256"]
    for k in ("authoritative", "shadow", "report_dwg"):
        require(digest(Path(q[k]).read_bytes()) == dwg_hash, k + " DWG hash mismatch")
    source = {k: q[k] for k in ("project_id", "drawing_instance_id", "dwg_sha256", "report_sha256")}
    require(all(isinstance(v, str) and v for v in source.values()), "missing provenance")
    data = Path(q["report"]).read_bytes()
    manifest = Path(q["manifest"]).read_bytes()
    require(digest(data) == q["report_sha256"] and digest(manifest) == q["manifest_sha256"],
            "source snapshot mismatch")
    identity = verify_manifest(data, q["report"], "utf-8-sig", json.loads(manifest))["report_identity"]
    require(Path(identity["drawing"]).resolve() == Path(q["report_dwg"]).resolve()
            and identity["acquisition_mode"] == "ModelSpaceTopLevelAllLayers", "incompatible entity source")
    text = data.decode("utf-8-sig")
    require(re.findall(r'(?m)^ReadErrorCount=(.*?)\r?$', text) == ["0"]
            and text.rstrip().splitlines()[-1].startswith("END_OF_REPORT:"), "incomplete entity report")
    styles = selected_styles(text, q["handles"], source)
    used = set()
    for style in styles.values():
        hint = style["style_resolution_status"]["linetype"]
        if hint == "direct":
            used.add(style["raw_entity_style"]["entity_linetype"]["value"].upper())
        elif hint == "bylayer_candidate":
            used.add(style["layer_raw_style"]["fields"]["layer_linetype"]["value"].upper())
    require(used == {name.upper() for name in q["names"]}, "requested names differ from verified entity styles")
    trace = Path(q["dbmod_trace"]).read_bytes()
    lines = trace.decode("utf-8-sig").splitlines()
    require(len(lines) >= 3 and lines[:2] == ["before_load|0", "after_load|0"]
            and lines[-1] == "after_close|0", "incomplete host session")
    for line in lines[2:-1]:
        parts = line.split("|")
        require(len(parts) == 4 and parts[1:3] == ["0", "0"], "dirty host trace")
    native = Path(native_path).read_bytes()
    records = [json.loads(line) for line in native.decode("utf-8-sig").splitlines()]
    defs, refs, missing = unpack(records, q, digest(request_bytes), source)
    expected_trace = []
    for record in records:
        if record["kind"] == "dbmod_stage":
            expected_trace.append(f'{record["stage"]}|0|0|{record["call"]}')
        expected_trace.append("report_output|0|0|serialize/write-line")
    require(lines[2:-1] == expected_trace, "report and host trace disagree")
    links = [associate(s, source, defs) for s in styles.values()]
    return dict(LinetypeDefinitionEvidenceVersion=1, source=source, request_sha256=digest(request_bytes),
                acquisition_sha256=digest(native), trace_sha256=digest(trace), encoding="utf-8-sig", dbmod_unchanged=True,
                dwg_hash_unchanged=True, definitions=defs, style_records=refs,
                host=records[0], unavailable_definitions=missing, associations=links)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("request", "capture", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    result = verify(args.request, args.capture)
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False)
