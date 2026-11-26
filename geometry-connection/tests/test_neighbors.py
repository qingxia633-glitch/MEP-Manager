from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from neighbors import query_endpoint, load_source
from resolver import DrawingContext


def line(handle, a, b):
    return dict(handle=handle, type="LINE", vertices=[a,b])


def fixture():
    a, b = [0,0,0], [2,0,0]
    entities = {"A":line("A",a,[-2,0,0]), "B":line("B",b,[3,0,0]),
                "D":dict(type="INSERT",handle="D",block="symbol",normal=[0,0,1],
                         insertion=a,scale=[1,1,1],rotation=0)}
    definition = dict(base=a,dynamic=False,complete=True,entities=[
        dict(handle="P",type="POINT",point=a),dict(handle="Q",type="POINT",point=b)])
    ctx=DrawingContext(entities,{"symbol":definition},[],project_id="proj",drawing_ref="dwg")
    ctx.contact_tolerance=0.001
    ctx.floor_evidence={"status":"unresolved"}
    identities={"D":{"block_record":"R","probe_sha256":"probe"}}
    return ctx, identities


class NeighborTests(unittest.TestCase):
    def setUp(self):
        self.ctx,self.defs=fixture()

    def query(self):
        return query_endpoint(self.ctx, self.defs, {"project_id":"proj","drawing_instance_id":"drawing",
                              "snapshot_id":"snapshot"}, "A", "start")

    def test_other_port(self):
        result=self.query()
        device=result["devices"][0]
        self.assertEqual(["P"],[p["identity"]["handle"] for p in device["source_points"]])
        self.assertEqual([("B","Q","different_point")],[(e["edge"]["handle"],e["point"]["handle"],
                         e["relation"]) for e in device["neighbors"]])

    def test_multiple_on_same_point(self):
        for h in ["C","E"]:
            self.ctx.entities[h]=line(h,[0,0,0],[0,3,0])
        ns=self.query()["devices"][0]["neighbors"]
        self.assertEqual(["C","E"],[n["edge"]["handle"] for n in ns if n["relation"]=="same_point"])

    def test_shared_definition_and_coincident_devices(self):
        self.ctx.entities["F"]=dict(self.ctx.entities["D"],handle="F")
        self.defs["F"]=self.defs["D"]
        r=self.query()
        self.assertIn("ambiguous_device_or_point",r["stop_reasons"])
        self.assertEqual([["D"],["F"]],[d["source_points"][0]["identity"]["parent_path"] for d in r["devices"]])

    def test_multiple_point_identities(self):
        self.ctx.definitions["symbol"]["entities"].append(dict(type="POINT",handle="U",point=[0,0,0]))
        r=self.query()
        self.assertEqual(2,len(r["devices"][0]["source_points"]))
        self.assertIn("ambiguous_device_or_point",r["stop_reasons"])

    def test_missing_definition(self):
        self.defs["D"]=None
        self.assertIn("missing_current_block_definition",self.query()["stop_reasons"])

    def test_no_interior_crossing(self):
        self.ctx.entities["B"]=line("B",[2,-1,0],[2,1,0])
        self.assertFalse(self.query()["devices"][0]["neighbors"])

    def test_jump_no_turn(self):
        self.ctx.entities.update(B=line("B",[2,-2,0],[2,2,0]),C=line("C",[2.2,0,0],[4,0,0]))
        self.assertEqual("unresolved",self.query()["neighboring_edge_discovery_status"])

    def test_other_elevation(self):
        self.ctx.entities["B"]=line("B",[2,0,1],[4,0,1])
        result=self.query()
        self.assertFalse(result["devices"][0]["neighbors"])
        self.assertEqual("xy_only_xyz_contact_unverified",result["unresolved_contacts"][0]["reason"])

    def test_cycle_and_no_approvals(self):
        self.ctx.entities["B"]=line("B",[2,0,0],[0,0,0])
        r=self.query()
        self.assertEqual(2,len(r["devices"][0]["neighbors"]))
        self.assertEqual("unresolved",r["engineering_connection_status"])
        self.assertEqual("unresolved",r["circuit_identity_status"])
        self.assertNotIn("quantity",r)

    def test_order(self):
        before=self.query()
        self.ctx.entities=dict(reversed(self.ctx.entities.items()))
        self.ctx.definitions["symbol"]["entities"].reverse()
        self.assertEqual(before,self.query())

    def test_source_pin(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"registry.json"
            p.write_text("{}")
            with self.assertRaises(ValueError):
                load_source(dict(project_id="p",registry=dict(path=str(p),sha256="0"*64),
                                 source={},device_handles=["D"]))

    def test_closed_edge(self):
        self.ctx.entities["A"].update(type="LWPOLYLINE",closed=True)
        self.assertIn("source_endpoint_unverified",self.query()["stop_reasons"])

    def test_shared_definition_different_instances(self):
        self.ctx.entities["F"]=dict(self.ctx.entities["D"],handle="F",insertion=[10,0,0])
        self.defs["F"]=self.defs["D"]
        self.assertEqual(["D"],[d["identity"]["handle"] for d in self.query()["devices"]])

    def test_invalid_tolerance(self):
        for value in (True,float("inf"),float("nan"),0,-1):
            self.ctx.contact_tolerance=value
            with self.assertRaises(ValueError):
                self.query()

    def test_missing_one_instance_preserves_independent_contact(self):
        self.defs["F"]=None
        r=self.query()
        self.assertEqual("supported",r["geometric_contact_status"])
        self.assertEqual("F",r["coverage_gaps"][0]["device"])

    def test_interior_vertices_are_not_endpoints(self):
        self.ctx.entities["B"].update(type="LWPOLYLINE",closed=False,vertices=[[2,-1,0],[2,0,0],[2,1,0]])
        self.assertFalse(self.query()["devices"][0]["neighbors"])

    def test_no_probe_device(self):
        self.defs.clear()
        r=self.query()
        self.assertFalse(r["devices"])
        self.assertIn("missing_current_block_definition",r["stop_reasons"])

    def test_foreign_drawing_version(self):
        import hashlib
        import json
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"registry.json"
            p.write_text(json.dumps(dict(project_id="p",ProjectDrawingRegistryVersion=2,
                drawing_instances=[dict(project_id="p",report_sha256="old",source_dwg_sha256="dwg",
                                        source_filename="drawing.dwg",instance_id="old-instance")])))
            pin=dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
            with self.assertRaisesRegex(ValueError,"unqualified drawing"):
                load_source(dict(project_id="p",registry=pin,source=dict(sha256="new",dwg_sha256="dwg",
                                                                  dwg="drawing.dwg")))

    def test_duplicate_top_level_handle_is_not_overwritten(self):
        record = 'EntityHandle="A"\nDXF_Type="LINE"\nStart_WCS=(0 0 0)\nEnd_WCS=(1 0 0)\n'
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/"snapshot.txt"
            p.write_text(record+record)
            with self.assertRaisesRegex(ValueError,"duplicate top-level handle"):
                DrawingContext.from_reports(p,[],strict_endpoint_inventory=True)

    def test_incomplete_polyline_wcs_does_not_create_shortcut(self):
        self.ctx.entities["B"].update(type="LWPOLYLINE",closed=False,path_verified=False)
        result = self.query()
        self.assertEqual(["B"],result["coverage"]["incomplete_edge_handles"])
        self.assertFalse(result["devices"][0]["neighbors"])

    def test_one_unsupported_point_keeps_known_neighbor(self):
        self.ctx.definitions["symbol"]["entities"].append(dict(handle="X",type="POINT",normal=None,point=None))
        result = self.query()
        self.assertEqual("supported",result["neighboring_edge_discovery_status"])
        self.assertIn("unsupported_entity_normal:X",result["coverage_gaps"][0]["reasons"])
