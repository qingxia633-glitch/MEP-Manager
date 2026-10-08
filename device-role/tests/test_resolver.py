import copy
import sys
import unittest
import tempfile
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from resolver import RoleContext, resolve_device_role

ROOT=Path(__file__).resolve().parents[2]
SNAP=ROOT/'local_test_data/fire-alarm-full-snapshot-20260923/MEP-full-entity-report.txt'
PROBES=[ROOT/'local_test_data'/p/'block-definition-probe.txt' for p in [
    'module-13304-probe-20261005','block-definition-probe.txt',
    'valve-132F7-probe-20261005','fire-alarm-smoke-block-Equip00002649-probe-20260926']]

def attr(value,tag='A',handle='A1'):
    return dict(tag=tag,raw_value=value,handle=handle)

def inst(handle='I',attrs=None,block='B'):
    return dict(handle=handle,block_name=block,effective_block_name=block,attributes=attrs or [])

def ctx(attrs=None,defaults=None):
    return RoleContext('project.dwg',{'I':inst(attrs=attrs)}, {'B':dict(defaults=defaults or [],children=[])})


class RealFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.context=RoleContext.from_reports(SNAP,PROBES)

    def test_real_roles(self):
        for h,role in [('13304','input_output_module'),('134D9','input_output_module'),
                       ('13017','module_box'),('132F7','fire_damper'),
                       ('135D6','smoke_exhaust_outlet'),('12D65','smoke_detector')]:
            with self.subTest(handle=h):
                r=resolve_device_role(h,self.context)
                self.assertEqual((r['canonical_role'],r['role_status']),(role,'supported'))
                if h=='13017':self.assertEqual(r['selected_evidence'][0]['source_definition_path'],['13017','10B16'])
                if h=='132F7':
                    self.assertEqual(r['properties']['action_temperature'],280)
                    self.assertTrue(any('70' in e['raw_value'] for e in r['overridden_defaults']))
                if h in ('13304','134D9'):self.assertEqual(r['display_code'],'I')
                print(h,role,r['role_status'])

    def test_real_inherited_smoke(self):
        r=resolve_device_role('12EA0',self.context)
        self.assertEqual((r['canonical_role'],r['role_status']),('smoke_detector','inherited'))
        self.assertEqual(r['selected_evidence'][0]['evidence_type'],'block_definition_default')

    def test_real_code_only_history(self):
        c=RoleContext.from_reports(SNAP,[])
        r=resolve_device_role('13017',c)
        self.assertEqual(r['canonical_role'],'unknown')
        self.assertIn(r['role_status'],['unresolved','partial'])

    def test_contradicting_definition_reports(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'conflicting.txt'
            p.write_text(PROBES[0].read_text(encoding='utf-8-sig').replace('单输入单输出模块','感温探测器'),encoding='utf-8')
            c=RoleContext.from_reports(SNAP,[PROBES[0],p])
            c.instances['13304']['attributes']=[]
            self.assertEqual(resolve_device_role('13304',c)['role_status'],'conflicting')


class Priorities(unittest.TestCase):
    def test_override_and_raw(self):
        raw='280℃动作的常开防火阀'
        r=resolve_device_role('I',ctx([attr(raw)],[attr('70℃动作的常开防火阀')]))
        self.assertEqual(r['raw_role_text'],raw)
        self.assertEqual(r['properties'],dict(action_temperature=280,temperature_unit='℃',normal_state='normally_open'))
        self.assertEqual(r['role_status'],'supported')
        self.assertFalse(r['conflicting_evidence'])
        self.assertEqual(len(r['overridden_defaults']),1)

    def test_child_priority_and_path(self):
        c=ctx([attr('M2')],[attr('感烟探测器')])
        c.definitions['B']['children']=[inst('CH',[attr('模块箱','A','CH-A')],'C')]
        r=resolve_device_role('I',c)
        self.assertEqual(r['canonical_role'],'module_box')
        self.assertEqual(r['selected_evidence'][0]['priority'],2)
        self.assertEqual(r['selected_evidence'][0]['source_definition_path'],['I','CH'])

    def test_conflicting_equal_priority(self):
        for values in [('感烟探测器','感温探测器'),('70℃动作的常开防火阀','280℃动作的常开防火阀')]:
            r=resolve_device_role('I',ctx([attr(values[0]),attr(values[1],handle='A2')]))
            self.assertEqual(r['role_status'],'conflicting')
            self.assertTrue(r['conflicting_evidence'])
            self.assertEqual(r['canonical_role'],'unknown')

    def test_normalization_and_unknown(self):
        for text,role in [('输入出模块','input_output_module'),('单输入模块','input_module'),
                          ('点型感温探测器','heat_detector'),('手动报警按钮','manual_call_point'),
                          ('排烟口','smoke_exhaust_outlet'),('风机','unknown')]:
            r=resolve_device_role('I',ctx([attr(text)]))
            self.assertEqual(r['canonical_role'],role)
            self.assertEqual(r['raw_role_text'],text)
        r=resolve_device_role('I',ctx([attr('风机')],[attr('感烟探测器')]))
        self.assertEqual(r['canonical_role'],'unknown')

    def test_same_definition_inheritance(self):
        c=ctx()
        c.instances.update({h:inst(h,[attr('感烟探测器')]) for h in ['D1','D2']})
        r=resolve_device_role('I',c)
        self.assertEqual((r['role_status'],r['canonical_role']),('inherited','smoke_detector'))
        c.instances['D2']['attributes']=[attr('感温探测器')]
        self.assertEqual(resolve_device_role('I',c)['role_status'],'conflicting')

    def test_legend_source_binding_and_code_only(self):
        c=ctx([attr('M2')]); base=dict(source_drawing='EC-4#-P+TBD_t8_t3.dwg',source_handle='2399E',
            raw_value='模块箱',display_code='M2',target_drawing='project.dwg',target_block_name='B',
            binding_verified=True,binding_evidence_refs=['reviewed equivalence'],evidence_type='project_legend')
        import hashlib,json
        c.legend_policy=dict(policy_id='test-project-policy',version='1',status='approved',
            target_drawing='project.dwg',allowed_sources=[base['source_drawing']],provenance=['test reviewed policy'])
        c.legend_policy['content_hash']=hashlib.sha256(json.dumps(c.legend_policy,sort_keys=True,
            ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
        for change in [dict(source_drawing='other.dwg'),dict(target_block_name='OTHER'),dict(binding_verified=False)]:
            c.legends=[dict(base,**change)]
            self.assertEqual(resolve_device_role('I',c)['canonical_role'],'unknown')
        c.legends=[base]
        r=resolve_device_role('I',c)
        self.assertEqual((r['canonical_role'],r['role_status']),('module_box','partial'))
        c.instances['I']['attributes']=[attr('排烟口')]
        self.assertEqual(resolve_device_role('I',c)['canonical_role'],'smoke_exhaust_outlet')

    def test_forbidden_inputs_do_not_classify(self):
        c=ctx([attr('M2')]);c.instances['I'].update(nearby_text='模块箱',layer='EQUIP-消防',connected_device='smoke_detector',insertion=[1,2,3])
        self.assertEqual(resolve_device_role('I',c)['canonical_role'],'unknown')
        c.instances['D']=inst('D',[attr('模块箱')],'OTHER')
        self.assertEqual(resolve_device_role('I',c)['canonical_role'],'unknown')

    def test_no_mutation_and_mirror_independence(self):
        c=ctx([attr('单输入单输出模块')]);before=copy.deepcopy(c.instances)
        a=resolve_device_role('I',c);self.assertEqual(c.instances,before)
        c.instances['I']['scale']=[-1,1,1]
        self.assertEqual(resolve_device_role('I',c)['canonical_role'],a['canonical_role'])

    def test_arbitrary_attribute_not_role(self):
        r=resolve_device_role('I',ctx([attr('感烟探测器','REMARK')]))
        self.assertEqual(r['canonical_role'],'unknown')

    def test_unknown_donor_and_single_donor(self):
        c=ctx();c.instances['D']=inst('D',[attr('感烟探测器')])
        self.assertEqual(resolve_device_role('I',c)['role_status'],'partial')
        c.instances['D2']=inst('D2',[attr('风机')])
        self.assertEqual(resolve_device_role('I',c)['canonical_role'],'unknown')

    def test_partial_definition_and_missing_device(self):
        c=ctx(defaults=[attr('感烟探测器')]);c.definitions['B']['complete']=False
        self.assertEqual(resolve_device_role('I',c)['role_status'],'partial')
        self.assertEqual(resolve_device_role('missing',c)['role_status'],'unresolved')

    def test_direct_children_conflict(self):
        c=ctx([attr('M2')]);c.definitions['B']['children']=[inst('C1',[attr('模块箱')]),inst('C2',[attr('排烟口')])]
        self.assertEqual(resolve_device_role('I',c)['role_status'],'conflicting')

    def test_no_definition_alias_inheritance(self):
        c=ctx();c.instances.update({h:inst(h,[attr('感烟探测器')],'OTHER') for h in ['D1','D2']})
        for x in c.instances.values():x['effective_block_name']='same_display_alias'
        self.assertEqual(resolve_device_role('I',c)['role_status'],'unresolved')


if __name__=='__main__':unittest.main(verbosity=2)
