# FIRM_CARD_01

FIRM_CARD_01 is a smart-card controller ASIC prototype for the FIRM access system.

## Features

- Custom 8-bit CardMCU core
- UART command interface
- GET_VERSION command
- GET_CARD_ID command
- AUTH challenge-response command
- GPIO support
- SPI master support
- Timer support
- Tapeout edition removes the unused 256-byte data RAM to reduce ASIC area

## TinyTapeout interface

- `ui_in[0]` : UART RX into FIRM_CARD_01
- `uo_out[0]`: UART TX from FIRM_CARD_01
- `uo_out[1]`: CPU halted status
- `uo_out[7:2]`: debug PC bits
- `uio[7:0]`: unused in this revision

## Clock

Target clock: 50 MHz.

With `UART_CLKS_PER_BIT = 434`, the UART baud rate is approximately 115200 baud.

## Test commands

- `0x01` - GET_VERSION
- `0x02` - GET_CARD_ID
- `0x10 + 8-byte challenge` - AUTH

## Security notice

The current AUTH function is intended for RTL, FPGA and first-silicon validation only. It is not a production-grade cryptographic authentication implementation.
