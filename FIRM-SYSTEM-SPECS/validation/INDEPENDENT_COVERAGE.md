# Independently calibrated Reader-host point coverage

The previous CVC statement sentinel remains unqualified. This package adds a
separate Verilator5.032 Debian5.032-1+b2 measurement path, leaving the original
simulators, all product RTL, clocks, deadlines and required manufacturing CI
unchanged. It does not upgrade the release coverage gate to PASS.

The tool is staged only under the workspace. Debian Release signatures were
verified with sqv and the system Debian archive keyring; Release→Packages.xz→deb
SHA256/size checks match. The lock JSON records package/binary hashes, public
signature fingerprints and the unchanged publisher license file hash. The
package license is Artistic2.0 or LGPL3; the package and license remain in the
local tool directory. No claim of an upstream reproducible build is made.

The known hit/miss probe checks functional values and distinguishes three
executed/nonexecuted line groups plus all16 bits of a two-element unpacked
array. Seven controls reject swapped/all-hit/all-miss and malformed data.
Verilator reports basic-block line groups and branch points, and undirected
toggle counts; these are not all source statements or directional CVC bins.
Two-state simulation does not establish X/Z behavior.

`tools/run_independent_reader_coverage.py` rechecks the9 formal Reader source
files against its pinned Git tree and measures two actual modules:
firm_frame_rx and firm_host_proof_bridge at Readerbae4732. It runs the unchanged
29-scenario/9-operation host bench with both Verilator and Icarus. It preserves
all14 reviewed PINMISSING/TIMESCALEMOD/WIDTHEXPAND/WIDTHTRUNC diagnostics in the
build log, allows them to remain nonfatal in this supplemental simulator only,
and rejects other warning categories. This is NOT a replacement lint pass or a
waiver of any original required product check. The missing output is the bench's
unused request_identity observation; the original identity/full-system tests
remain separately required.

The runner passes `--coverage-max-width 4096`: Verilator's default256-bit limit omits the
84-byte result array. Increasing instrumentation includes all672 result bits
without changing the RTL. Current observations are448 hit/224 unhit; no unhit
point is removed to improve a percentage. The two measured sources have61/70
line points and50/54 branch points hit in this specific bench. Defensive and
potentially unreachable points remain listed for directed testing/proof.

Example after staging the exact locked package:

```
python3 tools/run_independent_reader_coverage.py \
 --reader READER_DIR --card CARD_DIR --reader-tree reader-source-tree.json \
 --verilator TOOL_DIR/usr/bin/verilator \
 --verilator-root TOOL_DIR/usr/share/verilator \
 --tool-manifest FIRM-SYSTEM-SPECS/validation/locks/verilator-debian-5.032.json \
 --out reports/independent-reader
```

The source-tree JSON is captured through the connected GitHub commit/tree API;
offline input files are not themselves authenticity certificates. Per-run hex
fixtures, source hashes and raw coverage are retained. This measures only two
modules, not the whole Reader, CARD, secure device, factory, production server,
physical card or official TinyTapeout submission. Coverage stays PARTIAL.

The separate directed parser recovery bench adds five checked inputs: sync noise,
repeated sync followed by an invalid version, valid-frame recovery, reserved-flag
rejection, and a second valid-frame recovery. Both Verilator and Icarus observe
exactly two accepted frames and two errors. It uses the same MAX_PAYLOAD32,
BYTE_TIMEOUT160 and FRAME_TIMEOUT1000 parameters as the host bench. Four source
sites previously unhit in the host measurement (two line groups at84 and branch
points at91/94) are now exercised. Statistics remain separate; no cross-bench
percentage or whole-design coverage claim is made. Remaining defensive/default
and timeout points need directed tests or proof rather than removal.
