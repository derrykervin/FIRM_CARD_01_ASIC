"""Single-process challenge reference, NOT a deployed backend/device adapter.

Inputs named trusted_* must come from server-side Steam/binding checks, never
request JSON. Production requires shared transactional storage and durable audit.
Any proof attempt consumes its challenge, including invalid proofs (fail closed).
"""
from dataclasses import dataclass
from threading import Lock
import secrets
from auth_transcript import Challenge, encode_challenge
from proof_signature import verify_proof


@dataclass(frozen=True)
class TrustedContext:
    account_id: bytes
    steam_id: int
    uid: str
    app_id: int
    audience_id: int
    key_id: bytes
    binding_version: int


class ChallengeStore:
    def __init__(self, *, clock, ttl=60, capacity=1024):
        if type(ttl) is not int or not 1 <= ttl <= 120:
            raise ValueError('ttl must be 1..120 seconds')
        if type(capacity) is not int or capacity < 1:
            raise ValueError('capacity must be positive')
        self.clock, self.ttl, self.capacity = clock, ttl, capacity
        self._pending, self._lock = {}, Lock()
        self._last_time = 0

    def _now(self):
        now = self.clock()
        if type(now) is not int or now <= 0 or now < self._last_time:
            # A rollback must never extend validity of outstanding proofs.
            self._pending.clear()
            raise ValueError('invalid or rolled-back server clock')
        self._last_time = now
        return now

    def issue(self, trusted_context, *, trusted_eligible):
        if trusted_eligible is not True:
            raise PermissionError('Steam ownership, card status and binding required')
        if type(trusted_context) is not TrustedContext or type(trusted_context.binding_version) is not int or trusted_context.binding_version < 1:
            raise ValueError('versioned trusted context required')
        with self._lock:
            now = self._now()
            self._pending = {k:v for k,v in self._pending.items() if v[0].expires_at > now}
            if len(self._pending) >= self.capacity:
                raise RuntimeError('challenge capacity reached')
            challenge_id = secrets.token_bytes(16)
            if challenge_id in self._pending:
                raise RuntimeError('challenge identifier collision')
            c = trusted_context
            challenge = Challenge(c.key_id, challenge_id, secrets.token_bytes(32),
                                  c.account_id, c.steam_id, c.uid, c.app_id,
                                  c.audience_id, now+self.ttl)
            encode_challenge(challenge)  # validate before persisting
            self._pending[challenge_id] = (challenge, c)
            return challenge

    def consume(self, challenge_id, signature, *, trusted_context,
                trusted_public_key, trusted_eligible):
        if type(challenge_id) is not bytes or len(challenge_id) != 16:
            return False
        with self._lock:
            try:
                now = self._now()
            except ValueError:
                return False
            entry = self._pending.pop(challenge_id, None)
            if entry is None:
                return False
            challenge, issued_context = entry
            if (trusted_eligible is not True or type(trusted_context) is not TrustedContext
                    or issued_context != trusted_context or now >= challenge.expires_at):
                return False
            # Verify exactly the stored transcript. Never accept a client nonce,
            # expiry or account as a replacement; public key is registry-resolved.
            return verify_proof(trusted_public_key, challenge, signature)
