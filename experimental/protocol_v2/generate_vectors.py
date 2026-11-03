"""Generate HDL stimulus from the independently tested Python framing model."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'FIRM-SYSTEM-SPECS/tools'))
from protocol import Frame, encode


def generate():
    lines = []
    accepted = 0

    def send(packet):
        lines.extend(f"send_byte(8'h{value:02X});" for value in packet)

    def valid(frame):
        nonlocal accepted
        packed = int.from_bytes(frame.payload, 'little')
        lines.extend([f"wanted_sequence=16'd{frame.sequence}; wanted_command=8'd{frame.command};",
                      f"wanted_flag=1'b{frame.flags}; wanted_length=8'd{len(frame.payload)};",
                      f"wanted_payload=1024'h{packed:0256X};"])
        send(encode(frame))
        accepted += 1
        lines.append(f'check_count({accepted});')

    send(b'\x00\x5A\xA5\xA5')
    valid(Frame(0, 1))
    valid(Frame(65535, 0x10, b'\xA5\x5A'*64, 1))
    # Bad CRC and invalid headers must not publish a frame.
    for index, value in ((2, 3), (3, 2), (7, 1), (8, 129), (12, 0)):
        bad = bytearray(encode(Frame(7, 2, b'ok')))
        if index == 12:
            bad[-1] ^= 1
        else:
            bad[index] = value
        send(bad)
        lines.append(f'check_count({accepted});')
        valid(Frame(8, 1, b'recovered'))
    # Partial header, byte timeout, then a clean valid command.
    send(encode(Frame(10, 2, b'abc'))[:8])
    lines.append('repeat(2001) @(negedge clk);')
    valid(Frame(11, 1))
    # Slow trickle stays inside byte timeout but hits whole-frame timeout.
    for value in encode(Frame(12, 2, b'abc'))[:10]:
        send(bytes([value]))
        lines.append('repeat(1100) @(negedge clk);')
    lines.append(f'check_count({accepted});')
    lines.append('repeat(2001) @(negedge clk);')
    valid(Frame(13, 1))
    # External clear discards unpublished and previously published identity data.
    send(encode(Frame(14, 2, b'abc'))[:10])
    lines.append('@(negedge clk); clear=1; @(negedge clk); clear=0; #1;')
    lines.append('if(payload!==0 || sequence_id!==0 || frame_valid!==0) $fatal(1,"Clear failed");')
    valid(Frame(15, 1, b'after clear'))
    lines.append('if(errors<7) $fatal(1,"Missing diagnostic errors");')
    lines.append('$display("PASS v2 frame RX generated vectors"); $finish;')
    return '\n'.join(lines)+'\n'


if __name__ == '__main__':
    destination = Path(sys.argv[1]) if len(sys.argv)>1 else Path('build/vectors.vh')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(generate())
