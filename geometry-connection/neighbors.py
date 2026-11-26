"""Read-only, one-hop endpoint lookup on independently verified device POINTs."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

from resolver import DrawingContext, resolve_connection

reader_dir = Path(__file__).resolve().parents[1] / "device-legend-instance-matching"
sys.path.insert(0, str(reader_dir))
spec = importlib.util.spec_from_file_location("verified_native_reader",reader_dir / "resolve.py")
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)
from matching import number, point

def xyz(raw):
    return [float(v) for v in point(raw)]


def attach_points(ctx, symbol):
    """Install only this seed's verified, static definition-local POINT members."""
    definition = symbol.get("definition")
    if not definition or not symbol["inventory_verified"]:
        return None
    if symbol["dynamic"] != ":vlax-false" or symbol["name"] != symbol["effective_name"]:
        return None
    handle = symbol["identity"]["handle"]
    inst = ctx.entities[handle]
    raw = symbol["transform"]
    if inst["array"] or inst["block"] != symbol["name"] or native.values(raw,60) not in ([],[0]):
        return None
    refined = dict(insertion=xyz(native.one(raw,10)),normal=xyz(native.one(raw,210)),
                   rotation=float(number(native.one(raw,50))),
                   scale=[float(number(native.one(raw,c))) for c in (41,42,43)])
    # Snapshot fields use six decimal places. Cross-check before refining precision.
    for key, value in refined.items():
        left = [inst[key]] if key == "rotation" else inst[key]
        right = [value] if key == "rotation" else value
        if not left or len(left) != len(right) or any(a is None or not math.isclose(
                a,b,rel_tol=0,abs_tol=0.0000006) for a,b in zip(left,right)):
            raise ValueError("snapshot/probe transform disagreement: " + handle)
    inst.update(refined)
    members = []
    for member in symbol["members"]:
        if member["entity_type"] != "POINT":
            continue
        raw = member["raw"]
        native.require(member["owner"] == definition["block_record"] and member["read_status"] == "read",
                       "unqualified POINT owner")
        try:
            local = xyz(native.one(raw,10))
            normal = xyz(native.one(raw,210))
        except (ValueError, ArithmeticError, TypeError):
            # Retain its identity. The forward resolver reports this member as
            # unsupported and can still transform other independent POINTs.
            local, normal = None, None
        members.append(dict(handle=member["handle"],type="POINT",point=local,normal=normal,
                            hidden=native.values(raw,60) not in ([],[0])))
    candidate = dict(base=xyz(symbol["base"]),entities=members,dynamic=False,complete=True)
    prior = ctx.definitions.setdefault(symbol["name"],candidate)
    native.require(prior == candidate,"conflicting current block definitions")
    return definition


def pinned_json(pin):
    raw = Path(pin["path"]).read_bytes()
    native.require(hashlib.sha256(raw).hexdigest()==pin["sha256"],"input pin mismatch: "+pin["path"])
    return json.loads(raw.decode("utf-8-sig"))


