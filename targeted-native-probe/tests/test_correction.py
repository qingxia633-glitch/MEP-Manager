import unittest
from test_probe import fixture,v

class CorrectionTests(unittest.TestCase):
    def test_serialization_does_not_dereference_entities(self):
        from test_probe import ROOT
        source=(ROOT/'TargetedNativeProbe.lsp').read_text()
        body=source.split('(defun tnp:json ',1)[1].split('(defun tnp:emit ',1)[0]
        for call in ('(tnp:handle ', '(entget ', '(tnp:call '):
            self.assertNotIn(call,body)

    def test_trace_rejects_dirty_and_missing_stages(self):
        with self.assertRaises(ValueError):v.validate_trace('load_before|0|1|getvar')
        with self.assertRaises(ValueError):v.validate_trace('load_before|0|0|getvar')
    def test_trace_all_stages_clean(self):
        names=['idle_control_before','idle_control_after','load_before','load_after','helpers_before','helpers_after','report_closed','report_output']
        self.assertEqual(len(v.validate_trace('\n'.join(n+'|0|0|getvar' for n in names))),8)
    def test_valid_distinct_block_record(self):
        q,r=fixture()
        r.insert(-1,{'kind':'insert_definition','insert':'A','block_name':'B','block_record_handle':'C','block_begin_handle':'D','identity_status':'read','block_begin_raw':[[0,'STR','BLOCK'],[5,'STR','D'],[330,'ENAME','C']],'block_record_raw':[[0,'STR','BLOCK_RECORD'],[5,'STR','C'],[2,'STR','B']]})
        self.assertEqual(v.validate(r,q,'a'*64)['input_integrity'],'verified')
    def test_creation_apis_not_used(self):
        from test_probe import ROOT
        source=(ROOT/'TargetedNativeProbe.lsp').read_text().lower()
        for forbidden in ('getextensiondictionary','regapp','entmake','entmod','entupd','dictadd','dictremove'):
            self.assertNotIn(forbidden,source)
    def test_wrong_block_type_rejected(self):
        q,r=fixture()
        r.insert(-1,{'kind':'insert_definition','insert':'A','block_name':'B','block_record_handle':'C','block_begin_handle':'D','identity_status':'read','block_begin_raw':[[0,'STR','BLOCK'],[5,'STR','D'],[330,'ENAME','C']],'block_record_raw':[[0,'STR','BLOCK'],[5,'STR','C'],[2,'STR','B']]})
        with self.assertRaises(ValueError):v.validate(r,q,'a'*64)
    def test_dictionary_absent(self):
        self.assertEqual(v.extension_dictionary([[0,'STR','LINE']]),('absent',None))
    def test_dictionary_present(self):
        self.assertEqual(v.extension_dictionary([[102,'STR','{ACAD_XDICTIONARY'],[360,'ENAME','D'],[102,'STR','}']]),('read','D'))
    def test_dictionary_unknown(self):
        self.assertEqual(v.extension_dictionary([[102,'STR','{ACAD_XDICTIONARY']]),('unavailable',None))
    def test_stage_change_rejected_even_with_clean_footer(self):
        q,r=fixture();r.insert(-1,{'kind':'dbmod_stage','before':0,'after':1,'stage':'entity_data','call':'entget'})
        with self.assertRaises(ValueError):v.validate(r,q,'a'*64)

if __name__=='__main__':unittest.main()
