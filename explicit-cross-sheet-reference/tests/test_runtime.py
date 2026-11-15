import importlib.util,json,hashlib,tempfile,unittest,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'explicit-cross-sheet-reference'))
spec=importlib.util.spec_from_file_location('reference_runtime',ROOT/'explicit-cross-sheet-reference/resolve.py')
entry=importlib.util.module_from_spec(spec);spec.loader.exec_module(entry)
from registry import build_registry
from report_manifest import write_manifest

class RuntimeTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);p=Path(self.tmp.name);self.inputs=[]
  for i,text in enumerate(['详见 E-101','图号: E-101']):
   report=p/(str(i)+'.txt');manifest=p/(str(i)+'.json')
   report.write_text('DWG="'+str(i)+'.dwg"\nExtractorVersion="2.4-leader-evidence-v1"\nAcquisitionMode="ModelSpaceTopLevelAllLayers"\nModelSpaceTopLevel="included"\nNestedBlocks="not expanded"\nEntityHandle=A\nDXF_Type="TEXT"\nText_RAW='+json.dumps(text,ensure_ascii=False)+'\nReadErrorCount=0\nEND_OF_REPORT: scan finished. Inspect errors and scope limitations before interpreting results.',encoding='utf-8')
   write_manifest(report,manifest,encoding='utf-8');self.inputs.append({'report_path':str(report),'manifest_path':str(manifest)})
  registry=build_registry('P',self.inputs);rp=p/'registry.json';rp.write_text(json.dumps(registry),encoding='utf-8')
  self.mapping={'project_id':'P','registry_path':str(rp),'registry_sha256':hashlib.sha256(rp.read_bytes()).hexdigest(),'inputs':self.inputs}
 def test_runtime_positive(self):self.assertEqual(entry.run(self.mapping)['summary']['partial_resolutions'],1)
 def test_manifest_tamper(self):
  Path(self.inputs[0]['report_path']).write_text('tampered')
  with self.assertRaises(ValueError):entry.run(self.mapping)
 def test_registry_pin(self):
  self.mapping['registry_sha256']='f'*64
  with self.assertRaises(ValueError):entry.run(self.mapping)
 def test_runtime_project(self):
  self.mapping['project_id']='Q'
  with self.assertRaises(ValueError):entry.run(self.mapping)
 def test_empty_inputs(self):
  self.mapping['inputs']=[]
  with self.assertRaises(ValueError):entry.run(self.mapping)
 def test_no_writes(self):
  before={p:p.read_bytes() for p in Path(self.tmp.name).iterdir()};entry.run(self.mapping)
  self.assertEqual(before,{p:p.read_bytes() for p in Path(self.tmp.name).iterdir()})

if __name__=='__main__':unittest.main()
