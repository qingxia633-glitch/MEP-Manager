import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from run import freeze, qualify
from recognition import load_symbols


class FreezeTests(unittest.TestCase):
    def test_changed_prediction_cannot_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/"prediction.json"
            freeze(file,{"b":1,"a":2})
            first=file.read_bytes()
            freeze(file,{"a":2,"b":1})
            with self.assertRaises(ValueError):
                freeze(file,{"a":3})
            self.assertEqual(file.read_bytes(),first)

    def test_changed_manifest_blocks_before_probe(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest=Path(tmp)/"manifest.json"
            manifest.write_text("{}",encoding="utf8")
            with self.assertRaisesRegex(ValueError,"manifest changed"):
                load_symbols({"manifest":manifest,"manifest_sha256":"other"},"project",[])

    def test_modified_blank_pack_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in ("scope.json","review-pack.md"):
                (root/name).write_bytes(b"{}")
            digest=hashlib.sha256(b"{}").hexdigest()
            pins=dict(plan={},scope_sha256=digest,review_pack_sha256=digest)
            source=dict(path=root/"scope.json",sha256=digest)
            (root/"review-pack.md").write_text("already contains predictions",encoding="utf8")
            with self.assertRaisesRegex(ValueError,"pin mismatch"):
                qualify(pins,dict(registry=source,unit_source=source),root)
