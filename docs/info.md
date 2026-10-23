## How it works
FIRM_CARD_01 is a CardMCU C1 protocol prototype. It contains the 8-bit CPU,
fixed program ROM, UART, timer, SPI master and test challenge-response logic.
The unused 256-byte data RAM is removed. Authentication is reversible XOR/rotate
with a public test key; the fixed card ID is shared by every manufactured copy.
This is not a secure access credential, persistent account store or ISO7816 card.

The implemented wrapper and info.yaml use 40 MHz and UART_CLKS_PER_BIT=347,
giving approximately 115273.8 baud (8N1). The 1x2 tile allocation is required.

| Port | Function |
|---|---|
| ui[0] | UART RX |
| uo[0] | UART TX |
| uo[1] | SPI SCLK |
| uo[2] | SPI MOSI |
| uo[3] | SPI CS_N |
| uo[4] | CPU halted |
| uo[7:5] | debug PC bits 2:0 |
| uio[7:0] | unused, output-enable fixed zero |

GPIO input and SPI MISO are tied to zero. GPIO outputs are not exported.
SPI readback and external GPIO are therefore unavailable in this wrapper.

## How to test
Configure the shuttle mux, supply a 40 MHz clock, assert rst_n low, then release.
UART RX idles high. Send 0x01 for version 0x01; 0x02 for ID
F1 00 00 00 00 00 00 01; 0x10 followed by eight challenge bytes for AUTH.
Challenge 01 23 45 67 89 AB CD EF returns FE D4 80 C1 9D 70 FF A5.
Unknown commands produce no reply. Reset clears a partial AUTH request.
The automated RTL and gate-level test covers these commands, three AUTH vectors,
unknown-command recovery, partial AUTH and reset recovery.

## External hardware
Use a shared external oscillator when testing with FIRM_READER_01 at 40 MHz.
Do not forward that clock through a SKY output pad: its specified limit is 33 MHz.
CARD and READER must be selected on two separate physical ASIC packages to run
concurrently. Provide mux selection, core/IO supplies, decoupling and ESD externally.
The eight-contact board remains a separate unfinished carrier design.
