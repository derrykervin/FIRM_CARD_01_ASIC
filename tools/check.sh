#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
for tool in iverilog vvp yosys; do
 command -v "$tool" >/dev/null || { printf 'BLOCKED: missing %s\n' "$tool" >&2; exit 127; }
done
mkdir -p build reports/current
read -r -a names <<< "$(python3 test/project_sources.py)"
formal=(); for name in "${names[@]}"; do formal+=("src/$name"); done
legacy=(src/card.v src/card_cpu.v src/program_rom.v src/spi_master.v src/uart_rx.v src/uart_tx.v)
iverilog -Wall -g2001 -s tt_um_derrykervin_firm_card_01 -o build/rtl "${formal[@]}" >reports/current/lint.log 2>&1
yosys -p "read_verilog ${formal[*]}; hierarchy -check -top tt_um_derrykervin_firm_card_01; synth -top tt_um_derrykervin_firm_card_01 -flatten; check -assert; select -assert-none t:\$dlatch t:\$_DLATCH_*; stat; write_json build/synth.json" >reports/current/synthesis.log 2>&1
for cpb in 8 16 347 434; do
 iverilog -g2012 -s uart_rx_fault_tb -Puart_rx_fault_tb.CPB="$cpb" -o build/uart_rx_fault src/uart_rx.v test/uart_rx_fault_tb.v
 vvp build/uart_rx_fault | tee "reports/current/uart_rx_fault_$cpb.log"
 iverilog -g2012 -s card_tb -Pcard_tb.CPB="$cpb" -o build/card_tb "${legacy[@]}" test/card_tb.v
 vvp build/card_tb | tee "reports/current/uart_$cpb.log"
done
for tb in cpu_reset_tb mmio_tb uart_pending_tb; do
 iverilog -g2012 -s "$tb" -o "build/$tb" "${legacy[@]}" "test/$tb.v"
 vvp "build/$tb" | tee "reports/current/$tb.log"
done
for tb in wrapper_tb spi_wrapper_tb; do
 iverilog -g2012 -s "$tb" -o "build/$tb" "${formal[@]}" "test/$tb.v"
 vvp "build/$tb" | tee "reports/current/$tb.log"
done
python3 -B tools/check_cpu_isa.py --sim iverilog --out reports/current/cpu-isa
python3 -B tools/check_registered_fetch.py --out reports/current/registered-fetch
iverilog -g2012 -s registered_fetch_ram_tb -o build/registered_fetch_ram src/firm_core/card_cpu.v test/registered_fetch_ram_tb.v
vvp build/registered_fetch_ram | tee reports/current/registered_fetch_ram.log
printf 'PASS: RTL and generic synthesis only; physical signoff is separate.\n'
