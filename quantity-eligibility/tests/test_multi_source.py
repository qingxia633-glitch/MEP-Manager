"""Synthetic engineering reviews and direct execution boundary tests."""
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'design-net-quantity'))
from builder import build, replay_validate
import multi_source as multi
from resolver import resolve_eligibility


def approval_bytes(scope,route):
    bounded=dict(scope,native_identities=[e['identity'] for e in route['native_steps']],
                 component_ids=sorted({g['id'] for g in route['approved_recovered_components']}))
    return json.dumps(dict(approval_id='local-review',scope=bounded,source='synthetic sign-off')).encode()


def fixture():
    scope = dict(project_id='P', drawing_instance_id='sheet-file', report_sha256='a'*64,
                 dwg_sha256='b'*64, space='ModelSpace', drawing='example.dwg')
    identity = {k:v for k,v in scope.items() if k != 'drawing'}
    ids = [dict(identity, handle=h, parent_path=[]) for h in ('A','B','C')]
    pt = lambda x: [str(x),'0','0']
    ends = [['A', [], 'end'], ['B', [], 'start']]
    key = dict(project_id='P', drawing_instance_id='sheet-file', snapshot='a'*64,
               space='ModelSpace', endpoints=ends)
    provenance = dict(review_sha256='e'*64, assumption_id='pair-review', assumption_sha256='c'*64,
                      unit=dict(id='unit-review',sha256='d'*64,conversion_to_meter='0.001'),
                      manifest_sha256='f'*64,report_sha256='a'*64)
    gap = dict(kind='approved_recovered_gap',id='gap:'+multi.digest(key),scope=scope,
               parents=ids[:2],endpoints=ends,wcs_mm=[pt(1000),pt(1500)],length_mm='500',
               squared_length_mm2='250000',length_m='0.5',crossed_witness=ids[2],
               crossed_connection_allowed=False,eligibility='project_path_component_only',
               competing_continuation_status='excluded_in_reviewed_inventory',provenance=provenance)
    native = [dict(kind='geometry',identity=i,vertices_wcs_mm=[pt(start),pt(end)],
                   native_length_mm=str(end-start)) for i,start,end in zip(ids,[0,1500],[1000,3500])]
    route = dict(RoutePathComponentVersion=1,status='qualified',native_steps=native,
                 approved_recovered_components=[gap],unresolved_gaps=[])
    def event(i,kind,targets):
        return dict(id=i,kind=kind,targets=targets,status='approved',source='review:'+i,
                    allocation_basis='per_route_before_counts')
    drop = dict(event('drop','vertical',['physical','conduit','wire']),wcs_mm=[pt(0),['0','0','1000']])
    beam = dict(event('beam','beam',['physical','conduit','wire']),length_m='0')
    slack = dict(event('slack','reserve',['wire']),length_m='0.25')
    return dict(schema_version='0.4',scope=scope,route=route,route_sha256=multi.digest(route),
                approval=dict(id='local-review',sha256=hashlib.sha256(approval_bytes(scope,route)).hexdigest()),role='signal',
                installation=dict(status='approved',source='section:1',method='embedded'),
                material=dict(wire='W',conduit='T',group_count=2,conductor_count=3,
                              conductor_cross_section_mm2='1.5',issue_basis='conductor'),
                events=[drop,beam,slack])


