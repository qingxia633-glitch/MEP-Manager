import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'drawing-sheet-identity'))
sys.path.insert(0, str(ROOT / 'project-drawing-registry'))
from identity import read_identity
from registry import build_registry, lookup


def q(x): return json.dumps(x, ensure_ascii=False)


def insert(number='A-01', title='Plan', handle='10', defs=False, field=False):
    s = f'PaperEntity_BEGIN\nEntityHandle="{handle}"\nDXF_Type="INSERT"\nEntityLayoutName="Layout1"\nEntityOwnerBlock="B1"\nEntityOwnerType="BLOCK_RECORD"\nBlockName="FRAME"\n'
    for h, tag, val in [('11', 'DRAWING NO', number), ('12', 'DRAWING TITLE', title)]:
        s += f'AttributeTag={q(tag)}\nAttributeText_RAW={q(val)}\nAttribute_DXF=((0 . "ATTRIB") (5 . "{handle+h}") (330 . <Entity name: owner>))\nAttributeLayout.ParentINSERTHandle="{handle}"\n'
        if field and h == '11':
            s += f'FieldEvidence_BEGIN\nFieldEvidenceVersion="2"\nField.CarrierHandle="{handle+h}"\nFieldGraphVersion="1"\nFieldGraph.Root="F1"\nFieldGraph.Status="read"\nFieldNode_BEGIN\nNode.Handle="F1"\nNode.Type="FIELD"\nNode.Status="read"\nNode.Evaluator="AcSm"\nNode.ChildCount=0\nNode.ReferenceCount=0\nNode.Code="AcSm SheetNumber"\nNode.CodeStatus="read"\nFieldNode_END\nFieldEvidence_END\n'
    if defs:
        s += 'ConstantAttributeDefinition_BLOCK_LOCAL=((0 . "ATTDEF") (5 . "D1") (2 . "DRAWING NO") (1 . "DEFAULT") (70 . 2))\n'
    return s + 'PaperEntity_END\n'


