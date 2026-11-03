#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
for tool in iverilog vvp yosys; do
 command -v "$tool" >/dev/null || { printf 'BLOCKED: missing %s\n' "$tool" >&2; exit 127; }
done
mkdir -p build reports/current
iverilog -Wall -g2001 -s tt_um_derrykervin_firm_card_01 -o build/rtl src/*.v >reports/current/lint.log 2>&1
yosys -p 'read_verilog src/*.v; hierarchy -check -top tt_um_derrykervin_firm_card_01; synth -top tt_um_derrykervin_firm_card_01 -flatten; check -assert; select -assert-none t:$dlatch t:$_DLATCH_*; stat; write_json build/synth.json' >reports/current/synthesis.log 2>&1
for cpb in 8 16 347 434; do
 iverilog -g2012 -s uart_rx_fault_tb -Puart_rx_fault_tb.CPB="$cpb" -o build/uart_rx_fault src/uart_rx.v test/uart_rx_fault_tb.v
 vvp build/uart_rx_fault | tee "reports/current/uart_rx_fault_$cpb.log"
 iverilog -g2012 -s card_tb -Pcard_tb.CPB="$cpb" -o build/card_tb src/*.v test/card_tb.v
 vvp build/card_tb | tee "reports/current/uart_$cpb.log"
done
for tb in mmio_tb wrapper_tb spi_wrapper_tb uart_pending_tb; do
 iverilog -g2012 -s "$tb" -o "build/$tb" src/*.v "test/$tb.v"
 vvp "build/$tb" | tee "reports/current/$tb.log"
done
printf 'PASS: RTL and generic synthesis only; physical signoff is separate.\n'
