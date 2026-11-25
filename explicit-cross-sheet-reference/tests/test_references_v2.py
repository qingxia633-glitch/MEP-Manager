"""Synthetic typed-target contracts, not BX or identity authority evidence."""
import copy
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'explicit-cross-sheet-reference'),str(ROOT/'project-drawing-registry')]
from registry import content_hash
from registry_v2 import migrate_v1,legacy_view
from references import scan as scan_v1
from references_v2 import scan,resolve_reference,decide_resolution


def fixture(text='详见 EW-0074',count=1,alias_role='drawing_number_candidate',drawing_alias=False):
    drawings=[]
    for name,h in [('source.dwg','a'),('target.dwg','b')]:
        b=dict(project_id='P',drawing_ref=name,report_sha256=h*64,source_dwg_sha256=None)
        drawings.append(dict(b,instance_id=content_hash(b),report_identity={'drawing':name},
            provenance=[{'source_type':'report_bytes','sha256':h*64}],labels=[],report_version='2.8-field-graph-evidence-v1',
            logical_identity_status='unresolved',sheet_identity_status='unresolved'))
    d=drawings[1];iid=d['instance_id'];lp=[{'source_type':'layout_report_bytes','sha256':'c'*64}]
    layouts=[];cs=[]
    for i in range(count):
        name='Layout'+str(i);native={'handle':str(i+1),'block_handle':str(i+10)}
        lid=content_hash(['P',iid,name,native['handle'],native['block_handle']])
        layouts.append(dict(project_id='P',drawing_instance_id=iid,layout_name=name,layout_source_identity=native,
            layout_identity=lid,space_type='PaperSpace',layout_order=i,layout_acquisition_status='read',entity_count=1,provenance=lp))
        cs.append(dict(kind=alias_role,identifier_role=alias_role.removesuffix('_candidate'),value='EW-0074',raw_value='EW-0074',
            layout_identity=lid,status='candidate',evidence_strength='synthetic_tag',tag='TAG',provenance=lp,
            carrier_identity=dict(project_id='P',drawing_instance_id=iid,drawing_ref='target.dwg',snapshot_id='c'*64,
                layout_identity=lid,handle='F'+str(i),parent_path=['B'+str(i)])))
    if count:d['drawing_sheet_identity_evidence']=dict(DrawingSheetIdentityEvidenceVersion=1,project_id='P',drawing_instance_id=iid,layouts=layouts,candidates=cs,provenance=lp)
    aliases=[]
    if drawing_alias:aliases=[dict(kind='drawing_number_candidate',value='EW-0074',instance_id=iid,status='partial',provenance=d['provenance'],source_type='synthetic_text')]
    old=dict(registry_version=1,project_id='P',drawing_instances=drawings,aliases=aliases)
    c=dict(project_id='P',drawing_ref='source.dwg',snapshot_id='a'*64,report_integrity='verified',report_identity={'drawing':'source.dwg'},
        annotations=[dict(handle='A',type='TEXT',project_id='P',source_drawing='source.dwg',parent_path=[],decoded_text=text,
            raw_serialized_text=text,text_decode_status='read',provenance=[{'sha256':'a'*64}])],leaders=[],field_evidence=[],table_evidence=[])
    return migrate_v1(old),c


