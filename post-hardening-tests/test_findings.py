import copy
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'safety-hardening'))
from fixtures import item as old_item, plan as old_plan, seal
from test_adversarial import load


def complete_identity(value):
    if isinstance(value, dict):
        if all(k in value for k in ('project_id', 'drawing_ref', 'edge_handle')):
            value['parent_path'] = []
            value['scope_type'] = 'segment' if value.get('segment_id') is not None else 'edge'
        for child in value.values(): complete_identity(child)
    elif isinstance(value, list):
        for child in value: complete_identity(child)
    return value


def item():
    x=complete_identity(old_item())
    binding=copy.deepcopy(x['measurement_scope']['binding'])
    x['semantic_gate']['object_identity']=binding
    x['semantic_gate']['provenance']['context']=copy.deepcopy(binding)
    x['semantic_gate']['accepted_evidence']=[{'object_identity':binding,'provenance':['synthetic-review']}]
    x['height'].update(status='supported',provenance=['synthetic approved height'])
    return x


def plan():
    p=complete_identity(old_plan())
    x=item()
    p['geometry_basis']=x['geometry'];p['height_evidence']=x['height']
    return seal(p)


class Findings(unittest.TestCase):
    def test_P1_1_instance_authorization_cannot_cross(self):
        m=load('project-evidence-gate')
        identity={'project_id':'P','drawing_ref':'D','parent_path':['I2'],'edge_handle':'E','scope_type':'edge'}
        c=dict(identity,candidate_role='alarm_or_linkage_bus')
        e={'evidence_id':'e','evidence_type':'human_project_confirmation','evidence_strength':'direct_object_binding',
           'status':'supported','semantic_role':'bus','assertion':'affirm','binding_id':'b','provenance':['review']}
        b=dict(identity,parent_path=['I1'],binding_id='b',review_status='reviewed',evidence_ids=['e'],provenance=['review'])
        result=m.evaluate_semantics(c,{'project_id':'P','drawing_ref':'D','evidence':[e],'bindings':[b]},identity)
        self.assertFalse(result['semantic_gate_passed'])

    def test_P1_2_self_consistent_wrong_physical_factor(self):
        x=item();x['geometry']['source_unit']='mm';x['geometry']['conversion'].update(from_unit='mm',factor='1',converted_length='10')
        result=load('quantity-eligibility').resolve_eligibility(x)
        self.assertNotEqual(result['quantity_eligibility_status'],'eligible')

    def test_P1_3_missing_3d_basis_blocks_builder(self):
        p=plan();p['base_path']['mode']='approved_3d';p.pop('geometry_basis',None);p.pop('height_evidence',None)
        result=load('design-net-quantity','builder.py').build(seal(p),[])
        self.assertNotEqual(result['status'],'built')

    def test_P1_4_same_value_changed_spec_review_not_full_match(self):
        m=load('design-net-quantity','builder.py');p=plan();q=m.build(p,[])['quantity']
        p['specification']['provenance']=[{'source_id':'different-approved-review'}]
        result=m.replay_validate(seal(p),q)
        self.assertTrue(result['numeric_match'])
        self.assertNotEqual(result['status'],'replay_matched')

    def test_P2_1_report_attribute_owner_binding(self):
        m=load('project-evidence-discovery','discovery.py')
        from annotations import load_report
        report='DWG="sample.dwg"\nEntityHandle="I"\nDXF_Type="INSERT"\nAttributeTag="A"\nAttributeText_RAW="S"\nAttribute_DXF=((5 . "T") (10 0 0 0))\n'
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'report.txt';p.write_text(report,encoding='utf-8')
            c=load_report(p);r=m.discover(c)
        self.assertEqual(len(r['bindings']),1)
        self.assertEqual(r['bindings'][0]['target_id'],'I')
        self.assertEqual(r['bindings'][0]['binding_status'],'supported')


if __name__=='__main__':unittest.main()
