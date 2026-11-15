`timescale 1ns/1ps
module tb_frame_recovery;
 reg clk=0;always #12.5 clk=~clk;
 reg reset_n=0,clear=0,valid=0;reg [7:0] data=0;
 wire frame,error_flag,response_flag;wire [2:0] error_code;
 wire [15:0] sequence_id;wire [7:0] command,length;
 wire [4:0] command_class;wire [255:0] payload;
 reg [7:0] packet[0:10];integer i,frames=0,errors=0;
 firm_frame_rx #(.MAX_PAYLOAD(32),.BYTE_TIMEOUT_CYCLES(160),.FRAME_TIMEOUT_CYCLES(1000)) dut(
  .clk(clk),.reset_n(reset_n),.clear(clear),.byte_valid(valid),.byte_data(data),
  .frame_valid(frame),.sequence_id(sequence_id),.command(command),.command_class(command_class),
  .response_flag(response_flag),.payload_length(length),.payload(payload),
  .error_valid(error_flag),.error_code(error_code));
 always @(posedge clk) begin
  #2;
  if(error_flag) begin
   if(error_code!==2) $fatal(1,"wrong header rejection code");
   errors=errors+1;
  end
  if(frame) begin
   if(sequence_id!==16'h1234 || command!==1 || command_class!==5'b01000 || response_flag || length!==0 || payload!==0)
    $fatal(1,"bad context after parser recovery");
   frames=frames+1;
  end
 end
 task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
 task send_byte;input [7:0] value;
  begin data=value;valid=1;tick;valid=0;tick;end
 endtask
 task good_frame;begin for(i=0;i<11;i=i+1)send_byte(packet[i]);end endtask
 initial begin
  $readmemh("frame-recovery.hex",packet);
  repeat(3)tick;reset_n=1;tick;
  send_byte(8'ha5);send_byte(0);
  if(errors!=0 || frames!=0) $fatal(1,"noise unexpectedly published");
  send_byte(8'ha5);send_byte(8'ha5);send_byte(8'h5a);send_byte(3);
  if(errors!=1 || frames!=0) $fatal(1,"invalid version not rejected after repeated sync");
  good_frame;
  if(errors!=1 || frames!=1) $fatal(1,"version recovery failed");
  send_byte(8'ha5);send_byte(8'h5a);send_byte(2);send_byte(8'h80);
  if(errors!=2 || frames!=1) $fatal(1,"reserved flags not rejected");
  good_frame;
  if(errors!=2 || frames!=2) $fatal(1,"flags recovery failed");
  $display("PASS frame parser recovery cases=5 frames=2 errors=2");$finish;
 end
 initial begin #100000;$fatal(1,"parser recovery watchdog");end
endmodule
