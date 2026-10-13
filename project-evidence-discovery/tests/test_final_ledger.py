import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import legacy_failure_checker as checker

class FinalLedger(unittest.TestCase):
 def inputs(self):
  return ({'cases':[{'test_id':'t','raw_status':'error','traceback':"    x=r['bindings'][0]\nIndexError: list index out of range"}]},
          {'version':'2','failures':[{'test_id':'t','category':'A','classification':'intentional_legacy_rejection','normalized_reason':'binding_candidate_absent'}]})
 def test_matching_reason(self):
  self.assertTrue(checker.check_current(*self.inputs())['accepted'])
 def test_changed_reason_same_id(self):
  r,l=self.inputs();r['cases'][0]['traceback']='RuntimeError: unrelated defect'
  self.assertFalse(checker.check_current(r,l)['accepted'])
 def test_v2_existing_api_checks_reason(self):
  r,l=self.inputs();r['cases'][0]['traceback']='RuntimeError: unrelated defect'
  self.assertFalse(checker.check(r,l)['accepted'])
 def test_other_index_error(self):
  r,l=self.inputs();r['cases'][0]['traceback']='    x=other[0]\nIndexError: list index out of range'
  self.assertFalse(checker.check_current(r,l)['accepted'])
 def test_category_mismatch(self):
  r,l=self.inputs();l['failures'][0]['classification']='legacy_fixture_missing_current_contract_fields'
  self.assertFalse(checker.check_current(r,l)['accepted'])
 def test_category_missing(self):
  r,l=self.inputs();l['failures'][0].pop('category');l['failures'][0].pop('classification')
  self.assertFalse(checker.check_current(r,l)['accepted'])
 def test_unexpected_pass(self):
  r,l=self.inputs();r['cases'][0]['raw_status']='passed';self.assertFalse(checker.check_current(r,l)['accepted'])
 def test_unknown_failure(self):
  r,l=self.inputs();r['cases'].append({'test_id':'other','raw_status':'failure','traceback':'AssertionError'})
  self.assertFalse(checker.check_current(r,l)['accepted'])
 def test_legacy_id_only_not_current(self):
  r,l=self.inputs();l['version']='1';self.assertFalse(checker.check_current(r,l)['accepted'])
