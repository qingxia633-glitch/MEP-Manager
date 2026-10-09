import copy
import tempfile
import unittest
from pathlib import Path
from test_findings import item, plan, seal, load


class Boundaries(unittest.TestCase):
    def gate(self, path):
        identity=dict(project_id='P',drawing_ref='D',parent_path=path,edge_handle='E',scope_type='edge')
        evidence=dict(evidence_id='e',evidence_type='human_project_confirmation',evidence_strength='direct_object_binding',status='supported',semantic_role='bus',assertion='affirm',binding_id='b',provenance=['review'])
        binding=dict(identity,binding_id='b',review_status='reviewed',evidence_ids=['e'],provenance=['review'])
        return identity, evidence, binding

    def test_complete_identity_positive_and_preserved(self):
        i,e,b=self.gate(['I1'])
        r=load('project-evidence-gate').evaluate_semantics(dict(i,candidate_role='bus'),dict(project_id='P',drawing_ref='D',evidence=[e],bindings=[b]),i)
        self.assertTrue(r['semantic_gate_passed'])
        self.assertEqual(r['object_identity']['parent_path'],['I1'])
        self.assertEqual(r['accepted_evidence'][0]['object_identity'],r['object_identity'])

    def test_missing_path_is_not_modelspace(self):
        i,e,b=self.gate([]);del i['parent_path']
        r=load('project-evidence-gate').evaluate_semantics(i,dict(project_id='P',drawing_ref='D',evidence=[e],bindings=[b]),i)
        self.assertFalse(r['semantic_gate_passed'])

    def test_missing_scope_identity_is_not_assumed(self):
        i,e,b=self.gate([])
        del i['scope_type']
        r=load('project-evidence-gate').evaluate_semantics(i,dict(project_id='P',drawing_ref='D',evidence=[e],bindings=[b]),i)
        self.assertFalse(r['semantic_gate_passed'])

    def test_gate_identity_cannot_cross_eligibility(self):
        m=load('quantity-eligibility');x=item()
        self.assertEqual(m.resolve_eligibility(x)['quantity_eligibility_status'],'eligible')
        x['semantic_gate']['object_identity']=dict(x['semantic_gate']['object_identity'],parent_path=['I1'])
        self.assertFalse(m.resolve_eligibility(x)['design_net_quantity_generation_allowed'])

    def test_gate_provenance_identity_cannot_disagree(self):
        x=item();x['semantic_gate']['provenance']['context']=dict(x['measurement_scope']['binding'],parent_path=['foreign'])
        self.assertFalse(load('quantity-eligibility').resolve_eligibility(x)['design_net_quantity_generation_allowed'])

    def test_physical_conversion_and_wrong_contract(self):
        m=load('quantity-eligibility');x=item()
        x['geometry'].update(source_unit='mm',base_length='10000')
        x['geometry']['conversion'].update(from_unit='mm',factor='0.001',converted_length='10')
        self.assertEqual(m.resolve_eligibility(x)['quantity_eligibility_status'],'eligible')
        x['geometry']['conversion'].update(factor='1',converted_length='10000')
        x['base_path']['value']='10000'
        r=m.resolve_eligibility(x)
        self.assertIn('unit_conversion_contract_invalid',r['blocking_reasons'])

    def test_versioned_physical_and_reviewed_cad_contracts(self):
        load('quantity-eligibility')
        from unit_contract import conversion_contract
        binding=item()['measurement_scope']['binding']
        c=conversion_contract(dict(from_unit='m',to_unit='mm',factor='1000'),binding)
        self.assertEqual(c['contract_id'],'engineering-length-units/1')
        with self.assertRaises(ValueError):
            conversion_contract(dict(from_unit='m',to_unit='mm',factor='1'),binding)
        cad=seal(dict(contract_id='reviewed-cad-scale',version='1',kind='cad_geometry_scale',
            status='approved',binding=copy.deepcopy(binding),source_unit='drawing_unit',target_unit='m',
            factor='0.001',provenance=['independent scale review']))
        conv=dict(from_unit='drawing_unit',to_unit='m',factor='0.001',conversion_kind='cad_geometry_scale',reviewed_scale_contract=cad)
        self.assertEqual(conversion_contract(conv,binding)['contract_id'],'reviewed-cad-scale')
        self.assertRaises(ValueError,conversion_contract,conv,dict(binding,parent_path=['other']))

    def test_cad_scale_without_reviewed_contract_blocked(self):
        x=item();x['geometry']['conversion']['conversion_kind']='cad_geometry_scale'
        self.assertFalse(load('quantity-eligibility').resolve_eligibility(x)['design_net_quantity_generation_allowed'])

    def test_required_height_all_invalid_states(self):
        m=load('design-net-quantity','builder.py')
        self.assertEqual(m.build(plan(),[])['status'],'built')
        for field in ('geometry_basis','height_evidence'):
            for state in ('unknown','unresolved','conflicting','partial','not_applicable'):
                with self.subTest(field=field,state=state):
                    p=plan();p['base_path']['mode']='approved_3d';p[field]['status']=state
                    self.assertNotEqual(m.build(seal(p),[])['status'],'built')
            p=plan();p[field]['provenance']=[]
            self.assertNotEqual(m.build(seal(p),[])['status'],'built')
            p=plan();p[field]['binding']['parent_path']=['foreign']
            self.assertNotEqual(m.build(seal(p),[])['status'],'built')

    def test_native_replay_full_evidence_contract(self):
        m=load('design-net-quantity','builder.py');p=plan();q=m.build(p,[])['quantity']
        self.assertEqual(m.replay_validate(p,q)['status'],'replay_matched')
        for field in ('specification','geometry_basis','height_evidence','deduplication'):
            with self.subTest(field=field):
                changed=plan();changed[field]['provenance']=[{'source_id':'changed-review'}]
                r=m.replay_validate(seal(changed),q)
                self.assertTrue(r['numeric_match']);self.assertFalse(r['evidence_contract_match'])
        changed=plan();changed['owned_adjustments'][0]['owner']['parent_path']=['foreign']
        self.assertNotEqual(m.replay_validate(seal(changed),q)['status'],'replay_matched')
        changed=plan();changed['geometry_basis']['path']='reviewed-geometric-evidence-identity'
        self.assertNotEqual(m.replay_validate(seal(changed),q)['status'],'replay_matched')

    def test_replay_source_assumption_and_correction_changes(self):
        m=load('design-net-quantity','builder.py');p=plan();q=m.build(p,[])['quantity']
        changed=plan();changed['source_evidence_hashes']['synthetic-review']['sha256']='d'*64
        r=m.replay_validate(seal(changed),q)
        self.assertTrue(r['numeric_match']);self.assertFalse(r['evidence_contract_match'])
        changed=plan();changed['assumptions']=[dict(id='a',status='approved',value='declared',
            scope={'binding':copy.deepcopy(changed['binding'])},provenance=['approved-assumption'])]
        r=m.replay_validate(seal(changed),q)
        self.assertTrue(r['numeric_match']);self.assertFalse(r['evidence_contract_match'])
        changed=plan();correction=seal(dict(correction_id='c',status='approved',target_object_ids=[changed['object_id']],
            edge_handle=changed['binding']['edge_handle'],corrected_value=changed['binding']['drawing_ref'],
            historical_value='old-reference',provenance=['review']))
        changed['corrections_applied']={'evidence':correction,'changed_paths':[]}
        r=m.replay_validate(seal(changed),q)
        self.assertTrue(r['numeric_match']);self.assertFalse(r['evidence_contract_match'])

    def test_reviewed_path_is_not_a_machine_locator(self):
        m=load('design-net-quantity','builder.py');p=plan()
        p['specification']['provenance']=[{'path':'instance/I1','sha256':'a'*64}]
        q=m.build(seal(p),[])['quantity']
        p['specification']['provenance'][0]['path']='instance/I2'
        r=m.replay_validate(seal(p),q)
        self.assertTrue(r['numeric_match'])
        self.assertNotEqual(r['status'],'replay_matched')

    def test_adapter_repeated_attribute_handle_keeps_owners_separate(self):
        m=load('project-evidence-discovery','discovery.py')
        from annotations import load_report
        raw='DWG="sample.dwg"\n'
        for owner in ('I1','I2'):
            raw+='EntityHandle="'+owner+'"\nDXF_Type="INSERT"\nAttributeTag="A"\nAttributeText_RAW="S"\nAttribute_DXF=((5 . "T") (10 0 0 0))\n'
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'r.txt';path.write_text(raw,encoding='utf-8')
            c=load_report(path,project_id='P');r=m.discover(c)
        self.assertEqual({b['target_id'] for b in r['bindings']},{'I1','I2'})
        for a in c['annotations']:
            self.assertEqual(a['owner_parent_path'],[])
            self.assertEqual(a['attribute_path'],[a['parent_handle'],'T'])
            self.assertEqual(a['owner_insert_identity']['project_id'],'P')
            self.assertEqual(a['owner_insert_identity']['handle'],a['parent_handle'])

if __name__=='__main__':unittest.main()
