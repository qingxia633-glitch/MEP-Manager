"""Admission tests on synthetic native records; independent of private project artifacts."""
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import resolve
from report_manifest import write_manifest


class Inputs(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.report = root / "report.txt"
        dwg = root / "x.dwg"
        dwg.write_bytes(b'synthetic-test')
        header = (f'DWG="{dwg}"\nExtractorVersion="2.8-field-graph-evidence-v1"\n'
                  'AcquisitionMode="ModelSpaceTopLevelAllLayers"\nModelSpaceTopLevel="included"\n'
                  'NestedBlocks="not expanded"\nAllLayers="included"\nSelectedEntityTotal=1\n')
        self.content = (header + 'EntityHandle="A"\nDXF_Type="INSERT"\nBlockName="test"\n'
                        'ReadErrorCount=0\nEND_OF_REPORT: synthetic\n')
        self.report.write_text(self.content, encoding="utf-8-sig")
        manifest = root / "manifest.json"
        write_manifest(self.report, manifest)
        self.spec = dict(report=self.report, manifest=manifest, sha256=resolve.digest(self.report),
                         dwg=dwg, dwg_sha256=resolve.digest(dwg))

    def test_missing_dynamic_is_unknown(self):
        found = resolve.drawing_symbols(self.spec,"project",["A"])
        self.assertIsNone(found["A"]["dynamic"])
        self.assertNotIn("definition", found["A"])

    def test_tampered_report(self):
        self.report.write_text(self.content+" ", encoding="utf-8-sig")
        with self.assertRaisesRegex(ValueError,"manifest mismatch"):
            resolve.drawing_symbols(self.spec,"p",["A"])

    def test_dwg_pin(self):
        self.spec["dwg"].write_bytes(b'another drawing')
        with self.assertRaisesRegex(ValueError,"version pin"):
            resolve.drawing_symbols(self.spec,"p",["A"])

    def test_duplicate_handle_not_selected(self):
        self.report.write_text(self.content.replace('ReadErrorCount','EntityHandle="A"\nReadErrorCount'),encoding="utf-8-sig")
        new = self.report.with_suffix(".json")
        write_manifest(self.report,new)
        self.spec.update(manifest=new,sha256=resolve.digest(self.report))
        with self.assertRaises(ValueError):
            resolve.drawing_symbols(self.spec,"p",["A"])

    def test_absent_handle(self):
        with self.assertRaisesRegex(ValueError,"missing"):
            resolve.drawing_symbols(self.spec,"p",["B"])
