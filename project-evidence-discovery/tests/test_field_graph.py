"""Synthetic graph observations: not project approval or host acquisition."""
import copy
import json
import sys
import unittest
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from field_graph import graph_record

I = {'project_id':'P','drawing_ref':'D','snapshot_id':'a'*64,
     'table_handle':'AA','parent_path':[],'row_index':0,'column_index':0}

def node(h='A', children=(), code='value', **changes):
    n={'Handle':h,'Type':'ACAD_FIELD','Code':code,'CodeStatus':'read',
       'Evaluator':'_text','ChildCount':len(children),'Child':list(children),
       'ReferenceCount':0,'Reference':[],'Status':'read'}
    n.update(changes)
    return n

def raw(nodes, **changes):
    h={'FieldGraphVersion':'1','FieldGraph.Root':'A','FieldGraph.Status':'read'}
    h.update(changes)
    text=''.join(k+'='+json.dumps(v)+'\n' for k,v in h.items())
    for n in nodes:
        text+='FieldNode_BEGIN\n'
        for k,v in n.items():
            for val in (v if isinstance(v,list) else [v]):
                text+='Node.'+k+'='+json.dumps(val)+'\n'
        text+='FieldNode_END\n'
    return text

def resolve(nodes, **kw):return graph_record(raw(nodes,**kw),I,[])

