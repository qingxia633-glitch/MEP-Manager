"""Synthetic operator-pinned inputs. No project handles or field data."""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from decimal import Inexact, localcontext
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from route_path_gap import project
from report_manifest import write_manifest


def digest(data):
    return hashlib.sha256(data).hexdigest()


def put(path, value):
    path.write_text(json.dumps(value), encoding='utf-8')
    return digest(path.read_bytes())


class LegacyEntryPoint(unittest.TestCase):
    @unittest.skipUnless(shutil.which('pwsh'), 'requires PowerShell 7')
    def test_legacy_output_path_keeps_first_position(self):
        check = """
        $ErrorActionPreference = 'Stop'
        $entry = Get-Command ./Read-RoutePath.ps1
        $legacy = @($entry.ParameterSets | Where-Object IsDefault)
        $output = @($legacy.Parameters | Where-Object Name -eq OutputPath)
        if ($legacy.Count -ne 1 -or $legacy.Name -ne 'Legacy' -or
            $output.Count -ne 1 -or $output[0].Position -ne 0) { exit 1 }
        """
        subprocess.run(['pwsh', '-NoProfile', '-NonInteractive', '-Command', check],
                       cwd=Path(__file__).resolve().parents[1], check=True)


class ReviewedPath(unittest.TestCase):
    def setUp(self):
        work = tempfile.TemporaryDirectory()
        self.addCleanup(work.cleanup)
        self.root = Path(work.name)
        self.files = {k:self.root/k for k in ('report','manifest','assumption','unit','dwg')}
        self.files['dwg'].write_bytes(b'synthetic source')
        self.scope = dict(project_id='example',drawing='sample.dwg',drawing_instance_id='drawing-A',
                          dwg_sha256=digest(self.files['dwg'].read_bytes()),space='ModelSpace')
        self.ends = [['A', [], 'end'], ['B', [], 'start']]
        self.segments = {'A':[(0,0,0),(2,0,0)], 'B':[(6,0,0),(8,0,0)], 'C':[(4,-1,0),(4,1,0)]}
        self.prepare()

    def prepare(self):
        header = ('DWG="sample.dwg"\nExtractorVersion="2.8-field-graph-evidence-v1"\n'
                  'AcquisitionMode="ModelSpaceTopLevelAllLayers"\nModelSpaceTopLevel="included"\n'
                  'AllLayers="included"\nNestedBlocks="not expanded"\n')
        text = header
        for handle, (a,b) in self.segments.items():
            points = [' '.join(map(str,p)) for p in (a,b)]
            text += (f'EntityHandle="{handle}"\nDXF_Type="LINE"\nLayer="example"\nStyle.entity_linetype.Value="Continuous"\n'
                     f'Start_WCS=({points[0]})\nEnd_WCS=({points[1]})\n')
        text += f'SelectedEntityTotal={len(self.segments)}\nReadErrorCount=0\nEND_OF_REPORT: done\n'
        self.files['report'].write_text(text,encoding='utf-8')
        self.files['manifest'].unlink(missing_ok=True)
        write_manifest(self.files['report'],self.files['manifest'])
        self.scope['report_sha256'] = digest(self.files['report'].read_bytes())
        self.rule = dict(id='rule',status='approved_assumption',
                         scope=dict(project_id='example',verified_application=dict(self.scope)),
                         source=dict(kind='explicit_user_confirmation'))
        self.unit = dict(assumption_id='units',status='approved',authorization_type='approved_assumption',
                         cad_coordinate_unit='mm',physical_length_unit='m',conversion_to_meter='0.001',
                         applicability={**self.scope,'scope':'current verified version ModelSpace',
                                        'universal_engineering_rule':False,'other_drawings_allowed':False})
        rule_sha = put(self.files['assumption'],self.rule)
        unit_sha = put(self.files['unit'],self.unit)
        def row(h):
            ident = {k:v for k,v in self.scope.items() if k != 'drawing'}
            return dict(identity=dict(ident,handle=h,parent_path=[]),vertices_wcs_mm=self.segments[h],
                        layer='example',entity_type='LINE',explicit_linetype='Continuous')
        key = dict(project_id='example',drawing_instance_id='drawing-A',snapshot=self.scope['report_sha256'],
                   space='ModelSpace',endpoints=self.ends)
        self.review = dict(assumption='rule',assumption_sha256=rule_sha,
                           unit_authorization=dict(id='units',sha256=unit_sha,conversion_to_meter='0.001'),
                           source=dict(snapshot=key['snapshot'],dwg_sha256=self.scope['dwg_sha256'],
                                       drawing='sample.dwg',manifest_sha256=digest(self.files['manifest'].read_bytes())),
                           review=dict(local_gap_path_basis='eligible_under_project_assumption',
                                       review_evidence=['human_native_observation'],crossed_engineering_connection=False),
                           raw_parents=[row('A'),row('B')],crossed=row('C'),
                           derived_gap=dict(id='gap:'+digest(json.dumps(key,sort_keys=True,separators=(',',':')).encode()),
                                            dedup_key=key,from_wcs=[2,0,0],to_wcs=[6,0,0],squared_mm='16',length_mm='4',length_m='.004'),
                           competition=dict(contact_tolerance_mm='.001',angle_tolerance_deg='.01',search_distance_mm='5',
                                            device_control_endpoint_status={'A':{'end':'unresolved'},'B':{'start':'unresolved'}},
                                            qualified_oriented_pairs={'A:end':[['B','start']],'B:start':[['A','end']]},
                                            existing_endpoint_peers={'A:end':[],'B:start':[]},
                                            existing_overlapping_native_segments=[],bulged_segments_with_nearby_bounds=[],
                                            arc_or_circle_circumferences_in_expanded_window=[]))
        self.request = dict(scope=dict(self.scope),files={k:k for k in self.files},
                            traversals=[dict(item_id='item-A',endpoints=self.ends)])

    def replay(self, pin=None):
        r = self.root/'review.json'
        accepted = put(r,self.review)
        q = self.root/'request.json'
        put(q,self.request)
        return project(q,r,pin or accepted)

    def blocked(self, reason):
        result = self.replay()
        self.assertEqual(result['status'],'blocked',result)
        self.assertIn(reason,result['reason'])
        self.assertEqual(result['approved_recovered_components'],[])
        self.assertIsNone(result['formal_quantity'])

    def test_qualified_native_and_derived_lengths_separate(self):
        r=self.replay()
        self.assertEqual(r['status'],'qualified',r)
        self.assertEqual([s['native_length_mm'] for s in r['native_steps']],['2','2'])
        self.assertEqual(r['approved_recovered_components'][0]['length_m'],'0.004')
        self.assertFalse(r['observed_visual_gap']['additive'])
        self.assertIsNone(r['formal_quantity'])
        self.assertFalse(r['approved_recovered_components'][0]['crossed_connection_allowed'])

    def test_reverse_and_repeat_per_item_not_global(self):
        original=self.replay()['approved_recovered_components']
        self.request['traversals'] += [dict(item_id=i,endpoints=self.ends[::-1]) for i in ('item-A','item-B','item-B')]
        r=self.replay()
        self.assertEqual(r['approved_recovered_components'],original)
        self.assertEqual(r['item_component_refs'],{i:[original[0]['id']] for i in ('item-A','item-B')})
        self.assertEqual([view[0]['handle'] for view in r['ordered_path_views']],['A','B'])
        self.assertTrue(all(view[1]['ref'] == original[0]['id'] for view in r['ordered_path_views']))

    def test_visual_only(self):
        self.review['review']['local_gap_path_basis']='visual_only'
        self.blocked('missing_pair_approval')

    def test_untrusted_replacement(self):
        self.assertIn('source_hash_mismatch',self.replay('0'*64)['reason'])

    def test_competing_forward_end(self):
        self.segments['D']=[(5,0,0),(5.5,0,0)]
        self.prepare()
        self.blocked('competing_endpoint')

    def test_closer_off_axis_endpoint(self):
        self.segments['D']=[(3,1,0),(3,2,0)]
        self.prepare()
        self.assertEqual(self.replay()['status'],'qualified')

    def test_existing_native_coverage(self):
        self.segments['D']=[(-10,0,0),(30,0,0)]
        self.prepare()
        self.blocked('native_path_overlap')

    def test_wrong_crossed_edge(self):
        self.segments['C']=[(10,-1,0),(10,1,0)]
        self.prepare()
        self.blocked('missing_or_ambiguous_crossing')

    def test_crossing_is_not_a_turn(self):
        self.request['traversals'][0]['endpoints']=[self.ends[0],['C',[],'end']]
        self.blocked('traversal_not_authorized')

    def test_cross_project_drawing_snapshot(self):
        for key in ('project_id','drawing','report_sha256','drawing_instance_id'):
            with self.subTest(key=key):
                self.request['scope']={**self.scope,key:'other'}
                self.blocked('approval_scope_mismatch')

    def test_unit_not_authorized(self):
        self.unit['status']='missing'
        self.review['unit_authorization']['sha256']=put(self.files['unit'],self.unit)
        self.blocked('unit_authorization_mismatch')

    def test_mismatched_length_pinned_review(self):
        self.review['derived_gap']['length_mm']='4.1'
        self.blocked('declared_length')

    def test_wrong_source_vertices(self):
        self.review['raw_parents'][0]['vertices_wcs_mm']=[(1,0,0),(2,0,0)]
        self.blocked('native_geometry_mismatch')

    def test_request_cannot_supply_length_or_material_approval(self):
        self.request['traversals'][0]['length_mm']='17'
        self.blocked('unexpected_traversal_fields')
        self.request['approved_quantity']='17'
        self.blocked('unexpected_request_fields')

    def test_conflicting_review_even_if_geometry_clear(self):
        self.review['competition']['qualified_oriented_pairs']['A:end'].append(['D','start'])
        self.blocked('unresolved_pair_review')

    def test_crossing_at_different_elevation(self):
        self.segments['C']=[(4,-1,2),(4,1,2)]
        self.prepare()
        self.blocked('missing_or_ambiguous_crossing')

    def test_raw_snapshot_tampered(self):
        self.files['report'].write_bytes(b'other report')
        self.blocked('source_hash_mismatch')

    def test_device_contact_at_recovered_end_blocks(self):
        self.review['competition']['device_control_endpoint_status']['B']['start']='supported'
        self.blocked('device_contact_at_gap')

    def test_another_reviewed_pair_cannot_borrow_traversal(self):
        self.request['traversals'][0]['endpoints']=[['A',[],'end'],['B',['PARENT'],'start']]
        self.blocked('traversal_not_authorized')

    def test_decimal_context_is_isolated(self):
        with localcontext() as ctx:
            ctx.prec=2
            ctx.traps[Inexact]=True
            self.assertEqual(self.replay()['approved_recovered_components'][0]['length_m'],'0.004')
