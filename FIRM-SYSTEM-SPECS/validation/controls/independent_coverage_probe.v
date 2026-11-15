module independent_coverage_probe(
 input wire clk,rst_n,gate,input wire [7:0] value,
 output reg [7:0] observed,output wire [7:0] peek0,peek1);
 reg [7:0] bank[0:1];
 assign peek0=bank[0];assign peek1=bank[1];
 always @(posedge clk) begin
  if(!rst_n) begin observed<=0;bank[0]<=0;bank[1]<=0;end
  else if(gate) begin
   observed<=value; // CONTROL_BRANCH_TARGET
   bank[0]<=value; // CONTROL_ARRAY0_TARGET
   bank[1]<=~value; // CONTROL_ARRAY1_TARGET
  end
 end
endmodule
