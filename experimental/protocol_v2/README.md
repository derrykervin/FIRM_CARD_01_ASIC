# Experimental receive RTL — UNVALIDATED

This module is deliberately outside `src` and the TinyTapeout source list.
It has not been simulated, synthesized, timed, placed or integrated with either
ASIC. It is not a release candidate and does not implement secure authentication.

Run `bash experimental/protocol_v2/check.sh` from the repository root.
The Python generator derives frame bytes and expected payloads from the framing
reference; the HDL scoreboard compares every published field, not just CRC status.
CRC rejects, header rejects, idle timeout, total timeout and clear recovery are
included. No HDL results are claimed until this command actually passes.

`byte_valid` must pulse for one clock per received UART byte. `clear` cancels
partial input and clears published data on card removal/framing errors. Timeout
parameters are positive cycle counts, defaulting to 20ms/100ms at 40MHz.
`frame_valid` is one cycle; consumer must capture it immediately. No backpressure
or FIFO is provided. Payload byte zero occupies bits [7:0]. CRC covers header and
payload with CCITT-FALSE parameters. `error_valid` pulses with diagnostic code
1 timeout, 2 header, 3 length, 4 CRC. Stale published data is not a valid frame.

The 1024-bit candidate plus 1024-bit published payload buffers are intentionally
an executable staging interface, NOT an area-qualified 1x2 tile implementation.
Before integration, select a bounded command-specific buffer/streaming consumer,
prove atomic publication, establish area/timing and test exact timeout boundaries.
This work cannot replace the security-device interface, personalization or dynamic
server challenge path. Existing production sources and C0 are unaffected.

`python3 -B experimental/protocol_v2/check_vectors.py` independently replays
stimulus against the Python receive reference. It checks 10 expected frames and
rejects malformed scoreboard expectations, but does not execute HDL or prove
hardware error pulse counts, clearing of published registers, cycle boundaries,
area or timing. The combined runner performs this check before probing HDL tools.
