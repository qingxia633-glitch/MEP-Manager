import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from annotations import load_report
from discovery import discover

HEADER='DWG="test.dwg"\nAcquisitionMode="ModelSpaceTopLevelAllLayers"\nModelSpaceTopLevel="included"\nNestedBlocks="not expanded"\n'
LAYOUT='Position_WCS=(10 20 30)\npositionFrame="WCS"\npositionStatus="read"\nbboxMin=(9 19 29)\nbboxMax=(11 21 31)\nbboxFrame="WCS"\nbboxStatus="read"\n'
def context(kind='TEXT',layout=LAYOUT):
    if kind=='ATTRIB':
        rec='EntityHandle="I"\nDXF_Type="INSERT"\nAttributeTag="A"\nAttributeText_RAW="S"\nAttributeLayer="L"\nAttribute_DXF=((5 . "T") (10 1 2 3))\n'
        layout=''.join('AttributeLayout.'+s+'\n' for s in layout.splitlines())
    else:rec=f'EntityHandle="T"\nDXF_Type="{kind}"\nText_RAW="S"\nLayer="L"\n'
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/'r.txt';p.write_text(HEADER+rec+layout,encoding='utf-8')
        return load_report(p,'P')
def ann(kind='TEXT',layout=LAYOUT):return context(kind,layout)['annotations'][0]

class TextLayoutTests(unittest.TestCase):
    def test_text_roundtrip(self):
        a=ann(layout=LAYOUT+'Rotation=1.2\nRotation_Status="read"\n')
        self.assertEqual(a['bounds']['min_wcs'],[9,19,29]);self.assertEqual(a['position_wcs'],[10,20,30]);self.assertEqual(a['rotation'],1.2)
    def test_mtext_direction(self):
        a=ann('MTEXT',LAYOUT+'Direction_WCS_RAW=(0 1 0)\nDirection_WCS_RAW_Status="read"\nRotation=nil\nRotation_Status="not_interpreted_use_direction_vector"\n')
        self.assertEqual(a['direction_wcs'],[0,1,0]);self.assertIsNone(a['rotation']);self.assertEqual(a['rotation_status'],'not_interpreted_use_direction_vector')
    def test_mtext_bbox(self):self.assertEqual(ann('MTEXT')['bounds']['status'],'read')
    def test_attribute_wcs(self):self.assertEqual(ann('ATTRIB')['position_wcs'],[10,20,30])
    def test_attribute_owner(self):
        a=ann('ATTRIB');self.assertEqual(a['parent_path'],['I']);self.assertEqual(a['owner_insert_identity']['parent_path'],[]);self.assertEqual(a['tag'],'A');self.assertEqual(a['decoded_text'],'S')
    def test_attribute_bbox(self):self.assertEqual(ann('ATTRIB')['bounds']['max_wcs'],[11,21,31])
    def test_visibility(self):self.assertEqual(ann('ATTRIB',LAYOUT+'VisibilityEvidence="attribute_invisible_flag"\n')['visibility_evidence'],'attribute_invisible_flag')
    def test_missing(self):self.assertEqual(ann(layout='')['bounds']['status'],'missing')
    def test_error(self):self.assertEqual(ann(layout=LAYOUT.replace('bboxStatus="read"','bboxStatus="unavailable"'))['bounds']['status'],'unavailable')
    def test_bad_box(self):
        for v in ['(99 19 29)','(nan 19 29)','(1 2)','junk']:
            a=ann(layout=LAYOUT.replace('(9 19 29)',v));self.assertEqual(a['bounds']['status'],'invalid_result');self.assertIsNone(a['bounds']['min_wcs'])
    def test_legacy_ocs(self):
        a=ann('ATTRIB','');self.assertEqual(a['position_source'],'legacy_raw_dxf');self.assertIsNone(a['position_wcs']);self.assertEqual(a['position_raw'],[1,2,3])
    def test_no_proximity_binding(self):
        c=context();c['targets']=[{'id':'E','target_type':'edge','geometry':{'type':'LINE','vertices_wcs':[[10,20,30],[11,20,30]],'complete':True}}]
        self.assertEqual(discover(c)['bindings'],[])
    def test_no_scope(self):self.assertIsNone(discover(context())['evidence'][0]['scope_candidate'])
    def test_discovery_retains_layout(self):
        e=discover(context())['evidence'][0]
        self.assertEqual(e['bounds']['status'],'read');self.assertEqual(e['position_source'],'exporter_wcs');self.assertIn('text_height_status',e)
    def test_read_value_without_status(self):
        a=ann(layout=LAYOUT.replace('positionStatus="read"\n',''))
        self.assertIsNone(a['position_wcs']);self.assertEqual(a['position_status'],'unresolved')
    def test_legacy_explicit_wcs(self):
        a=ann(layout='Insertion_WCS=(1 2 3)\n')
        self.assertEqual(a['position_source'],'legacy_exporter_wcs');self.assertEqual(a['position_contract_status'],'legacy')
    def test_failed_scalar(self):
        a=ann(layout=LAYOUT+'TextHeight=nan\nTextHeight_Status="read"\n')
        self.assertIsNone(a['text_height']);self.assertEqual(a['text_height_status'],'invalid_result')
    def test_text_visibility(self):
        a=ann(layout=LAYOUT+'Style.entity_visibility.Status="read"\nStyle.entity_visibility.Value=true\nStyle.entity_visibility.Source="DXF60"\n')
        self.assertTrue(a['visibility_evidence']['value']);self.assertEqual(a['visibility_status'],'read')
    def test_foreign_frame(self):self.assertIsNone(ann(layout=LAYOUT.replace('bboxFrame="WCS"','bboxFrame="OCS"'))['bounds']['min_wcs'])
    def test_failed_current_never_fallback(self):
        a=ann('ATTRIB',LAYOUT.replace('positionStatus="read"','positionStatus="conversion_error"'));self.assertIsNone(a['position_wcs']);self.assertEqual(a['position_status'],'conversion_error')

if __name__=='__main__':unittest.main()
