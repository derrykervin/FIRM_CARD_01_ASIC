"""Read-only ATECC608 M0 personalization reference, NOT a real device/HAL validation.

Factory authorization, Steam checks and binding context are server-resolved inputs,
never client JSON. Configuration CRC/serial/public key are not device attestation.
The current ASIC ROM still has only Random/Nonce/Sign; this reference's readback
commands are not integrated into that RTL. No provisioning writes are issued.
"""
from dataclasses import dataclass
from threading import Lock, RLock
import math
import time
from cryptography.hazmat.primitives.asymmetric import ec
from atecc608_codec import DeviceSession, DeviceError, response, _packet
from challenge_store import TrustedContext
from auth_transcript import Challenge, encode_challenge


SUPPORTED_SLOT = 2
SUPPORTED_SLOT_CONFIG = 0x2087
# Strict proposed profile: private P256, public-key calculation, individually
# lockable; no ReqAuth/ReqRandom flow, which this reference does not implement.
SUPPORTED_KEY_CONFIG = 0x0033


def config_read_command(block):
    if type(block) is not int or not 0 <= block < 4:
        raise ValueError('configuration block must be 0..3')
    return _packet(0x02, 0x80, block << 3)


def public_key_command(slot):
    if type(slot) is not int or slot != SUPPORTED_SLOT:
        raise ValueError('only the current slot-2 RTL profile is qualified')
    # GenKey PUBLIC=0: calculation only, never private-key generation mode 4.
    return _packet(0x40, 0, slot)


@dataclass(frozen=True)
class ConfigurationFacts:
    header: bytes
    slot_config: int
    key_config: int
    slot: int

    @property
    def serial(self):
        return self.header[:4] + self.header[8:13]


def configuration_facts(config, *, slot=SUPPORTED_SLOT):
    if type(config) is not bytes or len(config) != 128:
        raise DeviceError('exact 128-byte configuration required')
    public_key_command(slot)
    if config[4:7] != b'\0\0\x60':
        raise DeviceError('unsupported revision family; only the pinned 608 family profile')
    if config[19] & 0xf8:
        raise DeviceError('only observed M0 clock divider is supported')
    if config[19] & 1 or config[16] != 0xc0 or not config[14] & 1:
        raise DeviceError('fixed 7-bit I2C address 0x60 must be enabled')
    if config[86:88] != b'\0\0':
        raise DeviceError('config and data zones must be locked with canonical 0')
    if int.from_bytes(config[88:90], 'little') & (1 << slot):
        raise DeviceError('personalized private-key slot must be individually locked')
    slot_word = int.from_bytes(config[20+2*slot:22+2*slot], 'little')
    key_word = int.from_bytes(config[96+2*slot:98+2*slot], 'little')
    if slot_word != SUPPORTED_SLOT_CONFIG or key_word != SUPPORTED_KEY_CONFIG:
        raise DeviceError('unsupported signing/key policy; no silent fallback')
    serial = config[:4] + config[8:13]
    if serial in (b'\0'*9, b'\xff'*9):
        raise DeviceError('invalid serial number')
    # Hardware counters and unrelated slots can change legitimately. Bind the
    # immutable header and selected policy; never treat the full config as an
    # immutable counter snapshot or CRC as authentication of physical silicon.
    return ConfigurationFacts(config[:20], slot_word, key_word, slot)


def public_key_from_xy(raw):
    if type(raw) is not bytes or len(raw) != 64:
        raise DeviceError('P256 public X||Y must be 64 bytes')
    try:
        return ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), b'\x04'+raw)
    except ValueError as e:
        raise DeviceError('invalid P256 point') from e


@dataclass(frozen=True)
class FactoryRecord:
    uid: str
    key_id: bytes
    config: bytes
    public_xy: bytes
    slot: int = SUPPORTED_SLOT

    @property
    def facts(self):
        return configuration_facts(self.config, slot=self.slot)

    @classmethod
    def from_factory(cls, *, uid, key_id, config, public_xy, slot=SUPPORTED_SLOT):
        if type(uid) is not str or len(uid) != 10 or not uid.isascii() or not uid.isdecimal():
            raise ValueError('exact ASCII 10-digit UID required')
        if type(key_id) is not bytes or len(key_id) != 8:
            raise ValueError('8-byte registry lookup key ID required')
        public_key_from_xy(public_xy)
        configuration_facts(config, slot=slot)
        return cls(uid, key_id, config, public_xy, slot)

    def validate(self):
        return self.from_factory(uid=self.uid, key_id=self.key_id, config=self.config, public_xy=self.public_xy, slot=self.slot)

    def public_key(self):
        return public_key_from_xy(self.public_xy)


class _Budget:
    def __init__(self, clock, milliseconds):
        if type(milliseconds) is not int or not 1 <= milliseconds <= 1000:
            raise ValueError('bounded total timeout required')
        self.clock = clock
        self.last = self._sample()
        self.deadline = self.last + milliseconds/1000

    def _sample(self):
        now = self.clock()
        if type(now) not in (int, float) or not math.isfinite(now):
            raise DeviceError('invalid monotonic clock')
        return now

    def remaining(self):
        now = self._sample()
        if now < self.last:
            raise DeviceError('reversed monotonic clock')
        self.last = now
        if now >= self.deadline:
            raise TimeoutError('personalized session total deadline')
        return max(1, int((self.deadline-now)*1000))


