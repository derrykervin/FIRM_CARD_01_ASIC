`timescale 1ns/1ps
module wrapper_tb;
 reg clk=0, rst_n=1, ena=1;
 reg [7:0] ui_in=8'h01, uio_in=0;
 wire [7:0] uo_out, uio_out, uio_oe;
 tt_um_derrykervin_firm_card_01 dut(ui_in,uo_out,uio_in,uio_out,uio_oe,ena,clk,rst_n);
 always #50 clk=~clk;
 initial begin
  #1 rst_n=0;
  #200;
  if (uo_out[0] !== 1'b1 || uio_out !== 0 || uio_oe !== 0) $fatal(1,"Reset/IO state");
  @(negedge clk) rst_n=1;
  repeat (10000) begin
   @(negedge clk);
   if ((^uo_out) === 1'bx || uio_out !== 0 || uio_oe !== 0) $fatal(1,"Undefined/driven IO");
  end
  ena=0; ui_in=8'hff; uio_in=8'hff;
  #100;
  if (uio_oe !== 0 || uio_out !== 0) $fatal(1,"Disabled pads");
  $display("PASS wrapper: reset, defined outputs, bidirectional pads remain inputs");
  $finish;
 end
endmodule
