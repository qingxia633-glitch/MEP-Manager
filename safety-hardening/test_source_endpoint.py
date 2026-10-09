"""Named-edge endpoint integrity, separate from target Z semantics."""
import unittest
from test_adversarial import load


class SourceEndpointTests(unittest.TestCase):
    def context(self, edge):
        m = load('geometry-connection')
        inst = dict(handle='I', type='INSERT', block='B', insertion=[0,0,3000],
                    scale=[1,1,1], rotation=0, normal=[0,0,1], dynamic=False)
        entities = {'I': inst}
        if edge is not None: entities['E'] = edge
        definition = dict(base=[0,0,0], dynamic=False, complete=True,
                          entities=[dict(type='POINT', handle='P', point=[0,0,0])])
        return m, m.DrawingContext(entities, {'B':definition}, ['synthetic source'])

    def test_source_endpoint_must_be_present(self):
        for edge in (None, {'type':'TEXT'}, {'type':'LINE','vertices':[[0,0,0]]},
                     {'type':'LWPOLYLINE','closed':True,'vertices':[[0,0,0],[1,0,0]]},
                     {'type':'LINE','vertices':[[0,0,20],[1,0,20]]}):
            with self.subTest(edge=edge):
                m, ctx = self.context(edge)
                self.assertEqual(m.resolve_connection('E',[0,0,0],'I',ctx,.001)['geometric_connection_status'],'unresolved')

    def test_verified_source_preserves_target_unknown_z(self):
        m, ctx = self.context({'type':'LINE','vertices':[[0,0,0],[1,0,0]]})
        r = m.resolve_connection('E',[0,0,0],'I',ctx,.001)
        self.assertEqual(r['geometric_connection_status'],'supported')
        self.assertEqual(r['z_semantics_status'],'unresolved')
        self.assertEqual(r['endpoint_source']['endpoint_index'],0)
        self.assertEqual(r['endpoint_source']['edge_handle'],'E')


if __name__ == '__main__': unittest.main()
