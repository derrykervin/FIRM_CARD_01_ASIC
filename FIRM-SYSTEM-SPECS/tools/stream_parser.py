"""Bounded v2 receive reference; no dispatch, authentication or RTL implementation.

Use monotonic milliseconds. Call tick during UART silence and reset on removal.
The caller must discard UART framing-error bytes and reset this parser.
"""
import math
from protocol import MAGIC, MAX_PAYLOAD, VERSION, decode


class StreamParser:
    def __init__(self, byte_timeout_ms=20, frame_timeout_ms=100):
        if (not math.isfinite(byte_timeout_ms) or byte_timeout_ms <= 0
                or not math.isfinite(frame_timeout_ms) or frame_timeout_ms <= 0):
            raise ValueError('timeouts must be positive and finite')
        self.byte_timeout_ms = byte_timeout_ms
        self.frame_timeout_ms = frame_timeout_ms
        self._last_time = None
        self.reset()

    def reset(self):
        """Clear partial frame on reset/removal; retain monotonic clock guard."""
        self._buffer = bytearray()
        self._started = None
        self._last_byte = None

    @property
    def buffered_bytes(self):
        return len(self._buffer)

    def tick(self, now_ms):
        """Expire partial frame even when no next byte arrives; return expiry."""
        if not math.isfinite(now_ms) or (self._last_time is not None
                                        and now_ms < self._last_time):
            raise ValueError('time must be finite and monotonic')
        self._last_time = now_ms
        expired = bool(self._buffer) and (
            now_ms - self._last_byte >= self.byte_timeout_ms
            or now_ms - self._started >= self.frame_timeout_ms)
        if expired:
            self.reset()
        return expired

    def feed(self, value, now_ms):
        """Consume one byte; return a validated Frame or None.

        Invalid header or CRC discards the entire candidate, never executing a
        sync word embedded inside that candidate. Recovery starts at next byte.
        Sync words inside a valid payload have no special meaning.
        """
        if not isinstance(value, int) or not 0 <= value <= 255:
            raise ValueError('expected one byte')
        self.tick(now_ms)
        if not self._buffer:
            if value == MAGIC[0]:
                self._buffer.append(value)
                self._started = self._last_byte = now_ms
            return None
        if len(self._buffer) == 1:
            if value == MAGIC[0]:
                self._started = self._last_byte = now_ms
                return None
            if value != MAGIC[1]:
                self.reset()
                return None
        self._buffer.append(value)
        self._last_byte = now_ms
        count = len(self._buffer)
        if ((count == 3 and value != VERSION)
                or (count == 4 and value not in (0, 1))):
            self.reset()
            return None
        if count < 9:
            return None
        size = int.from_bytes(self._buffer[7:9], 'big')
        if size > MAX_PAYLOAD:
            self.reset()
            return None
        if count < size + 11:
            return None
        packet = bytes(self._buffer)
        self.reset()
        try:
            return decode(packet)
        except ValueError:
            return None
