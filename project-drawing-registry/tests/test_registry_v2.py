"""Synthetic contract tests; not approved project sheet identities."""
import copy
import sys
import unittest
import json
import hashlib
import tempfile
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'project-drawing-registry'))
from registry import content_hash
from registry_v2 import migrate_v1, lookup, legacy_view


def fixture(values=('D-01', 'D-02'), roles=None, model=False):
    basis = dict(project_id='P', drawing_ref='source.dwg', source_dwg_sha256='a'*64, report_sha256='b'*64)
    iid = content_hash(basis)
    prov = [dict(source_type='report_bytes', sha256='b'*64)]
    lp = [dict(source_type='layout_report_bytes', sha256='c'*64, report_version='2.9-layout-identity-v1')]
    d = dict(basis, instance_id=iid, report_version='2.8-field-graph-evidence-v1',
             report_identity={'drawing':'source.dwg'}, provenance=prov, labels=[],
             logical_identity_status='unresolved', sheet_identity_status='unresolved')
    layouts=[];candidates=[]
    for n,value in enumerate(values):
        name='Model' if model else 'Layout'+str(n)
        native={'handle':str(n+1), 'block_handle':str(n+10)}
        lid=content_hash(['P',iid,name,native['handle'],native['block_handle']])
        layouts.append(dict(project_id='P',drawing_instance_id=iid,layout_name=name,
            layout_identity=lid,layout_source_identity=native,space_type='ModelSpace' if model else 'PaperSpace',
            layout_order=n,layout_acquisition_status='read',entity_count=1,provenance=lp))
        if value is not None:
            kind=roles[n] if roles else 'drawing_number_candidate'
            candidates.append(dict(kind=kind,identifier_role='unresolved' if kind.startswith('unresolved') else kind.removesuffix('_candidate'),
                value=value,raw_value=value,layout_identity=lid,status='candidate',tag='TAG',
                carrier_identity=dict(project_id='P',drawing_instance_id=iid,drawing_ref='source.dwg',
                    snapshot_id='c'*64,layout_identity=lid,handle='A'+str(n),parent_path=['B'+str(n)]),
                evidence_strength='layout_title_block_attribute_candidate',provenance=lp))
    d['drawing_sheet_identity_evidence']=dict(DrawingSheetIdentityEvidenceVersion=1,project_id='P',
        drawing_instance_id=iid,layouts=layouts,candidates=candidates,provenance=lp)
    return dict(registry_version=1,project_id='P',drawing_instances=[d],aliases=[],lookup_index={},summary={})


