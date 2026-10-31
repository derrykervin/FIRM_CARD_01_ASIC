"""Proposed v2 framing reference. Not yet implemented in CARD/READER RTL."""
from dataclasses import dataclass
import binascii
import struct

MAGIC = b'\xA5\x5A'
VERSION = 2
MAX_PAYLOAD = 128

@dataclass(frozen=True)
class Frame:
    sequence: int
    command: int
    payload: bytes = b''
    flags: int = 0

def encode(frame: Frame) -> bytes:
    if not 0 <= frame.sequence <= 65535 or not 0 <= frame.command <= 255:
        raise ValueError('field range')
    if frame.flags not in (0, 1) or len(frame.payload) > MAX_PAYLOAD:
        raise ValueError('flags or length')
    body = struct.pack('>BBHBH', VERSION, frame.flags, frame.sequence,
                       frame.command, len(frame.payload)) + frame.payload
    return MAGIC + body + struct.pack('>H', binascii.crc_hqx(body, 0xFFFF))

def decode(packet: bytes) -> Frame:
    if len(packet) < 11 or packet[:2] != MAGIC:
        raise ValueError('frame boundary')
    version, flags, seq, command, size = struct.unpack('>BBHBH', packet[2:9])
    if version != VERSION or flags not in (0, 1):
        raise ValueError('version or flags')
    if size > MAX_PAYLOAD or len(packet) != size + 11:
        raise ValueError('length')
    if binascii.crc_hqx(packet[2:-2], 0xFFFF) != int.from_bytes(packet[-2:], 'big'):
        raise ValueError('CRC')
    return Frame(seq, command, packet[9:-2], flags)

def validate_uid(uid: str) -> str:
    if len(uid) != 10 or any(c not in '0123456789' for c in uid):
        raise ValueError('UID must be ten ASCII decimal digits')
    return uid

def mod97_check_digits(first14: str) -> str:
    if len(first14) != 14 or any(c not in '0123456789' for c in first14):
        raise ValueError('expected fourteen ASCII digits')
    return f'{98 - int(first14 + "00") % 97:02d}'

def valid_printed_number(number: str) -> bool:
    return (len(number) == 16 and all(c in '0123456789' for c in number)
            and number[-2:] == mod97_check_digits(number[:14]))
