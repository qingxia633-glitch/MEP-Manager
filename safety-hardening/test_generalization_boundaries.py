import copy
import unittest
from decimal import localcontext, ROUND_UP, Inexact, Rounded
from fixtures import item, policy, seal
from test_adversarial import load


class GeneralizationBoundaries(unittest.TestCase):
    def discovery_context(self):
        return {'project_id':'P','drawing_ref':'D','annotations':[
            {'handle':'T','parent_path':[p],'type':'TEXT','raw_text':'S,余同','provenance':['review']}
            for p in ('I1','I2')],
            'targets':[{'id':'E','parent_path':[p],'target_type':'edge'} for p in ('I1','I2')],
            'object_associations':[{'annotation_handle':'T','parent_path':['I1'],'target_id':'E',
                'status':'supported','provenance':['review']}]}

    def test_instance_qualified_association_and_summaries(self):
        r=load('project-evidence-discovery','discovery.py').discover(self.discovery_context())
        self.assertEqual(len(r['bindings']),1)
        self.assertEqual(r['bindings'][0]['target_parent_path'],['I1'])
        self.assertEqual(len(r['edge_summaries']),2)
        self.assertEqual(sorted(s['direct_binding_count'] for s in r['edge_summaries'].values()),[0,1])
        self.assertNotEqual(r['evidence'][1]['binding_status'],'supported')

    def test_instance_qualified_bounded_group_and_membership(self):
        c=self.discovery_context()
        c['bounded_groups']=[{'annotation_handle':'T','parent_path':['I1'],'root_target_id':'E',
            'bounded_set':[{'target_id':'E','target_type':'edge','target_parent_path':['I1']}],
            'propagation_relation':'group','scope_boundary':'B','termination_condition':'B',
            'status':'supported','provenance':['review']}]
        c['memberships']=[{'annotation_handle':'T','parent_path':['I1'],'target_id':'E',
            'target_type':'edge','geometric_basis':['region'],'provenance':['review']}]
        r=load('project-evidence-discovery','discovery.py').discover(c)
        self.assertEqual([p['propagation_scope_status'] for p in r['propagation_roots']],['supported','unresolved'])
        self.assertEqual(len(r['membership_candidates']),1)
        self.assertEqual(r['membership_candidates'][0]['target_parent_path'],['I1'])

    def test_same_handle_foreign_project_not_joined(self):
        c=self.discovery_context();c['object_associations'][0]['project_id']='foreign'
        r=load('project-evidence-discovery','discovery.py').discover(c)
        self.assertFalse(r['bindings'])

    def test_missing_nested_path_cannot_bind(self):
        c=self.discovery_context();del c['object_associations'][0]['parent_path']
        self.assertFalse(load('project-evidence-discovery','discovery.py').discover(c)['bindings'])

    def test_no_correction_export_is_buildable_and_immutable(self):
        x=item();before=copy.deepcopy(x)
        decision=load('quantity-eligibility').resolve_eligibility(x)
        p=load('quantity-eligibility','plan_v02.py').export_plan(decision,'a'*64,None,policy())
        self.assertEqual(load('design-net-quantity','builder.py').build(p,[])['status'],'built')
        self.assertEqual(x,before)
        self.assertFalse(p['corrections_applied']['changed_paths'])

    def test_invalid_drawing_requires_correction(self):
        decision=load('quantity-eligibility').resolve_eligibility(item())
        decision['quantity_formula_plan']['binding']['drawing_ref']='????.dwg'
        with self.assertRaises(ValueError):
            load('quantity-eligibility','plan_v02.py').export_plan(decision,'a'*64,None,policy())

    def test_decimal_traps_rounding_and_precision_do_not_leak(self):
        x=item();g=x['geometry'];g['base_length']='123456789012345678901234567890'
        g['source_unit']='mm';g['conversion'].update(from_unit='mm',factor='0.001',converted_length='123456789012345678901234567.890')
        x['base_path']['value']=g['conversion']['converted_length']
        m=load('quantity-eligibility');expected=m.resolve_eligibility(x)
        with localcontext() as c:
            c.prec=2;c.rounding=ROUND_UP;c.traps[Inexact]=True;c.traps[Rounded]=True
            self.assertEqual(m.resolve_eligibility(x),expected)
            self.assertEqual(c.prec,2)

    def semantic_input(self):
        identity={'project_id':'P','drawing_ref':'D'}
        ep={'geometry_connection':{'edge_handle':'E','target_handle':'I','geometric_connection_status':'supported',
            'evidence_identity':dict(identity,edge_parent_path=[],target_parent_path=['X'])},
            'device_role':{'device_handle':'I','canonical_role':'smoke_detector','role_status':'supported',
                'evidence_identity':dict(identity,parent_path=['X'])}}
        x={'edge_handle':'E','scope':{'project':'P'},'evidence_identity':dict(identity,parent_path=[]),
            'endpoint_A':ep,'endpoint_B':copy.deepcopy(ep)}
        rules={'rules':[{'kind':'role_pair','rule_id':'A','roles_A':['smoke_detector'],'roles_B':['smoke_detector'],
            'scope':{'project':'P'},'validation_status':'validated','candidate_role':'alarm_or_linkage_bus'}],
            'scope_keys':['project'],'confidence_policy':{'validated':'medium'}}
        return x,rules

    def test_semantic_full_identity_positive_and_mismatches(self):
        m=load('candidate-semantic');x,rules=self.semantic_input()
        self.assertEqual(m.resolve_candidate(x,rules)['candidate_status'],'candidate')
        for field,value in [('project_id','Q'),('drawing_ref','other'),('parent_path',['Y'])]:
            other=copy.deepcopy(x);other['endpoint_A']['device_role']['evidence_identity'][field]=value
            self.assertEqual(m.resolve_candidate(other,rules)['candidate_status'],'unresolved')
        del x['endpoint_A']['device_role']['evidence_identity']
        self.assertEqual(m.resolve_candidate(x,rules)['candidate_status'],'unresolved')

    def test_legend_policy_absent_tampered_or_foreign_blocks(self):
        m=load('device-role')
        c=m.RoleContext('D',{'I':{'block_name':'B','attributes':[]}},{},legends=[{
            'source_drawing':'independent.dwg','target_drawing':'D','target_block_name':'B','binding_verified':True,
            'binding_evidence_refs':['review'],'raw_value':'模块箱'}])
        self.assertEqual(m.resolve_device_role('I',c)['canonical_role'],'unknown')
        p=seal({'policy_id':'policy','version':'1','status':'approved','target_drawing':'D',
            'allowed_sources':['independent.dwg'],'provenance':['review']})
        c.legend_policy=p
        r=m.resolve_device_role('I',c)
        self.assertEqual(r['canonical_role'],'module_box')
        self.assertEqual(r['legend_policy_evidence']['content_hash'],p['content_hash'])
        p['version']='changed'
        self.assertEqual(m.resolve_device_role('I',c)['canonical_role'],'unknown')
        p['target_drawing']='foreign';seal(p)
        self.assertEqual(m.resolve_device_role('I',c)['canonical_role'],'unknown')


if __name__=='__main__':unittest.main()