def load_source(request):
    project = request["project_id"]
    registry = pinned_json(request["registry"])
    native.require(project and registry["ProjectDrawingRegistryVersion"] == 2 and registry["project_id"] == project,
                   "project/registry mismatch")
    source = request["source"]
    drawings = [d for d in registry["drawing_instances"] if d["project_id"]==project
                and d["report_sha256"]==source["sha256"] and d["source_dwg_sha256"]==source["dwg_sha256"]
                and d["source_filename"]==Path(source["dwg"]).name]
    native.require(len(drawings)==1 and native.digest(source["manifest"])==source["manifest_sha256"],
                   "unqualified drawing instance or manifest")
    drawing = drawings[0]
    ctx = DrawingContext.from_reports(source["report"],[],strict_endpoint_inventory=True)
    native.require(ctx.provenance[0]["sha256"]==source["sha256"], "snapshot pin mismatch")
    handles = request.get("device_handles")
    if handles is None:
        # A probe can seed edges as well as devices. Only read INSERT definitions
        # from this probe, whose request is verified by drawing_symbols below.
        probe = source.get("probe")
        seeds = native.read(probe["request"])["seed_handles"] if probe else []
        handles = [h for h in seeds if ctx.entities.get(h,{}).get("type")=="INSERT"]
    native.require(isinstance(handles,list) and all(isinstance(h,str) and h for h in handles)
                   and len(handles)==len(set(handles)), "distinct INSERT selectors required")
    symbols = native.drawing_symbols(source,project,handles)
    ctx.project_id = project
    policy = request["contact_policy"]
    policy_data = pinned_json(policy)
    rules = [r for r in policy_data["rules"] if r["rule_id"]==policy["rule_id"]]
    native.require(policy_data["model_type"]=="GeometryConnectionEvidenceRuleSet" and len(rules)==1,
                   "missing or ambiguous geometry contact rule")
    ctx.contact_tolerance = rules[0]["tolerance_drawing_units"]
    ctx.floor_evidence = dict(status="unresolved",space="ModelSpace",registry_instance=drawing["instance_id"],
                              sheet_identity_status=drawing["sheet_identity_status"],
                              reason="no floor binding for this ModelSpace path")
    defs = {h:attach_points(ctx,symbols[h]) for h in sorted(handles)}
    ctx.provenance.append(dict(dwg_sha256=source["dwg_sha256"],manifest=source["manifest"],
                               manifest_sha256=source["manifest_sha256"],registry=request["registry"],
                               probe=source.get("probe"),contact_policy=policy))
    return ctx,defs,dict(project_id=project,drawing_instance_id=drawing["instance_id"],snapshot_id=source["sha256"])


def eligible(edge):
    vertices = edge.get("vertices",[])
    return (edge.get("type") in ("LWPOLYLINE","LINE") and edge.get("path_verified",True)
            and (edge["type"]=="LINE" or edge.get("closed") is False)
            and len(vertices)>=2 and all(isinstance(p,(list,tuple)) and len(p)==3 and
                                         all(math.isfinite(v) for v in p) for p in vertices))


def edge_record(scope,edge):
    return dict(scope,handle=edge["handle"],parent_path=[],entity_type=edge["type"],
                vertices_wcs=edge["vertices"],profile_dxf=edge.get("profile_dxf",[]))


def contacts(points, position, tolerance, edge, endpoint, unresolved):
    hits = []
    for point_record in points:
        wcs = point_record["wcs"]
        if math.dist(position,wcs) <= tolerance:
            hits.append(point_record)
        elif math.dist(position[:2],wcs[:2]) <= tolerance:
            unresolved.append(dict(edge=edge,endpoint=endpoint,point=point_record["identity"],
                                   endpoint_wcs=position,point_wcs=wcs,reason="xy_only_xyz_contact_unverified"))
    return hits