class Composite(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.enterContext(patch.object(multi,'AUTHORITY_DIR',self.root))
        self.p=fixture()
        self.approved_bytes=approval_bytes(self.p['scope'],self.p['route'])

    def grant(self,p=None):
        p=p or self.p
        approvals=self.root/'approvals'
        approvals.mkdir(exist_ok=True)
        (approvals/(p['approval']['sha256']+'.json')).write_bytes(self.approved_bytes)
        record=dict(status='approved_for_design_net',scope=p['scope'],approval=p['approval'],
                    plan_sha256=multi.digest(p),role=p['role'],source='independent review 7')
        record['parent_gates']={}
        record['event_allocations']={
            event['id']:dict(physical_component_id=event['source'],source=event['source'],
                             basis='vertical_path' if event['kind']=='vertical' else 'net_additional_to_measured_path')
            for event in p['events']}
        record['reporting_policy']=dict(decimal_places=3,rounding_mode='half_even',source='synthetic policy')
        for edge in p['route']['native_steps']:
            ident=edge['identity']
            binding=dict(project_id=ident['project_id'],drawing_ref=p['scope']['drawing'],
                         parent_path=ident['parent_path'],scope_type='edge',edge_handle=ident['handle'])
            record['parent_gates'][multi.digest(ident)]=dict(
                project_specific_status='supported',semantic_gate_passed=True,design_net_quantity_eligible=True,
                approved_semantic_role=p['role'],edge_handle=ident['handle'],object_identity=binding,
                provenance=dict(context=binding),binding_targets=[dict(binding,binding_id='bind',review_status='approved',
                    semantic_role=p['role'],assertion='affirm',evidence_ids=['ev'])],
                accepted_evidence=[dict(object_identity=binding,status='supported',evidence_id='ev',binding_id='bind',
                    evidence_type='human_project_confirmation',evidence_strength='direct_object_binding',
                    semantic_role=p['role'],assertion='affirm',provenance='synthetic discipline review')])
        (self.root/(multi.digest(p)+'.json')).write_text(json.dumps(record),encoding='utf8')

    def test_independent_complete_and_replay(self):
        self.grant()
        self.assertTrue(resolve_eligibility(self.p)['quantity_formula_ready'])
        result=build(self.p,[])
        self.assertEqual(result['status'],'built')
        q=result['quantity']
        # 3 m native + .5 gap + 1 drop. Wire alone receives .25 per group.
        self.assertEqual(Decimal(q['computed_quantity']['exact_value']),Decimal('28.5'))
        self.assertEqual(Decimal(q['views']['grouped_wire']),Decimal('9.5'))
        self.assertIsNone(q['procurement_quantity'])
        self.assertEqual(replay_validate(self.p,q)['status'],'replay_matched')
        changed=copy.deepcopy(q);changed['nodes'][0]['source']='changed'
        self.assertEqual(replay_validate(self.p,changed)['status'],'replay_mismatch')

    def test_same_path_different_material_not_double_wire(self):
        self.grant(); wire=build(self.p,[])['quantity']
        self.p['material']['issue_basis']='grouped_wire';self.grant()
        self.assertEqual(build(self.p,[wire])['status'],'duplicate_detected')
        self.p['material']['issue_basis']='conduit';self.grant()
        self.assertEqual(Decimal(build(self.p,[wire])['quantity']['computed_quantity']['exact_value']),Decimal('4.5'))

    def test_untrusted_self_hash(self):
        # A complete, internally consistent receipt next to the submitted plan
        # still has no authority. Use a valid payload without unknown JSON keys.
        submitter=self.root/'submitted'
        submitter.mkdir()
        with patch.object(self,'root',submitter):
            self.grant()
            (submitter/'request.json').write_text(json.dumps(self.p))
        self.assertTrue((submitter/(multi.digest(self.p)+'.json')).is_file())
        result=build(json.loads((submitter/'request.json').read_bytes()),[])
        self.assertIn('independent_execution_grant_missing',result['blocking_reasons'])
        self.assertIsNone(result['quantity'])
        self.assertEqual(Decimal(result['audit']['views']['planar_m']),Decimal('3.5'))
        for view in ('physical','conduit','grouped_wire','conductor'):
            self.assertIsNone(result['audit']['views'][view])
        self.assertFalse(resolve_eligibility(self.p)['quantity_formula_ready'])

    def test_foreign_approval(self):
        for field in ('project_id','drawing_instance_id','report_sha256'):
            p=fixture();self.grant(p)
            grant=self.root/(multi.digest(p)+'.json')
            r=json.loads(grant.read_bytes());r['scope'][field]='foreign';grant.write_text(json.dumps(r))
            self.assertNotEqual(build(p,[])['status'],'built')

    def test_direct_builder_requires_each_gate(self):
        self.grant()
        path=self.root/(multi.digest(self.p)+'.json')
        r=json.loads(path.read_bytes())
        next(iter(r['parent_gates'].values()))['semantic_gate_passed']=False
        path.write_text(json.dumps(r))
        self.assertNotEqual(build(self.p,[])['status'],'built')

    def test_evidence_bundle_and_export(self):
        from evidence import load_evidence
        path=self.root/'bundle.json'
        path.write_text(json.dumps({'objects':[self.p],'sources':[]}))
        obj=load_evidence(path)['objects'][0]
        with self.assertRaises(ValueError):
            multi.export_plan(obj)
        self.grant()
        exported=multi.export_plan(obj)
        self.assertEqual(exported,self.p)
        self.assertIsNot(exported,self.p)

    def test_missing_and_zero(self):
        self.grant()
        self.assertEqual(build(self.p,[])['status'],'built')
        ev=self.p['events'][1];ev.update(status='pending',length_m=None);self.grant()
        r=build(self.p,[]);self.assertEqual(r['status'],'blocked')
        self.assertIsNone(r['quantity'])
        self.assertEqual(Decimal(r['audit']['views']['planar_m']),Decimal('3.5'))

    def test_repeated_reverse(self):
        route=self.p['route'];gap=copy.deepcopy(route['approved_recovered_components'][0])
        for key in ('parents','endpoints','wcs_mm'):gap[key].reverse()
        route['approved_recovered_components'].append(gap)
        route['native_steps'].reverse()
        self.p['route_sha256']=multi.digest(route);self.grant()
        q=build(self.p,[])['quantity']
        self.assertEqual(Decimal(q['views']['planar_m']),Decimal('3.5'))
        self.assertEqual(Decimal(q['computed_quantity']['exact_value']),Decimal('28.5'))

    def test_invalid_geometry_units_ownership_and_omissions(self):
        for mutation in (
            lambda p:p['route']['native_steps'][0]['identity'].update(parent_path=['x']),
            lambda p:p['route']['native_steps'][0].update(native_length_mm='111'),
            lambda p:p['route']['approved_recovered_components'][0]['provenance']['unit'].update(conversion_to_meter='1'),
            lambda p:p['events'].append(copy.deepcopy(p['events'][1])),
            lambda p:p['events'].pop(),
            lambda p:p['material'].update(group_count=True),
            lambda p:p['route'].update(unresolved_gaps=['unknown']),
        ):
            p=fixture();mutation(p);p['route_sha256']=multi.digest(p);self.grant(p)
            with self.subTest(mutation=mutation):
                self.assertNotEqual(build(p,[])['status'],'built')

    def test_exact_node_replay(self):
        self.grant();q=build(self.p,[])['quantity'];values={}
        for node in q['nodes']:
            v=Decimal(node['value'])
            args=[values[i] for i in node['inputs']]
            if node['op']=='sum': self.assertEqual(v,sum(args))
            if node['op']=='multiply': self.assertEqual(v,args[0]*args[1])
            if node['op']=='distance_mm':
                a,b=node['source']['wcs_mm']
                self.assertEqual(v,sum((Decimal(x)-Decimal(y))**2 for x,y in zip(a,b)).sqrt())
            self.assertNotIn(node['id'],values);values[node['id']]=v

    def test_rehash_modified_request_cannot_reuse_execution_grant(self):
        self.grant()
        self.p['material']['conductor_count']=4
        self.assertIn('independent_execution_grant_missing',build(self.p,[])['blocking_reasons'])

    def test_independent_approval_bytes_required(self):
        self.grant()
        next((self.root/'approvals').iterdir()).write_bytes(b'{}')
        self.assertIn('independent_approval_bytes_mismatch',build(self.p,[])['blocking_reasons'])

    def test_witness_cannot_become_native_parent(self):
        route=self.p['route']
        gap=route['approved_recovered_components'][0]
        gap['crossed_witness']=gap['parents'][0]
        self.p['route_sha256']=multi.digest(route);self.grant()
        self.assertEqual(build(self.p,[])['status'],'blocked')

    def test_material_adjustment_once_only(self):
        e=dict(self.p['events'][0],id='reverse-drop')
        e['wcs_mm']=e['wcs_mm'][::-1]
        self.p['events'].append(e);self.grant()
        self.assertIn('duplicate_vertical_allocation',build(self.p,[])['blocking_reasons'])

    def test_unconfirmed_adjustment_basis(self):
        self.p['events'][2]['allocation_basis']='unknown';self.grant()
        self.assertEqual(build(self.p,[])['status'],'blocked')

    def test_wire_only_pending_does_not_make_conduit_unknown(self):
        self.p['events'][-1].update(status='pending',length_m=None)
        self.p['material']['issue_basis']='conduit'
        self.grant()
        q=build(self.p,[])['quantity']
        self.assertEqual(Decimal(q['computed_quantity']['exact_value']),Decimal('4.5'))
        self.assertIsNone(q['views']['conductor'])

    def test_legacy_ownership_requires_same_project_reconciliation(self):
        self.grant()
        scope=dict(project_id='P',drawing_ref='file',edge_handle='F',parent_path=[],scope_type='edge')
        entry=dict(scope=scope,quantity_kind='conduit',approved_semantic_role='signal')
        self.assertEqual(build(self.p,[entry])['status'],'blocked')
        scope['project_id']='independent-project'
        self.assertEqual(build(self.p,[entry])['status'],'built')

    def test_resealed_registry_cannot_relabel_wire_as_conduit(self):
        self.grant()
        row=build(self.p,[])['quantity']
        row['material_family']='conduit'
        row.pop('content_hash')
        row['content_hash']=multi.digest(row)
        self.assertEqual(build(self.p,[row])['status'],'blocked')

    def test_three_native_parents(self):
        route=self.p['route']
        extension=copy.deepcopy(route['native_steps'][1])
        extension['identity']['handle']='D'
        extension['vertices_wcs_mm']=[['3500','0','0'],['4500','0','0']]
        extension['native_length_mm']='1000'
        route['native_steps'].append(extension)
        self.p['route_sha256']=multi.digest(route)
        self.grant()
        self.assertIn('approval_path_extent_mismatch',build(self.p,[])['blocking_reasons'])
        self.approved_bytes=approval_bytes(self.p['scope'],route)
        self.p['approval']['sha256']=hashlib.sha256(self.approved_bytes).hexdigest()
        self.grant()
        self.assertEqual(Decimal(build(self.p,[])['quantity']['views']['planar_m']),Decimal('4.5'))

    def test_visual_gap_cannot_substitute_for_review(self):
        route=self.p['route']
        route['observed_visual_gap']=route.pop('approved_recovered_components')
        self.p['route_sha256']=multi.digest(route)
        self.grant()
        self.assertEqual(build(self.p,[])['status'],'blocked')

    def test_existing_bounded_review_refers_to_outer_endpoints(self):
        gap=self.p['route']['approved_recovered_components'][0]
        scope=dict(self.p['scope'],parent_path=[],component_id=gap['id'],
                   bounded_start='A/start',bounded_end='B/end')
        for last,expected in [('B/end','built'),('C/end','blocked')]:
            scope['bounded_end']=last
            self.approved_bytes=json.dumps(dict(approval_id='local-review',scope=scope)).encode()
            self.p['approval']['sha256']=hashlib.sha256(self.approved_bytes).hexdigest()
            self.grant()
            self.assertEqual(build(self.p,[])['status'],expected)

    def test_registry_required_and_final_only_rounding(self):
        self.p['events'][2]['length_m']='0.123456789'
        self.grant()
        self.assertEqual(build(self.p)['status'],'blocked')
        q=build(self.p,[])['quantity']['computed_quantity']
        self.assertEqual(Decimal(q['exact_value']),Decimal('27.740740734'))
        self.assertEqual(q['reported_value'],'27.741')

    def test_authority_rejects_linked_metadata(self):
        import stat
        from types import SimpleNamespace
        self.grant()
        original = Path.lstat
        for target, attributes in [
            (self.root, {'st_file_attributes':stat.FILE_ATTRIBUTE_REPARSE_POINT}),
            (self.root/'approvals', {'st_mode':stat.S_IFLNK}),
            (self.root/(multi.digest(self.p)+'.json'), {'st_nlink':2}),
        ]:
            def metadata(path):
                actual = original(path)
                if path != target:
                    return actual
                fields = {k:getattr(actual,k) for k in dir(actual) if k.startswith('st_')}
                return SimpleNamespace(**(fields | attributes))
            with self.subTest(target=target), patch.object(Path,'lstat',metadata):
                self.assertIsNone(build(self.p,[])['quantity'])

    def test_partial_native_backtrack(self):
        route = self.p['route']
        sub = copy.deepcopy(route['native_steps'][1])
        sub['identity']['handle'] = 'D'
        sub.update(vertices_wcs_mm=[['3500','0','0'],['3000','0','0']],native_length_mm='500')
        route['native_steps'].append(sub)
        self.p['route_sha256'] = multi.digest(route)
        self.approved_bytes = approval_bytes(self.p['scope'],route)
        self.p['approval']['sha256'] = hashlib.sha256(self.approved_bytes).hexdigest()
        self.grant()
        self.assertIsNone(build(self.p,[])['quantity'])

    def test_partial_vertical_overlap(self):
        self.p['events'].append(dict(self.p['events'][0],id='upper-drop',
                                     wcs_mm=[['0','0','500'],['0','0','1500']]))
        self.grant()
        self.assertIsNone(build(self.p,[])['quantity'])

    def test_scalar_cannot_repeat_drop_under_an_alias(self):
        self.p['events'].append(dict(self.p['events'][2],id='second-label',kind='other',
                                     source=self.p['events'][0]['source'],length_m='1'))
        self.grant()
        self.assertIsNone(build(self.p,[])['quantity'])

    def test_independently_reviewed_installations_can_share_wire_route(self):
        def reviewed_item(item):
            self.p['material']['item_id']=item
            self.grant()
            path=self.root/(multi.digest(self.p)+'.json')
            grant=json.loads(path.read_bytes())
            grant['material_item_id']=item
            path.write_text(json.dumps(grant))
        reviewed_item('installation-one')
        first=build(self.p,[])['quantity']
        self.p['material']['wire']='W2'
        reviewed_item('installation-two')
        second=build(self.p,[first])
        self.assertEqual(second['status'],'built')
        self.assertNotEqual(first['quantity_id'],second['quantity']['quantity_id'])

    def test_single_source_consumer_rechecks_composite_registry_row(self):
        self.grant()
        previous=build(self.p,[])['quantity']
        previous['scope']=dict(previous['scope'],project_id='foreign')
        previous.pop('content_hash')
        previous['content_hash']=multi.digest(previous)
        with patch('builder._execute',return_value={'status':'built','quantity':{}}):
            self.assertNotEqual(build({'binding':{'project_id':'P'}},[previous])['status'],'built')

    def test_registry_overlap_with_distinct_handles_and_disjoint_installation(self):
        self.grant()
        issued=build(self.p,[])['quantity']
        for offset,expected in [(250,'duplicate_detected'),(10000,'built')]:
            p=fixture()
            route=p['route']
            gap=route['approved_recovered_components'][0]
            for edge in route['native_steps']:
                edge['identity']['handle']+='1'
                for xyz in edge['vertices_wcs_mm']:
                    xyz[0]=str(int(xyz[0])+offset)
            for endpoint,xyz in zip(gap['endpoints'],gap['wcs_mm']):
                endpoint[0]+='1'
                xyz[0]=str(int(xyz[0])+offset)
            key=dict(project_id='P',drawing_instance_id='sheet-file',snapshot='a'*64,
                     space='ModelSpace',endpoints=gap['endpoints'])
            gap['id']='gap:'+multi.digest(key)
            for xyz in p['events'][0]['wcs_mm']:
                xyz[0]=str(int(xyz[0])+offset)
            for e in p['events']:
                e['source']+='-second-installation'
            p['route_sha256']=multi.digest(route)
            self.approved_bytes=approval_bytes(p['scope'],route)
            p['approval']['sha256']=hashlib.sha256(self.approved_bytes).hexdigest()
            self.grant(p)
            self.assertEqual(build(p,[issued])['status'],expected)

    def test_unreconciled_scalar_extent_stays_blocked(self):
        self.grant()
        path=self.root/(multi.digest(self.p)+'.json')
        receipt=json.loads(path.read_bytes())
        del receipt['event_allocations']['slack']
        path.write_text(json.dumps(receipt))
        self.assertEqual(build(self.p,[])['status'],'blocked')

    def test_duplicate_native_identity_rejected_in_either_direction(self):
        for reverse in (False,True):
            p=fixture()
            edge=copy.deepcopy(p['route']['native_steps'][0])
            if reverse:
                edge['vertices_wcs_mm'].reverse()
            p['route']['native_steps'].append(edge)
            p['route_sha256']=multi.digest(p['route'])
            self.grant(p)
            self.assertIsNone(build(p,[])['quantity'])
