`timescale 1ns/1ps
module card_tb;
    parameter CPB = 16;
    localparam BIT_NS = CPB * 20;
    reg clk=0, reset_n=0, uart_rx=1;
    wire uart_tx, halted;
    wire [7:0] gpio_out, debug_pc, debug_r0;
    wire spi_sclk, spi_mosi, spi_cs_n;
    card #(.UART_CLKS_PER_BIT(CPB), .SPI_CLK_DIV(2)) dut (
        .clk(clk), .reset_n(reset_n), .gpio_in(8'h96), .gpio_out(gpio_out),
        .uart_rx(uart_rx), .uart_tx(uart_tx), .spi_sclk(spi_sclk),
        .spi_mosi(spi_mosi), .spi_miso(1'b1), .spi_cs_n(spi_cs_n),
        .halted(halted), .debug_pc(debug_pc), .debug_r0(debug_r0)
    );
    always #10 clk=~clk;
    reg [7:0] received [0:255];
    reg [7:0] sampled;
    integer count=0, j, base, k;
    // Independent line decoder, active while the host sends the final byte.
    initial forever begin
        @(negedge uart_tx);
        #(BIT_NS/2);
        if (uart_tx !== 0) $fatal(1,"Bad start bit");
        for (j=0;j<8;j=j+1) begin
            #(BIT_NS); sampled[j]=uart_tx;
        end
        #(BIT_NS);
        if (uart_tx !== 1) $fatal(1,"Bad stop bit");
        received[count]=sampled;
        count=count+1;
    end
    task send;
        input [7:0] value;
        integer b;
        begin
            @(negedge clk); uart_rx=0;
            #(BIT_NS);
            for (b=0;b<8;b=b+1) begin uart_rx=value[b]; #(BIT_NS); end
            uart_rx=1; #(BIT_NS);
        end
    endtask
    task expect_byte;
        input integer index;
        input [7:0] value;
        begin
            wait(count>index);
            if(received[index] !== value)
                $fatal(1,"RX[%0d] expected %02h got %02h",index,value,received[index]);
        end
    endtask
    task auth;
        input [63:0] challenge;
        input [63:0] expected;
        integer n, start_count;
        begin
            start_count=count;
            send(8'h10);
            for(n=0;n<8;n=n+1) send(challenge[63-n*8 -: 8]);
            for(n=0;n<8;n=n+1) expect_byte(start_count+n,expected[63-n*8 -: 8]);
            if(dut.auth_done !== 1 || dut.auth_challenge !== challenge)
                $fatal(1,"AUTH state mismatch");
            #(BIT_NS*2);
            if(count != start_count+8) $fatal(1,"Extra AUTH response");
        end
    endtask
    initial begin
        #(BIT_NS*1500); $fatal(1,"Timeout PC=%02h",debug_pc);
    end
    initial begin
        repeat(5) @(negedge clk);
        reset_n=1;
        #(BIT_NS*2);
        if(count!=0) $fatal(1,"Unexpected boot output");
        send(8'h01); expect_byte(0,8'h01);
        #(BIT_NS*2);
        send(8'h02);
        expect_byte(1,8'hF1);
        for(k=2;k<8;k=k+1) expect_byte(k,8'h00);
        expect_byte(8,8'h01);
        #(BIT_NS*2);
        auth(64'h0000000000000000,64'hDD91E74836BD10A4);
        auth(64'h0123456789ABCDEF,64'hFED480C19D70FFA5);
        auth(64'hFFFFFFFFFFFFFFFF,64'h226E18B7C942EF5B);
        base=count; send(8'hFF); #(BIT_NS*20);
        if(count!=base) $fatal(1,"Unknown command emitted output");
        send(8'h01); expect_byte(base,8'h01); #(BIT_NS*2);
        send(8'h10); send(8'h12); send(8'h34); #(BIT_NS*2);
        if(count!=base+1) $fatal(1,"Partial AUTH emitted output");
        @(negedge clk); reset_n=0;
        repeat(5) @(negedge clk);
        if(dut.auth_done!==0 || dut.auth_response!==0 || dut.auth_challenge!==0)
            $fatal(1,"Reset did not clear AUTH");
        reset_n=1; #(BIT_NS*2);
        send(8'h01); expect_byte(base+1,8'h01); #(BIT_NS*2);
        if(halted!==0) $fatal(1,"CPU halted");
        $display("PASS UART CPB=%0d: VERSION, ID, 3 AUTH vectors, repeat, unknown, partial/reset",CPB);
        $finish;
    end
endmodule
