"""Read-only checks using excluded project sources; no new quantity issuance."""
import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from source_adapter import ROOT, OUT, read, pointer
from synthetic_contract import previous


class PrivateSources(unittest.TestCase):
    def test_source_backed_replay(self):
        m=previous.load('design-net-quantity','builder.py');migration=previous.load('contract-migration/tests','test_migration.py')
        for kind in ('conduit','wire'):
            p=read(OUT/('golden-'+kind+'-profile1.json'))['fixture']
            r=m.replay_validate(p,migration.frozen(kind))
            self.assertEqual(r['status'],'replay_value_matched_legacy_evidence_incomplete',r)
            self.assertEqual(r['quantity']['computed_quantity']['exact_value'],'7.77128331912231535912969050917979628')
            self.assertEqual(r['quantity']['computed_quantity']['reported_value'],'7.771283319')
            self.assertEqual(p['multiplier']['value'],1)
            self.assertEqual(m.replay_validate(p,r['quantity'])['status'],'replay_matched')
    def test_every_source_hash_pointer(self):
        for kind in ('conduit','wire'):
            wrapper=read(OUT/('golden-'+kind+'-profile1.json'));self.assertFalse(wrapper['historical_files_modified'])
            for change in wrapper['changes']:
                self.assertTrue(change['source_evidence'])
                for ref in change['source_evidence']:
                    f=ROOT/ref['path'];self.assertEqual(hashlib.sha256(f.read_bytes()).hexdigest(),ref['sha256']);pointer(read(f),ref['pointer'])
    def test_old_plan_not_implicitly_upgraded(self):
        m=previous.load('design-net-quantity','builder.py')
        for kind in ('conduit','wire'):
            p=read(ROOT/('outputs/post-hardening-pass3-20261008/golden-'+kind+'-v03.json'))['fixture']
            self.assertEqual(m.build(p,[])['status'],'contract_violation')
    def test_real_report(self):
        prior=previous.load('post-hardening-pass2','current_contract_checks.py')
        prior.CurrentContract('test_actual_report_load_discover_owner_identity').test_actual_report_load_discover_owner_identity()
