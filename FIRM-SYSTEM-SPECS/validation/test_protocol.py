import sys
from pathlib import Path
import unittest
import binascii
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from protocol import Frame, encode, decode, validate_uid, mod97_check_digits, valid_printed_number

class ProtocolTests(unittest.TestCase):
    def test_crc_standard_check(self):
        self.assertEqual(binascii.crc_hqx(b'123456789', 0xFFFF), 0x29B1)

    def test_roundtrip_boundaries(self):
        for size in (0, 1, 64, 128):
            for sequence in (0, 65535):
                frame = Frame(sequence, 0x10, bytes(range(size)), 1)
                self.assertEqual(decode(encode(frame)), frame)

    def test_every_single_bit_corruption_rejected(self):
        packet = encode(Frame(123, 0x10, bytes(range(64))))
        for index in range(len(packet)):
            for bit in range(8):
                bad = bytearray(packet)
                bad[index] ^= 1 << bit
                with self.assertRaises(ValueError):
                    decode(bytes(bad))

    def test_truncation_extra_bytes(self):
        packet = encode(Frame(0, 1, b'abc'))
        for size in range(len(packet)):
            with self.assertRaises(ValueError):
                decode(packet[:size])
        with self.assertRaises(ValueError):
            decode(packet + b'\x00')

    def test_ranges(self):
        for frame in (Frame(-1, 0), Frame(65536, 0), Frame(0, 256),
                      Frame(0, 0, b'a'*129), Frame(0, 0, flags=2)):
            with self.assertRaises(ValueError):
                encode(frame)

    def test_uid_preserves_zeroes_and_rejects_unicode(self):
        self.assertEqual(validate_uid('0000000001'), '0000000001')
        for uid in ('1', '１２３４５６７８９０', '123456789a'):
            with self.assertRaises(ValueError):
                validate_uid(uid)

    def test_printed_check_and_single_digit_errors(self):
        prefix = '00010000000001'
        number = prefix + mod97_check_digits(prefix)
        self.assertTrue(valid_printed_number(number))
        self.assertEqual(int(number) % 97, 1)
        for index, digit in enumerate(number):
            for replacement in '0123456789':
                if replacement != digit:
                    self.assertFalse(valid_printed_number(number[:index]+replacement+number[index+1:]))
        self.assertFalse(valid_printed_number('１２３４５６７８９０１２３４５６'))

if __name__ == '__main__':
    unittest.main()
