import random
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from protocol import Frame, encode
from stream_parser import StreamParser


class StreamTests(unittest.TestCase):
    def send(self, parser, data, start=0, step=0.1):
        frames = []
        for index, value in enumerate(data):
            frame = parser.feed(value, start + index * step)
            if frame is not None:
                frames.append(frame)
            self.assertLessEqual(parser.buffered_bytes, 138)
        return frames

    def test_back_to_back_and_embedded_sync(self):
        frames = [Frame(0, 1), Frame(65535, 0x10, b'\xA5\x5A'*64, 1)]
        self.assertEqual(self.send(StreamParser(), b''.join(map(encode, frames))), frames)

    def test_noise_and_overlapping_sync(self):
        frame = Frame(9, 2, b'test')
        self.assertEqual(self.send(StreamParser(), b'\x00\x5A\xA5\xA5'+encode(frame)), [frame])

    def test_every_truncation_timeout_then_valid_frame(self):
        frame = Frame(5, 0x10, bytes(range(128)))
        packet = encode(frame)
        for size in range(1, len(packet)):
            parser = StreamParser()
            self.assertEqual(self.send(parser, packet[:size]), [])
            self.assertTrue(parser.tick(50))
            self.assertEqual(parser.buffered_bytes, 0)
            self.assertEqual(self.send(parser, packet, start=51), [frame])

    def test_byte_timeout_boundary(self):
        parser = StreamParser()
        parser.feed(0xA5, 0)
        self.assertFalse(parser.tick(19.999))
        self.assertTrue(parser.tick(20))

    def test_whole_frame_deadline_defeats_slow_sender(self):
        parser = StreamParser()
        packet = encode(Frame(0, 1, b'x'*128))
        self.assertEqual(self.send(parser, packet[:10], step=10), [])
        self.assertTrue(parser.tick(100))

    def test_bad_headers_and_crc_recover(self):
        good = encode(Frame(3, 2))
        for index, value in ((2, 3), (3, 2), (7, 1), (8, 129), (10, good[10]^1)):
            bad = bytearray(good)
            bad[index] = value
            parser = StreamParser()
            self.assertEqual(self.send(parser, bad), [])
            self.assertEqual(self.send(parser, good, start=10), [Frame(3, 2)])

    def test_bad_crc_does_not_replay_embedded_frame(self):
        inner = Frame(123, 0x10)
        outer = bytearray(encode(Frame(1, 2, encode(inner))))
        outer[-1] ^= 1
        self.assertEqual(self.send(StreamParser(), outer), [])

    def test_removal_and_reset_cancel_partial_frame(self):
        parser = StreamParser()
        frame = Frame(1, 1, b'x')
        packet = encode(frame)
        self.send(parser, packet[:9])
        parser.reset()
        self.assertEqual(self.send(parser, packet[9:], start=1), [])
        self.assertEqual(self.send(parser, packet, start=2), [frame])

    def test_invalid_inputs_do_not_consume_bytes(self):
        parser = StreamParser()
        parser.feed(0xA5, 10)
        for value in (-1, 256, b'x'):
            with self.assertRaises(ValueError):
                parser.feed(value, 11)
        for when in (9, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                parser.tick(when)
        self.assertEqual(parser.buffered_bytes, 1)
        for timeout in (0, -1, float('inf'), float('nan')):
            with self.assertRaises(ValueError):
                StreamParser(byte_timeout_ms=timeout)

    def test_seeded_noise_is_bounded_and_recovers_after_idle(self):
        rng = random.Random(20261030)
        parser = StreamParser()
        self.send(parser, bytes(rng.randrange(256) for _ in range(10000)))
        parser.tick(2000)
        frame = Frame(42, 1)
        self.assertEqual(self.send(parser, encode(frame), start=2001), [frame])


if __name__ == '__main__':
    unittest.main()
