# Registered I2C phase authorization candidate

The actual4de357e gate-level run43649550562/job132619928078 fails its first
identity request. Retained wire data shows a correct C1/04/11/33/43 wake read,
then no complete STOP; the CARD eventually reports F0/2A/07/00. At the final
byte, received changes3→4 and the shared transaction state clears to idle rather
than completing STOP. Native RTL passed, so RTL success alone did not qualify
this build. The full failing waveform is retained, with read-only probe results
in deliverables/gl-wire-debug and the original failed job log preserved.

Raw counter/context/timer decoders previously entered asynchronous child-reset
and physical I2C output enable paths. Replace that phase authorization with six
explicitly kept register bits in the session, wake and command controllers.
Assert/release each grant on the original state-transition/request/STOP events.
All existing abort, removal, context, timer fault and deadline checks retain
their clocked priority and failure codes; payload acceptance stays guarded.
Grant/state consistency is additionally checked. Idle busy masking prevents an
inactive grant from driving a pin. This candidate requires new actual GL and
physical validation before the issue can be declared resolved.

`check_grants.py` runs the complete23-source CARD TT, flips each grant during its
active phase, requires the owner to close within8 clocks, and checks a successful
subsequent identity transaction without external recovery reset. Its three real
source mutants disable the session, wake or command grant-consistency checks;
each must trip the prompt-closure assertion. The original15+5 CARD identity and
31-case complete TT suites remain; software fixtures are not device validation.

The new GL orchestration retains the original full RTL test. GL executes two
chains concurrently: identity→proof→bad-CRC→identity recovery, and recreated
identity/context→late mismatch→proof recovery→partial frame/ENA isolation→proof.
Together they preserve every original operation/assertion, replaying one boundary
precondition. Measured old GL rate51.44ms/2865s predicts the original465.90ms
sequence would exceed the hosted6h cap. Each child owns its FST/XML/log; the
unmodified official GL action checks aggregate results.xml and uploads every
child file in output/**. Empty, missing, malformed, skipped, failed and nonzero
children cannot pass. The control-plan audit compares both chains to the exact
original operation sequence. No hardware deadline or test condition is relaxed.

Reproduce grant-fault tests using Icarus or add --cvc /path/to/cvc64:

```sh
python3 -B experimental/gl_reset/check_grants.py --out /tmp/grant-faults
python3 -B test/check_gl_profiles.py
```

The current full CARD source lock now names actual src/firm_core paths rather
than historical experimental aliases. Older experimental designs remain archived.
Full GDS/nine-corner STA/DRC/LVS/Precheck/GL and required CI remain mandatory.
Physical testing stays deferred because user test capability is unavailable.
