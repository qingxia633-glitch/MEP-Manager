import json,sys,tempfile,unittest,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from table_evidence import table_record, consolidate_tables

IDENTITY={'project_id':'P','drawing_ref':'D','snapshot_id':'a'*64,'parent_path':[], 'table_handle':'T','space':'ModelSpace'}
def field(k,v,status='read'):
    return f'{k}.Value={json.dumps(v,ensure_ascii=False)}\n{k}.Status="{status}"\n{k}.Source="synthetic getter"\n'
def cell(r=0,c=0,text='中文',empty=False,typ=1,content=1,merged=False,region=None):
    s=f'TableCell_BEGIN\nCell.Row={r}\nCell.Column={c}\n'
    for k,v in [('Cell.Type',typ),('Cell.ContentType',content),('Cell.Text',text),('Cell.Empty',empty),('Cell.FieldId',0),('Cell.Merged',merged)]:s+=field(k,v)
    if region is not None:s+='Cell.MergeRange=('+ ' '.join(map(str,region))+')\n'
    return s+'TableCell_END\n'
def report(cells=None,rows=1,cols=1):
    return 'TableEvidenceVersion="1"\nTableEvidence_BEGIN\n'+field('Table.Rows',rows)+field('Table.Columns',cols)+(cell() if cells is None else cells)+'TableEvidence_END\n'
def read(text=None):return table_record(report() if text is None else text,IDENTITY,[{'sha256':'a'*64}],'2.6-table-cell-evidence-v1')

class TableEvidenceTests(unittest.TestCase):
    def test_identity(self):self.assertEqual(read()['identity'],IDENTITY)
    def test_dimensions(self):self.assertEqual(read()['row_count'],1);self.assertEqual(read()['column_count'],1)
    def test_cell_stable(self):self.assertEqual(read()['cells'][0]['identity'],read()['cells'][0]['identity'])
    def test_chinese(self):self.assertEqual(read()['cells'][0]['decoded_text'],'中文')
    def test_empty_distinct(self):
        a=read(report(cell(text='',empty=True)))['cells'][0]
        self.assertEqual(a['content_kind'],'empty');self.assertEqual(a['decoded_text'],'')
        b=read(report(cell().replace('Cell.Text.Status="read"','Cell.Text.Status="unavailable"')))['cells'][0]
        self.assertIsNone(b['decoded_text']);self.assertNotEqual(b['content_kind'],'empty')
        self.assertEqual(b['acquisition_status'],'unavailable')
    def test_merged_alias(self):
        a=read(report(cell(merged=True,region=[0,0,0,1])+cell(c=1,merged=True,region=[0,0,0,1]),cols=2))
        self.assertEqual(a['cells'][1]['master_cell_identity'],a['cells'][0]['identity'])
        self.assertFalse(a['cells'][1]['independent_content_candidate'])
    def test_failure(self):self.assertEqual(read(report().replace('Table.Rows.Status="read"','Table.Rows.Status="unavailable"'))['cells'],[])
    def test_old(self):self.assertEqual(read('Raw_DXF=(0 . "ACAD_TABLE")')['acquisition_status'],'missing');self.assertEqual(read('')['cells'],[])
    def test_block(self):
        a=read(report(cell(typ=2,content=4)))['cells'][0];self.assertEqual(a['content_kind'],'block');self.assertIsNone(a['decoded_text'])
    def test_field(self):
        a=read(report(cell(content=2)))['cells'][0];self.assertEqual(a['content_kind'],'field');self.assertEqual(a['field_provenance'],'missing');self.assertFalse(a['static_text_provenance_established'])
    def test_duplicate_cell(self):self.assertEqual(read(report(cell()+cell()))['acquisition_status'],'conflicting')
    def test_bad_index(self):self.assertEqual(read(report(cell(r=2)))['acquisition_status'],'invalid_result')
    def test_bad_merge(self):self.assertEqual(read(report(cell(merged=True,region=[0,5,0,0])))['acquisition_status'],'invalid_result')
    def test_missing_grid(self):self.assertEqual(read(report('',rows=2))['acquisition_status'],'partial')
    def test_duplicate_table(self):
        a=read();b=copy.deepcopy(a);out=consolidate_tables([a,b]);self.assertEqual(out[0]['acquisition_status'],'conflicting')
    def test_unknown_version(self):self.assertEqual(read(report().replace('TableEvidenceVersion="1"','TableEvidenceVersion="9"'))['acquisition_status'],'unsupported')
    def test_bad_decode(self):
        a=read(report().replace('Cell.Text.Value="中文"','Cell.Text.Value="\\Zbad"'))['cells'][0];self.assertIsNone(a['decoded_text'])
    def test_merge_master_conflict(self):
        a=read(report(cell()+cell(c=1,merged=True,region=[0,0,0,1]),cols=2));self.assertEqual(a['acquisition_status'],'conflicting')
    def test_snapshot_identity(self):
        a=read();other=dict(IDENTITY,snapshot_id='b'*64)
        b=table_record(report(),other,[], '2.6-table-cell-evidence-v1');self.assertNotEqual(a['cells'][0]['identity'],b['cells'][0]['identity'])
    def test_style_version_compatibility(self):
        from line_style import style_evidence
        r='StyleEvidenceVersion="1"\nStyle.entity_aci.Status="read"\nStyle.entity_aci.Value=3\nStyle.entity_aci.Source="DXF62"\n'
        a=style_evidence(r,'ExtractorVersion="2.6-table-cell-evidence-v1"',IDENTITY,[])
        self.assertEqual(a['raw_entity_style']['entity_aci']['value'],3)
    def test_adapter_boundary(self):
        from annotations import load_report
        from discovery import discover
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'r.txt';p.write_text('DWG="D"\nExtractorVersion="2.6-table-cell-evidence-v1"\nAcquisitionMode="ModelSpaceTopLevelAllLayers"\nModelSpaceTopLevel="included"\nNestedBlocks="not expanded"\nEntityHandle="T"\nDXF_Type="ACAD_TABLE"\n'+report(cell(text='S JDG20 火灾报警二总线')),encoding='utf-8')
            c=load_report(p,'P');self.assertEqual(len(c['table_evidence']),1);self.assertEqual(c['annotations'],[])
            r=discover(c);self.assertEqual(r['bindings'],[]);self.assertEqual(r['propagation_roots'],[]);self.assertEqual(len(r['table_evidence']),1)

if __name__=='__main__':unittest.main()
