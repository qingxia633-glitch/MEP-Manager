import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from inventory import relation, identity, aggregate, reconcile, duplicate_groups, merge_evidence

class RegionalTests(unittest.TestCase):
    def test_point_membership(self):
        for point,want in [((1,1),'inside'),((0,4),'on_boundary'),((11,4),'outside'),(None,'unresolved')]:
            self.assertEqual(relation(point,(0,0,10,10)),want)

    def obj(self,h,xy=(3,3),path=()):
        return dict(project_id='p',drawing_instance_id='d',snapshot='s',parent_path=list(path),handle=h,
                    entity_type='INSERT',location=xy,inventory_class='unclassified',candidate_types=[],
                    device_status='unresolved',boundary_relation='inside',floor_id=None)

    def test_same_identity_multiple_entries(self):
        a=self.obj('A')
        self.assertEqual(len(merge_evidence([(identity(a),'a'),(identity(a),'b')])),1)

    def test_close_distinct(self):
        a,b=self.obj('A'),self.obj('B',(3.00001,3))
        self.assertEqual(duplicate_groups([a,b]),[])
        self.assertEqual(aggregate([a,b])['distinct_native_object_count'],2)

    def test_colocated(self):
        a,b=self.obj('A'),self.obj('B')
        self.assertEqual(len(duplicate_groups([a,b])[0]),2)

    def test_parent_child(self):
        a,b=self.obj('A'),self.obj('A',path=['P'])
        self.assertNotEqual(identity(a),identity(b))
        self.assertEqual(aggregate([a,b])['distinct_native_object_count'],1)

    def test_multi(self):
        a=self.obj('A');a.update(inventory_class='device_candidate',candidate_types=['x','y'],device_status='multiple')
        r=aggregate([a])
        self.assertEqual(r['distinct_device_candidate_count'],1)
        self.assertEqual(sum(r['candidate_type_hits'].values()),2)

    def test_unknown_and_floor(self):
        r=aggregate([self.obj('A')])
        self.assertEqual(r['unclassified_object_count'],1)
        self.assertEqual(r['unresolved_instance_count'],1)
        self.assertIsNone(r['approved_device_quantity'])
        self.assertIsNone(r['approved_floor_quantity'])

    def test_role_conflict(self):
        self.assertEqual(reconcile(['x'],'supported',['y'])[1],'conflicting')
        self.assertEqual(reconcile([],'conflicting',[])[1],'conflicting')

    def test_negative_pair_is_not_instance_conflict(self):
        self.assertEqual(reconcile(['x'],'supported',[]),(['x'],'single'))

    def test_input_order(self):
        a,b=self.obj('A'),self.obj('B')
        self.assertEqual(aggregate([a,b]),aggregate([b,a]))
        self.assertEqual(duplicate_groups([a,b]),duplicate_groups([b,a]))

    def test_border_not_counted(self):
        a=self.obj('A');a['boundary_relation']='on_boundary'
        self.assertEqual(aggregate([a])['distinct_native_object_count'],0)
