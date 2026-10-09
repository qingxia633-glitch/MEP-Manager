import math
import sys
import unittest
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from resolver import DrawingContext, resolve_connection

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / 'local_test_data/fire-alarm-full-snapshot-20260923/MEP-full-entity-report.txt'
PROBES = [ROOT / 'local_test_data' / p / 'block-definition-probe.txt' for p in [
    'module-13304-probe-20261005',
    'fire-alarm-smoke-block-Equip00002649-probe-20260926',
    'block-definition-probe.txt',
    'module-13017-child-10B16-probe-20261005',
    'valve-132F7-probe-20261005']]


def insert(name='B', handle='I', insertion=(0, 0, 0), scale=(1, 1, 1), rotation=0):
    return dict(type='INSERT', handle=handle, block=name, insertion=list(insertion),
                scale=list(scale), rotation=rotation, normal=[0, 0, 1], dynamic=False)


def context(entities, instance=None, base=(0, 0, 0), source_endpoint=(0,0,0)):
    return DrawingContext({'I': instance or insert(),
                           'E':dict(type='LINE',vertices=[list(source_endpoint),[.002,0,0]])},
                          {'B': dict(base=list(base), entities=entities, complete=True, dynamic=False)}, [])


class RealEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx = DrawingContext.from_reports(SNAPSHOT, PROBES)

    def test_real_connections(self):
        cases = [('13CF0', '13304', '10315'), ('13CE9', '13304', '10317'),
                 ('13CE9', '134D9', '10317'), ('13CE8', '12D65', '102F5'),
                 ('14147', '13017', '10301')]
        for edge, target, point in cases:
            with self.subTest(edge=edge, target=target):
                # Endpoint selection uses the already recorded endpoint order, not proximity.
                index = 0 if (edge, target) == ('13CE9', '134D9') else -1
                ep = self.ctx.entities[edge]['vertices'][index]
                r = resolve_connection(edge, ep, target, self.ctx, .001)
                self.assertEqual(r['geometric_connection_status'], 'supported')
                self.assertEqual(r['candidate_geometry'][0]['source_entity_handle'], point)
                self.assertLessEqual(r['candidate_geometry'][0]['xy_distance'], .001)
                if target == '13017':
                    self.assertEqual(r['candidate_geometry'][0]['source_definition_path'], ['13017', '10B16', '10301'])
                print(edge, target, r['geometric_connection_status'], point)

    def test_rejected_valve(self):
        r = resolve_connection('14423', self.ctx.entities['14423']['vertices'][-1], '132F7', self.ctx, .001)
        self.assertEqual(r['geometric_connection_status'], 'rejected')
        self.assertAlmostEqual(r['nearest_geometry']['xy_distance'], 373.729594, places=5)
        print('14423 132F7 rejected', r['nearest_geometry']['xy_distance'])

    def test_missing_definition_history(self):
        ctx = DrawingContext.from_reports(SNAPSHOT, [])
        r = resolve_connection('14147', ctx.entities['13017']['insertion'], '13017', ctx, .001)
        self.assertEqual(r['geometric_connection_status'], 'unresolved')

    def test_provenance_mismatch_blocked(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'foreign.txt'
            p.write_text('DWG="other.dwg"\n',encoding='utf-8')
            with self.assertRaises(ValueError):DrawingContext.from_reports(SNAPSHOT,[p])

    def test_missing_parent_transform_field(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'incomplete.txt'
            text=PROBES[0].read_text(encoding='utf-8-sig')
            text='\n'.join(s for s in text.splitlines() if not s.startswith('ParentReferenceDXF:50='))
            p.write_text(text,encoding='utf-8')
            ctx=DrawingContext.from_reports(SNAPSHOT,[p])
            r=resolve_connection('13CF0',ctx.entities['13CF0']['vertices'][-1],'13304',ctx,.001)
            self.assertEqual(r['geometric_connection_status'],'unresolved')


class SyntheticEvidence(unittest.TestCase):
    def run_case(self, entities, ep, instance=None, base=(0, 0, 0)):
        return resolve_connection('E', ep, 'I', context(entities, instance, base, ep), .001)

    def test_rotations_mirror_base_and_z(self):
        for angle in [0, math.pi/2, math.pi, 3*math.pi/2]:
            for sx in [2, -2]:
                p = [2, 3, 4]; base = [1, 1, 1]
                expected = [10 + sx*math.cos(angle)-6*math.sin(angle),
                            20 + sx*math.sin(angle)+6*math.cos(angle), 0]
                r = self.run_case([dict(type='POINT', handle='P', point=p)], expected,
                                  insert(insertion=(10, 20, 3000), scale=(sx, 3, 4), rotation=angle), base)
                self.assertEqual(r['geometric_connection_status'], 'supported')
                self.assertGreater(r['candidate_geometry'][0]['xyz_distance'], 3000)

    def test_line_and_open_polyline(self):
        for typ in ['LINE', 'LWPOLYLINE', 'POLYLINE']:
            r = self.run_case([dict(type=typ, handle='L', vertices=[[1, 2, 0], [3, 4, 0]], closed=False)], [1, 2, 0])
            self.assertEqual(r['geometric_connection_status'], 'supported')

    def test_closed_and_middle_not_anchor(self):
        r = self.run_case([dict(type='LWPOLYLINE', handle='L', vertices=[[0,0,0],[2,0,0],[2,2,0]], closed=True)], [0,0,0])
        self.assertEqual(r['geometric_connection_status'], 'partial')
        r = self.run_case([dict(type='LINE', handle='L', vertices=[[0,0,0],[2,0,0]])], [1,0,0])
        self.assertEqual(r['geometric_connection_status'], 'partial')

    def test_attributes_and_insertion_not_anchors(self):
        for typ in ['ATTDEF', 'ATTRIB', 'TEXT', 'MTEXT']:
            r = self.run_case([dict(type=typ, handle='T', point=[0,0,0])], [0,0,0])
            self.assertEqual(r['geometric_connection_status'], 'unresolved')

    def test_incomplete_and_unsupported(self):
        for e in [insert('MISSING', 'N'), dict(type='ACAD_PROXY_ENTITY',handle='X'),
                  dict(type='ARC',handle='A'), dict(type='SPLINE',handle='S')]:
            self.assertEqual(self.run_case([e],[0,0,0])['geometric_connection_status'],'unresolved')
        i=insert();i['normal']=[0,1,0]
        self.assertEqual(self.run_case([dict(type='POINT',handle='P',point=[0,0,0])],[0,0,0],i)['geometric_connection_status'],'unresolved')
        i=insert();del i['scale']
        self.assertEqual(self.run_case([], [0,0,0],i)['geometric_connection_status'],'unresolved')

    def test_nested_composition_and_cycle(self):
        c=context([insert('C','N',insertion=(5,0,0),scale=(-2,3,1),rotation=math.pi/2)],insert(rotation=math.pi/2),source_endpoint=[2,5,0])
        c.definitions['C']=dict(base=[1,0,0],complete=True,dynamic=False,entities=[dict(type='POINT',handle='P',point=[2,0,0])])
        r=resolve_connection('E',[2,5,0],'I',c,.001)
        self.assertEqual(r['geometric_connection_status'],'supported')
        self.assertEqual(r['candidate_geometry'][0]['source_definition_path'],['I','N','P'])
        c.definitions['C']['entities']=[insert('B','LOOP')]
        self.assertEqual(resolve_connection('E',[2,5,0],'I',c,.001)['geometric_connection_status'],'unresolved')

    def test_width_near_and_tolerance(self):
        e=dict(type='LWPOLYLINE',handle='L',vertices=[[0,0,0],[10,0,0]],closed=False,width=2)
        self.assertEqual(self.run_case([e],[5,.5,0])['geometric_connection_status'],'partial')
        e=dict(type='POINT',handle='P',point=[0,0,0])
        self.assertEqual(self.run_case([e],[.002,0,0])['geometric_connection_status'],'rejected')
        self.assertEqual(resolve_connection('E',[.002,0,0],'I',context([e]),.003)['geometric_connection_status'],'supported')
        with self.assertRaises(ValueError): resolve_connection('E',[0,0,0],'I',context([e]),-1)

    def test_circle_and_dynamic(self):
        e=dict(type='CIRCLE',handle='C',point=[0,0,0],radius=2)
        self.assertEqual(self.run_case([e],[2,0,0])['geometric_connection_status'],'partial')
        i=insert();i['dynamic']=True
        self.assertEqual(self.run_case([e],[2,0,0],i)['geometric_connection_status'],'unresolved')

    def test_incomplete_definition_blocks_rejection(self):
        c=context([dict(type='POINT',handle='P',point=[5,5,0])])
        c.definitions['B']['complete']=False
        self.assertEqual(resolve_connection('E',[0,0,0],'I',c,.001)['geometric_connection_status'],'unresolved')
        c=context([dict(type='POINT',handle='P',point=[float('nan'),0,0])])
        self.assertEqual(resolve_connection('E',[0,0,0],'I',c,.001)['geometric_connection_status'],'unresolved')

    def test_curve_array_and_nested_missing(self):
        e=dict(type='LWPOLYLINE',handle='L',vertices=[[0,0,0],[10,0,0]],bulges=[1])
        self.assertEqual(self.run_case([e],[0,0,0])['geometric_connection_status'],'unresolved')
        i=insert();i['array']=True
        self.assertEqual(self.run_case([dict(type='POINT',handle='P',point=[0,0,0])],[0,0,0],i)['geometric_connection_status'],'unresolved')
        c=context([dict(type='POINT',handle='P',point=[5,5,0]),insert('Missing','N')])
        r=resolve_connection('E',[0,0,0],'I',c,.001)
        self.assertEqual(r['geometric_connection_status'],'unresolved')
        self.assertTrue(any('missing_definition' in s for s in r['issues']))


if __name__ == '__main__':
    unittest.main(verbosity=2)
