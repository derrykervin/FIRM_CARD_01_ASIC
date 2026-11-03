import sys
from pathlib import Path
import unittest
from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from cryptography.hazmat.primitives.asymmetric import ec, utils
from cryptography.hazmat.primitives import hashes
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from challenge_store import ChallengeStore, TrustedContext
from auth_transcript import challenge_digest
from proof_signature import der_to_wire


class ChallengeStoreTests(unittest.TestCase):
    def setUp(self):
        self.now = 1800000000
        self.store = ChallengeStore(clock=lambda:self.now, capacity=2)
        self.ctx = TrustedContext(b'A'*16, 76561198000000000, '0000000001',480,1,b'key00001',1)
        self.key = ec.generate_private_key(ec.SECP256R1())  # ephemeral software fixture only

    def issue(self):
        return self.store.issue(self.ctx, trusted_eligible=True)

    def sign(self,c):
        return der_to_wire(self.key.sign(challenge_digest(c), ec.ECDSA(utils.Prehashed(hashes.SHA256()))))

    def consume(self,c,sig=None,**changes):
        args=dict(trusted_context=self.ctx,trusted_public_key=self.key.public_key(),trusted_eligible=True)
        args.update(changes)
        return self.store.consume(c.challenge_id, self.sign(c) if sig is None else sig, **args)

    def test_one_time_and_parallel_replay(self):
        c=self.issue(); sig=self.sign(c)
        with ThreadPoolExecutor(max_workers=8) as pool:
            results=list(pool.map(lambda _:self.consume(c,sig),range(16)))
        self.assertEqual(sum(results),1)

    def test_expiry_boundary_and_rollback(self):
        c=self.issue(); self.now+=60
        self.assertFalse(self.consume(c))
        c=self.issue(); self.now-=1
        self.assertFalse(self.consume(c)); self.now+=2
        self.assertFalse(self.consume(c))

    def test_invalid_attempt_burns_challenge(self):
        for invalid in (b'',b'\0'*64,b'x'*63):
            c=self.issue(); self.assertFalse(self.consume(c,invalid)); self.assertFalse(self.consume(c))

    def test_every_binding_field_rechecked(self):
        for field,value in dict(account_id=b'B'*16,steam_id=self.ctx.steam_id+1,uid='0000000002',
                app_id=481,audience_id=2,key_id=b'key00002',binding_version=2).items():
            c=self.issue()
            self.assertFalse(self.consume(c,trusted_context=replace(self.ctx,**{field:value})))
            self.assertFalse(self.consume(c))

    def test_revocation_and_wrong_registry_key(self):
        c=self.issue();self.assertFalse(self.consume(c,trusted_eligible=False))
        c=self.issue(); other=ec.generate_private_key(ec.SECP256R1()).public_key()
        self.assertFalse(self.consume(c,trusted_public_key=other))
        self.assertFalse(self.consume(c))

    def test_new_challenge_rejects_old_signature(self):
        old=self.issue();new=self.issue()
        self.assertNotEqual(old.challenge_id,new.challenge_id)
        self.assertNotEqual(old.nonce,new.nonce)
        self.assertFalse(self.consume(new,self.sign(old)))
        self.assertTrue(self.consume(old))

    def test_issue_requires_strict_server_eligibility(self):
        for eligible in (False,None,1,'true'):
            with self.assertRaises(PermissionError):self.store.issue(self.ctx,trusted_eligible=eligible)

    def test_capacity_expiry_and_identifier_collision(self):
        c=self.issue()
        with patch('challenge_store.secrets.token_bytes',return_value=c.challenge_id):
            with self.assertRaises(RuntimeError):self.issue()
        self.issue()
        with self.assertRaises(RuntimeError):self.issue()
        self.now+=60;self.issue()

    def test_configuration_and_malformed_context(self):
        for ttl in (0,121,True):
            with self.assertRaises(ValueError):ChallengeStore(clock=lambda:self.now,ttl=ttl)
        with self.assertRaises(ValueError):self.store.issue(replace(self.ctx,uid='1'),trusted_eligible=True)
        with self.assertRaises(ValueError):self.store.issue(replace(self.ctx,binding_version=0),trusted_eligible=True)
        self.assertFalse(self.store.consume([],b'',trusted_context=self.ctx,trusted_public_key=self.key.public_key(),trusted_eligible=True))


if __name__=='__main__': unittest.main()
