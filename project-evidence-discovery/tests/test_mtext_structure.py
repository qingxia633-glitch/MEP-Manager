import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mtext_structure import structure_record


def source(text):
    return {'type':'MTEXT','handle':'M','project_id':'P','source_drawing':'D.dwg',
            'parent_path':[], 'raw_serialized_text':json.dumps(text,ensure_ascii=False),
            'decoded_text':text,'text_decode_status':'read','provenance':[{'sha256':'a'*64}]}


def structure(text):
    return structure_record(source(text),'a'*64)


class MTextStructureTests(unittest.TestCase):
    def test_single(self):
        s=structure('ordinary text');self.assertEqual(s['status'],'read');self.assertEqual(len(s['paragraphs']),1)
    def test_two(self):
        self.assertEqual([p['decoded_text'] for p in structure(r'a\Pb')['paragraphs']],['a','b'])
    def test_order_and_empty(self):
        self.assertEqual([p['raw_fragment'] for p in structure(r'\Pa\P\Pb\P')['paragraphs']],['','a','','b',''])
    def test_visual_wrap(self):
        a=source('a long line');a['reference_width']=1
        self.assertEqual(len(structure_record(a,'a'*64)['paragraphs']),1)
    def test_traceability(self):
        t=r'甲\P乙\P丙';s=structure(t)
        for p in s['paragraphs']:
            start,end=p['source_span'];self.assertEqual(t[start:end],p['raw_fragment'])
        self.assertEqual(r'\P'.join(p['raw_fragment'] for p in s['paragraphs']),t)
    def test_escaped_backslash(self):
        self.assertEqual(len(structure(r'a\\Pb')['paragraphs']),1)
    def test_unknown_escape(self):
        s=structure(r'a\Zunknown\Pb');self.assertEqual(s['status'],'partial');self.assertEqual(len(s['paragraphs']),1)
    def test_font_payload_not_boundary(self):
        s=structure(r'{\Fname\Ppayload;a\Pb}')
        self.assertEqual(len(s['paragraphs']),2);self.assertEqual(s['status'],'partial')
        self.assertEqual(s['paragraphs'][0]['raw_fragment'],r'{\Fname\Ppayload;a')
    def test_unterminated_control(self):
        s=structure(r'a\H2\Pb');self.assertEqual(s['status'],'partial');self.assertEqual(len(s['paragraphs']),1)
    def test_unicode_preserved(self):
        s=structure(r'\U+4E2D\P文');self.assertEqual(s['paragraphs'][0]['decoded_text'],r'\U+4E2D');self.assertEqual(s['status'],'partial')
    def test_newline_not_paragraph(self):
        s=structure('a\nb');self.assertEqual(len(s['paragraphs']),1);self.assertEqual(s['status'],'partial')
    def test_list_markers(self):
        for mark in ['1.','1、','（1）','(1)','一、','①','●','-']:
            self.assertEqual(structure(mark+' 内容')['paragraphs'][0]['list_marker_candidate'],mark)
    def test_heading_lexical(self):
        self.assertEqual(structure('设计说明：')['paragraphs'][0]['heading_lexical_candidate'],'设计说明')
    def test_original_unchanged(self):
        a=source(r'a\Pb');before=copy.deepcopy(a);structure_record(a,'a'*64);self.assertEqual(a,before)
    def test_stable_identity(self):
        self.assertEqual(structure('a')['paragraphs'][0]['identity'],structure('a')['paragraphs'][0]['identity'])
    def test_snapshot_separation(self):
        a=source('a');self.assertNotEqual(structure_record(a,'a'*64)['paragraphs'][0]['identity'],structure_record(a,'b'*64)['paragraphs'][0]['identity'])
    def test_missing_identity(self):
        a=source('a');a['parent_path']=None;self.assertEqual(structure_record(a,'a'*64)['status'],'unresolved')
    def test_nested_out_of_scope(self):
        a=source('a');a['parent_path']=['I'];self.assertEqual(structure_record(a,'a'*64)['paragraphs'],[])
    def test_failed_decode(self):
        a=source('a');a['text_decode_status']='unresolved';self.assertEqual(structure_record(a,'a'*64)['paragraphs'],[])
    def test_field_preserved(self):
        s=structure(r'a%<field\Pnotbreak>%\Pb');self.assertEqual(s['status'],'partial');self.assertEqual(len(s['paragraphs']),1)
    def test_adapter_and_discovery_boundary(self):
        from annotations import load_report
        from discovery import discover
        text=r'说明\P未注明内容'
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'report.txt'
            p.write_text('DWG="D.dwg"\nAcquisitionMode="ModelSpaceTopLevelAllLayers"\nModelSpaceTopLevel="included"\nNestedBlocks="not expanded"\nEntityHandle="M"\nDXF_Type="MTEXT"\nText_RAW='+json.dumps(text,ensure_ascii=False)+'\n',encoding='utf-8')
            c=load_report(p,'P');a=c['annotations'][0];self.assertEqual(a['decoded_text'],text)
            self.assertEqual(len(a['mtext_structure']['paragraphs']),2)
            before=copy.deepcopy(c);result=discover(c);self.assertEqual(c,before)
            self.assertEqual(result['bindings'],[]);self.assertEqual(result['propagation_roots'],[])
            self.assertEqual(len(result['mtext_structures']),1)
            for e in result['evidence']:self.assertIsNone(e['scope_candidate'])


if __name__=='__main__':unittest.main()
