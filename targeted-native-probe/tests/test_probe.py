import copy, importlib.util, json, pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('probe_verify',ROOT/'verify.py')
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)

def fixture():
    request={'project_id':'synthetic','drawing_path':'C:/synthetic.dwg','dwg_sha256_before':'a'*64,'seed_handles':['A']}
    return request,[{'kind':'header','contract':'TargetedNativeProbe/1','project_id':'synthetic','drawing_path':'C:/synthetic.dwg','seeds':['A'],'dbmod':0},
      {'kind':'node','handle':'A','entity_type':'LINE','depth':0,'raw':[[0,'STR','LINE'],[5,'STR','A'],[330,'ENAME','B']],'read_status':'read','xdata_status':'absent','owner':'B','owner_status':'read'},
      {'kind':'footer','completed':True,'dbmod':0,'node_count':1,'coverage':'incomplete','reverse_arbitrary':'not_acquired'}]

class Tests(unittest.TestCase):
    def test_valid(self):
        q,r=fixture();self.assertEqual(v.validate(r,q,'a'*64)['native_association_status'],'acquisition_incomplete')
    def test_owner_reactor(self):
        self.assertEqual(v.owner([[102,'STR','{ACAD_REACTORS'],[330,'ENAME','R'],[102,'STR','}'],[330,'ENAME','O'],[100,'STR','AcDbEntity']]),'O')
    def test_owner_malformed(self):self.assertIsNone(v.owner([[102,'STR','}'],[330,'ENAME','O']]))
    def test_duplicate_owner(self):self.assertIsNone(v.owner([[330,'ENAME','A'],[330,'ENAME','B']]))
    def test_group_role(self):self.assertEqual(v.reference_role('GROUP',340,''),'group_member')
    def test_leader_role(self):self.assertEqual(v.reference_role('LEADER',340,''),'annotation_reference')
    def test_mleader_not_target(self):self.assertEqual(v.reference_role('MULTILEADER',340,''),'uninterpreted_reference')
    def test_reactor_not_owner(self):self.assertEqual(v.reference_role('LINE',330,'{ACAD_REACTORS'),'reactor_reference')
    def test_unknown(self):self.assertEqual(v.reference_role('CUSTOM',340,''),'uninterpreted_reference')
    def test_bad_inputs(self):
        for field,value in [('project_id','foreign'),('drawing_path','C:/other.dwg'),('seeds',['B']),('contract','other')]:
            with self.subTest(field=field):
                q,r=fixture();r[0][field]=value
                with self.assertRaises(ValueError):v.validate(r,q,'a'*64)
    def test_hash(self):
        q,r=fixture()
        with self.assertRaises(ValueError):v.validate(r,q,'b'*64)
    def test_missing_seed(self):
        q,r=fixture();r.pop(1);r[-1]['node_count']=0
        with self.assertRaises(ValueError):v.validate(r,q,'a'*64)
    def test_duplicate_node(self):
        q,r=fixture();r.insert(1,copy.deepcopy(r[1]));r[-1]['node_count']=2
        with self.assertRaises(ValueError):v.validate(r,q,'a'*64)
    def test_incomplete(self):
        q,r=fixture()
        with self.assertRaises(ValueError):v.validate(r[:-1],q,'a'*64)
    def test_dbmod(self):
        q,r=fixture();r[-1]['dbmod']=1
        with self.assertRaises(ValueError):v.validate(r,q,'a'*64)
    def test_no_false_absence(self):
        q,r=fixture();r[1]['xdata_status']='absent';r[1]['raw'].append([-3,'LIST',['APP']])
        with self.assertRaises(ValueError):v.validate(r,q,'a'*64)
    def test_owner_mismatch(self):
        q,r=fixture();r[1]['owner']='X'
        with self.assertRaises(ValueError):v.validate(r,q,'a'*64)
    def test_missing_read(self):
        q,r=fixture();r[1]['read_status']='unavailable';r[1]['raw']=None;r[1]['owner']=None;r[1]['owner_status']='unresolved';r[1]['xdata_status']='unavailable'
        self.assertEqual(v.validate(r,q,'a'*64)['native_association_status'],'acquisition_incomplete')

if __name__=='__main__':unittest.main()
