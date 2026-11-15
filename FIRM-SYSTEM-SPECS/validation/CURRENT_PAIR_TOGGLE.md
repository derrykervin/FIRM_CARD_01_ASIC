# Current-pair measured toggle supplement

This package observes CARD4ea89ba3d056db4405229a95074044f11587c652 and
Readerbae4732e6c889a0c95f3634a91f820e882fec513. It does not modify either
product branch or replace any manufacturing/functional/coverage gate.

`tools/run_current_pair_toggle.py` checks23 CARD and9 Reader actual info.yaml
sources against freshly fetched Git commit→tree→blob bindings, qualifies the
unchanged pinned compiled CVC with known hit/miss controls, then executes the
existing complete20-case paired TT regression at CPB16 or347. The compiler
wrapper adds DUT toggle instrumentation and preserves the existing test flags,
assertions, simulator/RTL time limits, firmware and vectors. Per-run generated
crypto fixtures are hashed; percentages from separate runs cannot be compared
as identical stimuli or averaged into a suite-wide union.

`tools/parse_current_toggle.py` cross-checks bit counts in the raw tgldat against
the independent report parser, supports multi-line wide vectors, and separates
the actual CARD/Reader hierarchies from bench-only firmware probes and an
uninstantiated default-ROM root. All raw report counts and outside-DUT names
remain available; no untouched DUT bits or required feature are removed to
improve a percentage. Port aliases count as separate declared nets, not unique
physical storage. Empty/malformed/wrong-width/duplicate records and wrong source
bindings are rejected by controls.

The scalar control must report3 bits with exactly one0→1 and one1→0 hit.
The array probe distinguishes whether unpacked arrays are measured. This CVC
build reports only the scalar bit in that probe: **unpacked arrays are not
measured**. Reader result banks, CPU scratch arrays and other unpacked memories
therefore have no complete coverage claim. A re-run of the old statement
sentinel still fails measurement qualification; its statement report must not
be promoted to100% coverage.

The authentication scenario exercises little SPI traffic. The separate
`tools/run_current_spi_toggle.py` uses the existing whole-TT SPI bench to run
three external-MISO high/low/high transfers through actual peripherals. Its
MMIO injection is explicit; it does not qualify CPU-issued SPI firmware or
physical wires. Results remain separate scenarios, with no combined percentage.

Use immutable source-tree JSON generated through the connected GitHub read API
and the current local candidate worktrees:

```
python3 tools/run_current_pair_toggle.py --card CARD_DIR --reader READER_DIR \
  --card-tree card-source-tree.json --reader-tree reader-source-tree.json \
  --cvc /path/to/cvc64 --out reports/pair347 --cpb 347
```

All accepted values and required arguments are shown by `--help`.

This is a measured scalar/packed-net supplement only. It does not establish
statement/branch/complete functional/memory coverage, real device/factory/server
security, electrical/mechanical qualification or official TT submission.
The release coverage field stays **PARTIAL**. Existing numeric STA, GL,
Precheck, DRC/LVS and required CI remain mandatory and source-scoped.
