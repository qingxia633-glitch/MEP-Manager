import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from matching import compare, compare_set
from resolve import membership


def group(code, value):
    return [code, "LIST" if isinstance(value,list) else "STR", value]


def make(handle, drawing):
    i = dict(project_id="project", drawing=drawing, handle=handle, parent_path=[], snapshot_id="1"*64,
             dwg_sha256=("2" if drawing=="legend" else "3")*64)
    definition = {k:i[k] for k in ("project_id","drawing","dwg_sha256")}
    definition.update(block_begin="B", block_record="C", probe_sha256="4"*64)
    def line(a,b):
        return dict(entity_type="LINE",raw=[group(10,a),group(11,b),group(210,[0,0,1])])
    return dict(identity=i, definition=definition, dynamic=":vlax-false",name="symbol",effective_name="symbol",
                base=[0,0,0], inventory_verified=True, attributes=[], defaults=[],
                transform=[group(10,[1,2,0]),group(50,0),group(41,1),group(42,1),group(43,1),group(210,[0,0,1])],
                members=[line([0,0,0],[1,0,0]),line([0,0,0],[0,2,0])])


class Matching(unittest.TestCase):
    def setUp(self):
        self.l, self.p = make("L","legend"), make("P","plan")
        self.row = dict(row_id="r",status="bounded",lexical_roles=[dict(role="smoke_detector", source_handle="T")])

    def result(self):
        return compare(self.l, self.p, self.row)

    def test_same_definition_distinct_instances(self):
        self.p = copy.deepcopy(self.l)
        self.p["identity"]["handle"] = "different"
        self.assertEqual(self.result()["supported_scope"],"native_curve_geometry_only")

    def test_same_name_different_drawing_different_geometry(self):
        self.p["members"][1]["raw"][1][2][1]=3
        self.assertEqual(self.result()["match_status"],"conflicting")

    def test_different_names(self):
        self.p.update(name="other",effective_name="other")
        self.assertEqual(self.result()["match_status"],"supported")

    def test_rotation_translation(self):
        self.p["transform"][0][2]=[100,200,0]
        self.p["transform"][1][2]="1.23"
        self.assertEqual(self.result()["match_status"],"supported")

    def test_scale(self):
        for item in self.p["transform"][2:5]:item[2]=100
        self.assertEqual(self.result()["match_status"],"supported")

    def test_mirror(self):
        self.p["transform"][2][2]=-1
        self.assertEqual(self.result()["match_status"],"unresolved")

    def test_nonuniform(self):
        self.p["transform"][3][2]=2
        self.assertEqual(self.result()["match_status"],"unresolved")

    def test_block_base_point(self):
        self.p["base"]=[12,0,0]
        self.assertEqual(self.result()["match_status"],"conflicting")
        for node in self.p["members"]:
            for _,_,v in node["raw"][:2]:v[0]+=12
        self.assertEqual(self.result()["match_status"],"supported")

    def test_inclined_normal(self):
        self.p["transform"][5][2]=[1,0,0]
        self.assertEqual(self.result()["match_status"],"unresolved")

    def test_attribute_over_default(self):
        self.p.update(attributes=[dict(value="actual",lexical_role="heat_detector")],
                      defaults=[dict(value="default",lexical_role="smoke_detector")])
        r=self.result()
        self.assertEqual(r["match_status"],"conflicting")
        self.assertEqual(r["attribute_evidence"][1]["actual"][0]["value"],"actual")
        self.assertEqual(r["candidate_device_roles"],[])

    def test_width_difference(self):
        raw=[group(k,v) for k,v in [(90,2),(70,0),(43,1),(38,0),(210,[0,0,1]),
                                    (10,[0,0]),(40,1),(41,1),(42,0),(10,[0,1]),(40,1),(41,1),(42,0)]]
        for s in (self.p,self.l):s["members"].append(dict(entity_type="LWPOLYLINE",raw=copy.deepcopy(raw)))
        self.p["members"][-1]["raw"][2][2]="1.000001"
        self.assertEqual(self.result()["geometry_comparison_status"],"equal_paths_different_widths")
        self.assertEqual(self.result()["match_status"],"candidate")

    def test_multiple_and_order(self):
        other=make("L2","legend")
        pairs=[(self.l,self.p,self.row),(other,self.p,dict(self.row,row_id="r2"))]
        a=compare_set(pairs)
        self.assertEqual(a,compare_set(reversed(pairs)))
        self.assertEqual([r["match_status"] for r in a],["ambiguous"]*2)

    def test_polyline_reversal_is_not_a_proven_graphic_conflict(self):
        for s, ends in [(self.l,[0,1]),(self.p,[1,0])]:
            raw = [group(k,v) for k,v in [(90,2),(70,0),(43,0),(38,0),(210,[0,0,1])]]
            for x in ends:
                raw.extend(group(k,v) for k,v in [(10,[x,0]),(40,0),(41,0),(42,0)])
            s["members"].append(dict(entity_type="LWPOLYLINE",raw=raw))
        self.assertEqual(self.result()["match_status"],"unresolved")

    def test_duplicate(self):
        with self.assertRaises(ValueError):compare_set([(self.l,self.p,self.row)]*2)

    def test_missing_definition(self):
        self.p.pop("definition")
        self.assertEqual(self.result()["match_status"],"unresolved")

    def test_unverified_inventory(self):
        self.p["inventory_verified"]=False
        self.assertEqual(self.result()["match_status"],"unresolved")

    def test_probe_version_mismatch(self):
        self.p["definition"]["dwg_sha256"]="0"*64
        self.assertEqual(self.result()["match_status"],"unresolved")

    def test_cross_project(self):
        self.p["identity"]["project_id"]="foreign"
        self.assertEqual(self.result()["match_status"],"unresolved")

    def test_nested(self):
        self.p["members"].append(dict(entity_type="INSERT",raw=[]))
        self.assertEqual(self.result()["match_status"],"unresolved")

    def test_dynamic_and_anonymous(self):
        for dynamic,name in [(":vlax-true","symbol"),(None,"symbol"),(":vlax-false","*U123")]:
            self.p.update(dynamic=dynamic,name=name,effective_name=name)
            self.assertEqual(self.result()["match_status"],"unresolved")

    def test_uncertain_row(self):
        self.row["status"]="ambiguous"
        self.assertEqual(self.result()["match_status"],"candidate")

    def test_member_order(self):
        before=self.result()
        self.p["members"].reverse()
        self.assertEqual(before,self.result())

    def test_no_attribute_propagation(self):
        self.row["texts"]=[dict(text="Model-Z"),dict(text="ceiling")]
        r=self.result()
        self.assertEqual(r["propagated_attributes"],[])
        self.assertEqual(r["attribute_evidence"][1]["actual"],[])
        self.assertEqual(r["supported_scope"],"native_curve_geometry_only")

    def test_visible_text_and_hidden_attdef(self):
        self.p["members"].append(dict(entity_type="ATTDEF",raw=[group(70,1)]))
        self.assertEqual(self.result()["match_status"],"supported")
        self.p["members"][-1]["raw"][0][2]=0
        self.assertEqual(self.result()["match_status"],"unresolved")

    def test_hidden_curve(self):
        self.p["members"][0]["raw"].append(group(60,1))
        self.assertEqual(self.result()["match_status"],"unresolved")

    def test_no_row(self):
        self.row=dict(status="unresolved")
        self.assertEqual(self.result()["match_status"],"unresolved")

    def test_foreign_legend_region(self):
        with self.assertRaisesRegex(ValueError,"foreign"):
            membership(dict(regions=[dict(provenance={})]),self.l)

    def test_unresolved_cell_never_becomes_candidate(self):
        i = self.l["identity"]
        src = {k:i[k] for k in ("project_id","drawing","snapshot_id")}
        obj = dict(kind="INSERT",identity=dict(project_id=i["project_id"],drawing_ref=i["drawing"],
                   snapshot_id=i["snapshot_id"],parent_path=[],handle="L"))
        row = dict(provenance=src,row_id="r",original_members=["L"],row_only_candidates=[],
                   evidence_status="bounded",cells=[dict(cell_id="c",members=["L"],evidence_status="unresolved")])
        rows = dict(regions=[dict(provenance=src,objects={"L":obj},rows=[row])])
        self.row = membership(rows,self.l)[0]
        self.assertEqual(self.row["status"],"unresolved")
        self.assertEqual(self.result()["match_status"],"unresolved")
