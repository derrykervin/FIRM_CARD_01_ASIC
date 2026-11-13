# Integrated thirteen-command observation candidate

Experimental branch based on 400d8e08d8514004e1d576df3d3b6e8f351f9c45. Formal src/info.yaml/main and the submitted C0 are untouched. `stage.py` replaces the RAM candidate's three-command session and two typed command modules in a hash-locked 22-file full CARD tree (the unchanged RAM base is included under base_source for reproducibility). The CPU scratch RAM, boot checks, fixed service ROM, MMIO ownership, UART request guards and shared wake/I2C transport remain present.

After wake, steps 0..12 are Config32 blocks 0..3, GenKey PUBLIC, Random, Nonce digest buffer, Sign, Config32 blocks 0..3, GenKey PUBLIC. The parent commits only after all thirteen checked packets, exact payload lengths, the completion mask and exactly 64 provisional signature bytes pass. Sign payload bytes still reach the host provisionally; a later readback/CRC/removal/deadline failure means the host must discard them. No signature or secure-login success is asserted by this hardware.

The proposed slot-2 profile mirrors the existing software reference: revision bytes 4..6 = 00/00/60; enabled fixed I2C address 0x60; supported M0 clock bits; canonical config/data locks 0; slot2 individually locked; SlotConfig=2087 and KeyConfig=0033. All-zero/all-FF serials reject. Failed prechecks stop before Sign. Public backing stores the 20-byte immutable header and 64-byte public X||Y for exact post-read comparison, without replacing them with CRC/XOR hashes. Unrelated slots/counters are not compared as immutable snapshots. Backing is public and unreset; request state, count and packet checks govern validity. Reset/abort invalidation is not physical erasure.

Only slot2/address0x60 qualify. Standalone digest capture remains the default; the CARD's MMIO owner holds the request digest stable with child copies disabled. The original shared owner deadline and its fault checks remain in use. A sequence-completion mask prevents silently skipping post-observation steps. The session's one-second total budget covers the whole flow; command budgets remain 200 ms, M0 SDK timing estimates are not silicon/PVT guarantees, and no check is waived.

Digital evidence in deliverables/personalized-session:

- Each Icarus/CVC session qualification combines six normal configurations (DIV1/2/8/100, attempts1/3, shared/unshared resources; 166 completed cases) and eight actual RTL defect controls. The final sequence/early-return controls are separate recorded runs. A skipped-step mutant is detected first by the exact wrong wire opcode, before the later completion assertion; the initial driver expected the later assertion and is retained as a harness failure.
- Both tools exhaust 32,768 single-byte config mutations against the proposed Python policy and test all 672 individual header/public-key comparison bits. This checks agreement, not device or factory approval.
- Full CARD CVC: CPB16/DIV2, CPB32/DIV8 and CPB434/DIV100, 31 completed UART/CPU/MMIO/I2C cases each; plus three real mutations (premature commit, wrong digest, skipped post-read). Icarus runs the full 31-case CPB16/DIV2 suite. Current Reader RTL is not part of these runs.
- Full CARD CVC at 40 MHz: all thirteen actual command STOP/ACK windows respect SDK M0 estimates (Read5, GenKey115, Random23, Nonce20, Sign115 ms); old20 polls fail before Sign, a premature-ACK model rejects, and a last-key mismatch after all signature bytes fails then recovers without external reset.
- Original Microchip C constructors and CRC at pinned d49c7d578efb09d4a498d5ab86839d4c17812f15 compile with strict warnings and match all 26 commands across two digest contexts. Curve-valid public fixtures come from known test scalars; signature-shaped fixture bytes are not valid proofs, and no secure device crypto is modeled or validated.

Same full CARD boundary, pinned Yosys/Liberty+LEF, every generic FF retained:

| Candidate | FF | Standard-cell area µm² |
|---|---:|---:|
| Prior RAM / three commands | 1450 | 64847.1936 |
| Thirteen commands / exact observations | 2150 | 92003.2384 |

The added 700 FF comprise 160 header + 512 public bits and 28 net metadata bits. All other 1446 FF match one-to-one by common named Q alias; this is structural accounting, not formal equivalence. Area increases by 27156.0448 µm². Against whole tile rectangles, 3×2 is approximately 80.10% and 4×2 approximately 59.70%; routing, power, fillers, constraints and physical margins are not included. Original 1×2 and 2×2 rectangles are smaller than this cell area. No larger tile allocation, price, purchase or physical fit is confirmed.

Reproduce with the pinned native toolchain PATH, using `check_session.py`, `check_card.py` (`--slow` for M0), `check_profile.py` (each also accepts `--cvc`), `check_vendor_packets.py <output>`, and `tools/measure_personalized_session.py --output <mapping> --library /workspace/toolchain/pr11-synthesis/pdk`. `tools/check_personalized_storage.py --mapping <mapping>` checks the FF partition. `verify.py --output <json>` rejects missing/mismatched evidence.

The current Reader formal entry uses a shared 40MHz external clock and CPB347. A supplementary full-CARD M0 run uses CPB347 for all thirteen commands. The experimental CARD default remains CPB434; final TT wrapper parameter/pin alignment is pending, and no new Reader RTL joint test is claimed.

Clock-only 25 ns SDC and OpenSTA report script are prepared for the exact new 2150-FF netlist, with all generic FF clock pins checked against the real top clock and nine corrupt-manifest controls. Native STA has not run; WNS/TNS remain null. IO/reset budgets and RC are explicitly missing, with no timing exceptions or disabled checks. Use `prepare_clock.py --inputs <clock-inputs.json> --output <fresh-folder>` and `check_clock.py` for preparation checks. This is not numeric timing evidence.

Still required: approved real device SKU/factory profile, trusted registered-factory facts and UID/key binding (the current hardware compares observations to each other, not to a trusted factory record), actual cryptographic verification and one-time server challenge path through Reader/HAL, current Reader joint regression, numeric clock STA, synthesis/physical official required CI, P&R/DRC/LVS/Precheck/GL and live official submission. Public readbacks are not attestation or proof of private-key nonextractability. Hardware tests remain DEFERRED_BY_USER with electrical/mechanical risks retained. Both formal chips remain INCOMPLETE / NOT_SUBMITTED.
