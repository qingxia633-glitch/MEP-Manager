"""Direct Builder correction-root contract; synthetic evidence only."""
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'post-hardening-pass4'))
from synthetic_contract import plan, cite_synthetic, previous

PATH = '/corrections_applied/evidence'


def corrected_plan():
    p = plan()
    correction = dict(correction_id='synthetic-correction', status='approved',
        target_object_ids=[p['object_id']], edge_handle=p['binding']['edge_handle'],
        historical_value='synthetic-old-drawing', corrected_value=p['binding']['drawing_ref'])
    cite_synthetic(p, correction, PATH)
    p['corrections_applied'] = dict(evidence=correction, changed_paths=['/binding/drawing_ref'])
    return reseal(p)


def reseal(p):
    correction = p['corrections_applied'].get('evidence')
    if isinstance(correction, dict): previous.seal(correction)
    return previous.seal(p)


class CorrectionRoot(unittest.TestCase):
    def setUp(self): self.builder = previous.load('design-net-quantity','builder.py')
    def reject(self, p):
        p = reseal(p); before = copy.deepcopy(p)
        r = self.builder.build(p, [])
        self.assertEqual(r['status'], 'contract_violation', r)
        self.assertNotIn('quantity', r)
        self.assertEqual(p, before)
    def test_missing_provenance(self):
        p=corrected_plan();p['corrections_applied']['evidence'].pop('provenance')
        # Remove now-unused index entry as well: reject the missing root, not an orphan hash.
        p['source_evidence_hashes'].pop('synthetic:'+PATH)
        p['provenance']=copy.deepcopy(p['source_evidence_hashes'])
        self.reject(p)
    def test_empty_record(self):
        p=corrected_plan();p['corrections_applied']['evidence']['provenance']=[{}];self.reject(p)
    def test_foreign_identity(self):
        p=corrected_plan();p['corrections_applied']['evidence']['provenance'][0]['object_identity']['parent_path']=['FOREIGN'];self.reject(p)
    def test_unresolved(self):
        p=corrected_plan();p['corrections_applied']['evidence']['provenance'][0]['status']='unresolved';self.reject(p)
    def test_source_mismatch(self):
        p=corrected_plan();p['corrections_applied']['evidence']['provenance'][0]['source_id']='missing-source';self.reject(p)
    def test_hash_mismatch(self):
        p=corrected_plan();p['corrections_applied']['evidence']['provenance'][0]['sha256']='0'*64;self.reject(p)
    def test_ref_mismatch(self):
        p=corrected_plan();p['corrections_applied']['evidence']['provenance'][0]['evidence_ref']='/base_path';self.reject(p)
    def test_valid_build(self):
        p=corrected_plan();before=copy.deepcopy(p);r=self.builder.build(p,[])
        self.assertEqual(r['status'],'built',r);self.assertEqual(p,before)
        self.assertEqual(r['quantity']['computed_quantity']['exact_value'],'10.5')
    def test_native_replay_changed_provenance(self):
        p=corrected_plan();q=self.builder.build(p,[])['quantity']
        self.assertEqual(self.builder.replay_validate(p,q)['status'],'replay_matched')
        p['corrections_applied']['evidence']['provenance'][0]['pointer']='/different-approved-record'
        r=self.builder.replay_validate(reseal(p),q)
        self.assertEqual(r['status'],'replay_mismatch',r);self.assertTrue(r['numeric_match'])
    def test_absent_correction_allowed(self):
        p=plan();self.assertEqual(self.builder.build(p,[])['status'],'built')
    def test_empty_correction_object_rejected(self):
        p=plan();p['corrections_applied']['evidence']={};self.reject(p)


if __name__=='__main__': unittest.main()
