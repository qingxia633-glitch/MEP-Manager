from pathlib import Path
import random
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rows import reconstruct

SOURCE = dict(project_id='demo', drawing='example.dwg', snapshot_id='a'*64)
WINDOW = [-2, -2, 42, 32]


def line(h, a, b):
    return dict(handle=h, kind='LINE', points=[a, b], straight=True, closed=False)


def box(h, x, y, right=None, top=None, kind='TEXT'):
    return dict(handle=h, kind=kind, bounds=[x,y,x if right is None else right,
                                            y if top is None else top], text=h)


def grid(dx=0, prefix=''):
    return [line(prefix+'h'+str(y), [dx,y], [dx+10,y]) for y in (0,5,10)] + [
        line(prefix+'v'+str(x), [dx+x,0], [dx+x,10]) for x in (0,5,10)]


def run(items):
    return reconstruct(SOURCE, 'region', WINDOW, 0, items)


class Rows(unittest.TestCase):
    def test_closed_cells(self):
        r = run(grid())
        self.assertEqual([len(row['cells']) for row in r['rows']], [2,2])
        self.assertTrue(all(c['evidence_status']=='bounded' for row in r['rows'] for c in row['cells']))

    def test_multiple_glyphs(self):
        r = run(grid()+[line('stroke',[1,6],[4,6]),box('S',2,8),line('stroke2',[1,9],[4,9])])
        self.assertEqual(set(r['rows'][0]['cells'][0]['members']), {'stroke','S','stroke2'})

    def test_similar_symbols_in_different_rows(self):
        r=run(grid()+[line('x',[1,1],[3,1]),line('y',[1,6],[3,6])])
        self.assertEqual([r0['original_members'] for r0 in r['rows']], [['y'],['x']])

    def test_offset_and_multiline(self):
        r=run(grid()+[box('offset',1,5.1,4.8,7), box('multi',6,5.3,9,9.8,'MTEXT')])
        self.assertEqual(r['rows'][0]['original_members'], ['multi','offset'])

    def test_crossing_is_unassigned(self):
        r=run(grid()+[box('cross',4,7,6,9)])
        self.assertFalse(any('cross' in row['original_members'] for row in r['rows']))
        issue=next(i for i in r['unresolved_items'] if i.get('handle')=='cross')
        self.assertEqual(len(issue['candidate_cells']),2)

    def test_native_and_text_alignment(self):
        r=run([box('first',1,1),box('second',1,8)])
        self.assertEqual(r['region_kind'],'ordinary_arrangement')
        self.assertEqual(r['rows'],[])

    def test_missing_row_boundary(self):
        a=[e for e in grid() if e['handle']!='h5']+[line('half',[0,5],[5,5])]
        r=run(a)
        self.assertTrue(any(c['evidence_status']=='unresolved' for row in r['rows'] for c in row['cells']))

    def test_missing_column_or_merge(self):
        a=[e for e in grid() if e['handle']!='v5']+[line('v5lower',[5,0],[5,5])]
        r=run(a)
        self.assertTrue(any('merge_or_missing_divider' in c['unresolved_items'] for row in r['rows'] for c in row['cells']))

    def test_duplicated_edge(self):
        r=run(grid()+[line('overlap',[0,5],[10,5])])
        self.assertTrue(any(c['evidence_status']=='ambiguous' for row in r['rows'] for c in row['cells']))

    def test_two_tables(self):
        r=run(grid()+grid(22,'B'))
        self.assertEqual(len(r['rows']),4)
        self.assertEqual(sum(len(row['cells']) for row in r['rows']),8)

    def test_order_and_provenance(self):
        a=grid()+[box('a',2,1),box('b',2,2)]
        b=a.copy()
        random.Random(13).shuffle(b)
        self.assertEqual(run(a),run(b))
        row=run(a)['rows'][0]
        self.assertEqual(row['provenance']['snapshot_id'],SOURCE['snapshot_id'])
        self.assertTrue(row['row_boundary'])

    def test_identity_not_content(self):
        a=grid()+[box('one',1,1)]
        old=run(a)['rows'][1]
        a[-1]['text']='modified'
        new=run(a)['rows'][1]
        self.assertEqual(old['row_id'],new['row_id'])
        self.assertEqual(old['cells'][0]['cell_id'],new['cells'][0]['cell_id'])

    def test_no_engineering_effect(self):
        r=run(grid()+[box('S',1,1)])
        self.assertFalse({'semantic_role','quantity_eligible','approved_rule'} & r.keys())

    def test_open_u_shape(self):
        r=run([line('a',[0,0],[0,5]),line('b',[0,5],[10,5]),line('c',[10,5],[10,0])])
        self.assertEqual(r['rows'],[])
        self.assertEqual(r['region_kind'],'incomplete_grid_candidate')

    def test_closed_polyline_perimeter(self):
        rect=dict(handle='frame',kind='LWPOLYLINE',points=[[0,0],[10,0],[10,8],[0,8]],
                  straight=True,closed=True)
        r=run([rect,box('a',1,1)])
        self.assertEqual(r['drawn_tables'][0]['rectangular_outer_status'],'bounded')
        self.assertEqual(r['rows'][0]['original_members'],['a'])

    def test_header_on_shared_rails_is_candidate_only(self):
        r=run(grid()+[dict(box('head',1,6),decoded_text='图例'),box('lower',1,1)])
        role=r['rows'][1]['column_role_candidates'][0]
        self.assertEqual(role['source'],'head')
        self.assertEqual(role['cell_id'],r['rows'][1]['cells'][0]['cell_id'])

    def test_missing_outer_rail_retains_unassigned_row_candidate(self):
        r=run([e for e in grid() if e['handle']!='v10']+[box('outside',8,8)])
        self.assertEqual(r['rows'][0]['row_only_candidates'],['outside'])
        self.assertNotIn('outside',r['rows'][0]['original_members'])
        self.assertEqual(r['drawn_tables'][0]['rectangular_outer_status'],'unresolved')

    def test_same_glyph_on_shared_divider_not_picked(self):
        r=run(grid()+[box('mark',5,8)])
        i=next(i for i in r['unresolved_items'] if i['handle']=='mark')
        self.assertEqual(len(i['candidate_cells']),2)

    def test_duplicate_identity_rejected(self):
        with self.assertRaises(ValueError):
            run(grid()+[box('v0',1,1)])

    def test_foreign_identity_rejected(self):
        a=box('member',1,1)
        a['identity']=dict(project_id='foreign',drawing_ref='example.dwg',handle='member',
                           parent_path=[],snapshot_id=SOURCE['snapshot_id'])
        with self.assertRaises(ValueError):
            run(grid()+[a])
