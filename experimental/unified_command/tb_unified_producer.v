`timescale 1ns/1ps
module tb_unified_producer;
parameter CAPTURE=1;
parameter SLOT=2;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,req=0,abort=0,tx_ready=0;
reg [2:0] operation=0;reg [1:0] config_block=0;reg [255:0] digest=0;
wire ready,busy,done,valid;wire [2:0] err;wire [6:0] length,count;wire [7:0] data;
reg [7:0] commands[0:1023];integer k,j,n,len,expected_count,completed=0;reg [7:0] held;
atecc_unified_producer #(.KEY_SLOT(SLOT),.CAPTURE_DIGEST(CAPTURE),.TIMEOUT_CYCLES(512)) dut(
.clk(clk),.rst_n(rst_n),.req(req),.abort(abort),.operation(operation),.config_block(config_block),.digest(digest),
.ready(ready),.busy(busy),.done(done),.err(err),.command_length(length),.response_count(count),.tx_valid(valid),.tx_data(data),.tx_ready(tx_ready));
task launch;begin wait(ready);@(negedge clk);req=1;@(negedge clk);req=0;end endtask
task result;input [2:0] expected;begin
if(!done || busy || valid || err!==expected || dut.saved_digest!==0)$fatal(1,"producer result");
completed=completed+1;@(posedge clk);#1;if(done)$fatal(1,"done pulse");end endtask
initial begin
$readmemh("commands.hex",commands,0,1023);repeat(4)@(negedge clk);rst_n=1;
if(SLOT!=2)begin
 for(k=3;k<=4;k=k+1)begin operation=k;config_block=0;launch;result(2);end
end else begin
for(k=0;k<8;k=k+1)begin
 operation=k<3?k:(k==7?4:3);config_block=k-3;for(j=0;j<32;j=j+1)digest[255-j*8-:8]=j;
 len=k==1?39:7;expected_count=k==1?4:((k==2 || k==7)?67:35);launch;
 if(length!==len || count!==expected_count)$fatal(1,"producer metadata");
 operation=7;config_block=~config_block;if(CAPTURE)digest=~digest;
 for(n=0;n<len;n=n+1)begin
 if(!valid || data!==commands[128*k+n])$fatal(1,"producer byte kind=%0d index=%0d",k,n);
 held=data;repeat(2)begin @(negedge clk);if(!valid || data!==held)$fatal(1,"stall stability");end
 req=1;tx_ready=1;@(negedge clk);req=0;tx_ready=0;
 end result(0);
end
for(k=5;k<8;k=k+1)begin operation=k;launch;result(2);end
operation=1;launch;repeat(3)@(negedge clk);abort=1;#1;if(valid||ready)$fatal(1,"abort mask");@(negedge clk);abort=0;result(1);
operation=1;launch;wait(done);#1;result(3);
operation=1;launch;@(negedge clk);dut.index=63;#1;if(valid)$fatal(1,"invalid index");@(negedge clk);result(4);
operation=0;launch;rst_n=0;@(negedge clk);if(busy || done || valid || dut.saved_digest!==0)$fatal(1,"reset cleanup");completed=completed+1;
end
$display("PASS unified producer CAPTURE=%0d SLOT=%0d completed=%0d",CAPTURE,SLOT,completed);$finish;
end
initial begin #1000000;$fatal(1,"producer watchdog");end
endmodule