def query_endpoint(ctx,definitions,scope,edge_handle,endpoint):
    """One hop within a context already qualified by load_source."""
    tolerance = ctx.contact_tolerance
    if type(tolerance) not in (int,float) or not math.isfinite(tolerance) or tolerance<=0:
        raise ValueError("positive finite drawing-unit tolerance required")
    if endpoint not in ("start","end"):
        raise ValueError("endpoint must be start or end")
    src = ctx.entities.get(edge_handle,{})
    out = dict(DeviceNetworkNeighborQueryVersion=1,scope=scope,source_endpoint=endpoint,
               source_edge=dict(scope,handle=edge_handle,parent_path=[]),devices=[],coverage_gaps=[],unresolved_contacts=[],
               geometric_contact_status="unresolved",neighboring_edge_discovery_status="unresolved",
               engineering_connection_status="unresolved",circuit_identity_status="unresolved",
               floor_evidence=ctx.floor_evidence,tolerance_drawing_units=tolerance,
               provenance=ctx.provenance,stop_reasons=[])
    if not eligible(src):
        out["stop_reasons"]=["source_endpoint_unverified"]
        return out
    out["source_edge"]=edge_record(scope,src)
    position=src["vertices"][0 if endpoint=="start" else -1]
    out["source_endpoint_wcs"]=position
    edges=sorted((e for e in ctx.entities.values() if eligible(e)),key=lambda e:e["handle"])
    out["coverage"]=dict(eligible_open_edges=len(edges),requested_instances=sorted(definitions),
                         inventory="top-level LINE/open LWPOLYLINE endpoints, direct native POINT members",
                         incomplete_edge_handles=sorted(h for h,e in ctx.entities.items()
                             if e.get("type") in ("LINE","LWPOLYLINE") and e.get("closed") is not True
                             and not eligible(e)))
    reasons=set()
    for device, definition in sorted(definitions.items()):
        if not definition:
            reasons.add("missing_current_block_definition")
            out["coverage_gaps"].append(dict(device=device,reason="missing_or_unqualified_current_definition"))
            continue
        resolved=resolve_connection(edge_handle,position,device,ctx,tolerance,include_point_inventory=True)
        if resolved["issues"]:
            out["coverage_gaps"].append(dict(device=device,reasons=sorted(resolved["issues"])))
        points=[]
        for a in sorted(resolved["point_inventory"],key=lambda p:p["source_definition_path"]):
            points.append(dict(identity=dict(scope,handle=a["source_entity_handle"],
                               parent_path=a["source_definition_path"][:-1],block_record=definition["block_record"]),
                               local=a["local_coordinate"],wcs=a["transformed_wcs"],transform=a["transform_chain"],
                               source_endpoint_distance_xyz=a["xyz_distance"]))
        hits=contacts(points,position,tolerance,edge_handle,endpoint,out["unresolved_contacts"])
        if not hits or not resolved["endpoint_source"]:
            continue
        neighbors=[]
        for edge in edges:
            if edge["handle"]==edge_handle:
                continue
            for label,index in (("start",0),("end",-1)):
                ep=edge["vertices"][index]
                touched=contacts(points,ep,tolerance,edge["handle"],label,out["unresolved_contacts"])
                if len(touched)>1:
                    reasons.add("ambiguous_device_or_point")
                for p in touched:
                    relation="source_point_ambiguous" if len(hits)>1 else (
                        "same_point" if p["identity"]==hits[0]["identity"] else "different_point")
                    neighbors.append(dict(edge=edge_record(scope,edge),endpoint=label,endpoint_wcs=ep,
                                          point=p["identity"],residual_xyz=math.dist(ep,p["wcs"]),relation=relation,
                                          source_point_separations=[dict(point=h["identity"],distance_wcs=math.dist(
                                              h["wcs"],p["wcs"])) for h in hits],geometric_contact_status="supported"))
        out["devices"].append(dict(identity=dict(scope,handle=device,parent_path=[]),definition=definition,
                                   points=points,source_points=hits,neighbors=neighbors))
    devices=out["devices"]
    reasons.add("circuit_identity_unresolved")
    if not definitions:
        reasons.add("missing_current_block_definition")
    if devices:
        out["geometric_contact_status"]="supported"
        reasons.add("device_internal_connectivity_unresolved")
        if len(devices)>1 or any(len(d["source_points"])>1 for d in devices):
            reasons.add("ambiguous_device_or_point")
    else:
        reasons.add("no_verified_device_point")
        # This entry cannot resolve a bypass or promote an interior intersection.
        out["alternative_path_status"]="jump_or_crossing_relationship_unresolved"
    if any(d["neighbors"] for d in devices):
        out["neighboring_edge_discovery_status"]="supported"
    else:
        reasons.add("neighbor_endpoint_contact_unproven")
    out["stop_reasons"]=sorted(reasons)
    return out


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request",type=Path)
    parser.add_argument("output",type=Path)
    args=parser.parse_args()
    try:
        request=native.read(args.request)
        ctx,defs,scope=load_source(request)
        queries=request["queries"]
        native.require(isinstance(queries,list) and queries,"missing queries")
        results=[query_endpoint(ctx,defs,scope,q["edge"],q["endpoint"]) for q in queries]
    except (ValueError,KeyError,TypeError,OSError,ArithmeticError) as exc:
        parser.exit(2,"source_evidence_inconsistent: "+str(exc)+"\n")
    with args.output.open("x",encoding="utf-8") as stream:
        json.dump(results,stream,ensure_ascii=False,indent=2,allow_nan=False)


if __name__=="__main__":
    main()