class RegistryV2Tests(unittest.TestCase):
    def test_v1_preserved(self):
        old=fixture();before=copy.deepcopy(old);v=migrate_v1(old)
        self.assertEqual(old,before);self.assertEqual(legacy_view(v),old)
        self.assertEqual(v['registry_version'],2)

    def test_missing_not_empty(self):
        old=fixture();del old['drawing_instances'][0]['drawing_sheet_identity_evidence']
        v=migrate_v1(old)
        self.assertEqual(v['drawing_layout_coverage'][0]['status'],'not_supplied')
        self.assertEqual(v['summary']['drawing_without_layout_evidence_count'],1)

    def test_one_parent_two_children(self):
        v=migrate_v1(fixture());self.assertEqual(len(v['drawing_instances']),1);self.assertEqual(len(v['layout_instances']),2)

    def test_model_not_sheet(self):
        v=migrate_v1(fixture((None,),model=True));l=v['layout_instances'][0]
        self.assertEqual(l['space_type'],'ModelSpace');self.assertEqual(l['sheet_identity_status'],'not_applicable')
        self.assertFalse(v['sheet_identity_candidates'])

    def test_stable_id_not_label(self):
        a=migrate_v1(fixture(('D-01',)));b=migrate_v1(fixture(('D-99',)))
        self.assertEqual(a['layout_instances'][0]['layout_instance_id'],b['layout_instances'][0]['layout_instance_id'])

    def test_roles_distinct(self):
        for role in ['drawing_number_candidate','drawing_title_candidate','sheet_number_candidate','sheet_title_candidate']:
            v=migrate_v1(fixture(('X',),[role]));l=v['layout_instances'][0]
            self.assertEqual([c['alias_role'] for c in l['identity_candidates']],[role])
            self.assertNotEqual(l['sheet_identity_status'],'supported')

    def test_unknown_not_duplicated(self):
        v=migrate_v1(fixture(('X',),['unresolved_number_candidate']))
        self.assertEqual(v['layout_instances'][0]['identity_candidates'][0]['alias_role'],'unknown_identifier_candidate')
        self.assertEqual(lookup(v,'X',roles=['drawing_number_candidate'])['matches'],[])

    def test_role_filter(self):
        v=migrate_v1(fixture(('D-01',)))
        self.assertEqual(lookup(v,'D-01',roles=['sheet_number_candidate'])['lookup_status'],'not_found')
        self.assertEqual(lookup(v,'D-01',roles=['drawing_number_candidate'])['lookup_status'],'unique_registry_candidate')

    def test_target_filter(self):
        v=migrate_v1(fixture(('D-01',)))
        self.assertFalse(lookup(v,'D-01',target_kinds=['drawing_instance'])['matches'])
        self.assertEqual(len(lookup(v,'D-01',target_kinds=['layout_instance'])['matches']),1)

    def test_drawing_layout_ambiguity(self):
        r=fixture(('D-01',));d=r['drawing_instances'][0]
        r['aliases']=[dict(kind='drawing_number_candidate',value='D-01',instance_id=d['instance_id'],status='partial',provenance=d['provenance'])]
        v=migrate_v1(r);self.assertEqual(lookup(v,'D-01')['lookup_status'],'ambiguous')
        self.assertEqual(lookup(v,'D-01',target_kinds=['layout_instance'])['lookup_status'],'unique_registry_candidate')

    def test_multiple_never_first(self):
        v=migrate_v1(fixture(('D-01','D-01')));r=lookup(v,'D-01')
        self.assertEqual(r['lookup_status'],'ambiguous');self.assertEqual(len(r['matches']),2)

    def test_conflict_same_layout(self):
        r=fixture(('D-01',));e=r['drawing_instances'][0]['drawing_sheet_identity_evidence']
        c=copy.deepcopy(e['candidates'][0]);c.update(value='D-02',raw_value='D-02');e['candidates'].append(c)
        v=migrate_v1(r);self.assertEqual(len(v['conflicts']),1)
        self.assertEqual(lookup(v,'D-01')['lookup_status'],'conflicting')

    def test_exact_dedup(self):
        r=fixture(('D-01',));e=r['drawing_instances'][0]['drawing_sheet_identity_evidence']
        e['layouts']*=2;e['candidates']*=2
        self.assertEqual(migrate_v1(r)['summary']['layout_instance_count'],1)

    def test_model_alias_not_attached(self):
        r=fixture(('D-02',));d=r['drawing_instances'][0]
        r['aliases']=[dict(kind='drawing_number_candidate',value='D-01',instance_id=d['instance_id'],status='partial',provenance=d['provenance'])]
        v=migrate_v1(r);self.assertEqual(lookup(v,'D-01')['matches'][0]['target_kind'],'drawing_instance')
        self.assertFalse(lookup(v,'D-01',target_kinds=['layout_instance'])['matches'])

    def test_revision_not_identity(self):
        v=migrate_v1(fixture(('A',),['revision_number_candidate']))
        self.assertEqual(len(v['layout_instances'][0]['revision_candidates']),1)
        self.assertFalse(lookup(v,'A',roles=['sheet_number_candidate'])['matches'])
        self.assertFalse(lookup(v,'a'*64)['matches'])

    def test_no_approval(self):
        v=migrate_v1(fixture());self.assertFalse(lookup(v,'D-01')['logical_identity_approved'])
        self.assertEqual(v['summary']['sheet_identity_supported_count'],0)
        self.assertFalse({'engineering_semantics','quantity','resolved_links'} & set(v))

    def test_foreign_candidate_rejected(self):
        r=fixture();r['drawing_instances'][0]['drawing_sheet_identity_evidence']['candidates'][0]['carrier_identity']['project_id']='Q'
        with self.assertRaises(ValueError):migrate_v1(r)

    def test_foreign_layout_rejected(self):
        r=fixture();r['drawing_instances'][0]['drawing_sheet_identity_evidence']['layouts'][0]['drawing_instance_id']='foreign'
        with self.assertRaises(ValueError):migrate_v1(r)

    def test_foreign_hash_rejected(self):
        r=fixture();r['drawing_instances'][0]['drawing_sheet_identity_evidence']['candidates'][0]['carrier_identity']['snapshot_id']='f'*64
        with self.assertRaises(ValueError):migrate_v1(r)

    def test_no_fuzzy(self):self.assertFalse(lookup(migrate_v1(fixture()),'D01')['matches'])

    def test_empty_filter_does_not_broaden(self):self.assertFalse(lookup(migrate_v1(fixture()),'D-01',roles=[])['matches'])

    def test_invalid_filter(self):
        with self.assertRaises(ValueError):lookup(migrate_v1(fixture()),'D-01',roles=['engineering_system'])

    def test_legacy_view_not_v2(self):
        sys.path.insert(0,str(ROOT/'explicit-cross-sheet-reference'))
        from references import validate_registry
        v=migrate_v1(fixture())
        with self.assertRaises(ValueError):validate_registry(v)
        validate_registry(legacy_view(v))

    def test_reordered_evidence(self):
        r=fixture();a=migrate_v1(r);e=r['drawing_instances'][0]['drawing_sheet_identity_evidence'];e['layouts'].reverse();e['candidates'].reverse()
        b=migrate_v1(r);self.assertEqual(a['layout_instances'],b['layout_instances']);self.assertEqual(lookup(a,'D-01'),lookup(b,'D-01'))

    def test_foreign_drawing_alias(self):
        r=fixture();d=r['drawing_instances'][0]
        r['aliases']=[dict(kind='drawing_number_candidate',value='D-01',instance_id=d['instance_id'],status='partial',
            source_identity={'project_id':'Q','snapshot_id':d['report_sha256']},provenance=d['provenance'])]
        with self.assertRaises(ValueError):migrate_v1(r)

    def test_index_tampering(self):
        v=migrate_v1(fixture());v['aliases'][0]['target_id']='foreign'
        with self.assertRaises(ValueError):lookup(v,'D-01')

    def test_sheet_role_typed_target(self):
        v=migrate_v1(fixture(('S-01',),['sheet_number_candidate']))
        r=lookup(v,'S-01',roles=['sheet_number_candidate'],target_kinds=['sheet_identity_candidate'])
        self.assertEqual(r['lookup_status'],'unique_registry_candidate')
        self.assertEqual(r['matches'][0]['target_kind'],'sheet_identity_candidate')
        self.assertFalse(r['sheet_identity_approved'])

    def test_same_sheet_number_across_drawings(self):
        r=fixture(('S-01',),['sheet_number_candidate']);d=copy.deepcopy(r['drawing_instances'][0])
        old=d['instance_id'];d['drawing_ref']='second.dwg'
        d['instance_id']=content_hash({k:d[k] for k in ('project_id','drawing_ref','source_dwg_sha256','report_sha256')})
        e=d['drawing_sheet_identity_evidence'];e['drawing_instance_id']=d['instance_id']
        l=e['layouts'][0];l['drawing_instance_id']=d['instance_id'];n=l['layout_source_identity']
        l['layout_identity']=content_hash(['P',d['instance_id'],l['layout_name'],n['handle'],n['block_handle']])
        c=e['candidates'][0];c['layout_identity']=l['layout_identity']
        c['carrier_identity'].update(drawing_instance_id=d['instance_id'],drawing_ref='second.dwg',layout_identity=l['layout_identity'])
        r['drawing_instances'].append(d)
        q=lookup(migrate_v1(r),'S-01',target_kinds=['sheet_identity_candidate'])
        self.assertEqual(q['lookup_status'],'ambiguous');self.assertEqual(q['match_count'],2)

    def test_unavailable_layout_cannot_supply_identity(self):
        r=fixture();r['drawing_instances'][0]['drawing_sheet_identity_evidence']['layouts'][0]['layout_acquisition_status']='unavailable'
        with self.assertRaises(ValueError):migrate_v1(r)

    def test_native_layout_name_is_not_title(self):
        v=migrate_v1(fixture())
        self.assertFalse(lookup(v,'Layout0',roles=['sheet_title_candidate'])['matches'])
        self.assertEqual(lookup(v,'Layout0',roles=['layout_name'])['match_count'],1)

    def test_new_sidecar_content_does_not_change_layout_identity(self):
        r=fixture(('D-01',));a=migrate_v1(r)
        e=r['drawing_instances'][0]['drawing_sheet_identity_evidence']
        # New sidecar bytes legitimately change snapshot/provenance, not native handles.
        e['provenance'][0]['sha256']='d'*64
        for c in e['candidates']:
            c['carrier_identity']['snapshot_id']='d'*64;c.update(value='D-02',raw_value='D-02')
        b=migrate_v1(r)
        self.assertEqual(a['layout_instances'][0]['layout_instance_id'],b['layout_instances'][0]['layout_instance_id'])
        self.assertNotEqual(a['layout_instances'][0]['layout_report_sha256'],b['layout_instances'][0]['layout_report_sha256'])

    def test_cli_pinned_migration_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'old.json';out=Path(tmp)/'new.json'
            data=json.dumps(fixture()).encode();p.write_bytes(data)
            cmd=[sys.executable,'-B',str(ROOT/'project-drawing-registry/resolve_v2.py'),
                 '--v1-registry',str(p),'--v1-sha256',hashlib.sha256(data).hexdigest(),'--output',str(out)]
            result=subprocess.run(cmd,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            first=out.read_bytes();self.assertEqual(p.read_bytes(),data)
            self.assertNotEqual(subprocess.run(cmd,capture_output=True).returncode,0)
            self.assertEqual(out.read_bytes(),first)

    def test_cli_bad_pin_has_no_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'old.json';out=Path(tmp)/'new.json';p.write_text(json.dumps(fixture()))
            result=subprocess.run([sys.executable,'-B',str(ROOT/'project-drawing-registry/resolve_v2.py'),
                '--v1-registry',str(p),'--v1-sha256','0'*64,'--output',str(out)],capture_output=True)
            self.assertNotEqual(result.returncode,0);self.assertFalse(out.exists())

if __name__=='__main__':unittest.main()
