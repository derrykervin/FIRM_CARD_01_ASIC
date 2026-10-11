`timescale 1ns/1ps
module mmio_tb;
    reg clk=0, reset_n=0;
    reg rd=0, wr=0;
    reg [7:0] addr=0, value=0;
    wire [7:0] gpio_out;
    wire cs;
    card #(.UART_CLKS_PER_BIT(16),.SPI_CLK_DIV(2)) dut(
        .clk(clk),.reset_n(reset_n),.gpio_in(8'h96),.gpio_out(gpio_out),
        .uart_rx(1'b1),.uart_tx(),.spi_sclk(),.spi_mosi(),.spi_miso(1'b1),
        .spi_cs_n(cs),.halted(),.debug_pc(),.debug_r0()
    );
    always #10 clk=~clk;
    task write_reg;
        input [7:0] a,d;
        begin
            @(negedge clk); addr=a; value=d; wr=1;
            @(negedge clk); wr=0;
        end
    endtask
    task check_reg;
        input [7:0] a,d;
        begin
            @(negedge clk); addr=a; rd=1; #1;
            if(dut.io_rdata !== d) $fatal(1,"MMIO %02h expected %02h got %02h",a,d,dut.io_rdata);
            @(negedge clk); rd=0;
        end
    endtask
    integer i;
    reg [63:0] expected;
    initial begin
        force dut.io_re=rd; force dut.io_we=wr;
        force dut.io_addr=addr; force dut.io_wdata=value;
        repeat(5) @(negedge clk); reset_n=1;
        check_reg(8'h40,8'h01); check_reg(8'h62,8'h01);
        check_reg(8'h59,0); check_reg(8'h58,0);
        for(i=0;i<8;i=i+1) begin check_reg(8'h50+i,0); check_reg(8'h5A+i,0); end
        write_reg(8'h41,0); check_reg(8'h41,8'hF1);
        write_reg(8'h62,0); check_reg(8'h62,1);
        write_reg(8'h59,1); check_reg(8'h59,0);
        write_reg(8'h5A,8'hFF); check_reg(8'h5A,0);
        for(i=0;i<8;i=i+1) begin write_reg(8'h50+i,i); check_reg(8'h50+i,i); end
        write_reg(8'h58,1); check_reg(8'h59,1);
        expected=64'hDC93E44C33BB17A4;
        for(i=0;i<8;i=i+1) check_reg(8'h5A+i,expected[63-i*8 -: 8]);
        write_reg(8'h58,0); check_reg(8'h59,1);
        write_reg(8'h50,8'h80); check_reg(8'h59,0);
        write_reg(8'h58,1); check_reg(8'h59,1);
        write_reg(8'h58,3); check_reg(8'h59,0); // CLEAR priority
        for(i=0;i<8;i=i+1) begin check_reg(8'h50+i,0); check_reg(8'h5A+i,0); end
        write_reg(8'h58,1); check_reg(8'h59,1);
        write_reg(8'h58,2); check_reg(8'h59,0);
        check_reg(8'h00,8'h96); write_reg(8'h01,8'hA5); check_reg(8'h01,8'hA5);
        if(gpio_out!==8'hA5) $fatal(1,"GPIO output mismatch");
        write_reg(8'h34,1);
        if(dut.timer_counter!==0) $fatal(1,"Timer clear failed");
        repeat(10) @(negedge clk);
        if(dut.timer_counter!==10) $fatal(1,"Timer stopped");
        write_reg(8'h21,8'hA5); write_reg(8'h20,1);
        if(cs!==0) $fatal(1,"SPI did not start");
        wait(dut.spi_busy==0); check_reg(8'h21,8'hFF);
        check_reg(8'h20,0); check_reg(8'h10,1);
        $display("PASS MMIO: endian, readonly, DONE, CLEAR, GPIO, Timer, SPI");
        $finish;
    end
    initial begin #100000; $fatal(1,"MMIO timeout"); end
endmodule
