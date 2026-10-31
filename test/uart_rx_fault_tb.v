`timescale 1ns/1ps
module uart_rx_fault_tb;
    parameter CPB=16;
    reg clk=0, reset_n=1, rx=1;
    wire [7:0] data;
    wire valid;
    integer received=0;
    reg [7:0] expected=0;
    uart_rx #(.CLKS_PER_BIT(CPB)) dut(clk,reset_n,rx,data,valid);
    always #5 clk=~clk;
    always @(posedge clk) begin
        #1;
        if(valid) begin
            received=received+1;
            if(data!==expected) $fatal(1,"RX expected %h got %h",expected,data);
        end
    end
    task bit_time;
        input level;
        begin
            @(negedge clk); rx=level;
            repeat(CPB-1) @(negedge clk);
        end
    endtask
    task frame;
        input [7:0] value;
        input stop;
        integer i;
        begin
            bit_time(0);
            for(i=0;i<8;i=i+1) bit_time(value[i]);
            bit_time(stop);
        end
    endtask
    task count_is;
        input integer wanted;
        begin
            #2;
            if(received!=wanted) $fatal(1,"RX count expected %0d got %0d",wanted,received);
        end
    endtask
    initial begin
        #1 reset_n=0;
        repeat(3) @(negedge clk); reset_n=1;
        expected=8'hA5; frame(8'hA5,1); count_is(1);
        // Consecutive valid frame with only the normal stop interval.
        expected=8'h3C; frame(8'h3C,1); count_is(2);
        // Rejected data must never reach the valid-byte consumer.
        frame(8'h7E,0);
        repeat(CPB*30) @(negedge clk); count_is(2);
        bit_time(1); bit_time(1);
        expected=8'h96; frame(8'h96,1); count_is(3);
        // A second sustained BREAK from idle must not manufacture bytes.
        bit_time(0); repeat(CPB*35) @(negedge clk); count_is(3);
        bit_time(1); bit_time(1);
        expected=0; frame(0,1); count_is(4);
        // Reset cancels a partial frame and recovers on an idle line.
        bit_time(0); bit_time(1);
        @(negedge clk); reset_n=0; rx=1;
        repeat(3) @(negedge clk); reset_n=1;
        bit_time(1);
        expected=8'hFF; frame(8'hFF,1); count_is(5);
        $display("PASS UART RX stop/BREAK/recovery CPB=%0d",CPB); $finish;
    end
    initial begin #(CPB*2000*10); $fatal(1,"RX fault test timeout"); end
endmodule
