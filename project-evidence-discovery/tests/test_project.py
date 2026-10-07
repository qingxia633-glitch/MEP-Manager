import hashlib,json,sys,unittest
from pathlib import Path
MODULE=Path(__file__).resolve().parents[1];ROOT=MODULE.parent
sys.path.insert(0,str(MODULE))
from annotations import load_report,corrected_reference
from discovery import discover

class ProjectTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.config=json.loads((MODULE/'fixtures/project-sources.json').read_text(encoding='utf-8'))
  cls.context=load_report(ROOT/cls.config['snapshots'][0])
  cls.result=discover(cls.context,.001,1000)
 def test_jdg25_51B44(self):self.check_negative('51B44','JDG25,余同')
 def test_jdg25_51AA5(self):self.check_negative('51AA5','JDG25,余同')
 def check_negative(self,h,raw):
  e=next(e for e in self.result['evidence'] if e['source_handle']==h)
  self.assertEqual(e['raw_text'],raw)
  self.assertFalse(any(b['annotation_handle']==h for b in self.result['bindings']))
  self.assertEqual(e['propagation_candidate']['root_status'],'unresolved')
 def test_sd_518D4(self):
  e=next(e for e in self.result['evidence'] if e['source_handle']=='518D4')
  self.assertEqual(e['line_codes'],['S+D'])
  self.assertFalse(any(b['annotation_handle']=='518D4' for b in self.result['bindings']))
 def test_shadow_13C9D(self):self.assert_no_direct('13C9D')
 def test_shadow_13CC7(self):self.assert_no_direct('13CC7')
 def test_shadow_13CC9(self):self.assert_no_direct('13CC9')
 def assert_no_direct(self,h):self.assertEqual(self.result['edge_summaries'][h]['direct_binding_count'],0)
 def test_golden_not_hardcoded(self):self.assert_no_direct('13CF5')
 def test_real_unicode(self):
  self.assertEqual(self.result['source_drawing'],'EX-BX地下车库火灾报警平面图_t8_t3.dwg')
  self.assertNotIn('?',self.result['source_drawing'])
 def test_real_correction_provenance(self):
  p=ROOT/self.config['correction_evidence'];c=json.loads(p.read_text(encoding='utf-8'))
  self.assertEqual(hashlib.sha256((ROOT/c['source_artifact']).read_bytes()).hexdigest(),c['source_artifact_sha256'])
  value,refs=corrected_reference(c['historical_value'],c['target_object_ids'][0],[c])
  self.assertEqual(value,self.result['source_drawing']);self.assertEqual(refs,[c['correction_id']])
 def test_golden_reference_type(self):
  b=json.loads((ROOT/self.config['historical_reference']).read_text(encoding='utf-8'))
  self.assertTrue(any(e['evidence_type']=='reviewed_project_rule' for e in b['evidence']))
  self.assertTrue(any(x['edge_handle']=='13CF5' for x in b['bindings']))

if __name__=='__main__':unittest.main()
