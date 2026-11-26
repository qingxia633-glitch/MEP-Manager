"""Run from the repository root with a private input map and pre-frozen review directory."""
import argparse
import csv
import io
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

from inventory import aggregate, duplicate_groups, interior
from recognition import classify, native
from survey import survey


def freeze(path, data):
    content = (json.dumps(data, ensure_ascii=False, sort_keys=True, allow_nan=False,
                          separators=(",",":")) + "\n").encode()
    if path.exists():
        if path.read_bytes() != content:
            raise ValueError(f"existing frozen artifact differs: {path.name}")
        return
    with path.open("xb") as out:
        out.write(content)


def qualify(cfg,scope,directory):
    plan = cfg["plan"]
    pins = [(directory/"scope.json",cfg["scope_sha256"]),
            (directory/"review-pack.md",cfg["review_pack_sha256"])]
    pins += [(scope[k]["path"],scope[k]["sha256"]) for k in ("unit_source","registry")]
    for path, digest in pins:
        if native.digest(path) != digest:
            raise ValueError("scope/evidence pin mismatch")
    unit = native.read(scope["unit_source"]["path"])
    reg = native.read(scope["registry"]["path"])
    drawings = [d for d in reg["drawing_instances"] if d["instance_id"]==scope["drawing_instance_id"]]
    applicability = unit["applicability"]
    if not (reg["ProjectDrawingRegistryVersion"]==2 and len(drawings)==1 and
            reg["project_id"]==scope["project_id"]==cfg["project_id"] and
            drawings[0]["source_filename"]==scope["drawing"]==Path(plan["dwg"]).name and
            drawings[0]["source_dwg_sha256"]==scope["dwg_sha256"]==plan["dwg_sha256"] and
            drawings[0]["report_sha256"]==scope["report_sha256"]==plan["sha256"] and
            unit["status"]=="approved" and unit["cad_coordinate_unit"]==scope["unit"] and
            unit["assumption_id"]==scope["unit_source"]["assumption_id"] and scope["space"]=="ModelSpace top-level"
            and applicability["scope"]=="current verified version ModelSpace" and
            all(applicability[k]==scope[k] for k in ("project_id","drawing","dwg_sha256","report_sha256"))):
        raise ValueError("registry or unit scope mismatch")
    x,y,X,Y=scope["scope_boundary"]
    if not (all(map(math.isfinite,(x,y,X,Y))) and x<X and y<Y and scope["coordinate_system"]=="WCS XY"):
        raise ValueError("invalid spatial frame")
    if scope["floor_id"] is not None or scope["floor_status"] != "unresolved":
        raise ValueError("this pilot has no verified floor assignment contract")
    native.drawing_symbols(plan, cfg["project_id"], [])


def explain(r):
    if r["device_status"]=="conflicting":
        return "角色或图例证据冲突，需核对"
    if r["boundary_relation"]!="inside":
        return r["location_basis"]+" / "+r["boundary_relation"]
    if r["entity_type"]!="INSERT":
        return "仅有原生图形或文字，独立设备身份待查"
    role=r["role_evidence"]
    reasons=list(role["issues"])
    if not r["candidate_types"]:
        reasons.append("设备类型未识别")
    if r["block_definition_identity"].get("status"):
        reasons.append("当前块定义未验证")
    if any(m["match_status"] in ("candidate","ambiguous") for m in r["legend_comparisons"]):
        reasons.append("图例几何候选，保留原生差异")
    return " / ".join(reasons)


def write_csv(path,rows):
    with io.StringIO(newline="") as f:
        writer=csv.writer(f)
        writer.writerow(["序号","设备候选名称","项目","图纸实例","快照","parent_path","handle","类型",
                         "WCS","范围关系","证据状态","图例行","角色原文","说明","CAD 定位","复核分组"])
        for i,r in enumerate(rows,1):
            role=r.get("role_evidence",{})
            viable=[m for m in r.get("legend_comparisons",[]) if m["match_status"] in ("candidate","supported","ambiguous")]
            names={m["regional_row_label"]["type"]:m["regional_row_label"]["raw"] for m in viable}
            if role.get("canonical_role") in r["candidate_types"]:
                names.setdefault(role["canonical_role"],role["raw_role_text"])
            # Formula-like CAD strings stay text in spreadsheet applications.
            def safe(value):
                if isinstance(value,str) and value.lstrip().startswith(("=","+","-","@")):
                    return "'"+value
                return value
            h=r["handle"]
            values=[i," / ".join(names.get(t,t) for t in r["candidate_types"]),r["project_id"],r["drawing_instance_id"],
                    r["snapshot"],json.dumps(r["parent_path"]),h,r["entity_type"],r["location"],r["boundary_relation"],
                    r["device_status"]," / ".join(str(m["legend_row_identity"]) for m in viable),
                    role.get("raw_role_text"),explain(r),f'(sssetfirst nil (ssadd (handent "{h}")))',r.get("cohort")]
            writer.writerow(map(safe,values))
        content = f.getvalue().encode("utf-8-sig")
    if path.exists():
        if path.read_bytes() != content:
            raise ValueError(f"existing review export differs: {path.name}")
    else:
        with path.open("xb") as out:
            out.write(content)


def run(config_path, directory):
    config=native.read(config_path)
    scope=native.read(directory/"scope.json")
    qualify(config,scope,directory)
    plan=config["plan"]
    data=Path(plan["report"]).read_bytes()
    if hashlib.sha256(data).hexdigest()!=scope["report_sha256"]:
        raise ValueError("survey input changed")
    text=data.decode("utf-8-sig").replace("\r\n","\n")
    rows,records=survey(text,scope)
    freeze(directory/"native-survey.json",rows)
    classify(rows,records,config)
    counts=aggregate(rows)
    regional=interior(rows)
    dispositions=dict(Counter(r["boundary_relation"] for r in rows))
    inspection=[r for r in rows if r["boundary_relation"]!="outside"]
    output=dict(RegionalDeviceInventoryVersion=1,scope=scope,counts=counts,source_population=len(rows),
                spatial_dispositions=dispositions,objects=inspection,duplicate_groups=duplicate_groups(rows),
                native_survey_sha256=native.digest(directory/"native-survey.json"),
                input_map_sha256=native.digest(config_path),human_review="pending",
                coverage="Top-level only. Child ATTRIBs and native definition primitives are evidence of their parent.")
    freeze(directory/"regional-inventory.json",output)
    candidates=[r for r in regional if r["inventory_class"]=="device_candidate"]
    unresolved=[r for r in inspection if r["boundary_relation"]!="inside" or
                r["inventory_class"]=="unclassified" or r["device_status"] in ("conflicting","multiple")]
    write_csv(directory/"device-candidates.csv",candidates)
    write_csv(directory/"unresolved-objects.csv",unresolved)
    return counts


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_map",type=Path)
    parser.add_argument("review_directory",type=Path)
    args=parser.parse_args()
    print(json.dumps(run(args.input_map,args.review_directory),ensure_ascii=False,indent=2))