class PersonalizedDeviceSession:
    """One broker per device. Entire pre-read/proof/post-read shares one budget/lock.

    The real HAL must implement wake, bounded/cancellable I/O, removal and cleanup.
    This synchronous Python reference can reject a late return but cannot interrupt
    an uncooperative HAL, establish physical origin or attest slot non-extractability.
    """
    def __init__(self, transact, *, clock=None):
        self._transact = transact
        self._clock = time.monotonic if clock is None else clock
        self._lock = Lock()

    def sign(self, challenge, record, *, total_timeout_ms=1000):
        if type(record) is not FactoryRecord or type(challenge) is not Challenge:
            raise ValueError('trusted factory record and challenge required')
        if challenge.uid != record.uid or challenge.key_id != record.key_id:
            raise DeviceError('challenge does not identify the registered card')
        record.validate()
        encode_challenge(challenge)
        budget = _Budget(self._clock, total_timeout_ms)
        if not self._lock.acquire(timeout=budget.remaining()/1000):
            raise TimeoutError('device broker busy deadline')
        try:
            def bounded(command, unused_timeout=None):
                timeout = min(200, budget.remaining())
                command_deadline = budget.last + timeout/1000
                packet = self._transact(command, timeout)
                budget.remaining()
                if budget.last >= command_deadline:
                    raise TimeoutError('M0 command deadline exceeded')
                return packet

            def observe():
                config = b''.join(response(bounded(config_read_command(block)), 35) for block in range(4))
                if configuration_facts(config, slot=record.facts.slot) != record.facts:
                    raise DeviceError('factory configuration/serial identity mismatch')
                raw = response(bounded(public_key_command(record.facts.slot)), 67)
                public_key_from_xy(raw)
                if raw != record.public_xy:
                    raise DeviceError('registered public key does not match readback')

            observe()
            proof = DeviceSession(bounded, clock=self._clock).sign(
                challenge, record.public_key(), slot=record.facts.slot,
                total_timeout_ms=budget.remaining())
            # Removal/identity changes after Sign must not release a proof.
            observe()
            budget.remaining()
            return proof
        finally:
            self._lock.release()


class PersonalizedRegistry:
    """In-memory server reference, not deployed enrollment or shared durable storage.

    Enrollment and rebind require a trusted factory/admin decision. CRC readback
    alone cannot authorize enrollment. Never accept a client-provided public key
    during proof consumption; resolve it by the stored factory record instead.
    All registry operations and challenge transitions share this registry lock.
    """
    def __init__(self):
        self._lock = RLock()
        self._cards = {}

    @staticmethod
    def _binding(context):
        if type(context) is not TrustedContext:
            raise ValueError('server trusted context required')
        if type(context.binding_version) is not int or context.binding_version < 1:
            raise ValueError('positive binding version required')
        encode_challenge(Challenge(context.key_id, b'I'*16, b'N'*32, context.account_id, context.steam_id, context.uid, context.app_id, context.audience_id, 1))
        # App/audience remain server-checked per request and are transcript-bound;
        # a card can legitimately access more than one eligible app/audience.
        return (context.account_id, context.steam_id, context.uid, context.key_id, context.binding_version)

    def enroll(self, record, context, *, trusted_factory_authorized):
        if trusted_factory_authorized is not True:
            raise PermissionError('authenticated factory authorization required')
        if type(record) is not FactoryRecord:
            raise ValueError('factory record required')
        binding = self._binding(context)
        if context.uid != record.uid or context.key_id != record.key_id:
            raise ValueError('record/binding identity mismatch')
        # Revalidate manually constructed records; dataclass type is not evidence.
        record.validate()
        with self._lock:
            for previous, _, _ in self._cards.values():
                if (previous.key_id == record.key_id or previous.uid == record.uid
                        or previous.facts.serial == record.facts.serial
                        or previous.public_xy == record.public_xy):
                    raise ValueError('duplicate/colliding key ID, UID, serial or public key')
            self._cards[record.key_id] = (record, binding, False)

    def revoke(self, key_id, *, trusted_authorized):
        if trusted_authorized is not True:
            raise PermissionError('trusted revocation authorization required')
        with self._lock:
            record, binding, _ = self._cards[key_id]
            self._cards[key_id] = (record, binding, True)

    def rebind(self, key_id, context, *, trusted_authorized):
        if trusted_authorized is not True:
            raise PermissionError('trusted rebinding authorization required')
        binding = self._binding(context)
        with self._lock:
            record, old_binding, revoked = self._cards[key_id]
            if revoked or context.key_id != key_id or context.uid != record.uid or context.binding_version != old_binding[-1]+1:
                raise ValueError('revoked or invalid versioned rebind')
            self._cards[key_id] = (record, binding, False)

    def _current(self, context):
        if type(context) is not TrustedContext:
            return None
        self._binding(context)
        entry = self._cards.get(context.key_id)
        if entry is None or entry[2] or self._binding(context) != entry[1]:
            return None
        return entry[0]

    def issue(self, store, context, *, trusted_ownership):
        with self._lock:
            eligible = trusted_ownership is True and self._current(context) is not None
            return store.issue(context, trusted_eligible=eligible)

    def consume(self, store, challenge_id, signature, *, context, trusted_ownership):
        with self._lock:
            try:
                record = self._current(context)
            except (ValueError, TypeError):
                record = None
            return store.consume(challenge_id, signature, trusted_context=context,
                                 trusted_public_key=None if record is None else record.public_key(),
                                 trusted_eligible=trusted_ownership is True and record is not None)
