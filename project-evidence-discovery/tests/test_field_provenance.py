"""Synthetic contract evidence; not project approval or real-host coverage."""
import copy
import json
import sys
import unittest
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from field_provenance import field_record

IDENTITY={'project_id':'P','drawing_ref':'D','snapshot_id':'a'*64,
          'parent_path':[],'table_handle':'T','row_index':0,'column_index':0}
def record(code='%<\\AcVar Date>%',**kwargs):
    raw='FieldEvidenceVersion="1"\nField.CarrierHandle="T"\n'
    raw+='Field.Code.Status="read"\nField.Code.Source="synthetic"\nField.Code.Value='+json.dumps(code)+'\n'
    return field_record(raw,kwargs.pop('identity',IDENTITY),'TABLE_CELL','A-01','read',
                        [{'sha256':'a'*64}],kwargs.pop('exporter','2.7-field-provenance-v1'),present=True,**kwargs)

class FieldProvenanceTests(unittest.TestCase):
    def test_display_separate(self):
        x=record();self.assertEqual(x['displayed_value'],'A-01');self.assertNotEqual(x['raw_field_code'],'A-01')
    def test_raw_code(self):
        code='%<\\AcExpr (1 + 2)>%';self.assertEqual(record(code)['raw_field_code'],code)
    def test_unknown_kind(self):self.assertEqual(record('%<mystery>%')['field_kind'],'unknown_field')
    def test_no_static_claim(self):self.assertFalse(record()['authored_static_text_established'])
    def test_evaluation(self):self.assertEqual(record()['evaluation_status'],'unsupported')
    def test_missing_code(self):
        x=field_record('',IDENTITY,'TABLE_CELL','V','read',[],'2.6-table-cell-evidence-v1',present=True)
        self.assertEqual(x['field_code_status'],'missing');self.assertEqual(x['provenance_strength'],'display_only')
    def test_malformed_code(self):self.assertEqual(record('%<broken')['field_code_status'],'invalid_result')
    def test_missing_identity(self):self.assertEqual(record(identity={})['status'],'unresolved')
    def test_foreign_carrier(self):self.assertEqual(record(identity=dict(IDENTITY,table_handle='OTHER'))['status'],'unresolved')
    def test_snapshot(self):self.assertNotEqual(record()['field_identity'],record(identity=dict(IDENTITY,snapshot_id='b'*64))['field_identity'])
    def test_path(self):self.assertNotEqual(record()['field_identity'],record(identity=dict(IDENTITY,parent_path=['I']))['field_identity'])
    def test_cell(self):self.assertNotEqual(record()['field_identity'],record(identity=dict(IDENTITY,column_index=1))['field_identity'])
    def test_immutable(self):
        before=copy.deepcopy(IDENTITY);record();self.assertEqual(IDENTITY,before)
    def test_unknown_version(self):self.assertEqual(record(exporter='future')['status'],'unsupported')
    def test_no_reference_guess(self):self.assertEqual(record()['referenced_object_identity'],[])
    def test_no_semantics(self):
        x=record();self.assertFalse(set(x)&{'bindings','note_scope','system_binding','quantity'})
    def test_mixed_not_split(self):self.assertEqual(record('prefix %<unknown>% suffix')['mixed_field_text_structure'],'unresolved')
    def test_static_no_field(self):
        self.assertIsNone(field_record('',IDENTITY,'TEXT','plain','read',[],'2.6-table-cell-evidence-v1'))
    def test_serialization_failure(self):
        raw='FieldEvidenceVersion="1"\nField.CarrierHandle="T"\nField.Code.Status="read"\nField.Code.Source="API"\nField.Code.Value="bad\\Q"\n'
        x=field_record(raw,IDENTITY,'TABLE_CELL','V','read',[], '2.7-field-provenance-v1',present=True)
        self.assertEqual(x['field_code_status'],'invalid_result')
    def test_duplicate_code(self):
        raw='FieldEvidenceVersion="1"\nField.CarrierHandle="T"\nField.Code.Status="read"\nField.Code.Source="API"\nField.Code.Value="a"\nField.Code.Value="b"\n'
        self.assertEqual(field_record(raw,IDENTITY,'TABLE_CELL','V','read',[],'2.7-field-provenance-v1',present=True)['field_code_status'],'invalid_result')
    def test_reference_partial_path(self):
        raw='FieldEvidenceVersion="1"\nField.CarrierHandle="T"\nField.ReferenceHandle="AB12"\n'
        x=field_record(raw,IDENTITY,'TABLE_CELL','V','read',[],'2.7-field-provenance-v1',present=True)
        self.assertEqual(x['referenced_object_identity'][0]['handle'],'AB12')
        self.assertIsNone(x['referenced_object_identity'][0]['parent_path'])
        self.assertEqual(x['reference_status'],'partial');self.assertIsNone(x['referenced_property'])
    def test_adapter_collection_only(self):
        from test_table_evidence import report,cell
        from annotations import load_report
        from discovery import discover
        raw='DWG="D"\nExtractorVersion="2.7-field-provenance-v1"\nAcquisitionMode="ModelSpaceTopLevelAllLayers"\nModelSpaceTopLevel="included"\nNestedBlocks="not expanded"\nEntityHandle="T"\nDXF_Type="ACAD_TABLE"\n'+report(cell(content=2))
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'r.txt';p.write_text(raw,encoding='utf-8')
            c=load_report(p,'P');self.assertEqual(len(c['field_evidence']),1)
            self.assertEqual(c['field_evidence'][0]['carrier_identity'],c['table_evidence'][0]['cells'][0]['identity'])
            result=discover(c);self.assertEqual(result['bindings'],[]);self.assertEqual(result['propagation_roots'],[])
            self.assertEqual(result['field_evidence'],c['field_evidence'])
    def test_old_marker_presence(self):
        x=field_record('',dict(IDENTITY,handle='A'),'ATTRIB','value %<unknown>%','read',[],'2.6-table-cell-evidence-v1')
        self.assertEqual(x['field_presence'],'marker_candidate');self.assertEqual(x['field_code_status'],'missing')
        self.assertIsNone(x['displayed_value']);self.assertEqual(x['displayed_value_status'],'unresolved')

if __name__=='__main__':unittest.main()
