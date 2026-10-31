#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
command -v python3 >/dev/null || exit 127
python3 -B check_vectors.py
for tool in iverilog vvp; do
 command -v "$tool" >/dev/null || { printf 'BLOCKED: missing %s\n' "$tool" >&2; exit 127; }
done
mkdir -p build
python3 -B generate_vectors.py build/vectors.vh
iverilog -Wall -g2012 -Ibuild -s tb_frame_rx -o build/frame_rx firm_frame_rx.v tb_frame_rx.v
vvp build/frame_rx
