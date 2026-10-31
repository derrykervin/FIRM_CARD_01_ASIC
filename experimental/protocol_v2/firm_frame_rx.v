`default_nettype none
// EXPERIMENTAL: not connected to tapeout top, not synthesized or simulated yet.
// UART byte interface; caller pulses clear on removal or framing error.
// Complete payload is published only after CRC. No authentication/dispatch.
module firm_frame_rx #(
    parameter integer BYTE_TIMEOUT_CYCLES = 800000,
    parameter integer FRAME_TIMEOUT_CYCLES = 4000000
)(
    input wire clk, reset_n, clear,
    input wire byte_valid,
    input wire [7:0] byte_data,
    output reg frame_valid,
    output reg [15:0] sequence_id,
    output reg [7:0] command,
    output reg response_flag,
    output reg [7:0] payload_length,
    output reg [1023:0] payload,
    output reg error_valid,
    output reg [2:0] error_code
);
    // error: 1 timeout, 2 header, 3 length, 4 CRC. Diagnostic only.
    localparam [2:0] SYNC0=0, SYNC1=1, HEADER=2, BODY=3, CRC_HI=4, CRC_LO=5;
    reg [2:0] state;
    reg [2:0] header_index;
    reg [7:0] body_index, length_work;
    reg [15:0] crc, sequence_work;
    reg [7:0] command_work, length_hi, received_crc_hi;
    reg response_work;
    reg [1023:0] payload_work;
    reg [31:0] byte_age, frame_age;
    wire expired = state != SYNC0 &&
        (byte_age >= BYTE_TIMEOUT_CYCLES-1 || frame_age >= FRAME_TIMEOUT_CYCLES-1);
    function [15:0] crc_byte;
        input [15:0] initial_crc;
        input [7:0] value;
        reg [15:0] c;
        integer bit_index;
        begin
            c = initial_crc ^ {value,8'h00};
            for(bit_index=0;bit_index<8;bit_index=bit_index+1)
                c = c[15] ? (c << 1) ^ 16'h1021 : (c << 1);
            crc_byte = c;
        end
    endfunction
    always @(posedge clk or negedge reset_n) begin
        if(!reset_n) begin
            state<=SYNC0; header_index<=0; body_index<=0; length_work<=0;
            crc<=16'hFFFF; sequence_work<=0; command_work<=0;
            length_hi<=0; received_crc_hi<=0; response_work<=0; payload_work<=0;
            byte_age<=0; frame_age<=0;
            frame_valid<=0; sequence_id<=0; command<=0; response_flag<=0;
            payload_length<=0; payload<=0; error_valid<=0; error_code<=0;
        end else begin
            frame_valid<=0; error_valid<=0;
            if(clear) begin
                state<=SYNC0; byte_age<=0; frame_age<=0; payload_work<=0;
                sequence_id<=0; command<=0; response_flag<=0;
                payload_length<=0; payload<=0; error_code<=0;
                sequence_work<=0; command_work<=0; response_work<=0;
                crc<=16'hFFFF; received_crc_hi<=0; length_hi<=0;
                header_index<=0; body_index<=0; length_work<=0;
            end else if(expired) begin
                error_valid<=1; error_code<=1; byte_age<=0; frame_age<=0;
                // A byte arriving at expiry belongs to a fresh sync search.
                state <= byte_valid && byte_data==8'hA5 ? SYNC1 : SYNC0;
            end else begin
                if(state!=SYNC0) begin
                    byte_age<=byte_age+1; frame_age<=frame_age+1;
                end
                if(byte_valid) begin
                    byte_age<=0;
                    case(state)
                        SYNC0: if(byte_data==8'hA5) begin
                            state<=SYNC1; frame_age<=0;
                        end
                        SYNC1: begin
                            if(byte_data==8'h5A) begin
                                state<=HEADER; header_index<=0; crc<=16'hFFFF;
                                payload_work<=0; body_index<=0;
                            end else if(byte_data==8'hA5) frame_age<=0;
                            else state<=SYNC0;
                        end
                        HEADER: begin
                            crc<=crc_byte(crc,byte_data);
                            header_index<=header_index+1;
                            case(header_index)
                                0: if(byte_data!=2) begin state<=SYNC0; error_valid<=1; error_code<=2; end
                                1: begin
                                    response_work<=byte_data[0];
                                    if(byte_data>1) begin state<=SYNC0; error_valid<=1; error_code<=2; end
                                end
                                2: sequence_work[15:8]<=byte_data;
                                3: sequence_work[7:0]<=byte_data;
                                4: command_work<=byte_data;
                                5: length_hi<=byte_data;
                                6: begin
                                    length_work<=byte_data;
                                    if(length_hi!=0 || byte_data>128) begin
                                        state<=SYNC0; error_valid<=1; error_code<=3;
                                    end else state<=byte_data==0 ? CRC_HI : BODY;
                                end
                                default: begin state<=SYNC0; error_valid<=1; error_code<=2; end
                            endcase
                        end
                        BODY: begin
                            payload_work[body_index*8 +: 8]<=byte_data;
                            crc<=crc_byte(crc,byte_data);
                            body_index<=body_index+1;
                            if(body_index==length_work-1) state<=CRC_HI;
                        end
                        CRC_HI: begin received_crc_hi<=byte_data; state<=CRC_LO; end
                        CRC_LO: begin
                            state<=SYNC0;
                            if({received_crc_hi,byte_data}==crc) begin
                                frame_valid<=1; sequence_id<=sequence_work;
                                command<=command_work; response_flag<=response_work;
                                payload_length<=length_work; payload<=payload_work;
                            end else begin error_valid<=1; error_code<=4; end
                        end
                        default: state<=SYNC0;
                    endcase
                end
            end
        end
    end
endmodule
`default_nettype wire
