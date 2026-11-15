module coverage_control;
reg flag=0;
reg other=0;
reg changing=0;
initial begin
 #1;
 changing=1;
 if(flag) begin
  other=1;
  $display("NEVER_EXECUTED_SENTINEL");
 end
 #1;
 changing=0;
 #1;
 $display("PASS coverage control");
 $finish;
end
endmodule
