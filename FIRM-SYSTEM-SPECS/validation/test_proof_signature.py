import sys
import subprocess
import tempfile
from pathlib import Path
from dataclasses import replace
import unittest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from auth_transcript import Challenge, challenge_digest, encode_challenge
from proof_signature import der_to_wire, wire_to_der, verify_proof, P256_ORDER


class ProofTests(unittest.TestCase):
    def setUp(self):
        # Ephemeral software fixture. Never exported as a production card key.
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.challenge = Challenge(b'key00001', bytes(range(16)), bytes(range(32)),
                                  bytes(range(16,32)), 76561198000000000,
                                  '0000000001', 480, 1, 1800000060)
        self.raw = der_to_wire(self.key.sign(challenge_digest(self.challenge),
                         ec.ECDSA(utils.Prehashed(hashes.SHA256()))))

    def test_software_and_openssl_interoperability(self):
        self.assertTrue(verify_proof(self.key.public_key(), self.challenge, self.raw))
        with tempfile.TemporaryDirectory(prefix='firm-proof-') as directory:
            path = Path(directory)
            (path/'public.pem').write_bytes(self.key.public_key().public_bytes(
                serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
            (path/'signature.der').write_bytes(wire_to_der(self.raw))
            (path/'message.bin').write_bytes(encode_challenge(self.challenge))
            result = subprocess.run(['openssl', 'dgst', '-sha256', '-verify', str(path/'public.pem'),
                '-signature', str(path/'signature.der'), str(path/'message.bin')],capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_tampered_context_and_wrong_key_rejected(self):
        for changed in (replace(self.challenge, nonce=b'X'*32),
                        replace(self.challenge, uid='0000000002'),
                        replace(self.challenge, app_id=481),
                        replace(self.challenge, audience_id=2)):
            self.assertFalse(verify_proof(self.key.public_key(), changed, self.raw))
        other = ec.generate_private_key(ec.SECP256R1()).public_key()
        self.assertFalse(verify_proof(other, self.challenge, self.raw))
        wrong_curve = ec.generate_private_key(ec.SECP384R1()).public_key()
        self.assertFalse(verify_proof(wrong_curve, self.challenge, self.raw))

    def test_high_s_and_invalid_wire_rejected(self):
        r = int.from_bytes(self.raw[:32], 'big')
        s = int.from_bytes(self.raw[32:], 'big')
        high = r.to_bytes(32,'big') + (P256_ORDER-s).to_bytes(32,'big')
        for invalid in (high, b'', b'\x00'*64, b'\xFF'*64, self.raw[:-1]):
            self.assertFalse(verify_proof(self.key.public_key(), self.challenge, invalid))
        self.assertEqual(der_to_wire(utils.encode_dss_signature(r,P256_ORDER-s)), self.raw)

    def test_no_double_hash_acceptance(self):
        # ECDSA(SHA256(digest)) must not verify as ECDSA(prehashed transcript).
        wrong = der_to_wire(self.key.sign(challenge_digest(self.challenge), ec.ECDSA(hashes.SHA256())))
        self.assertFalse(verify_proof(self.key.public_key(), self.challenge, wrong))

    def test_malformed_der_rejected(self):
        for invalid in (b'', b'not DER', utils.encode_dss_signature(0,1),
                        utils.encode_dss_signature(P256_ORDER,1)):
            with self.assertRaises(ValueError):
                der_to_wire(invalid)


if __name__ == '__main__':
    unittest.main()
