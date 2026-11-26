"""Exercise source selection independently from regional outcomes."""
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from replay_project_legend import native, pinned, source_material
from test_project_legend import fixture, recover


class SourceTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path=Path(tmp.name)/"report.txt"
        path.write_text('EntityHandle="FF"\nDXF_Type="TEXT"\nText_RAW="示例传感器"\n',encoding="utf-8-sig")
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        self.source=dict(report=str(path),sha256=digest)
        sel=dict(kind="legend_row",region="reg",symbol="AE",name_texts=["FF"],discipline=None)
        self.catalog=dict(project_id="P",snapshot_id=digest,sources=[sel])
        prov=dict(project_id="P",drawing="drawing",snapshot_id=digest)
        def obj(handle,kind,text):
            identity=dict(project_id="P",drawing_ref="drawing",snapshot_id=digest,handle=handle,parent_path=[])
            return dict(identity=identity,provenance=identity,kind=kind,decoded_text=text)
        def cell(h,status):
            return dict(cell_id="cell-"+h,members=[h],evidence_status=status)
        self.row=dict(row_id="row",provenance=prov,evidence_status="bounded",original_members=["AE","FF"],
                      row_only_candidates=[],cells=[cell("AE","bounded"),cell("FF","ambiguous")])
        self.region=dict(legend_region_id="reg",provenance=prov,rows=[self.row],
                         objects={"AE":obj("AE","INSERT",None),"FF":obj("FF","TEXT","示例传感器")})
        fake_symbol=dict(identity=dict(prov,handle="AE",parent_path=[]),name="source-block",attributes=[
            dict(owner="AE",handle="AF",tag="A",value="QQ"),dict(owner="AE",handle="BA",tag="$TEXT$",value="QQ")])
        mock=patch.object(native,"drawing_symbols",return_value={"AE":fake_symbol})
        mock.start()
        self.addCleanup(mock.stop)

    def build(self):
        return source_material(self.source,{"regions":[self.region]},self.catalog)

    def test_both_membership_states_and_raw_text(self):
        entry=self.build()[0]
        self.assertEqual(entry["row_status"],"bounded")
        self.assertEqual(entry["membership"],"ambiguous")
        self.assertEqual(entry["name_fragments"][0]["provenance"]["handle"],"FF")
        self.assertEqual(entry["symbol_cells"][0]["status"],"bounded")

    def test_name_not_in_a_cell(self):
        self.row["cells"][1]["members"]=[]
        with self.assertRaises(ValueError): self.build()

    def test_wrong_snapshot(self):
        self.region["objects"]["FF"]["identity"]["snapshot_id"]="other"
        with self.assertRaises(ValueError): self.build()

    def test_changed_title(self):
        self.region["objects"]["FF"]["decoded_text"]="other"
        with self.assertRaises(ValueError): self.build()

    def test_unknown_membership(self):
        self.row["cells"][1]["evidence_status"]="unresolved"
        with self.assertRaises(ValueError): self.build()

    def test_two_memberships(self):
        self.region["rows"].append(dict(self.row,row_id="elsewhere"))
        with self.assertRaises(ValueError): self.build()

    def test_stale_report(self):
        Path(self.source["report"]).write_text("changed")
        with self.assertRaises(ValueError): self.build()

    def test_stale_catalog_hash(self):
        with self.assertRaises(ValueError): pinned(self.source["report"],"mismatch")

    def test_prediction_selector_rejected(self):
        self.catalog["sources"][0]["target_handle"]="AA"
        with self.assertRaises(ValueError): self.build()

    def test_foreign_project_code_isolated(self):
        o,s,_=fixture("QQ")
        a=self.build()
        self.assertEqual(recover(o,s,a)["role_candidates"],["示例传感器"])
        a[0]["project_id"]="different"
        a[0]["label"]="其他设备"
        with self.assertRaises(ValueError): recover(o,s,a)
