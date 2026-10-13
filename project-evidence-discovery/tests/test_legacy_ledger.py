import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legacy_failure_checker import check

class LedgerChecks(unittest.TestCase):
 def test_registered_failure(self):
  self.assertTrue(check({'cases':[{'test_id':'a','raw_status':'failure'}]}, {'failures':[{'test_id':'a','category':'A'}]})['accepted'])
 def test_unknown_failure(self):
  self.assertFalse(check({'cases':[{'test_id':'b','raw_status':'failure'}]}, {'failures':[{'test_id':'a','category':'A'}]})['accepted'])
 def test_unexpected_pass(self):
  r=check({'cases':[{'test_id':'a','raw_status':'passed'}]}, {'failures':[{'test_id':'a','category':'A'}]})
  self.assertFalse(r['accepted']);self.assertEqual(r['registered_outcome_changed'],['a'])
 def test_missing_or_skipped(self):
  for cases in ([],[{'test_id':'a','raw_status':'skipped'}]):
   self.assertFalse(check({'cases':cases},{'failures':[{'test_id':'a'}]})['accepted'])
