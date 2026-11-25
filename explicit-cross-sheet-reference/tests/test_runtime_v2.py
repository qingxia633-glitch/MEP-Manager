import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'explicit-cross-sheet-reference'),str(ROOT/'project-drawing-registry'),str(ROOT/'project-evidence-discovery')]
spec=importlib.util.spec_from_file_location('cross_sheet_runtime_v2',ROOT/'explicit-cross-sheet-reference/resolve_v2.py')
entry=importlib.util.module_from_spec(spec);spec.loader.exec_module(entry)
from registry_v2 import build_registry
from report_manifest import write_manifest


class RuntimeV2Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        inputs=[]
        for i,text in enumerate(['详见 E-101','图号: E-101']):
            p=self.root/(str(i)+'.txt');m=self.root/(str(i)+'.json')
            p.write_text('DWG="'+str(i)+'.dwg"\nExtractorVersion="2.4-leader-evidence-v1"\nAcquisitionMode="ModelSpaceTopLevelAllLayers"\nModelSpaceTopLevel="included"\nNestedBlocks="not expanded"\nEntityHandle=A\nDXF_Type="TEXT"\nText_RAW='+json.dumps(text,ensure_ascii=False)+'\nReadErrorCount=0\nEND_OF_REPORT: scan finished. Inspect errors and scope limitations before interpreting results.',encoding='utf-8')
            write_manifest(p,m,encoding='utf-8');inputs.append({'report_path':str(p),'manifest_path':str(m)})
        r=build_registry('P',inputs);rp=self.root/'registry.json';rp.write_text(json.dumps(r),encoding='utf-8')
        self.mapping={'project_id':'P','registry_path':str(rp),'registry_sha256':hashlib.sha256(rp.read_bytes()).hexdigest(),'inputs':inputs}

    def test_real_adapter_entry(self):
        before={p:p.read_bytes() for p in self.root.iterdir()}
        r=entry.run(self.mapping);self.assertEqual(r['summary']['candidate'],1)
        self.assertEqual(r['resolutions'][0]['target_candidates'][0]['target_kind'],'drawing_instance')
        self.assertEqual(before,{p:p.read_bytes() for p in self.root.iterdir()})

    def test_bad_registry_pin(self):
        self.mapping['registry_sha256']='0'*64
        with self.assertRaises(ValueError):entry.run(self.mapping)

    def test_bad_report_bytes(self):
        Path(self.mapping['inputs'][0]['report_path']).write_text('changed')
        with self.assertRaises(ValueError):entry.run(self.mapping)

    def test_wrong_project(self):
        self.mapping['project_id']='Q'
        with self.assertRaises(ValueError):entry.run(self.mapping)

    def test_v1_with_recomputed_hash_rejected(self):
        p=Path(self.mapping['registry_path']);v=json.loads(p.read_text());p.write_text(json.dumps(v['source_registry_v1']))
        self.mapping['registry_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
        with self.assertRaises(ValueError):entry.run(self.mapping)

    def test_empty_inputs(self):
        self.mapping['inputs']=[]
        with self.assertRaises(ValueError):entry.run(self.mapping)

if __name__=='__main__':unittest.main()
