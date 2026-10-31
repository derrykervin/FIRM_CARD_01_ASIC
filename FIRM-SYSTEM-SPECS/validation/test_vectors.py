import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'experimental/protocol_v2'))
from generate_vectors import generate
from check_vectors import check_vectors


class VectorTests(unittest.TestCase):
    def test_generated_stimulus_matches_reference(self):
        self.assertEqual(check_vectors(generate()), 10)

    def test_wrong_expected_field_is_detected(self):
        corrupted = generate().replace("wanted_sequence=16'd0", "wanted_sequence=16'd1", 1)
        with self.assertRaisesRegex(AssertionError, 'golden frame mismatch'):
            check_vectors(corrupted)

    def test_wrong_count_is_detected(self):
        with self.assertRaisesRegex(AssertionError, 'frame count'):
            check_vectors(generate().replace('check_count(1);', 'check_count(99);', 1))

    def test_missing_and_unknown_statements_are_rejected(self):
        for source in (generate().split('$display')[0], generate()+'unsupported();\n',
                       'unsupported();\n'+generate()):
            with self.assertRaises(AssertionError):
                check_vectors(source)
