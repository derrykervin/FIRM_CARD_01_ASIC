import sys
from pathlib import Path
from dataclasses import replace
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from auth_transcript import Challenge, encode_challenge, challenge_digest
from protocol import Frame, encode, decode


class TranscriptTests(unittest.TestCase):
    def fixture(self):
        return Challenge(b'key00001', bytes(range(16)), bytes(range(32)),
                         bytes(range(16, 32)), 76561198000000000, '0000000001',
                         480, 1, 1800000060)

    def test_wire_offsets_and_transport_budget(self):
        data = encode_challenge(self.fixture())
        self.assertEqual(len(data), 123)
        self.assertEqual(data[:17], b'FIRM-CARD-PROOF\x00\x01')
        self.assertEqual(data[17:25], b'key00001')
        self.assertEqual(data[25:41], bytes(range(16)))
        self.assertEqual(data[41:73], bytes(range(32)))
        self.assertEqual(data[73:89], bytes(range(16,32)))
        self.assertEqual(data[97:107], b'0000000001')
        self.assertEqual(int.from_bytes(data[107:111], 'big'), 480)
        self.assertEqual(int.from_bytes(data[111:115], 'big'), 1)
        self.assertEqual(int.from_bytes(data[115:123], 'big'), 1800000060)
        self.assertEqual(decode(encode(Frame(42, 0x10, data))).payload, data)

    def test_all_context_fields_bound(self):
        value = self.fixture()
        replacements = dict(key_id=b'key00002', challenge_id=b'x'*16, nonce=b'y'*32,
                            account_id=b'z'*16, steam_id=value.steam_id+1, uid='0000000002',
                            app_id=481, audience_id=2, expires_at=value.expires_at+1)
        original = challenge_digest(value)
        for field, data in replacements.items():
            self.assertNotEqual(original, challenge_digest(replace(value, **{field: data})))

    def test_strict_bytes_and_integer_ranges(self):
        for field, bad in (('nonce', b'x'*31), ('key_id', b'x'*9),
                           ('account_id', 'x'*16), ('challenge_id', bytearray(16)),
                           ('steam_id', True), ('steam_id', 1<<64), ('app_id', -1),
                           ('audience_id', 0), ('expires_at', 0), ('uid', '１２３４５６７８９０')):
            with self.assertRaises(ValueError):
                encode_challenge(replace(self.fixture(), **{field: bad}))


if __name__ == '__main__':
    unittest.main()
