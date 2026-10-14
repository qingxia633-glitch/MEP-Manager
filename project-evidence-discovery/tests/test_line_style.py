"""Synthetic software contract tests; not project/AutoCAD evidence."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from annotations import load_report

def record(values=(), typ='LINE', version='2.5-line-style-evidence-v1', marker=True, tail=''):
    header=f'ExtractorVersion="{version}"\nDWG="test.dwg"\nAcquisitionMode="ModelSpaceTopLevelAllLayers"\nModelSpaceTopLevel="included"\nNestedBlocks="not expanded"\n'
    text=header+f'EntityHandle="A1"\nDXF_Type="{typ}"\nObjectName="'+('AcDbZombieEntity' if typ=='ACAD_PROXY_ENTITY' else 'AcDbLine')+'"\nLayer="L1"\nStart_WCS=(0 0 0)\nEnd_WCS=(1 0 0)\n'
    if marker:text+='StyleEvidenceVersion="1"\nStyleLayerHandle="B1"\n'
    for k,v in values:
        text+=f'Style.{k}.Status="read"\nStyle.{k}.Value={json.dumps(v)}\nStyle.{k}.Source="synthetic:raw"\n'
    return text+tail+'\nEND_OF_REPORT\n'

class StyleTests(unittest.TestCase):
    def load(self,text):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'report.txt';p.write_text(text,encoding='utf-8')
            return load_report(p,project_id='P')
    def evidence(self,values=(),**kw):return self.load(record(values,**kw))['style_evidence'][0]
    def test_explicit_aci(self):
        e=self.evidence([('entity_aci',3),('entity_color_mode','explicit_aci')]);self.assertEqual(e['raw_entity_style']['entity_aci']['value'],3)
    def test_truecolor(self):
        e=self.evidence([('entity_truecolor_rgb',[12,34,56]),('entity_color_mode','explicit_truecolor')]);self.assertEqual(e['raw_entity_style']['entity_truecolor_rgb']['value'],[12,34,56])
    def test_bylayer_separate(self):
        e=self.evidence([('entity_color_mode','ByLayer'),('layer_name','L1'),('layer_color_mode','explicit_aci'),('layer_aci',1)])
        self.assertEqual(e['raw_entity_style']['entity_color_mode']['value'],'ByLayer');self.assertEqual(e['layer_raw_style']['fields']['layer_aci']['value'],1)
    def test_byblock(self):
        e=self.evidence([('entity_color_mode','ByBlock')]);self.assertEqual(e['style_resolution_status']['color'],'unresolved_byblock')
    def test_layer_linetype(self):
        e=self.evidence([('entity_linetype','ByLayer'),('entity_linetype_mode','ByLayer'),('layer_name','L1'),('layer_linetype','DASHED')]);self.assertEqual(e['layer_raw_style']['fields']['layer_linetype']['value'],'DASHED');self.assertEqual(e['style_resolution_status']['linetype'],'bylayer_candidate')
    def test_entity_linetype(self):
        e=self.evidence([('entity_linetype','CENTER'),('entity_linetype_mode','explicit')]);self.assertEqual(e['raw_entity_style']['entity_linetype']['value'],'CENTER')
    def test_scale(self):self.assertEqual(self.evidence([('entity_linetype_scale',2.5)])['raw_entity_style']['entity_linetype_scale']['value'],2.5)
    def test_weight(self):self.assertEqual(self.evidence([('entity_lineweight',35)])['raw_entity_style']['entity_lineweight']['value'],35)
    def test_layer_states(self):
        e=self.evidence([(k,v) for k,v in [('layer_on',False),('layer_frozen',True),('layer_locked',True),('layer_plottable',False)]])
        self.assertIs(e['layer_raw_style']['fields']['layer_on']['value'],False)
    def test_old_missing(self):
        e=self.evidence(version='2.4-leader-evidence-v1',marker=False);self.assertEqual(e['raw_entity_style']['entity_aci']['status'],'missing');self.assertIsNone(e['raw_entity_style']['entity_aci']['value'])
    def test_old_cannot_claim_new_fields(self):
        e=self.evidence([('entity_aci',3)],version='2.4-leader-evidence-v1');self.assertEqual(e['raw_entity_style']['entity_aci']['status'],'unsupported')
    def test_width_legacy(self):
        e=self.evidence(typ='LWPOLYLINE',version='2.4-leader-evidence-v1',marker=False,tail='Flags_DXF70=128\nWidth_or_bulge_DXF=(43 . 2.0)\nVertex_OCS=(0 0 0)\nWidth_or_bulge_DXF=(40 . 1.0)\nWidth_or_bulge_DXF=(41 . 3.0)\n')
        self.assertEqual(e['polyline']['constant_width']['value'],2.0);self.assertEqual(e['polyline']['vertices'][0]['vertex_end_width']['value'],3.0);self.assertEqual(e['polyline']['linetype_generation_mode']['value'],'continuous_through_vertices')
    def test_proxy_no_children(self):
        c=self.load(record([('entity_aci',3)],typ='ACAD_PROXY_ENTITY'));self.assertEqual(c['targets'],[]);self.assertTrue(c['style_evidence'][0]['host_dependent_visual_evidence_unresolved'])
    def test_json_roundtrip(self):
        e=self.evidence([('entity_colorbook_name','book:name')]);self.assertEqual(e,json.loads(json.dumps(e)))
    def test_invalid_value(self):self.assertEqual(self.evidence([('entity_truecolor_rgb',[999,0,1])])['raw_entity_style']['entity_truecolor_rgb']['status'],'unavailable')
    def test_missing_source(self):
        c=self.load(record([('entity_aci',2)]).replace('Style.entity_aci.Source="synthetic:raw"\n',''));self.assertEqual(c['style_evidence'][0]['raw_entity_style']['entity_aci']['status'],'unavailable')
    def test_duplicate_field(self):self.assertEqual(self.evidence([('entity_aci',1),('entity_aci',2)])['raw_entity_style']['entity_aci']['status'],'unavailable')
    def test_foreign_layer(self):
        e=self.evidence([('entity_linetype_mode','ByLayer'),('layer_name','OTHER'),('layer_linetype','DASHED')]);self.assertEqual(e['style_resolution_status']['linetype'],'unresolved')
    def test_explicit_missing_value_not_direct(self):self.assertEqual(self.evidence([('entity_color_mode','explicit_aci')])['style_resolution_status']['color'],'unresolved')
    def test_unsupported_status(self):
        e=self.evidence(tail='Style.layer_transparency.Status="unsupported"\nStyle.layer_transparency.Source="host"\n');self.assertEqual(e['layer_raw_style']['fields']['layer_transparency']['status'],'unsupported')

    def test_incoherent_explicit_aci_not_direct(self):
        e=self.evidence([('entity_color_mode','explicit_aci'),('entity_aci',256)])
        self.assertEqual(e['style_resolution_status']['color'],'unresolved')
    def test_layer_unresolved_weight_not_candidate(self):
        e=self.evidence([('entity_lineweight_mode','ByLayer'),('layer_name','L1'),('layer_lineweight',-3)])
        self.assertEqual(e['style_resolution_status']['lineweight'],'unresolved')
    def test_layer_inherited_linetype_not_candidate(self):
        e=self.evidence([('entity_linetype_mode','ByLayer'),('layer_name','L1'),('layer_linetype','ByBlock')])
        self.assertEqual(e['style_resolution_status']['linetype'],'unresolved')
    def test_failed_acquisition_never_direct(self):
        e=self.evidence([('entity_color_mode','explicit_aci'),('entity_aci',3)],tail='StyleAcquisitionStatus="unavailable"\n')
        self.assertEqual(e['style_resolution_status']['color'],'unresolved')

    def test_style_does_not_change_discovery(self):
        from discovery import discover
        from test_leader_v1 import HEADER,BODY
        c=self.load(HEADER+BODY);before=discover(c)
        c['style_evidence']=[self.evidence([('entity_aci',1),('entity_color_mode','explicit_aci')])]
        self.assertEqual(discover(c),before)
    def test_all_required_types(self):
        for typ in ('LINE','LWPOLYLINE','POLYLINE','ARC','SPLINE'):
            with self.subTest(typ=typ):
                e=self.evidence([('entity_aci',3)],typ=typ)
                self.assertEqual(e['entity_type'],typ)
                self.assertEqual(e['raw_entity_style']['entity_aci']['value'],3)
    def test_old_polyline_flags_not_blessed(self):
        e=self.evidence(typ='POLYLINE',version='2.4-leader-evidence-v1',marker=False,tail='Flags_DXF70=0\n')
        self.assertEqual(e['polyline']['linetype_generation_mode']['status'],'missing')
    def test_polyline_vertex_raw_widths(self):
        e=self.evidence(typ='POLYLINE',tail='StylePolylineFlags=128\nSubentity_DXF=((0 . "VERTEX") (40 . 2.0) (41 . 4.0))\n')
        self.assertEqual(e['polyline']['vertices'][0]['vertex_start_width']['value'],2)
        self.assertEqual(e['polyline']['vertices'][0]['vertex_end_width']['value'],4)
