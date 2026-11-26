"""Replay a review-only project vocabulary against a pinned regional inventory."""
import argparse
import csv
import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path
import re
import sys

from project_legend import is_code, key, recover, require, specific_name

MATCHER = Path(__file__).resolve().parents[1] / "device-legend-instance-matching"
sys.path.insert(0,str(MATCHER))
spec = importlib.util.spec_from_file_location("device_legend_reader", MATCHER / "resolve.py")
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


def pinned(path, digest):
    data=Path(path).read_bytes()
    require(hashlib.sha256(data).hexdigest()==digest, "input hash mismatch: " + str(path))
    return json.loads(data.decode("utf-8-sig"))


def check_registry(registry, source, project):
    records = [d for d in registry["drawing_instances"] if d["report_sha256"] == source["sha256"]
               and d["source_dwg_sha256"] == source["dwg_sha256"]
               and d["source_filename"] == Path(source["dwg"]).name and d["project_id"] == project]
    require(len(records) == 1, "unqualified drawing instance")
    require(native.digest(source["manifest"]) == source["manifest_sha256"], "manifest pin mismatch")
    return records[0]["instance_id"]


def values(symbol, tag):
    return sorted({a["value"] for a in symbol["attributes"] if a["tag"] == tag and a["value"]})


def source_material(source, rows, catalogue):
    project = catalogue["project_id"]
    selectors = catalogue["sources"]
    require(set(catalogue) == {"project_id","snapshot_id","sources"} and selectors
            and catalogue["snapshot_id"] == source["sha256"], "invalid catalogue scope")
    symbols = {s["symbol"] for s in selectors}
    require(len(symbols)==len(selectors), "duplicate source selector")
    texts = {}
    for sel in selectors:
        fields = {"symbol","kind","discipline"}
        if sel["kind"] == "legend_row":
            fields.update(("region","name_texts"))
            require(sel["name_texts"] and len(set(sel["name_texts"]))==len(sel["name_texts"]), "invalid name selectors")
        else:
            require(sel["kind"] == "name_witness", "unknown source kind")
        require(set(sel)==fields, "unexpected source selector field")
    wanted_texts = {h for s in selectors for h in s.get("name_texts",[])}
    # Discover other uses in the source drawing before extracting owner-checked ATTRIBs.
    # Only records with the actual display tag participate in this reverse check.
    report=Path(source["report"]).read_bytes()
    require(hashlib.sha256(report).hexdigest()==source["sha256"],"legend source changed")
    text=report.decode("utf-8-sig").replace("\r\n","\n")
    for rec in re.split(r"(?m)(?=^EntityHandle=)",text)[1:]:
        h = native.field(rec,"EntityHandle")
        if h in wanted_texts:
            require(h not in texts and native.field(rec,"DXF_Type") == "TEXT", "ambiguous/non-TEXT label")
            texts[h] = native.text_record(native.serialized_field(rec,"Text_RAW"))["decoded_text"]
        if native.field(rec,"DXF_Type")=="INSERT" and re.search(r'^AttributeTag="\$TEXT\$"$',rec,re.M):
            symbols.add(h)
    originals = native.drawing_symbols(source,project,symbols)
    result = []
    for selector in selectors:
        symbol = originals[selector["symbol"]]
        ident = symbol["identity"]
        names = values(symbol,"A")
        codes = [v for v in values(symbol,"$TEXT$") if is_code(v)]
        entry = dict(project_id=project,kind=selector["kind"], names=names,codes=codes,
                     discipline=selector["discipline"], provenance=ident, attributes=symbol["attributes"],
                     symbol_block=symbol["name"],usages=[],row_id=None,membership=None)
        if selector["kind"] == "name_witness":
            require(len(names)==1 and specific_name(names[0]), "witness needs a specific full name")
            result.append(dict(entry,label=names[0]))
            continue
        regions = [r for r in rows["regions"] if r["legend_region_id"]==selector["region"]]
        require(len(regions)==1,"ambiguous/missing source region")
        region = regions[0]
        memberships = native.membership({"regions":regions},symbol)
        require(len(memberships)==1 and memberships[0]["status"] in ("ambiguous","bounded"),
                "missing or competing legend membership")
        membership = memberships[0]
        row = next(r for r in region["rows"] if r["row_id"]==membership["row_id"])
        fragments = []
        name_cells = None
        for h in selector["name_texts"]:
            obj = region["objects"][h]
            expected = dict(project_id=project,drawing_ref=ident["drawing"],snapshot_id=ident["snapshot_id"],
                            handle=h,parent_path=[])
            cells = [c for c in row["cells"] if h in c["members"]]
            require(h in row["original_members"] and obj["identity"]==expected and obj["kind"]=="TEXT"
                    and texts.get(h) and obj["decoded_text"]==texts[h] and len(cells)==1
                    and cells[0]["evidence_status"] in ("bounded","ambiguous"),"unqualified name cell")
            cell = cells[0]
            require(name_cells in (None,cell["cell_id"]), "name fragments in different cells")
            name_cells=cell["cell_id"]
            fragments.append(dict(text=texts[h],provenance=obj["provenance"],cell_id=name_cells,
                                  cell_status=cell["evidence_status"]))
        label = "".join(f["text"] for f in fragments)
        # Parenthetical qualifiers remain in the evidence. Use the old dictionary
        # only when it identifies the complete base name of a qualified row.
        base = re.fullmatch(r"([^（()）]+)[（(][^（）()]+[）)]",label)
        label_type = key(label)
        if base and native.canonicalize(base[1])[0]!="unknown":
            label_type=key(base[1])
        status = membership["status"]
        if any(f["cell_status"]=="ambiguous" for f in fragments):
            status="ambiguous"
        entry.update(label=label,label_type=label_type,row_id=row["row_id"],region_id=region["legend_region_id"],
                     row_status=row["evidence_status"],membership=status,symbol_cells=[
                         dict(cell_id=c["cell_id"],status=c["evidence_status"]) for c in row["cells"]
                         if c["cell_id"] in membership["symbol_cells"]],name_fragments=fragments)
        for other in originals.values():
            for code in sorted(set(codes).intersection(values(other,"$TEXT$"))):
                for name in values(other,"A"):
                    if name != code:
                        entry["usages"].append(dict(code=code,name=name,identity=other["identity"],
                                                 attributes=other["attributes"]))
        entry["usages"].sort(key=lambda u:(u["identity"]["handle"],u["code"],u["name"]))
        result.append(entry)
    return result


