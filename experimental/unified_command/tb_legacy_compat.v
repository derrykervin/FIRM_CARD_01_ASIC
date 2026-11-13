`timescale 1ns/1ps
module tb_legacy_compat;
parameter CAPTURE=1;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,req=0,abort=0,tx_ready=0;reg [1:0] operation=0;reg [255:0] digest=0;
wire [1:0] ready,busy,done,valid;wire [2:0] err0,err1;wire [6:0] len0,len1,count0,count1;wire [7:0] data0,data1;
atecc_command_producer #(.CAPTURE_DIGEST(CAPTURE),.TIMEOUT_CYCLES(128)) legacy(
.clk(clk),.rst_n(rst_n),.req(req),.abort(abort),.operation(operation),.digest(digest),
.ready(ready[0]),.busy(busy[0]),.done(done[0]),.err(err0),.command_length(len0),.response_count(count0),.tx_valid(valid[0]),.tx_data(data0),.tx_ready(tx_ready));
atecc_unified_producer #(.ENABLE_READBACK(0),.CAPTURE_DIGEST(CAPTURE),.TIMEOUT_CYCLES(128)) unified(
.clk(clk),.rst_n(rst_n),.req(req),.abort(abort),.operation({1'b0,operation}),.config_block(2'b11),.digest(digest),
.ready(ready[1]),.busy(busy[1]),.done(done[1]),.err(err1),.command_length(len1),.response_count(count1),.tx_valid(valid[1]),.tx_data(data1),.tx_ready(tx_ready));
integer cycle,checks=0;reg [31:0] rng=32'h3ec38a54;
always @(negedge clk)begin
 if(rst_n)begin
 if({ready[0],busy[0],done[0],err0,len0,count0,valid[0],data0}!=={ready[1],busy[1],done[1],err1,len1,count1,valid[1],data1})$fatal(1,"legacy compatibility cycle=%0d",cycle);
 checks=checks+1;end
end
initial begin
repeat(4)@(posedge clk);#1;rst_n=1;
for(cycle=0;cycle<20000;cycle=cycle+1)begin
 @(posedge clk);#1;rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
 req=rng[0];abort=rng[7:4]==0;tx_ready=rng[8];operation=rng[10:9];digest={8{rng}};
 if(cycle%997==0)rst_n=0;else rst_n=1;
end
@(negedge clk);#1;$display("PASS legacy compatibility CAPTURE=%0d checks=%0d",CAPTURE,checks);$finish;
end
endmodule
