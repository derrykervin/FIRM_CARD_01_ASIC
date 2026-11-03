`timescale 1ns/1ps
module uart_async_tb;
    parameter CPB=16;
    parameter RATE_PCT=0;
    parameter PHASE_NS=1;
    parameter JITTER_NS=0;
    localparam BIT_NS=CPB*10*(100+RATE_PCT)/100;
    reg clk=0, reset_n=1, rx=1;
    wire [7:0] data;
    wire valid;
    reg [7:0] expected [0:7];
    integer received=0, byte_index, bit_index, serial_bit=0;
    uart_rx #(.CLKS_PER_BIT(CPB)) dut(clk,reset_n,rx,data,valid);
    always #5 clk=~clk;
    always @(posedge clk) begin
        #1;
        if(valid) begin
            if(received>=8) $fatal(1,"Unexpected extra byte");
            if(data!==expected[received]) $fatal(1,"Asynchronous RX byte %0d expected %h got %h",received,expected[received],data);
            received=received+1;
        end
    end
    task send_bit;
        input value;
        begin
            rx=value;
            #(BIT_NS+((serial_bit%3)-1)*JITTER_NS);
            serial_bit=serial_bit+1;
        end
    endtask
    initial begin
        expected[0]=0; expected[1]=8'hFF; expected[2]=8'h55; expected[3]=8'hAA;
        expected[4]=8'h01; expected[5]=8'h80; expected[6]=8'h7F; expected[7]=8'hFE;
        #1 reset_n=0;
        repeat(4) @(negedge clk); reset_n=1;
        #(CPB*20+PHASE_NS);
        // No alignment to the receiver clock; only one stop bit between bytes.
        for(byte_index=0;byte_index<8;byte_index=byte_index+1) begin
            send_bit(0);
            for(bit_index=0;bit_index<8;bit_index=bit_index+1)
                send_bit(expected[byte_index][bit_index]);
            send_bit(1);
        end
        #(BIT_NS*3);
        if(received!=8) $fatal(1,"Missing byte after drift/jitter");
        // Sub-cycle idle glitch must not create another complete byte.
        rx=0; #1; rx=1; #(BIT_NS*12);
        if(received!=8) $fatal(1,"Glitch created a byte");
        $display("PASS UART ASYNC CPB=%0d RATE_PCT=%0d ACTUAL_BIT_NS=%0d PHASE_NS=%0d JITTER_NS=%0d",CPB,RATE_PCT,BIT_NS,PHASE_NS,JITTER_NS);
        $finish;
    end
    initial begin #(CPB*2000*10); $fatal(1,"Async test timeout"); end
endmodule
