`timescale 1ns/1ps
module spi_wrapper_tb;
 reg clk=0, rst_n=1, wr=0;
 reg [7:0] addr=0, value=0, ui_in=1;
 wire [7:0] uo_out, uio_out, uio_oe;
 tt_um_derrykervin_firm_card_01 dut(ui_in,uo_out,8'h00,uio_out,uio_oe,1'b1,clk,rst_n);
 always #12.5 clk=~clk;
 task write_reg;
  input [7:0] a,d;
  begin
   @(negedge clk); addr=a; value=d; wr=1;
   @(negedge clk); wr=0;
  end
 endtask
 task transfer;
  input level;
  input [7:0] expected;
  begin
   ui_in[1]=level;
   write_reg(8'h21,8'hA5); write_reg(8'h20,1);
   if(uo_out[3]!==0) $fatal(1,"SPI CS not asserted");
   wait(dut.u_card.spi_busy==0);
   @(negedge clk); addr=8'h21; #1;
   if(dut.u_card.io_rdata!==expected) $fatal(1,"External MISO readback mismatch");
   if(uio_oe!==0) $fatal(1,"Unexpected bidirectional driver");
  end
 endtask
 initial begin
  force dut.u_card.io_we=wr;
  force dut.u_card.io_addr=addr;
  force dut.u_card.io_wdata=value;
  #1 rst_n=0;
  repeat(5) @(negedge clk); rst_n=1;
  transfer(1'b1,8'hFF); transfer(1'b0,8'h00); transfer(1'b1,8'hFF);
  $display("PASS wrapper external MISO high/low/high"); $finish;
 end
 initial begin #100000; $fatal(1,"SPI wrapper timeout"); end
endmodule
