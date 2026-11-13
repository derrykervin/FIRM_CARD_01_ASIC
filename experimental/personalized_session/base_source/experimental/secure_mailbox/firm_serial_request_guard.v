`default_nettype none
// Experimental A1 + 32-byte request ownership deadline, not authentication.
// Observes actual CPU UART DATA reads. Timeout resets the experimental core;
// quarantine discards late bytes until a full quiet interval on the RX pad.
module firm_serial_request_guard #(
 parameter integer GAP_TIMEOUT=13888,FRAME_TIMEOUT=444416,QUIET_CYCLES=6076
)(
 input wire clk,reset_n,uart_rx,
 input wire io_re,input wire [7:0] io_addr,io_rdata,
 output wire core_reset_n,output reg request_expired,output wire request_active,
 output reg [1:0] timeout_cause
);
 function integer cw;
  input integer n;integer v;
  begin cw=1;v=n-1;while(v>1) begin v=v>>1;cw=cw+1;end end
 endfunction
 localparam INVALID=(GAP_TIMEOUT<1 || FRAME_TIMEOUT<1 || QUIET_CYCLES<1);
 reg active,quarantine;
 reg [5:0] received;
 reg [cw(GAP_TIMEOUT)-1:0] gap_elapsed;
 reg [cw(FRAME_TIMEOUT)-1:0] frame_elapsed;
 reg [cw(QUIET_CYCLES)-1:0] quiet_elapsed;
`ifndef FIRM_CVC_NO_ASYNC_ATTR
 (* ASYNC_REG = "TRUE" *)
`endif
 reg rx_meta,rx_sync;
 always @(posedge clk or negedge reset_n) begin
  if(!reset_n) begin rx_meta<=1;rx_sync<=1;end
  else begin rx_meta<=uart_rx;rx_sync<=rx_meta;end
 end
 wire read_byte=io_re && io_addr==8'h11;
 wire deadline=active && (gap_elapsed>=GAP_TIMEOUT-1 || frame_elapsed>=FRAME_TIMEOUT-1);
 assign core_reset_n=reset_n && !quarantine && !INVALID;
 assign request_active=active;
 always @(posedge clk or negedge reset_n) begin
  if(!reset_n) begin
   active<=0;quarantine<=0;received<=0;gap_elapsed<=0;frame_elapsed<=0;
   quiet_elapsed<=0;request_expired<=0;timeout_cause<=0;
  end else if(INVALID) begin
   active<=0;quarantine<=1;request_expired<=1;timeout_cause<=3;
   received<=0;gap_elapsed<=0;frame_elapsed<=0;quiet_elapsed<=0;
  end else if(quarantine) begin
   active<=0;received<=0;gap_elapsed<=0;frame_elapsed<=0;
   // Only the second synchronizer stage qualifies the quiet interval.
   if(!rx_sync) quiet_elapsed<=0;
   else if(quiet_elapsed>=QUIET_CYCLES-1) begin quarantine<=0;quiet_elapsed<=0;end
   else quiet_elapsed<=quiet_elapsed+1'b1;
  end else if(deadline) begin
   // Deadline wins even if the last byte is consumed on this clock.
   active<=0;quarantine<=1;request_expired<=1;
   timeout_cause<=(frame_elapsed>=FRAME_TIMEOUT-1)?2:1;
   received<=0;gap_elapsed<=0;frame_elapsed<=0;quiet_elapsed<=0;
  end else if(active) begin
   frame_elapsed<=frame_elapsed+1'b1;
   if(read_byte) begin
    gap_elapsed<=0;
    if(received==31) begin active<=0;received<=0;end
    else received<=received+1'b1;
   end else gap_elapsed<=gap_elapsed+1'b1;
  end else begin
   gap_elapsed<=0;frame_elapsed<=0;received<=0;quiet_elapsed<=0;
   if(read_byte && io_rdata==8'ha1) begin active<=1;request_expired<=0;timeout_cause<=0;end
  end
 end
endmodule
`default_nettype wire
