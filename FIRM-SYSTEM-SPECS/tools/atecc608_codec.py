"""Candidate ATECC608 command codec; no I2C HAL or provisioning implementation.

Packet bytes exclude I2C address and word-address 0x03. Contract follows pinned
Microchip cryptoauthlib d49c7d578efb09d4a498d5ab86839d4c17812f15.
The transport must bound its own timeout and serialize the entire sequence.
"""
from auth_transcript import challenge_digest
from proof_signature import P256_ORDER, verify_proof


class DeviceError(ValueError):
    pass


def crc16(data):
    crc = 0
    for byte in data:
        for bit in range(8):
            feedback = ((crc >> 15) ^ (byte >> bit)) & 1
            crc = (crc << 1) & 0xffff
            if feedback:
                crc ^= 0x8005
    return crc.to_bytes(2, 'little')


def _packet(opcode, mode=0, parameter=0, payload=b''):
    body = bytes([7+len(payload), opcode, mode]) + parameter.to_bytes(2,'little') + payload
    return body + crc16(body)


def random_command():
    return _packet(0x1b)


def digest_command(digest):
    if type(digest) is not bytes or len(digest) != 32:
        raise ValueError('exactly one SHA256 digest required')
    # ATECC608 Message Digest Buffer, not a random Nonce or a second SHA256.
    return _packet(0x16, 0x43, 0, digest)


def sign_command(slot):
    if type(slot) is not int or not 0 <= slot < 16:
        raise ValueError('personalized key slot must be 0..15')
    return _packet(0x41, 0xa0, slot)


def response(packet, expected_size):
    if type(packet) is not bytes or len(packet) < 4 or packet[0] != len(packet):
        raise DeviceError('invalid device response count')
    if crc16(packet[:-2]) != packet[-2:]:
        raise DeviceError('device CRC mismatch')
    if len(packet) != expected_size:
        raise DeviceError('unexpected response size or device status')
    if expected_size == 4 and packet[1] != 0:
        raise DeviceError('device rejected command')
    return packet[1:-2]


def sign_challenge(transact, challenge, trusted_public_key, *, slot, timeout_ms=1000):
    """Blocking adapter reference; caller holds exclusive device transaction lock.

    transact(command_packet, timeout_ms) returns count..CRC or raises on bus,
    removal, NACK or deadline. No retry/fallback; failures produce no proof.
    Returned proof verifies against the registered key before leaving this API.
    """
    sign = sign_command(slot)
    if type(timeout_ms) is not int or not 1 <= timeout_ms <= 5000:
        raise ValueError('bounded transport timeout required')
    digest = challenge_digest(challenge)
    response(transact(random_command(), timeout_ms), 35)
    response(transact(digest_command(digest), timeout_ms), 4)
    raw = response(transact(sign, timeout_ms), 67)
    r, s = int.from_bytes(raw[:32],'big'), int.from_bytes(raw[32:],'big')
    if not (0 < r < P256_ORDER and 0 < s < P256_ORDER):
        raise DeviceError('invalid signature scalars')
    raw = r.to_bytes(32,'big') + min(s,P256_ORDER-s).to_bytes(32,'big')
    if not verify_proof(trusted_public_key, challenge, raw):
        raise DeviceError('proof does not match registered key and challenge')
    return raw


class DeviceSession:
    """One shared session per physical device; serialized, bounded proof sequence.

    A late response is rejected. Python cannot interrupt a transport that ignores
    its timeout; the real HAL must enforce I/O cancellation and device cleanup.
    Multiple processes must share a device broker, not separate session locks.
    """
    def __init__(self, transact, *, clock=None):
        import threading
        import time
        self._transact = transact
        self._clock = time.monotonic if clock is None else clock
        self._lock = threading.Lock()

    def sign(self, challenge, trusted_public_key, *, slot, total_timeout_ms=1000):
        import math
        if type(total_timeout_ms) is not int or not 1 <= total_timeout_ms <= 5000:
            raise ValueError('bounded total timeout required')
        start = self._clock()
        if not isinstance(start, (int, float)) or not math.isfinite(start):
            raise DeviceError('invalid monotonic clock')
        deadline = start + total_timeout_ms / 1000
        last = start

        def remaining():
            nonlocal last
            now = self._clock()
            if not isinstance(now, (int, float)) or not math.isfinite(now) or now < last:
                raise DeviceError('invalid or reversed monotonic clock')
            last = now
            if now >= deadline:
                raise TimeoutError('secure-element sequence deadline')
            return max(1, int((deadline-now)*1000))

        if not self._lock.acquire(timeout=remaining()/1000):
            raise TimeoutError('secure-element busy deadline')
        try:
            def bounded(command, unused_timeout):
                result = self._transact(command, remaining())
                remaining()  # reject a HAL response returned at/after deadline
                return result
            proof = sign_challenge(bounded, challenge, trusted_public_key, slot=slot,
                                   timeout_ms=total_timeout_ms)
            remaining()  # include local validation time before releasing proof
            return proof
        finally:
            self._lock.release()