def replay(directory, inventory_hash, catalog_path, catalog_hash):
    inv=pinned(directory/"regional-inventory.json",inventory_hash)
    mp=pinned(directory/"input-map.json",inv["input_map_sha256"])
    scope=pinned(directory/"scope.json",mp["scope_sha256"])
    cat=pinned(catalog_path,catalog_hash)
    project=scope["project_id"]
    require(inv["RegionalDeviceInventoryVersion"]==1 and scope==inv["scope"]
            and project==mp["project_id"]==cat["project_id"],"project or frozen scope mismatch")
    registry=pinned(scope["registry"]["path"],scope["registry"]["sha256"])
    require(registry["project_id"]==project and registry["ProjectDrawingRegistryVersion"]==2,"registry scope")
    plan,legend=mp["plan"],mp["legend"]
    require(check_registry(registry,plan,project)==scope["drawing_instance_id"]
            and scope["report_sha256"]==plan["sha256"] and scope["dwg_sha256"]==plan["dwg_sha256"],
            "plan scope mismatch")
    check_registry(registry,legend,project)
    require(legend["sha256"]!=plan["sha256"],"need independent project source drawing")
    rows=pinned(mp["rows_path"],mp["rows_sha256"])
    require(rows["NativeLegendRowEvidenceVersion"]==1,"legend row version")
    catalogue=source_material(legend,rows,cat)
    items=sorted((r for r in inv["objects"] if r["boundary_relation"]=="inside" and r["entity_type"]=="INSERT"),
                 key=lambda r:r["handle"])
    handles=[r["handle"] for r in items]
    require(len(handles)==len(set(handles)), "duplicate interior instance")
    native_symbols=native.drawing_symbols(plan,project,handles)
    records=[]
    for obj in items:
        require(obj["drawing_instance_id"]==scope["drawing_instance_id"] and obj["scope_id"]==scope["scope_id"]
                and obj["scope_version"]==scope["scope_version"],"foreign regional object")
        records.append(recover(obj,native_symbols[obj["handle"]],catalogue))
    return dict(ProjectLegendBackedDeviceRoleVersion=1,project_id=project,
                provenance=dict(regional_inventory_sha256=inventory_hash,catalog_sha256=catalog_hash,
                                plan_sha256=plan["sha256"],legend_sha256=legend["sha256"],rows_sha256=mp["rows_sha256"],
                                scope_id=scope["scope_id"],scope_version=scope["scope_version"]),
                records=records)


def summarize(data):
    items=data["records"]
    single=[r for r in items if len(r["role_candidates"])==1
            and r["candidate_status"] not in ("conflicting_evidence","competing_interpretations")]
    discipline_hits=Counter()
    for r in items:
        group="|".join(r["discipline_candidates"]) or "unresolved"
        discipline_hits[group]+=len(r["role_candidates"])
    return dict(distinct_instances=len(items),original_single=sum(len(r["previous_candidate_types"])==1 for r in items),
                single_candidate_instances=len(single),instances_with_any_hypothesis=sum(bool(r["role_candidates"]) for r in items),
                status_counts=dict(Counter(r["candidate_status"] for r in items)),
                type_hits=dict(Counter(t for r in items for t in r["role_candidates"])),
                candidate_type_hits=sum(len(r["role_candidates"]) for r in items),
                discipline_group_type_hits=dict(discipline_hits),
                discipline_groups=dict(Counter("|".join(r["discipline_candidates"]) or "unresolved" for r in items)),
                approved_device_quantity=None)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("regional","inventory-sha256","catalog","catalog-sha256","out"):
        parser.add_argument("--"+name,required=True)
    args=parser.parse_args()
    output=Path(args.out)
    files=[output/n for n in ("role-candidates.json","regional-replay.json","before-after-comparison.csv")]
    require(not any(p.exists() for p in files),"output already exists")
    data=replay(Path(args.regional),args.inventory_sha256,Path(args.catalog),args.catalog_sha256)
    output.mkdir(parents=True,exist_ok=True)
    for path,obj in zip(files,(data,summarize(data))):
        with path.open("x",encoding="utf-8") as f:
            json.dump(obj,f,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)
    with files[2].open("x",encoding="utf-8-sig",newline="") as f:
        writer=csv.writer(f)
        writer.writerow(["handle","original candidates","new hypotheses","review status","discipline candidates"])
        for r in data["records"]:
            writer.writerow([r["stable_instance_identity"]["handle"]," | ".join(r["previous_candidate_types"]),
                             " | ".join(r["role_candidates"]),r["candidate_status"]," | ".join(r["discipline_candidates"])])


if __name__=="__main__":
    main()
