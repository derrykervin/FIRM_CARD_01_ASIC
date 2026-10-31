"""Software reference only: P-256 signature formatting and verification.

Caller supplies a trusted registered public key. A valid signature alone does
not establish Steam ownership, freshness, binding, revocation or a login session.
"""
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, utils
from auth_transcript import challenge_digest

P256_ORDER = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551


def der_to_wire(signature):
    """Convert a device/library DER signature to fixed r||s with low-S."""
    r, s = utils.decode_dss_signature(signature)
    if not (0 < r < P256_ORDER and 0 < s < P256_ORDER):
        raise ValueError('signature scalar outside P-256 order')
    s = min(s, P256_ORDER-s)
    return r.to_bytes(32, 'big') + s.to_bytes(32, 'big')


def wire_to_der(signature):
    if type(signature) is not bytes or len(signature) != 64:
        raise ValueError('expected 64-byte P-256 signature')
    r = int.from_bytes(signature[:32], 'big')
    s = int.from_bytes(signature[32:], 'big')
    if not (0 < r < P256_ORDER and 0 < s <= P256_ORDER//2):
        raise ValueError('invalid or noncanonical P-256 signature')
    return utils.encode_dss_signature(r, s)


def verify_proof(public_key, challenge, signature):
    if not isinstance(public_key, ec.EllipticCurvePublicKey) or not isinstance(public_key.curve, ec.SECP256R1):
        return False
    try:
        public_key.verify(wire_to_der(signature), challenge_digest(challenge),
                          ec.ECDSA(utils.Prehashed(hashes.SHA256())))
        return True
    except (ValueError, InvalidSignature):
        return False
