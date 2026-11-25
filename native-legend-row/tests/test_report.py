import tempfile
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from resolve import read_region
from report_manifest import write_manifest

HEADER = '''ExtractorVersion="2.8-field-graph-evidence-v1"
DWG="synthetic.dwg"
AcquisitionMode="ModelSpaceTopLevelAllLayers"
AllLayers="included; including off/frozen"
ModelSpaceTopLevel="included"
NestedBlocks="not expanded"
'''
TABLE = '''EntityHandle="A"
DXF_Type="ACAD_TABLE"
TableEvidenceVersion="1"
Table.InsertionPoint.Value=(1 1 0)
Table.InsertionPoint.Status="read"
Table.InsertionPoint.Source="getter"
Table.Rows.Value=1
Table.Rows.Source="getter"
Table.Rows.Status="read"
Table.Columns.Value=1
Table.Columns.Source="getter"
Table.Columns.Status="read"
TableCell_BEGIN
Cell.Row=0
Cell.Column=0
Cell.Type.Value=1
Cell.Type.Status="read"
Cell.Type.Source="getter"
Cell.Text.Value="literal"
Cell.Text.Status="read"
Cell.Text.Source="getter"
TableCell_END
TableEvidenceComplete=true
'''
END='SelectedEntityTotal=1\nReadErrorCount=0\nEND_OF_REPORT: completed\n'


class Adapter(unittest.TestCase):
    def prepare(self, text):
        folder=tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        p=Path(folder.name)/'r.txt'
        m=p.with_suffix('.json')
        p.write_text(text,encoding='utf-8-sig')
        write_manifest(p,m)
        return p,m

    def run_region(self,p,m):
        return read_region(p,m,'demo','view',[0,0,3,3])

    def test_table_uses_native_identity(self):
        r=self.run_region(*self.prepare(HEADER+TABLE+END))
        self.assertEqual(r['region_kind'],'native_table')
        c=r['objects']['A']['native_table']['cells'][0]
        self.assertEqual((c['identity']['table_handle'],c['row_index'],c['column_index']),('A',0,0))
        self.assertEqual(r['rows'],[])

    def test_manifest_mismatch(self):
        p,m=self.prepare(HEADER+TABLE+END)
        with p.open('ab') as f:f.write(b' ')
        with self.assertRaises(ValueError):self.run_region(p,m)

    def test_incomplete_acquisition(self):
        with self.assertRaises(ValueError):
            self.run_region(*self.prepare(HEADER+TABLE+END.replace('Count=0','Count=1')))

    def test_foreign_scope(self):
        with self.assertRaises(ValueError):
            self.run_region(*self.prepare(HEADER.replace('ModelSpaceTopLevel="included"','ModelSpaceTopLevel="unknown"')+TABLE+END))

    def test_no_version_guess(self):
        with self.assertRaises(ValueError):
            self.run_region(*self.prepare(HEADER.replace('2.8-field-graph-evidence-v1','unknown')+TABLE+END))

    def test_unavailable_text_bounds(self):
        ent='EntityHandle="E"\nDXF_Type="TEXT"\nText_RAW="a"\nPosition_WCS=(1 1 0)\nbboxStatus="missing"\n'
        r=self.run_region(*self.prepare(HEADER+ent+END))
        self.assertEqual(r['unresolved_items'][0]['reason'],'extent_unverified')
        self.assertEqual(r['objects']['E']['provenance']['record_start_line'],7)

    def test_nonplanar_line_not_a_boundary(self):
        ent='EntityHandle="E"\nDXF_Type="LINE"\nStart_WCS=(1 1 0)\nEnd_WCS=(2 1 1)\n'
        r=self.run_region(*self.prepare(HEADER+ent+END))
        self.assertFalse(r['objects']['E']['straight'])

    def test_curved_polyline_not_a_boundary(self):
        ent=('EntityHandle="E"\nDXF_Type="LWPOLYLINE"\nVertex_WCS=(1 1 0)\n'
             'Width_or_bulge_DXF=(42 . 1)\nVertex_WCS=(2 1 0)\n')
        r=self.run_region(*self.prepare(HEADER+ent+END))
        self.assertFalse(r['objects']['E']['straight'])
