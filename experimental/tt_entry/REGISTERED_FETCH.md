# Registered instruction fetch timing candidate

The retained SKY26d build `eb3220b6c0257c68c7381aaea27b124c9b7ebda1`,
run `43663783956`, has a -2.891226895 ns setup path from PC bit3 through
ROM/MMIO decode into session serial-zero state. The exact retained path and
cell mapping were recovered by source-checked diagnostic run43705645148.

`card_cpu.REGISTER_INSTRUCTION` defaults to0 for existing standalone users.
The integrated secure CPU port enables1: fetch captures16 instruction bits,
then execute retires on the next edge. PC, registers, flags, scratch writes
and MMIO takes are held during fetch. Reset invalidates the phase and cancels
a pending execute. Halt and scratch out-of-range fail-closed behavior remain.

This changes integrated instruction throughput from one to two clocks per
instruction, without changing40MHz, the UART rate, I2C timing, protocol
commands, child/owner/host deadlines, ROM size or16-byte scratch allocation.
It is a setup repair candidate, not a declaration of timing closure.

`tools/check_registered_fetch.py` uses independent ISA reference traces:
5187 programs and115038 retirement steps, excluding LD/ST as documented by
the original oracle. Two real mutants remove fetch gating from MMIO or
register writes and must fail. `test/registered_fetch_ram_tb.v` separately
checks LD/ST at address15, address16 failure, reset-invalidated scratch,
one exact OUT and cancellation of an OUT fetched before reset.
Both tests are required by `tools/check.sh`; all existing checks remain.

Full31-case TT regression and production-default paired M0 checks are
separate qualifications. Software device/server fixtures do not establish
real secure-device or production-service acceptance. Same-source nine-corner
STA, synthesis/P&R/DRC/LVS, Precheck, GL and required CI must finish before
acceptance. No main/C0 change, merge or formal submission is authorized here.
