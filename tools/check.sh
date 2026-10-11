#!/usr/bin/env bash
set -u
cd "$HOME/FIRM_CARD_01_ASIC"
mkdir -p build reports test
run() {
  label="$1"; shift
  "$@" > "reports/$label.log" 2>&1
  result=$?
  printf '%s exit=%s\n' "$label" "$result" | tee -a reports/status.txt
}
: > reports/status.txt
run modules grep -n '^module' src/card.v src/card_cpu.v src/program_rom.v src/uart_tx.v src/uart_rx.v src/spi_master.v src/project.v
run directory ls -lh src info.yaml
run syntax iverilog -Wall -g2001 -s tt_um_derrykervin_firm_card_01 -o build/rtl src/*.v
run synthesis yosys -p 'read_verilog src/*.v; hierarchy -check -top tt_um_derrykervin_firm_card_01; synth -top tt_um_derrykervin_firm_card_01 -flatten; check -assert; select -assert-none t:$dlatch t:$_DLATCH_*; stat; write_json build/synth.json'
run tt_config "$HOME/ttsetup/venv/bin/python" "$HOME/CardMCU_ASIC/tt/tt_tool.py" --project-dir "$PWD" --print-top-module
run precheck_help env PDK_ROOT="$HOME/ttsetup/pdk" PDK=sky130A "$HOME/ttsetup/venv/bin/python" "$HOME/CardMCU_ASIC/tt/precheck/precheck.py" --help
for cpb in 8 16 434; do
  run "uart_compile_$cpb" iverilog -g2012 -s card_tb -Pcard_tb.CPB="$cpb" -o build/card_tb src/*.v test/card_tb.v
  run "uart_$cpb" vvp build/card_tb
done
run mmio_compile iverilog -g2012 -s mmio_tb -o build/mmio_tb src/*.v test/mmio_tb.v
run mmio vvp build/mmio_tb
run wrapper_compile iverilog -g2012 -s wrapper_tb -o build/wrapper_tb src/*.v test/wrapper_tb.v
run wrapper vvp build/wrapper_tb
cat reports/status.txt
