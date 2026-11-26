import sys
import unittest
from copy import deepcopy
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from recognition import qualify_shared, row_label
from survey import locate, segment_hits, survey


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.rec = '\n'.join(['Insertion_OCS=(1 2 0)','Normal_DXF210=(0 0 1)',
                               'Style.entity_visibility.Status="read"','Style.entity_visibility.Value="true"']
                              + [f'BlockTransform_or_Array_DXF=({k} . {v})' for k,v in
                                 [(41,2),(42,2),(43,2),(50,0),(70,0),(71,0)]])
        self.sym = dict(name="symbol",effective_name="symbol",dynamic=":vlax-false",
                        identity=dict(project_id="p",drawing="d",dwg_sha256="v",snapshot_id="s",
                                      parent_path=[],handle="A"),attributes=[{"value":"actual"}])
        self.donor = deepcopy(self.sym)
        self.donor["identity"]["handle"]="B"
        self.donor.update(inventory_verified=True,definition={"block_record":"btr"},base=[0,0,0],
                          members=[],defaults=[],definition_coverage={},attributes=[],transform=[])

    def test_shared_definition_only(self):
        qualify_shared(self.sym,[self.donor],self.rec)
        self.assertEqual(self.sym['definition_source_insert'],'B')
        self.assertEqual(self.sym['attributes'],[{'value':'actual'}])
        self.assertEqual(self.sym['identity']['handle'],'A')
        self.assertNotEqual(self.sym['transform'],self.donor['transform'])

    def test_foreign_and_dynamic(self):
        for key in ("project_id","drawing","dwg_sha256","snapshot_id"):
            d=deepcopy(self.donor)
            d["identity"][key]="other"
            qualify_shared(self.sym,[d],self.rec)
            self.assertNotIn('definition',self.sym)
        self.sym['dynamic']=':vlax-true'
        qualify_shared(self.sym,[self.donor],self.rec)
        self.assertNotIn('definition',self.sym)

    def test_missing_transform_or_visibility(self):
        for token in ('(50 . 0)','"true"','Normal_DXF210='):
            qualify_shared(self.sym,[self.donor],self.rec.replace(token,""))
            self.assertNotIn('definition',self.sym)

    def test_conflicting_or_incomplete_definition(self):
        d=deepcopy(self.donor)
        d['definition']['block_record']='different'
        qualify_shared(self.sym,[d,self.donor],self.rec)
        self.assertNotIn('definition',self.sym)
        self.donor['inventory_verified']=False
        qualify_shared(self.sym,[self.donor],self.rec)
        self.assertNotIn('definition',self.sym)

    def test_boundary_crossing_without_interior_endpoint(self):
        box=(0,0,5,5)
        self.assertTrue(segment_hits((-1,1),(6,1),box))
        self.assertFalse(segment_hits((-5,1),(1,10),box))
        self.assertEqual(locate("Start_WCS=(-1 1 0)\nEnd_WCS=(6 1 0)",'LINE',box)[0],'on_boundary')

    def test_unread_extent_and_failed_report(self):
        self.assertEqual(locate('','PROXY',(0,0,2,2))[0],'unresolved')
        with self.assertRaises(ValueError):
            survey("ReadErrorCount=1\nEND_OF_REPORT: incomplete",{})

    def test_model_cell_cannot_be_a_device_name(self):
        symbol=dict(attributes=[dict(tag="A",value="example name"),dict(tag="B",value="model")])
        row=dict(row_id="r",texts=[dict(handle="a",membership="cell",text="model")])
        with self.assertRaises(ValueError):
            row_label(symbol,row,"a")
        row["texts"][0]["text"]="example name"
        self.assertEqual(row_label(symbol,row,"a")["type"],"example name")
        row["texts"][0]["membership"]="row_only"
        with self.assertRaises(ValueError):
            row_label(symbol,row,"a")
