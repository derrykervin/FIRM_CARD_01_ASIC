module memory_toggle_control;
reg changing=0;
reg [7:0] bank[0:1];
initial begin
 bank[0]=0;bank[1]=0;
 #1;changing=1;bank[0]=8'hff;bank[1]=8'h55;
 #1;changing=0;bank[0]=0;bank[1]=0;
 #1;if(bank[0]!==0 || bank[1]!==0) $fatal(1,"memory control values");
 $display("PASS memory toggle control");$finish;
end
endmodule
