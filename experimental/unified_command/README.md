# Shared command producer and transport owner

Experimental only; formal src/info.yaml/main/C0 are unchanged. Base c39bdb0861b293da83b8e3e0a1e17a5994f9d44d. This package extends the RAM candidate's three-command engine to support Config32 READ blocks 0..3 and slot-2 GenKey PUBLIC. There is one producer CRC/index/deadline and one command exchange, rather than adding the previous independent identity engine.

Operation map: 0 Random, 1 Nonce digest-buffer passthrough, 2 external Sign, 3 Config32 READ, 4 GenKey PUBLIC=0. Operations 5..7 reject. GenKey private mode 4 is absent from the normal path and is only a defect-injection test. Public readbacks require the proposed slot-2 profile; this does not authorize or validate provisioning. `config_block` is captured at request acceptance. Payload is tentative until count/CRC/STOP and producer completion pass.

The standalone default captures the digest. `CAPTURE_DIGEST=0` is only valid when the parent holds it immutable through completion; both modes are tested, including a resolved-bus owner case without duplicate digest storage. `ENABLE_READBACK=0` in the producer retains the original three-command behavior for binary operation inputs; deterministic dual-instance tests compare every output (including stalled data) over 39,960 checked cycles per simulator. This is simulation, not a formal equivalence proof.

Original Microchip cryptoauthlib commit d49c7d578efb09d4a498d5ab86839d4c17812f15 packet structures, CRC and five command constructor functions compile unchanged in a small native C harness. Vendor files with licenses are archived in deliverables/unified-command/vendor, hash checked including device-type/status headers. The harness uses ATECC608=3, little-endian host layout, and the original status values; it is not a whole-SDK, HAL, physical device or cryptographic validation. Responses contain arbitrary wire fixtures, including an unvalidated public-key payload. M0 timing table values Random23/Nonce20/Sign115/Read5/GenKey115 ms are SDK estimates, not silicon/PVT guarantees.

Each Icarus/CVC matrix has 19 configurations: eight normal configurations (223 completed cases, including divider 1/2/8/100, attempts 1/20, external bus and capture-disabled owner), and 11 real RTL defects that must trigger specific assertions. Each direct suite has two capture modes (15 probes each), five unsupported-slot configurations (two readback rejections each), and two legacy compatibility configurations. Each slow suite checks eight commands at 40MHz, an old-20-poll public-read failure, and an independently detected premature-ACK model. No 100% statement coverage claim.

With the same pinned Yosys/Liberty+LEF, all generic FF retained, CAPTURE_DIGEST=0 and both old/new owners set to 128 attempts:

| Block | Legacy FF / µm² | Unified FF / µm² | Added µm² |
|---|---:|---:|---:|
| Producer | 51 / 4220.2976 | 54 / 4397.9680 | 177.6704 |
| Internal-bus owner | 466 / 24050.5664 | 469 / 24233.2416 | 182.6752 |
| External-bus owner | 312 / 16737.3024 | 315 / 16902.4608 | 165.1584 |

These are same-boundary comparisons, not whole CARD increments. Do not sum either owner onto CARD or claim a tile fit. CARD remains the RAM candidate's 1450 FF / 64847.1936 µm² until integrated and remeasured. The prior separate readback block used different digest/timing/port boundaries and is not a directly interchangeable area baseline.

Run with PATH=/workspace/toolchain/owner-ci-native/launch:$PATH:

```
python -B experimental/unified_command/check_exchange.py --output <matrix>
python -B experimental/unified_command/check_direct.py --output <direct>
python -B experimental/unified_command/check_slow.py --output <slow>
# Add --cvc /workspace/toolchain/cvc-source/build64/cvc64 for each CVC suite.
python -B tools/measure_unified_command.py --output <mapping> --library /workspace/toolchain/pr11-synthesis/pdk
python -B experimental/unified_command/verify.py --base /workspace/deliverables/unified-command --output <verification.json>
```

Still pending: automatic pre-read → Random/Nonce/Sign → post-read 13-command CARD sequence; actual configuration/lock/serial/key validation and atomic transcript binding; Reader/HAL/server integration, device wake/selection and factory acceptance; full CARD measurement and official required CI, numeric clock STA, P&R/DRC/LVS/Precheck/GL and official submission. Physical tests remain DEFERRED_BY_USER, with electrical/mechanical risks retained. This engine does not establish identity, attestation, nonextractable keys or secure login by itself.
