"""Proposed fixed-width proof transcript. No signing, secrets or login grant.

All integers use unsigned big endian. No caller-controlled JSON serialization
or text normalization participates in the signed hash. Server reconstructs it.
"""
from dataclasses import dataclass
import hashlib
import struct
from protocol import validate_uid

DOMAIN = b'FIRM-CARD-PROOF\x00'
TRANSCRIPT_VERSION = 1
TRANSCRIPT_SIZE = 123


@dataclass(frozen=True)
class Challenge:
    key_id: bytes          # 8-byte registry lookup, not a credential
    challenge_id: bytes    # 16 opaque bytes
    nonce: bytes           # 32 server CSPRNG bytes; fixtures are not real nonces
    account_id: bytes      # 16-byte server account UUID representation
    steam_id: int          # authenticated server-side Steam identity
    uid: str               # exact ten ASCII digits, including leading zeroes
    app_id: int
    audience_id: int       # server registry: distinguish production/staging
    expires_at: int        # uint64 UTC Unix seconds, server checked


def encode_challenge(value: Challenge) -> bytes:
    for field, width in (('key_id', 8), ('challenge_id', 16), ('nonce', 32), ('account_id', 16)):
        data = getattr(value, field)
        if type(data) is not bytes or len(data) != width:
            raise ValueError(f'{field}: expected {width} bytes')
    for field, bits in (('steam_id', 64), ('app_id', 32), ('audience_id', 32), ('expires_at', 64)):
        data = getattr(value, field)
        if type(data) is not int or not 0 < data < (1 << bits):
            raise ValueError(f'{field}: expected nonzero uint{bits}')
    result = (DOMAIN + bytes([TRANSCRIPT_VERSION]) + value.key_id + value.challenge_id
              + value.nonce + value.account_id + struct.pack('>Q', value.steam_id)
              + validate_uid(value.uid).encode('ascii')
              + struct.pack('>IIQ', value.app_id, value.audience_id, value.expires_at))
    if len(result) != TRANSCRIPT_SIZE:
        raise AssertionError('transcript layout drift')
    return result


def challenge_digest(value: Challenge) -> bytes:
    return hashlib.sha256(encode_challenge(value)).digest()