def layout(name='Layout1', handle='A1', block='B1', entities=None, model=False):
    if entities is None: entities = '' if model else insert(handle='10' if handle=='A1' else '20')
    entities = entities.replace('EntityLayoutName="Layout1"', 'EntityLayoutName='+q(name)).replace('EntityOwnerBlock="B1"', 'EntityOwnerBlock='+q(block))
    return f'Layout_BEGIN\nLayoutName={q(name)}\nLayoutHandle={q(handle)}\nSpaceBlockHandle={q(block)}\nSpaceType={q("ModelSpace" if model else "PaperSpace")}\nLayoutOrder=1\nLayoutAcquisitionStatus="read"\n{entities}LayoutEntityCount={entities.count("PaperEntity_BEGIN")}\nLayoutReadErrorCount=0\nLayout_END\n'


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.instance = dict(project_id='P', instance_id='i', drawing_ref='a.dwg', source_dwg_hash_status='verified')

    def report(self, rows=None):
        if rows is None: rows = [layout()]
        p = self.root / 'layout.txt'
        p.write_text('ReportVersion="2.9-layout-identity-v1"\nDrawingSheetIdentityEvidenceVersion="1"\nLayoutOwnerContractVersion="1"\nOwnerExtractionSelfTest="PASS"\nDWG="a.dwg"\nLayoutInventoryStatus="read"\n'+''.join(rows)+f'LayoutCount={len(rows)}\nEND_LAYOUT_REPORT\n', encoding='utf-8')
        return p, hashlib.sha256(p.read_bytes()).hexdigest()

    def read(self, rows=None, project='P'):
        p, h = self.report(rows)
        return read_identity(dict(self.instance, project_id=project), p, h)

    def test_distinct_layouts_not_sheets(self):
        r = self.read([layout(), layout('Layout2', 'A2', 'B2')])
        self.assertEqual(len({x['layout_identity'] for x in r['layouts']}), 2)
        self.assertEqual(r['sheet_identity_status'], 'ambiguous')
        self.assertTrue(all(x['sheet_identity_status'] == 'candidate' for x in r['sheet_candidates']))

    def test_instance_attributes_and_defaults(self):
        r = self.read([layout(entities=insert(defs=True))])
        t = r['title_blocks'][0]
        self.assertEqual(t['status'], 'candidate_title_block')
        self.assertEqual(t['attribute_count'], 2)
        self.assertEqual(t['definition_defaults'][0]['value'], 'DEFAULT')
        self.assertEqual([c['value'] for c in r['candidates'] if c['kind']=='drawing_number_candidate'], ['A-01'])
        self.assertEqual([c['value'] for c in r['candidates'] if c['kind']=='drawing_title_candidate'], ['Plan'])
        self.assertTrue(all(c['carrier_identity']['owner_insert_handle']=='10' for c in r['candidates']))

    def test_field_requires_graph(self):
        r = self.read([layout(entities=insert(field=True))])
        self.assertEqual(len([c for c in r['candidates'] if c['kind']=='sheet_number_candidate']), 1)
        r = self.read([layout(entities=insert(field=True).replace('Field.CarrierHandle="1011"','Field.CarrierHandle="FFFF"'))])
        self.assertFalse(any(c['evidence_strength']=='field_graph_backed' for c in r['candidates']))

    def test_display_only_field_not_property(self):
        r=self.read([layout(entities=insert(number='%<SheetNumber>%'))])
        self.assertFalse(any(c['kind']=='sheet_number_candidate' for c in r['candidates']))

    def test_conflicting_numbers(self):
        r=self.read([layout(entities=insert()+insert('B-02',handle='20'))])
        self.assertEqual(r['identity_status'],'conflicting')

    def test_same_number_two_layouts_ambiguous(self):
        r=self.read([layout(),layout('Layout2','A2','B2')])
        self.assertEqual(r['identity_status'],'ambiguous')

    def test_projects_isolated(self):
        a=self.read(); b=self.read(project='Q')
        self.assertNotEqual(a['layouts'][0]['layout_identity'],b['layouts'][0]['layout_identity'])

    def test_no_revision_from_hash_or_date(self):
        r=self.read([layout(entities=insert().replace('DRAWING TITLE','DATE'))])
        self.assertFalse(any(c['kind'].startswith('revision') for c in r['candidates']))

    def test_explicit_revision(self):
        r=self.read([layout(entities=insert().replace('DRAWING TITLE','REVISION'))])
        self.assertTrue(any(c['kind']=='revision_number_candidate' for c in r['candidates']))

    def test_version_is_observed_revision_candidate_not_approval(self):
        r=self.read([layout(entities=insert().replace('DRAWING TITLE','版本'))])
        c=next(c for c in r['candidates'] if c['kind']=='revision_number_candidate')
        self.assertEqual(c['status'],'candidate')
        self.assertEqual(c['tag'],'版本')

    def test_unknown_roles_preserved(self):
        r=self.read([layout(entities=insert().replace('DRAWING NO','NUMBER').replace('DRAWING TITLE','TITLE'))])
        self.assertEqual({c['identifier_role'] for c in r['candidates']},{'unresolved'})

    def test_no_position_or_name_only(self):
        r=self.read([layout(entities=insert().replace('DRAWING NO','X').replace('DRAWING TITLE','Y'))])
        self.assertFalse(r['title_blocks'])

    def test_bad_owner_rejected(self):
        with self.assertRaises(ValueError):self.read([layout(entities=insert().replace('ParentINSERTHandle="10"','ParentINSERTHandle="99"'))])

    def test_space_mismatch_rejected(self):
        with self.assertRaises(ValueError):self.read([layout(entities=insert().replace('EntityOwnerBlock="B1"','EntityOwnerBlock="FFFF"'))])

    def test_reactor_is_not_owner(self):
        with self.assertRaises(ValueError):self.read([layout(entities=insert().replace('EntityOwnerType="BLOCK_RECORD"','EntityOwnerType="VIEWPORT"'))])

    def test_duplicate_layout_rejected(self):
        with self.assertRaises(ValueError):self.read([layout(),layout()])

    def test_entity_handle_cannot_belong_to_two_spaces(self):
        with self.assertRaises(ValueError):self.read([layout(),layout('Layout2','A2','B2',entities=insert())])

    def test_hash_mismatch_rejected(self):
        p,h=self.report()
        with self.assertRaises(ValueError):read_identity(self.instance,p,'0'*64)

    def test_foreign_drawing_rejected(self):
        p,h=self.report()
        with self.assertRaises(ValueError):read_identity(dict(self.instance,drawing_ref='b.dwg'),p,h)

    def test_unverified_dwg_rejected(self):
        p,h=self.report()
        with self.assertRaises(ValueError):read_identity(dict(self.instance,source_dwg_hash_status='unavailable'),p,h)

    def test_incomplete_envelope_rejected(self):
        with self.assertRaises(ValueError):self.read([layout().replace('PaperEntity_END','missing')])

    def test_partial_layout_not_empty(self):
        r=self.read([layout(entities='').replace('LayoutReadErrorCount=0','LayoutReadErrorCount=1')])
        self.assertEqual(r['layouts'][0]['layout_acquisition_status'],'unavailable')
        self.assertEqual(r['identity_status'],'unresolved')

    def registry(self, sidecar=False):
        dwg=self.root/'source.dwg';dwg.write_bytes(b'synthetic')
        p=self.root/'model.txt'
        p.write_text('DWG="a.dwg"\nExtractorVersion="2.8-field-graph-evidence-v1"\nAcquisitionMode="ModelSpaceTopLevelAllLayers"\nModelSpaceTopLevel="included"\nPaperSpaceLayouts="not included"\nNestedBlocks="not expanded"\nReadErrorCount=0\nEND_OF_REPORT: scan finished. Inspect errors and scope limitations before interpreting results.',encoding='utf-8')
        item=dict(report_path=str(p),encoding='utf-8',source_dwg_path=str(dwg))
        if sidecar:
            lp,lh=self.report();item.update(layout_report_path=str(lp),layout_report_sha256=lh)
        return build_registry('P',[item])

    def test_legacy_not_acquired(self):
        r=self.registry();d=r['drawing_instances'][0]
        self.assertEqual(d['layout_status'],'unresolved_out_of_scope')
        self.assertEqual(d['sheet_identity_status'],'unresolved')

    def test_registry_evidence_not_link_or_approval(self):
        r=self.registry(True);d=r['drawing_instances'][0]
        self.assertEqual(d['logical_identity_status'],'candidate')
        a=lookup(r,'A-01')['match_evidence'][0]
        self.assertEqual(a['evidence_strength'],'layout_title_block_attribute_candidate')
        self.assertNotEqual(a['kind'],'filename_stem')
        self.assertFalse(lookup(r,'A-01')['logical_identity_approved'])
        self.assertFalse({'quantity','resolved_links','engineering_semantics'} & set(r))
        sys.path.insert(0,str(ROOT/'explicit-cross-sheet-reference'))
        from references import validate_registry, scan
        validate_registry(r)
        self.assertEqual(scan(r,[])['resolved_links'],[])

    def test_registry_duplicate_input_with_layout(self):
        # Reuse the independently produced input map, not the output as input.
        r=self.registry(True)
        item={'report_path':str(self.root/'model.txt'),'encoding':'utf-8',
              'source_dwg_path':str(self.root/'source.dwg'),
              'layout_report_path':str(self.root/'layout.txt'),
              'layout_report_sha256':hashlib.sha256((self.root/'layout.txt').read_bytes()).hexdigest()}
        self.assertEqual(build_registry('P',[item,item]),r)

    def test_sheet_title_separate(self):
        r=self.read([layout(entities=insert().replace('DRAWING TITLE','SHEET TITLE'))])
        self.assertEqual([c['value'] for c in r['candidates'] if c['kind']=='sheet_title_candidate'],['Plan'])
        self.assertFalse(any(c['kind']=='drawing_title_candidate' for c in r['candidates']))

    def test_blank_instance_not_default(self):
        r=self.read([layout(entities=insert(number='',defs=True))])
        self.assertFalse(any(c['kind']=='drawing_number_candidate' for c in r['candidates']))

    def test_revision_role_separate_from_sheet_number(self):
        r=self.read([layout(entities=insert().replace('DRAWING TITLE','REVISION'))])
        self.assertFalse(any(c['kind']=='sheet_number_candidate' for c in r['candidates']))

    def test_field_graph_incomplete_not_backed(self):
        r=self.read([layout(entities=insert(field=True).replace('Node.ChildCount=0','Node.ChildCount=1'))])
        self.assertFalse(any(c['evidence_strength']=='field_graph_backed' for c in r['candidates']))


if __name__=='__main__':unittest.main()
