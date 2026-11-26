"""Independent admission and native geometry examples, with no project handles."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from test_matching import group, make
from matching import compare
from resolve import attach_definition, digest, load_probe


def primitive(kind, fields):
    return dict(entity_type=kind, raw=[group(210, [0, 0, 1]),
                                       *(group(k, v) for k, v in fields)])


def solid(corners):
    return primitive("SOLID", list(zip((10, 11, 12, 13), corners)))


def match(left, right):
    a, b = make("A", "legend"), make("B", "plan")
    a["members"].append(left)
    b["members"].append(right)
    return compare(a, b, dict(row_id="r", status="bounded"))


class NativeGeometry(unittest.TestCase):
    def test_circle(self):
        c = primitive("CIRCLE", [(10, [0, 0, 0]), (40, 2)])
        self.assertEqual(match(c, c)["exact_geometry_status"], "equal")
        for radius in (0, -1):
            other = primitive("CIRCLE", [(10, [0, 0, 0]), (40, radius)])
            self.assertEqual(match(c, other)["match_status"], "unresolved")

    def test_arc_direction(self):
        a = primitive("ARC", [(10, [0, 0, 0]), (40, 1), (50, 3), (51, 1)])
        self.assertEqual(match(a, a)["centerline_geometry_status"], "equal")
        b = primitive("ARC", [(10, [0, 0, 0]), (40, 1), (50, 1), (51, 3)])
        self.assertNotEqual(match(a, b)["exact_geometry_status"], "equal")
        for angles in [(0, 0), (0, 90)]:
            other = primitive("ARC", [(10, [0, 0, 0]), (40, 1), *zip((50, 51), angles)])
            self.assertEqual(match(a, other)["match_status"], "unresolved")

    def test_solid_triangle_and_quad(self):
        a, b, c, d = [0,0,0], [1,0,0], [0,1,0], [1,1,0]
        for corners in [(a,b,c,c), (a,a,b,c), (a,b,c,d)]:
            with self.subTest(corners=corners):
                self.assertEqual(match(solid(corners), solid(corners))["exact_geometry_status"], "equal")

    def test_solid_invalid_boundary(self):
        for corners in [([0,0,0],[1,0,0],[2,0,0],[2,0,0]),
                        ([0,0,0],[1,0,0],[1,1,0],[0,1,0]),
                        ([0,0,0],[1,0,0],[0,1,0],[1,1,1]),
                        ([0,0,0],[1,0,0],[0,1,0])]:
            self.assertEqual(match(solid(corners), solid(corners))["match_status"], "unresolved")

    def test_solid_shape_separate_from_curve_centerlines(self):
        a = solid(([0,0,0],[1,0,0],[0,1,0],[0,1,0]))
        b = solid(([0,0,0],[2,0,0],[0,1,0],[0,1,0]))
        result = match(a, b)
        self.assertEqual(result["centerline_geometry_status"], "equal")
        self.assertNotEqual(result["exact_geometry_status"], "equal")
        self.assertEqual(result["engineering_device_type_status"], "pending_independent_review")
        self.assertFalse(result["propagated_attributes"])

    def test_auxiliary_differences_separate(self):
        r = match(primitive("POINT", [(10,[0,0,0])]), primitive("POINT", [(10,[1,0,0])]))
        self.assertEqual(r["centerline_geometry_status"], "equal")
        self.assertTrue(r["auxiliary_geometry_differences"])
        self.assertEqual(r["exact_geometry_status"], "different_auxiliary_geometry")
        self.assertNotEqual(r["match_status"], "supported")

    def test_inventory_difference_with_same_name_is_only_geometric(self):
        result = match(primitive("CIRCLE", [(10,[0,0,0]), (40,1)]),
                       primitive("LINE", [(10,[0,0,0]), (11,[1,0,0])]))
        self.assertEqual(result["match_status"], "conflicting")
        self.assertEqual(result["engineering_device_type_status"], "pending_independent_review")
        self.assertFalse(result["propagated_attributes"])

    def test_hidden_or_tilted_member(self):
        c = primitive("CIRCLE", [(10,[0,0,0]), (40,1)])
        for i, v in [(210,[0,1,0]), (60,1), (39,1)]:
            b = deepcopy(c)
            b["raw"] = [g for g in b["raw"] if g[0] != i] + [group(i,v)]
            self.assertEqual(match(c,b)["match_status"], "unresolved")


def probe():
    seed = dict(kind="node", handle="A", entity_type="INSERT", read_status="read", raw=[group(2,"symbol")],
                layout="Model", parent_path=[], parent_path_status="top_level_verified")
    definition = dict(kind="insert_definition", insert="A", block_begin_handle="B", block_record_handle="R",
                      block_name="symbol", effective_block_name="symbol", identity_status="read",
                      block_begin_raw=[group(10,[0,0,0])])
    member = dict(kind="node",entity_type="LINE",handle="M",owner="R",traversal_path=["A","R"],read_status="read")
    other = dict(definition,insert="X",block_record_handle="Y",block_begin_handle="Z")
    foreign = dict(member,handle="F",owner="Y",traversal_path=["X","Y"],entity_type="SOLID")
    gap = dict(kind="gap",reason="unsupported_object_interpretation_raw_retained",handle="F")
    return [dict(kind="header",seeds=["A","X"]),seed,dict(seed,handle="X"),definition,other,member,foreign,
            dict(kind="dbmod_stage",target_context="A",stage="block_definition",call="ENTNEXT"),gap,
            dict(kind="footer",completed=True)]


def admitted(records):
    s = make("A","plan")
    attach_definition(s,records,"4"*64)
    return s["inventory_verified"]


class GapIsolation(unittest.TestCase):
    def test_foreign_leaf_gap(self):
        self.assertTrue(admitted(probe()))

    def test_unowned_gap(self):
        r = probe()
        r[-2]["handle"]="missing"
        self.assertFalse(admitted(r))

    def test_owner_path_disagreement(self):
        r = probe()
        r[6]["traversal_path"]=["A","R"]
        self.assertFalse(admitted(r))

    def test_shared_other_definition_reference(self):
        r = probe()
        r.insert(-1,dict(kind="reference",source="M",code=340,role="uninterpreted_reference",target="F"))
        self.assertFalse(admitted(r))

    def test_unknown_dependency(self):
        r = probe()
        r.insert(-1,dict(kind="reference",source="M",code=340,role="uninterpreted_reference",target={}))
        self.assertFalse(admitted(r))

    def test_null_layout_id_requires_matching_native_record(self):
        r = probe()
        target = dict(reference_status="unresolved_not_dereferenced", session_token="<Entity name: 0>")
        ref = dict(kind="reference",source="R",code=340,section=None,role="uninterpreted_reference",target=target)
        r.insert(-1, ref)
        self.assertFalse(admitted(r))
        r[3]["block_record_raw"] = [[340,"ENAME",target]]
        self.assertTrue(admitted(r))
        ref["section"] = "{other"
        self.assertFalse(admitted(r))
        ref["section"] = None
        target["session_token"] = "<unknown: 0>"
        self.assertFalse(admitted(r))

    def test_nested_block_with_foreign_gap(self):
        r = probe()
        r[5]["entity_type"]="INSERT"
        self.assertFalse(admitted(r))

    def test_global_limit(self):
        r = probe()
        r[-2]["reason"]="node_limit"
        self.assertFalse(admitted(r))

    def test_shared_definition_retains_own_solid_gap(self):
        r = probe()
        r[4]["block_record_handle"] = "R"
        r[4]["block_begin_handle"] = "B"
        r[6].update(owner="R",traversal_path=["A","R"],raw=[group(210,[0,0,1])])
        r.insert(8,deepcopy(r[7]))
        s = make("X","plan")
        attach_definition(s,r,"4"*64)
        self.assertEqual(s["definition_coverage"]["gaps"][0]["disposition"], "local_raw_requires_field_validation")
        s["transform"] = make("X","plan")["transform"]
        r[5]["raw"] = make("A","legend")["members"][0]["raw"]
        result = compare(s,s,dict(row_id="r",status="bounded"))
        self.assertEqual(result["match_status"], "unresolved")
        self.assertIn("SOLID F", str(result["missing_evidence"]))

    def test_dirty_global_stage_blocks_before_local_qualification(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            dwg = folder / "fixture.dwg"
            dwg.write_bytes(b"fixture")
            pin = digest(dwg)
            head = dict(kind="header",contract="TargetedNativeProbe/1",project_id="p",drawing_path=str(dwg),
                        collector_revision=3,seeds=["A"],dbmod=0)
            request = dict(project_id="p", drawing_path=str(dwg),collector_revision=3,seed_handles=["A"],
                           dwg_sha256_before=pin,dbmod_trace_path=str(folder/"trace"))
            report = [head,dict(kind="dbmod_stage",stage="entity_data",before=0,after=1),
                      dict(kind="node",handle="A",entity_type="LINE",read_status="read",owner=None,
                           xdata_status="absent",raw=[group(0,"LINE"),group(5,"A")]),
                      dict(kind="gap",handle="F",reason="unsupported_object_interpretation_raw_retained"),
                      dict(kind="footer",completed=True,dbmod=0,node_count=1)]
            for name, value in [("request",json.dumps(request)), ("manifest","{}"),
                                ("report","\n".join(map(json.dumps,report)))]:
                (folder/name).write_text(value,encoding="utf-8")
            spec = {key:folder/key for key in ("request","manifest","report")}
            with self.assertRaisesRegex(ValueError,"DBMOD"):
                load_probe(spec,"p",dwg.name,pin)
