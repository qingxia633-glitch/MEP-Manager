"""Exporter VARIANT_BOOL atoms; synthetic contract cases, not project facts."""
import unittest
from test_table_evidence import cell, report, read
from table_evidence import getter, boolean


def observe(raw, status='read', key='Cell.Empty'):
    value='' if raw is None else f'{key}.Value={raw}\n'
    return getter(value+f'{key}.Status="{status}"\n{key}.Source="vla-IsEmpty"\n',key)


class TableBooleanTests(unittest.TestCase):
    def test_false_atom(self):
        x=observe(':vlax-false');self.assertEqual(x['status'],'read')
        self.assertIs(x['value'],False);self.assertIs(boolean(x),False)
        self.assertEqual(x['raw_serialized_value'],':vlax-false')
    def test_true_atom(self):
        x=observe(':vlax-true');self.assertEqual(x['status'],'read')
        self.assertIs(x['value'],True);self.assertIs(boolean(x),True)
    def test_unknown_atom(self):
        x=observe(':vlax-unknown');self.assertEqual(x['status'],'invalid_result');self.assertIsNone(boolean(x))
    def test_quoted_atom(self):
        x=observe('":vlax-false"');self.assertEqual(x['status'],'invalid_result');self.assertIsNone(boolean(x))
    def test_missing(self):
        x=getter('','Cell.Empty');self.assertEqual(x['status'],'missing');self.assertIsNone(boolean(x))
    def test_missing_value_claimed_read(self):
        self.assertEqual(observe(None)['status'],'invalid_result')
    def test_unavailable(self):
        x=observe(':vlax-false','unavailable');self.assertEqual(x['status'],'unavailable');self.assertIsNone(boolean(x))
    def test_unsupported(self):
        x=observe(None,'unsupported');self.assertEqual(x['status'],'unsupported');self.assertIsNone(boolean(x))
    def test_malformed_values(self):
        for raw in [':VLAX-FALSE',':vlax-false extra','1','2','"nonsense"','null']:
            with self.subTest(raw=raw):
                x=observe(raw);self.assertEqual(x['status'],'invalid_result');self.assertIsNone(boolean(x))
    def test_text_not_interpreted(self):
        x=observe('":vlax-false"',key='Cell.Text');self.assertEqual(x['value'],':vlax-false');self.assertEqual(x['status'],'read')
    def test_cell_false(self):
        x=read(report(cell().replace('Cell.Empty.Value=false','Cell.Empty.Value=:vlax-false')))['cells'][0]
        self.assertIs(x['fields']['Empty']['value'],False);self.assertEqual(x['fields']['Empty']['status'],'read')
        self.assertEqual(x['content_kind'],'text_observation')
    def test_cell_true(self):
        x=read(report(cell(text='',empty=True).replace('Cell.Empty.Value=true','Cell.Empty.Value=:vlax-true')))['cells'][0]
        self.assertIs(x['fields']['Empty']['value'],True);self.assertEqual(x['content_kind'],'empty')


if __name__=='__main__':unittest.main()
