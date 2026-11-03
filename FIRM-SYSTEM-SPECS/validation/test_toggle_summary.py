import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from summarize_cvc_toggle import parse_report


class ToggleSummaryTests(unittest.TestCase):
    def fixture(self):
        return ('MODULE : example (1 INSTANCE(S))\n'
                'hits : 1 hits : 1\nmiss : 2 miss : 2\nbits : 3 bits : 3\n'
                'ALL TOGGLED BITS:\n'
                'hits : 1 hits : 1\nmiss : 2 miss : 2\nbits : 3 bits : 3\n')

    def test_known_control_counts(self):
        value=parse_report(self.fixture())
        self.assertEqual(value['total']['bits'],3)
        self.assertAlmostEqual(value['total']['percent_01'],100/3)

    def test_corrupted_counter_and_total_rejected(self):
        for bad in (self.fixture().replace('bits : 3 bits : 3','bits : 4 bits : 4',1),
                    self.fixture().replace('ALL TOGGLED BITS:\nhits : 1 hits : 1',
                                           'ALL TOGGLED BITS:\nhits : 2 hits : 1')):
            with self.assertRaises(ValueError): parse_report(bad)

    def test_empty_or_truncated_report_not_success(self):
        for bad in ('',self.fixture().split('ALL TOGGLED BITS:')[0],
                    'ALL TOGGLED BITS:\nhits : 0 hits : 0\nmiss : 0 miss : 0\nbits : 0 bits : 0'):
            with self.assertRaises(ValueError): parse_report(bad)
