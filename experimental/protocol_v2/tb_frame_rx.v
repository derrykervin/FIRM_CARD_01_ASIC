`timescale 1ns/1ps
module tb_frame_rx;
    reg clk=0, reset_n=1, clear=0, byte_valid=0;
    reg [7:0] byte_data=0;
    wire frame_valid, response_flag, error_valid;
    wire [15:0] sequence_id;
    wire [7:0] command, payload_length;
    wire [1023:0] payload;
    wire [2:0] error_code;
    reg [15:0] wanted_sequence;
    reg [7:0] wanted_command, wanted_length;
    reg wanted_flag;
    reg [1023:0] wanted_payload;
    integer frames=0, errors=0;
    firm_frame_rx #(.BYTE_TIMEOUT_CYCLES(2000),.FRAME_TIMEOUT_CYCLES(10000)) dut(
        clk,reset_n,clear,byte_valid,byte_data,frame_valid,sequence_id,
        command,response_flag,payload_length,payload,error_valid,error_code);
    always #5 clk=~clk;
    always @(posedge clk) begin
        #1;
        if(error_valid) errors=errors+1;
        if(frame_valid) begin
            frames=frames+1;
            if(sequence_id!==wanted_sequence || command!==wanted_command ||
               response_flag!==wanted_flag || payload_length!==wanted_length ||
               payload!==wanted_payload) $fatal(1,"Frame mismatch %0d",frames);
        end
    end
    task send_byte;
        input [7:0] value;
        begin
            @(negedge clk); byte_data=value; byte_valid=1;
            @(negedge clk); byte_valid=0;
        end
    endtask
    task check_count;
        input integer expected;
        begin
            #1;
            if(frames!=expected) $fatal(1,"Expected %0d frames got %0d",expected,frames);
        end
    endtask
    initial begin
        #1 reset_n=0;
        repeat(3) @(negedge clk); reset_n=1;
        `include "vectors.vh"
    end
    initial begin #1000000; $fatal(1,"Test timeout"); end
endmodule
