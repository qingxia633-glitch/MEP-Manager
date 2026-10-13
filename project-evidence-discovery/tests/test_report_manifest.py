import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from report_manifest import write_manifest

class ReportManifestTests(unittest.TestCase):
 def test_exact_bytes_separate_manifest_and_no_overwrite(self):
  with tempfile.TemporaryDirectory() as tmp:
   source=Path(tmp)/'report.txt';dest=Path(tmp)/'manifest.json'
   raw='DWG="独立验证.dwg"\n'.encode('utf-8');source.write_bytes(raw)
   result=write_manifest(source,dest)
   self.assertEqual(result['report_sha256'],hashlib.sha256(raw).hexdigest())
   self.assertEqual(source.read_bytes(),raw)
   self.assertEqual(json.loads(dest.read_text(encoding='utf-8')),result)
   with self.assertRaises(FileExistsError):write_manifest(source,dest)
 def test_wrong_encoding_fails_without_manifest(self):
  with tempfile.TemporaryDirectory() as tmp:
   source=Path(tmp)/'report.txt';dest=Path(tmp)/'manifest.json'
   source.write_bytes('中文'.encode('cp936'))
   with self.assertRaises(UnicodeDecodeError):write_manifest(source,dest)
   self.assertFalse(dest.exists())
