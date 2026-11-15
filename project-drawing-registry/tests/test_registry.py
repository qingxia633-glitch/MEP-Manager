import sys, unittest, tempfile, json, hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from registry import build_registry, lookup, content_hash

class RegistryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
 def source(self,name='a',drawing='a.dwg',text='图号: E-01',version='2.8-field-graph-evidence-v1',**extra):
  p=self.root/(name+'.txt')
  p.write_text('DWG="'+drawing+'"\nExtractorVersion="'+version+'"\nAcquisitionMode="ModelSpaceTopLevelAllLayers"\nModelSpaceTopLevel="included"\nNestedBlocks="not expanded"\nAllLayers="included; including off/frozen"\nXrefContents="not expanded"\nPaperSpaceLayouts="not included"\nEntityHandle=AB\nDXF_Type="TEXT"\nText_RAW='+json.dumps(text,ensure_ascii=False)+'\nReadErrorCount=0\nEND_OF_REPORT: scan finished. Inspect errors and scope limitations before interpreting results.',encoding='utf-8')
  return dict(report_path=str(p),encoding='utf-8',**extra)
 def build(self,*inputs,project='P'):return build_registry(project,list(inputs))
 def test_project_required(self):
  with self.assertRaises(ValueError):self.build(self.source(),project='')
 def test_two_drawings(self):self.assertEqual(self.build(self.source(),self.source('b','b.dwg'))['summary']['drawing_instance_count'],2)
 def test_dedup(self):
  a=self.source();self.assertEqual(self.build(a,a),self.build(a))
 def test_revision(self):self.assertEqual(self.build(self.source(source_dwg_sha256='a'*64),self.source('b',source_dwg_sha256='b'*64))['summary']['drawing_instance_count'],2)
 def test_number_ambiguous(self):self.assertEqual(lookup(self.build(self.source(),self.source('b','b.dwg')),'E-01')['lookup_status'],'ambiguous')
 def test_projects_isolated(self):
  a=self.source();self.assertNotEqual(self.build(a)['drawing_instances'][0]['instance_id'],self.build(a,project='Q')['drawing_instances'][0]['instance_id'])
 def test_same_bytes_different_names(self):self.assertEqual(self.build(self.source(source_dwg_sha256='a'*64),self.source('b','b.dwg',source_dwg_sha256='a'*64))['summary']['drawing_instance_count'],2)
 def test_missing_dwg(self):
  d=self.build(self.source())['drawing_instances'][0];self.assertIsNone(d['source_dwg_sha256']);self.assertEqual(d['source_dwg_hash_status'],'unavailable')
 def test_heterogeneous(self):self.assertEqual(len(self.build(self.source(version='2.4-leader-evidence-v1'),self.source('b','b.dwg'))['summary']['report_version_distribution']),2)
 def test_layout_unknown(self):self.assertEqual(self.build(self.source())['drawing_instances'][0]['layout_status'],'unresolved_out_of_scope')
 def test_filename_not_title(self):self.assertFalse(any(a['kind']=='drawing_title_candidate' for a in self.build(self.source(text='nothing'))['aliases']))
 def test_candidate_not_logical(self):self.assertEqual(self.build(self.source())['drawing_instances'][0]['logical_identity_status'],'unresolved')
 def test_lookup_zero_one(self):
  r=self.build(self.source());self.assertEqual(lookup(r,'absent')['lookup_status'],'not_found');self.assertEqual(lookup(r,'a')['lookup_status'],'matched')
 def test_order_hash(self):
  a,b=self.source(),self.source('b','b.dwg');self.assertEqual(content_hash(self.build(a,b)),content_hash(self.build(b,a)))
 def test_no_semantics(self):
  r=self.build(self.source(text='S'));self.assertFalse({'bindings','quantity','system_identity'} & set(r))
 def test_bad_hash(self):
  with self.assertRaises(ValueError):self.build(self.source(source_dwg_sha256='bad'))
 def test_unknown_version(self):
  with self.assertRaises(ValueError):self.build(self.source(version='99'))
 def test_manifest_mismatch(self):
  a=self.source();m=self.root/'manifest.json';m.write_text('{}');a['manifest_path']=str(m)
  with self.assertRaises((ValueError,KeyError)):self.build(a)
 def test_no_proximity_label(self):self.assertEqual(lookup(self.build(self.source(text='图号 E-01')),'E-01')['lookup_status'],'not_found')
 def test_full_source_path_distinct(self):self.assertEqual(self.build(self.source(drawing='one/a.dwg'),self.source('b','two/a.dwg'))['summary']['drawing_instance_count'],2)
 def test_unverified_status(self):self.assertEqual(self.build(self.source())['drawing_instances'][0]['registry_status'],'partial')
 def test_verified_manifest(self):
  from report_manifest import write_manifest
  a=self.source();m=self.root/'m.json';write_manifest(a['report_path'],m,encoding='utf-8');a['manifest_path']=str(m)
  self.assertEqual(self.build(a)['drawing_instances'][0]['registry_status'],'supported')
 def test_source_mismatch(self):
  a=self.source(source_dwg_sha256='a'*64);p=self.root/'x.dwg';p.write_bytes(b'synthetic');a['source_dwg_path']=str(p)
  with self.assertRaises(ValueError):self.build(a)
 def test_incomplete(self):
  a=self.source();Path(a['report_path']).write_text('DWG="a.dwg"\nExtractorVersion="2.4-leader-evidence-v1"')
  with self.assertRaises(ValueError):self.build(a)
 def test_title_remains_partial(self):
  r=self.build(self.source(text='图名：Example'));a=next(a for a in r['aliases'] if a['kind']=='drawing_title_candidate');self.assertEqual(a['status'],'partial')
 def test_input_unchanged(self):
  a=self.source();before=Path(a['report_path']).read_bytes();self.build(a);self.assertEqual(before,Path(a['report_path']).read_bytes())
 def test_attribute_tag_candidate(self):
  a=self.source(text='none');p=Path(a['report_path']);s=p.read_text(encoding='utf-8');s=s.replace('DXF_Type="TEXT"\nText_RAW="none"','DXF_Type="INSERT"\nAttributeTag="图号"\nAttributeText_RAW="E-02"\nAttribute_DXF=((5 . "AC"))')
  p.write_text(s,encoding='utf-8');r=self.build(a);self.assertEqual(lookup(r,'E-02')['match_count'],1)
 def test_directory_label_not_identity(self):
  q=lookup(self.build(self.source()),'E-01');self.assertFalse(q['logical_identity_approved']);self.assertEqual(q['match_evidence'][0]['identifies_current_drawing'],'unresolved')

if __name__=='__main__':unittest.main()
