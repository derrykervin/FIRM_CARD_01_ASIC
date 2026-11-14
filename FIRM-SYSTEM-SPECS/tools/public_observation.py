"""Untrusted84-byte CARD readback, not factory attestation or a login proof."""
from dataclasses import dataclass
from cryptography.hazmat.primitives.asymmetric import ec

@dataclass(frozen=True)
class PublicObservation:
    header:bytes
    public_xy:bytes

    @property
    def serial(self):
        return self.header[:4]+self.header[8:13]

    @classmethod
    def from_bytes(cls,raw):
        if type(raw)is not bytes or len(raw)!=84:
            raise ValueError('exact84-byte header/public observation required')
        obj=cls(raw[:20],raw[20:])
        if obj.serial in (bytes(9),b'\xff'*9):
            raise ValueError('blank serial observation')
        # Only fields actually returned on the wire can be checked here. Do not
        # fabricate the remaining108 configuration bytes or infer silicon origin.
        if obj.header[4:7]!=b'\0\0\x60' or obj.header[19]&0xf9 or obj.header[16]!=0xc0 or not obj.header[14]&1:
            raise ValueError('unsupported observed header profile')
        ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(),b'\x04'+obj.public_xy)
        return obj

    def validate(self):
        return self.from_bytes(self.header+self.public_xy)