class GraphTests(unittest.TestCase):
    def test_one_child(self):
        g=resolve([node(children=['B'],code='%<\\_FldIdx 0>%'),node('B')])
        self.assertTrue(g['graph_complete']);self.assertEqual(g['edges'][0]['child_index'],0)
        self.assertEqual(g['nodes'][0]['child_index_references'][0]['status'],'child_reference_resolved')
    def test_multiple(self):self.assertTrue(resolve([node(children=['B','C']),node('B'),node('C')])['graph_complete'])
    def test_nested(self):
        g=resolve([node(children=['B']),node('B',['C']),node('C')])
        self.assertEqual(g['maximum_depth'],2);self.assertTrue(g['graph_complete'])
    def test_count(self):self.assertFalse(resolve([node(ChildCount=1)])['graph_complete'])
    def test_missing_id(self):self.assertFalse(resolve([node(children=[''])])['graph_complete'])
    def test_missing_object(self):self.assertFalse(resolve([node(children=['B'])])['graph_complete'])
    def test_wrong_type(self):self.assertFalse(resolve([node(Type='LINE')])['graph_complete'])
    def test_cycle(self):self.assertFalse(resolve([node(children=['B']),node('B',['A'])])['graph_complete'])
    def test_duplicate(self):self.assertFalse(resolve([node(),node()])['graph_complete'])
    def test_duplicate_child(self):self.assertFalse(resolve([node(children=['B','B']),node('B')])['graph_complete'])
    def test_limit(self):
        nodes=[node(format(i,'X'),[format(i+1,'X')]) for i in range(10,28)]+[node('1C')]
        self.assertFalse(resolve(nodes)['graph_complete'])
    def test_index_without_child(self):self.assertFalse(resolve([node(code='%<\\_FldIdx 0>%')])['graph_complete'])
    def test_old_missing(self):
        g=graph_record('FieldEvidenceVersion="1"\nField.Code.Value="root"',I,[])
        self.assertFalse(g['graph_complete']);self.assertEqual(g['nodes'],[])
    def test_references(self):
        g=resolve([node(ReferenceCount=2,Reference=['D','E'])])
        self.assertTrue(g['graph_complete']);self.assertEqual(len(g['object_references']),2)
        self.assertIsNone(g['object_references'][0]['target_identity']['parent_path'])
    def test_reference_count(self):self.assertFalse(resolve([node(ReferenceCount=1)])['graph_complete'])
    def test_malformed(self):self.assertFalse(resolve([node(ChildCount='oops')])['graph_complete'])
    def test_missing_evaluator(self):self.assertFalse(resolve([node(Evaluator=None)])['graph_complete'])
    def test_no_static_or_semantics(self):
        g=resolve([node()]);self.assertFalse(set(g)&{'bindings','scope','quantity','authored_static_text'})
    def test_identity_and_input(self):
        before=copy.deepcopy(I);g=resolve([node()]);self.assertEqual(I,before)
        self.assertEqual(g['nodes'][0]['identity']['carrier_identity'],I)
    def test_foreign_identity(self):self.assertFalse(graph_record(raw([node()]),{},[])['graph_complete'])
    def test_unreachable(self):self.assertFalse(resolve([node(),node('B')])['graph_complete'])
    def test_export_truncated(self):self.assertFalse(resolve([node()],**{'FieldGraph.Status':'partial'})['graph_complete'])
    def test_v2_carrier_adapter(self):
        from field_provenance import field_record
        s='FieldEvidenceVersion="2"\nField.CarrierHandle="AA"\nField.Code.Status="read"\nField.Code.Source="entget"\nField.Code.Value="root"\n'+raw([node()])
        x=field_record(s,I,'TABLE_CELL','shown','read',[],'2.8-field-graph-evidence-v1',True)
        self.assertTrue(x['field_graph']['graph_complete'])
        self.assertEqual(x['displayed_value'],'shown');self.assertFalse(x['authored_static_text_established'])
        y=field_record(s,dict(I,table_handle='BB'),'TABLE_CELL','shown','read',[],'2.8-field-graph-evidence-v1',True)
        self.assertFalse(y['field_graph']['graph_complete'])
    def test_v1_cannot_claim_graph(self):
        from field_provenance import field_record
        s='FieldEvidenceVersion="1"\nField.CarrierHandle="AA"\n'+raw([node()])
        self.assertFalse(field_record(s,I,'TABLE_CELL','V','read',[],'2.7-field-provenance-v1',True)['field_graph']['graph_complete'])
    def test_text_root_preserved_when_getter_unavailable(self):
        from field_provenance import field_record
        s='FieldEvidenceVersion="2"\nField.CarrierHandle="AA"\nField.Code.Status="unavailable"\n'+raw([node()])
        x=field_record(s,dict(I,handle='AA'),'TEXT','shown','read',[],'2.8-field-graph-evidence-v1')
        self.assertIsNotNone(x);self.assertEqual(x['field_code_status'],'unavailable')
        self.assertEqual(len(x['field_graph']['nodes']),1)
    def test_envelope_truncated(self):
        self.assertFalse(graph_record(raw([node()]).replace('FieldNode_END',''),I,[])['graph_complete'])
    def test_duplicate_root(self):
        self.assertFalse(graph_record(raw([node()])+'FieldGraph.Root="A"\n',I,[])['graph_complete'])
    def test_report_adapter_discovery_collection(self):
        from test_table_evidence import report,cell
        from annotations import load_report
        from discovery import discover
        graph='FieldEvidenceVersion="2"\nField.CarrierHandle="AA"\n'+raw([node(children=['B']),node('B')])
        content=cell(content=2).replace('TableCell_END',graph+'TableCell_END')
        r='DWG="D"\nExtractorVersion="2.8-field-graph-evidence-v1"\nAcquisitionMode="ModelSpaceTopLevelAllLayers"\nModelSpaceTopLevel="included"\nNestedBlocks="not expanded"\nEntityHandle="AA"\nDXF_Type="ACAD_TABLE"\n'+report(content)
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'r.txt';p.write_text(r,encoding='utf-8')
            c=load_report(p,'P');self.assertTrue(c['field_evidence'][0]['field_graph']['graph_complete'])
            d=discover(c);self.assertEqual(d['bindings'],[]);self.assertEqual(d['propagation_roots'],[])
            self.assertEqual(d['field_evidence'],c['field_evidence'])

if __name__=='__main__':unittest.main()
