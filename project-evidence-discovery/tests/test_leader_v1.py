"""Versioned acquisition -> adapter -> candidate adversaries, no semantic approval."""
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from annotations import load_report
from discovery import discover
from report_manifest import write_manifest

HEADER='''DWG="synthetic-leader.dwg"
AcquisitionMode="ModelSpaceTopLevelAllLayers"
ModelSpaceTopLevel="included"
NestedBlocks="not expanded"
EntityHandle="A1"
DXF_Type="MTEXT"
Text_RAW="S"
Insertion_WCS=(5 5 0)
EntityHandle="E1"
DXF_Type="LINE"
Start_WCS=(0 0 0)
End_WCS=(10 0 0)
EntityHandle="L1"
DXF_Type="LEADER"
'''
BODY='''LeaderEvidenceVersion="1"
LeaderScope="ModelSpace top-level only"
LeaderParentPath="[]"
LeaderCoordinateSystem="WCS"
LeaderGeometryStatus="read"
LeaderArrowStatus="read"
LeaderAnnotationStatus="resolved"
AnnotationHandle="A1"
AnnotationType="MTEXT"
LeaderVertexCount=2
Arrow_WCS=(5 0 0)
LeaderVertex_WCS=(5 0 0)
LeaderVertex_WCS=(5 5 0)
'''

class LeaderV1(unittest.TestCase):
 def load(self,body=BODY,header=HEADER):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'report.txt';p.write_text(header+body,encoding='utf-8');return load_report(p,'synthetic-project')
 def test_classic_explicit_chain(self):
  c=self.load();l=c['leaders'][0];self.assertEqual(l['evidence_version'],'1');self.assertEqual(l['parent_path'],[])
  self.assertEqual(discover(c)['bindings'][0]['target_id'],'E1')
 def test_failed_geometry_not_admitted(self):
  self.assertFalse(discover(self.load(BODY.replace('LeaderGeometryStatus="read"','LeaderGeometryStatus="unresolved"')))['bindings'])
 def test_failed_annotation_not_admitted(self):
  self.assertFalse(discover(self.load(BODY.replace('LeaderAnnotationStatus="resolved"','LeaderAnnotationStatus="unresolved"')))['bindings'])
 def test_outside_scope_not_admitted(self):
  self.assertFalse(discover(self.load(BODY.replace('ModelSpace top-level only','PaperSpace')))['bindings'])
 def test_header_missing_not_top_level(self):
  self.assertFalse(discover(self.load(header=HEADER.replace('ModelSpaceTopLevel="included"','ModelSpaceTopLevel="unknown"')))['bindings'])
 def test_foreign_parent_not_admitted(self):
  self.assertFalse(discover(self.load(BODY.replace('LeaderParentPath="[]"','LeaderParentPath="[I1]"')))['bindings'])
 def test_invalid_scope_does_not_manufacture_top_level_identity(self):
  for old,new in [('LeaderParentPath="[]"','LeaderParentPath="[I1]"'),('ModelSpace top-level only','PaperSpace')]:
   leader=self.load(BODY.replace(old,new))['leaders'][0]
   self.assertIsNone(leader['parent_path'])
 def test_vertex_count_mismatch(self):
  self.assertFalse(discover(self.load(BODY.replace('LeaderVertexCount=2','LeaderVertexCount=3')))['bindings'])
 def test_no_arrow(self):
  self.assertFalse(discover(self.load(BODY.replace('LeaderArrowStatus="read"','LeaderArrowStatus="absent"')))['bindings'])
 def test_unknown_version(self):
  self.assertFalse(discover(self.load(BODY.replace('LeaderEvidenceVersion="1"','LeaderEvidenceVersion="999"')))['bindings'])
 def test_mleader_probe_not_promoted(self):
  c=self.load(BODY+'MLeaderCapabilityStatus="partial"\nMLeaderTextString_Status="read"\nMLeaderTextString="S\\\\P中文"\n',HEADER.replace('DXF_Type="LEADER"','DXF_Type="MULTILEADER"'))
  self.assertFalse(discover(c)['bindings']);self.assertEqual(c['leaders'][0]['capability_status'],'partial')
  self.assertEqual(c['annotations'][-1]['owner_entity_handle'],'L1')
 def test_manifest_hash_not_export_self_reference(self):
  with tempfile.TemporaryDirectory() as tmp:
   report=Path(tmp)/'report.txt';sidecar=Path(tmp)/'manifest.json'
   report.write_text(HEADER+BODY,encoding='utf-8')
   raw=report.read_bytes();manifest=write_manifest(report,sidecar)
   self.assertEqual(manifest['report_sha256'],hashlib.sha256(raw).hexdigest())
   self.assertEqual(manifest['report_bytes'],len(raw))
   self.assertNotIn(manifest['report_sha256'].encode('ascii'),raw)
   self.assertEqual(report.read_bytes(),raw)

if __name__=='__main__':unittest.main()
