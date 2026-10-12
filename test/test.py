import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge


CPB = 347


async def set_rx(dut, value):
    current = int(dut.ui_in.value)
    current &= ~1

    if value:
        current |= 1

    dut.ui_in.value = current


async def uart_send(dut, value):
    # Start bit
    await FallingEdge(dut.clk)
    await set_rx(dut, 0)
    await ClockCycles(dut.clk, CPB)

    # 8 data bits, LSB first
    for bit in range(8):
        await set_rx(dut, (value >> bit) & 1)
        await ClockCycles(dut.clk, CPB)

    # Stop bit
    await set_rx(dut, 1)
    await ClockCycles(dut.clk, CPB)


async def uart_monitor(dut, received):
    tx = dut.uart_tx

    while True:
        # UART start bit
        await FallingEdge(tx)

        # Middle of start bit
        await ClockCycles(dut.clk, CPB // 2)

        if int(tx.value) != 0:
            continue

        value = 0

        # Sample 8 bits
        for bit in range(8):
            await ClockCycles(dut.clk, CPB)

            if int(tx.value):
                value |= (1 << bit)

        # Stop bit
        await ClockCycles(dut.clk, CPB)

        assert int(tx.value) == 1, "Bad UART stop bit"

        received.append(value)

        dut._log.info(
            f"UART RX[{len(received)-1}] = 0x{value:02X}"
        )


async def wait_for_bytes(dut, received, target_count, max_bits=200):
    for _ in range(max_bits):
        if len(received) >= target_count:
            return

        await ClockCycles(dut.clk, CPB)

    assert len(received) >= target_count, (
        f"UART timeout: expected {target_count} bytes, "
        f"received {len(received)}"
    )


async def auth_test(dut, received, challenge, expected):
    base = len(received)

    await uart_send(dut, 0x10)

    for value in challenge:
        await uart_send(dut, value)

    await wait_for_bytes(
        dut,
        received,
        base + 8
    )

    response = bytes(
        received[base:base + 8]
    )

    assert response == expected, (
        f"AUTH mismatch: got {response.hex()}, "
        f"expected {expected.hex()}"
    )


@cocotb.test()
async def firm_card_protocol_test(dut):

    dut._log.info(
        "FIRM_CARD_01 RTL / Gate-Level protocol test"
    )

    # 40 MHz
    clock = Clock(
        dut.clk,
        25,
        unit="ns"
    )

    cocotb.start_soon(
        clock.start()
    )

    dut.ena.value = 1
    dut.ui_in.value = 0x01
    dut.uio_in.value = 0x00
    dut.rst_n.value = 0

    received = []

    cocotb.start_soon(
        uart_monitor(dut, received)
    )

    # Reset
    await ClockCycles(
        dut.clk,
        40
    )

    assert int(dut.uo_out.value) & 1 == 1
    assert int(dut.uio_out.value) == 0
    assert int(dut.uio_oe.value) == 0

    dut.rst_n.value = 1

    await ClockCycles(
        dut.clk,
        CPB * 2
    )

    # --------------------------------------------------
    # GET_VERSION
    # --------------------------------------------------

    base = len(received)

    await uart_send(
        dut,
        0x01
    )

    await wait_for_bytes(
        dut,
        received,
        base + 1
    )

    assert received[base] == 0x01

    dut._log.info(
        "PASS GET_VERSION"
    )

    # --------------------------------------------------
    # GET_CARD_ID
    # --------------------------------------------------

    base = len(received)

    await uart_send(
        dut,
        0x02
    )

    await wait_for_bytes(
        dut,
        received,
        base + 8
    )

    card_id = bytes(
        received[base:base + 8]
    )

    assert card_id == bytes.fromhex(
        "F1 00 00 00 00 00 00 01"
    )

    dut._log.info(
        "PASS CARD_ID"
    )

    # --------------------------------------------------
    # AUTH vector 1
    # --------------------------------------------------

    await auth_test(
        dut,
        received,
        bytes.fromhex(
            "00 00 00 00 00 00 00 00"
        ),
        bytes.fromhex(
            "DD 91 E7 48 36 BD 10 A4"
        )
    )

    dut._log.info(
        "PASS AUTH VECTOR 1"
    )

    # --------------------------------------------------
    # AUTH vector 2
    # --------------------------------------------------

    await auth_test(
        dut,
        received,
        bytes.fromhex(
            "01 23 45 67 89 AB CD EF"
        ),
        bytes.fromhex(
            "FE D4 80 C1 9D 70 FF A5"
        )
    )

    dut._log.info(
        "PASS AUTH VECTOR 2"
    )

    # --------------------------------------------------
    # AUTH vector 3
    # --------------------------------------------------

    await auth_test(
        dut,
        received,
        bytes.fromhex(
            "FF FF FF FF FF FF FF FF"
        ),
        bytes.fromhex(
            "22 6E 18 B7 C9 42 EF 5B"
        )
    )

    dut._log.info(
        "PASS AUTH VECTOR 3"
    )

    # --------------------------------------------------
    # Unknown command
    # --------------------------------------------------

    base = len(received)

    await uart_send(
        dut,
        0xFF
    )

    await ClockCycles(
        dut.clk,
        CPB * 20
    )

    assert len(received) == base

    dut._log.info(
        "PASS UNKNOWN COMMAND"
    )

    # Recovery after unknown command
    await uart_send(
        dut,
        0x01
    )

    await wait_for_bytes(
        dut,
        received,
        base + 1
    )

    assert received[base] == 0x01

    dut._log.info(
        "PASS UNKNOWN COMMAND RECOVERY"
    )

    # --------------------------------------------------
    # Partial AUTH
    # --------------------------------------------------

    base = len(received)

    await uart_send(
        dut,
        0x10
    )

    await uart_send(
        dut,
        0x12
    )

    await uart_send(
        dut,
        0x34
    )

    await ClockCycles(
        dut.clk,
        CPB * 5
    )

    assert len(received) == base

    # --------------------------------------------------
    # Reset recovery
    # --------------------------------------------------

    dut.rst_n.value = 0

    await ClockCycles(
        dut.clk,
        40
    )

    dut.rst_n.value = 1

    await ClockCycles(
        dut.clk,
        CPB * 2
    )

    await uart_send(
        dut,
        0x01
    )

    await wait_for_bytes(
        dut,
        received,
        base + 1
    )

    assert received[base] == 0x01

    assert int(dut.uio_out.value) == 0
    assert int(dut.uio_oe.value) == 0

    dut._log.info(
        "PASS RESET RECOVERY"
    )

    dut._log.info(
        "===================================="
    )
    dut._log.info(
        "PASS FIRM_CARD_01 COMPLETE TEST"
    )
    dut._log.info(
        "===================================="
    )