class ReferencesV2Tests(unittest.TestCase):
    def result(self,**kwargs):
        r,c=fixture(**kwargs);return scan(r,[c])

    def test_v2_layout_candidate(self):
        o=self.result();x=o['resolutions'][0];t=x['target_candidates'][0]
        self.assertEqual(o['version'],2);self.assertEqual(x['resolution_status'],'candidate')
        self.assertEqual(t['target_kind'],'layout_instance');self.assertEqual(t['target_id'],t['layout_instance_id'])
        self.assertNotEqual(t['target_id'],t['drawing_instance_id']);self.assertEqual(t['sheet_identity_status'],'unresolved')

    def test_v1_rejected(self):
        r,c=fixture()
        with self.assertRaises(ValueError):scan(legacy_view(r),[c])

    def test_source_id_v1_v2(self):
        r,c=fixture();self.assertEqual(scan_v1(legacy_view(r),[c])['source_references'][0]['reference_id'],scan(r,[c])['source_references'][0]['reference_id'])

    def test_source_id_target_change(self):
        a=self.result(count=1);b=self.result(count=2)
        self.assertEqual(a['source_references'],b['source_references'])

    def test_role_filter_not_title_fallback(self):
        self.assertEqual(self.result(alias_role='drawing_title_candidate')['resolutions'][0]['resolution_status'],'unresolved')

    def test_kind_filter(self):
        r,c=fixture();src=scan(r,[c])['source_references'][0]
        self.assertEqual(resolve_reference(r,src,allowed_target_kinds=['drawing_instance'])['resolution_status'],'unresolved')
        self.assertEqual(resolve_reference(r,src,allowed_target_kinds=['layout_instance'])['resolution_status'],'candidate')

    def test_invalid_kind(self):
        r,c=fixture();src=scan(r,[c])['source_references'][0]
        with self.assertRaises(ValueError):resolve_reference(r,src,allowed_target_kinds=['sheet_identity_candidate'])

    def test_drawing_plus_layout_ambiguous(self):
        x=self.result(drawing_alias=True)['resolutions'][0]
        self.assertEqual(x['resolution_status'],'ambiguous');self.assertEqual(len(x['target_candidates']),2)

    def test_two_layouts_no_first(self):
        x=self.result(count=2)['resolutions'][0]
        self.assertEqual(x['resolution_status'],'ambiguous');self.assertEqual(len(x['target_candidates']),2)

    def test_zero(self):self.assertEqual(self.result(count=0)['summary']['unresolved'],1)

    def test_cue_no_lookup(self):
        from unittest.mock import patch
        r,c=fixture(text='详见上级配电箱')
        with patch('references_v2.registry_lookup',side_effect=AssertionError('must not lookup')):
            x=scan(r,[c])['resolutions'][0]
        self.assertEqual(x['lookup_status'],'not_attempted');self.assertEqual(x['resolution_status'],'unresolved')

    def test_same_S_no_link(self):self.assertEqual(self.result(text='S')['source_references'],[])
    def test_same_equipment_no_link(self):self.assertEqual(self.result(text='设备 M2')['source_references'],[])

    def test_v1_unchanged(self):
        r,c=fixture();before=scan_v1(legacy_view(r),[c]);scan(r,[c]);self.assertEqual(before,scan_v1(legacy_view(r),[c]))

    def test_order(self):
        r,c=fixture(count=2);a=scan(r,[c]);r['layout_instances'].reverse()
        # Registry is canonical and rejects modified order rather than trusting a cached index.
        with self.assertRaises(ValueError):scan(r,[c])
        self.assertEqual(a,self.result(count=2))

    def test_source_conflict(self):
        r,c=fixture();a=copy.deepcopy(c['annotations'][0]);a.update(decoded_text='详见 EC-04',raw_serialized_text='详见 EC-04');c['annotations'].append(a)
        self.assertTrue(all(x['resolution_status']=='conflicting' for x in scan(r,[c])['resolutions']))

    def test_target_conflict(self):
        r,c=fixture();old=legacy_view(r);e=old['drawing_instances'][1]['drawing_sheet_identity_evidence'];a=copy.deepcopy(e['candidates'][0]);a.update(value='EW-0075',raw_value='EW-0075');e['candidates'].append(a)
        self.assertEqual(scan(migrate_v1(old),[c])['resolutions'][0]['resolution_status'],'conflicting')

    def test_partial_source_not_supported(self):
        r,c=fixture();src=scan(r,[c])['source_references'][0];src['reference_extraction_status']='partial'
        self.assertEqual(resolve_reference(r,src)['resolution_status'],'unresolved')

    def supported_fixture(self):
        t=copy.deepcopy(self.result()['resolutions'][0]['target_candidates'][0])
        t['logical_identity_status']='supported'
        t['sheet_identity_status']='supported'
        t['identity_support']={'status':'supported','independent':True,
            'target_identity':{k:t[k] for k in ('project_id','target_kind','target_id','drawing_instance_id','layout_instance_id')},
            'approved_alias_role':'drawing_number_candidate','approved_alias_value':'EW-0074',
            'provenance':[{'source_id':'synthetic-authority','sha256':'d'*64}]}
        return t

    def test_synthetic_supported_policy(self):
        self.assertEqual(decide_resolution('supported','unique_registry_candidate',[self.supported_fixture()],False)[0],'supported')

    def test_supported_status_alone_not_authority(self):
        t=self.supported_fixture();del t['identity_support']
        self.assertEqual(decide_resolution('supported','unique_registry_candidate',[t],False)[0],'candidate')

    def test_foreign_support_not_approved(self):
        t=self.supported_fixture();t['identity_support']['target_identity']['project_id']='foreign'
        self.assertEqual(decide_resolution('supported','unique_registry_candidate',[t],False)[0],'candidate')

    def test_weak_role_not_supported(self):
        self.assertEqual(decide_resolution('supported','unique_registry_candidate',[self.supported_fixture()],True)[0],'candidate')

    def test_partial_cannot_be_supported_even_with_authority(self):
        self.assertEqual(decide_resolution('partial','unique_registry_candidate',[self.supported_fixture()],False)[0],'unresolved')

    def test_no_approval_from_forged_registry(self):
        r,c=fixture();r['layout_instances'][0]['logical_layout_identity_status']='supported'
        with self.assertRaises(ValueError):scan(r,[c])

    def test_source_target_separated(self):
        o=self.result();src=o['source_references'][0]
        self.assertFalse({'target_candidate_instance_ids','resolution_status','registry_version','lookup_roles'} & set(src))
        self.assertEqual(o['resolutions'][0]['reference_id'],src['reference_id'])

    def test_drawing_target_not_attached_to_layout(self):
        x=self.result(count=0,drawing_alias=True)['resolutions'][0]['target_candidates'][0]
        self.assertEqual(x['target_kind'],'drawing_instance');self.assertIsNone(x['layout_instance_id'])

    def test_empty_kind_no_broadening(self):
        r,c=fixture();src=scan(r,[c])['source_references'][0]
        self.assertEqual(resolve_reference(r,src,allowed_target_kinds=[])['resolution_status'],'unresolved')

    def test_unique_lookup_cannot_hide_target_conflict(self):
        t=self.supported_fixture();t['logical_identity_status']='conflicting'
        self.assertEqual(decide_resolution('supported','unique_registry_candidate',[t],False)[0],'conflicting')

    def test_unknown_target_authority_hash(self):
        t=self.supported_fixture();t['identity_support']['provenance'][0]['sha256']='unknown'
        self.assertEqual(decide_resolution('supported','unique_registry_candidate',[t],False)[0],'candidate')

    def test_unknown_lookup_cannot_be_supported(self):
        self.assertEqual(decide_resolution('supported','unknown',[self.supported_fixture()],False)[0],'unresolved')

    def test_layout_unresolved_sheet_stays_candidate(self):
        t=self.supported_fixture();t['sheet_identity_status']='unresolved'
        self.assertEqual(decide_resolution('supported','unique_registry_candidate',[t],False)[0],'candidate')

if __name__=='__main__':unittest.main()
