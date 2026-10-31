import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from run_cvc_regression import passed


class CVCRunnerTests(unittest.TestCase):
    def test_normal_completion(self):
        self.assertTrue(passed('PASS test\nThere were 0 error(s), 0 warning(s)\n', 0, 'PASS test'))

    def test_zero_exit_fatal_is_failure(self):
        self.assertFalse(passed('PASS test\n$fatal[test.v:1] fail\nThere were 1 error(s)\n', 0, 'PASS test'))

    def test_marker_in_error_message_is_not_success(self):
        self.assertFalse(passed('Error while parsing "PASS test"\nThere were 0 error(s)\n', 0, 'PASS test'))

    def test_no_marker_or_error_summary_rejected(self):
        for log in ('There were 0 error(s)\n', 'PASS test\n', 'PASS test\nThere were 2 error(s)\n'):
            self.assertFalse(passed(log, 0, 'PASS test'))

    def test_nonzero_exit_rejected(self):
        self.assertFalse(passed('PASS test\nThere were 0 error(s)\n', 1, 'PASS test'))


if __name__ == '__main__':
    unittest.main()
