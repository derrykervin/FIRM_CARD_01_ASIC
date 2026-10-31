`timescale 1ns/1ps
module uart_pending_tb;
    reg clk=0, reset_n=1;
    reg rd=0, pulse=0;
    reg [7:0] addr=0, received=0;
    card #(.UART_CLKS_PER_BIT(16)) dut(
        .clk(clk),.reset_n(reset_n),.gpio_in(8'h00),.gpio_out(),
        .uart_rx(1'b1),.uart_tx(),.spi_sclk(),.spi_mosi(),
        .spi_miso(1'b0),.spi_cs_n(),.halted(),.debug_pc(),.debug_r0());
    always #5 clk=~clk;
    initial begin
        // Exercise the SoC byte-buffer boundary; the UART wire receiver is
        // covered separately by uart_rx_fault_tb. No production force logic.
        force dut.io_re=rd; force dut.io_addr=addr; force dut.io_we=1'b0;
        force dut.uart_rx_valid_pulse=pulse; force dut.uart_rx_data=received;
        #1 reset_n=0;
        repeat(3) @(negedge clk); reset_n=1;
        if(dut.uart_rx_pending!==0) $fatal(1,"Pending reset");
        // First byte becomes readable.
        @(negedge clk); received=8'hA5; pulse=1;
        @(negedge clk); pulse=0;
        if(dut.uart_rx_pending!==1 || dut.uart_rx_latch!==8'hA5) $fatal(1,"First receive");
        // Read sees the old byte before the edge; new byte must remain pending.
        addr=8'h11; rd=1; received=8'h3C; pulse=1; #1;
        if(dut.io_rdata!==8'hA5) $fatal(1,"Read did not see old byte");
        @(negedge clk); rd=0; pulse=0; #1;
        if(dut.uart_rx_pending!==1 || dut.io_rdata!==8'h3C) $fatal(1,"Simultaneous receive lost");
        // A later read without a receive acknowledges that new byte normally.
        rd=1; @(negedge clk); rd=0;
        if(dut.uart_rx_pending!==0) $fatal(1,"Normal acknowledgement failed");
        // A simultaneous read when initially empty also leaves new data pending.
        rd=1; pulse=1; received=8'h96;
        @(negedge clk); rd=0; pulse=0;
        if(dut.uart_rx_pending!==1 || dut.uart_rx_latch!==8'h96) $fatal(1,"Empty read lost receive");
        // Status reads do not consume the buffered byte.
        addr=8'h10; rd=1; @(negedge clk); rd=0;
        if(dut.uart_rx_pending!==1) $fatal(1,"Status read consumed byte");
        reset_n=0; @(negedge clk);
        if(dut.uart_rx_pending!==0 || dut.uart_rx_latch!==0) $fatal(1,"Reset did not clear buffer");
        $display("PASS UART pending read/receive priority"); $finish;
    end
    initial begin #10000; $fatal(1,"Pending test timeout"); end
endmodule
