"""TT entry RTL/GL functional wire model, not secure-device crypto or login validation.

The previous branch's fixed-ID/XOR test is retained in legacy_protocol_test.py as an archived legacy
protocol fixture. This entry requires A1+32 digest bytes, 13 checked device commands,
provisional D0 bytes and a final F0 status. SDK M0 worst-wait models are separate.
"""
import json
from pathlib import Path
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles,FallingEdge,RisingEdge,Timer,with_timeout

CPB=347
FIXTURE=json.loads(Path(__file__).with_name('proof_vectors.json').read_text())

def crc16(data):
    crc=0
    for value in data:
        for bit in range(8):
            crc=((crc<<1)^0x8005)&0xffff if ((crc>>15)^((value>>bit)&1))&1 else (crc<<1)&0xffff
    return crc.to_bytes(2,'little')

async def drive_sda(dut,release):
    value=int(dut.uio_in.value)
    dut.uio_in.value=(value|1) if release else (value&0xfe)

async def wait_start(dut):
    while True:
        await FallingEdge(dut.sda_line)
        await Timer(1,unit='ns')
        if int(dut.scl_line.value):return

async def wait_stop(dut):
    while True:
        await RisingEdge(dut.sda_line)
        await Timer(1,unit='ns')
        if int(dut.scl_line.value):return

async def receive_byte(dut,expected,ack=True):
    value=0
    for _ in range(8):
        await RisingEdge(dut.scl_line)
        await Timer(1,unit='ns')
        value=(value<<1)|int(dut.sda_line.value)
    assert value==expected,f'command wire byte {value:02x} != {expected:02x}'
    await FallingEdge(dut.scl_line)
    await drive_sda(dut,not ack)
    await RisingEdge(dut.scl_line)
    await FallingEdge(dut.scl_line)
    await drive_sda(dut,True)

async def send_byte(dut,value,ack):
    for bit in range(7,-1,-1):
        await drive_sda(dut,bool(value&(1<<bit)))
        await RisingEdge(dut.scl_line)
        await FallingEdge(dut.scl_line)
    await drive_sda(dut,True)
    await RisingEdge(dut.scl_line)
    await Timer(1,unit='ns')
    assert int(dut.sda_line.value)==(0 if ack else 1),'master ACK/NACK'
    await FallingEdge(dut.scl_line)

async def device(dut,context,late_mismatch=False,identity=False,crc_bad=False):
    # Wake pulse is not an I2C address transaction.
    await FallingEdge(dut.sda_line)
    assert int(dut.scl_line.value)==1
    await RisingEdge(dut.sda_line)
    await wait_start(dut)
    await receive_byte(dut,0xc1)
    for n,value in enumerate(bytes.fromhex('04113343')):
        await send_byte(dut,value,n!=3)
    await wait_stop(dut)
    for stage in range(5 if identity else 13):
        command=bytes.fromhex(FIXTURE['commands'][context*13+stage])
        reply=bytearray.fromhex(FIXTURE['responses'][context*13+stage])
        if crc_bad and stage==4:reply[-1]^=1
        if late_mismatch and stage==12:
            reply[64]^=1
            reply[-2:]=crc16(reply[:-2])
        await wait_start(dut)
        await receive_byte(dut,0xc0)
        await receive_byte(dut,3)
        for value in command:await receive_byte(dut,value)
        await wait_stop(dut)
        await wait_start(dut)
        await receive_byte(dut,0xc1)
        for n,value in enumerate(reply):await send_byte(dut,value,n!=len(reply)-1)
        await wait_stop(dut)

async def uart_send(dut,value):
    await FallingEdge(dut.clk)
    for bit in [0]+[(value>>n)&1 for n in range(8)]+[1]:
        dut.ui_in.value=(int(dut.ui_in.value)&0xfe)|bit
        await ClockCycles(dut.clk,CPB)
    await ClockCycles(dut.clk,CPB*2)

async def uart_read(dut):
    await FallingEdge(dut.uart_tx)
    await ClockCycles(dut.clk,CPB//2)
    assert int(dut.uart_tx.value)==0
    value=0
    for n in range(8):
        await ClockCycles(dut.clk,CPB)
        value|=int(dut.uart_tx.value)<<n
    await ClockCycles(dut.clk,CPB)
    assert int(dut.uart_tx.value)==1,'UART stop bit'
    return value

async def collect(dut):
    data=[]
    while True:
        tag=await uart_read(dut)
        if tag==0xd0:data.append(await uart_read(dut))
        else:
            assert tag==0xf0,f'unknown output tag {tag:02x}'
            status=await uart_read(dut);error=await uart_read(dut);count=await uart_read(dut)
            return bytes(data),status,error,count

async def transaction(dut,context,late_mismatch=False,identity=False,crc_bad=False):
    slave=cocotb.start_soon(device(dut,context,late_mismatch,identity,crc_bad))
    received=cocotb.start_soon(collect(dut))
    await uart_send(dut,0xa0 if identity else 0xa1)
    if not identity:
        for value in bytes.fromhex(FIXTURE['digests'][context]):await uart_send(dut,value)
    data,status,error,count=await with_timeout(received,250,timeout_unit='ms')
    await with_timeout(slave,1,timeout_unit='ms')
    expected=(bytes.fromhex(FIXTURE['responses'][context*13])[1:21]+bytes.fromhex(FIXTURE['responses'][context*13+4])[1:-2]) if identity else bytes.fromhex(FIXTURE['responses'][context*13+7])[1:-2]
    if crc_bad:expected=b''
    assert data==expected and count==(0 if crc_bad else 84 if identity else 64),'provisional signature bytes/count'
    assert status&2 and not status&1,'finished/idle qualification'
    assert bool(status&4)==(not(late_mismatch or crc_bad)),'final transport commit'
    assert error==(7 if late_mismatch or crc_bad else 0),'final owner error'
    assert bool(status&8)==(late_mismatch or crc_bad),'error status qualification'
    assert int(dut.uio_out.value)&3==0,'open-drain data must never drive HIGH'
    await ClockCycles(dut.clk,CPB*3)

@cocotb.test()
async def firm_card_protocol_test(dut):
    cocotb.start_soon(Clock(dut.clk,25,unit='ns').start())
    dut.ena.value=1;dut.rst_n.value=0;dut.ui_in.value=5;dut.uio_in.value=0xff
    await ClockCycles(dut.clk,40)
    assert int(dut.uo_out.value)==9 and int(dut.uio_oe.value)==0
    dut.rst_n.value=1
    await ClockCycles(dut.clk,CPB*2)
    await transaction(dut,0,identity=True)
    await transaction(dut,0)
    await transaction(dut,1,identity=True,crc_bad=True)
    await transaction(dut,1,identity=True)
    await transaction(dut,1,True)
    await transaction(dut,1)
    # Dropped host frame must invalidate ownership and recover after quiet time.
    await uart_send(dut,0xa1);await uart_send(dut,0x55)
    await ClockCycles(dut.clk,CPB*70)
    assert int(dut.uio_out.value)&0x20,'request timeout not visible on TT status'
    assert not(int(dut.uio_out.value)&0x10),'partial request committed'
    dut.ena.value=0
    await ClockCycles(dut.clk,4)
    assert int(dut.uio_oe.value)==0 and int(dut.uo_out.value)==9,'ENA pad isolation'
    dut.ena.value=1
    await ClockCycles(dut.clk,CPB*3)
    await transaction(dut,0)
