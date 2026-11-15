`timescale 1ns/1ps
module registered_fetch_ram_tb;
 reg clk=0; always #5 clk=~clk;
 reg rst=0;
 wire [7:0] pc,addr,data,r0; wire re,we,halted,fault;
 reg [15:0] rom[0:255]; integer i,takes=0;
 card_cpu #(.REGISTER_INSTRUCTION(1)) dut(.clk(clk),.reset_n(rst),
  .rom_addr(pc),.rom_data(rom[pc]),.io_re(re),.io_we(we),.io_addr(addr),
  .io_wdata(data),.io_rdata(8'h5a),.debug_pc(),.debug_r0(r0),
  .halted(halted),.memory_fault(fault));
 always @(posedge clk) if(we) begin
  if(addr!==8'h30 || data!==8'haa) $fatal(1,"RAM OUT mismatch");
  takes=takes+1;
 end
 initial begin
  for(i=0;i<256;i=i+1) rom[i]=16'hf000;
  rom[0]=16'h10aa; // LDI r0,aa
  rom[1]=16'h900f; // ST r0,15
  rom[2]=16'h820f; // LD r1,15
  rom[3]=16'he230; // OUT r1,30
  rom[4]=16'h8410; // LD r2,16: fail closed, no wrapping to scratch0
  repeat(2) @(negedge clk);rst=1;
  repeat(12) @(negedge clk);
  if(!halted || !fault || pc!==4 || takes!=1 || dut.regs[1]!==8'haa || dut.regs[2]!==0)
   $fatal(1,"RAM bounds or architectural retirement mismatch");
  // Reset invalidates scratch; a fresh LD must read zero.
  rst=0;rom[0]=16'h820f;rom[1]=16'hf000;repeat(2) @(negedge clk);rst=1;
  repeat(6) @(negedge clk);
  if(dut.regs[1]!==0 || fault || !halted) $fatal(1,"scratch reset view mismatch");
  // Reset after fetching OUT prevents a pending MMIO side effect.
  rst=0;rom[0]=16'he230;repeat(2) @(negedge clk);rst=1;
  @(posedge clk);#1;rst=0;#1;
  if(we || re || pc!==0) $fatal(1,"pending MMIO survived reset");
  $display("PASS registered fetch RAM bounds, reset invalidation, exact MMIO and pending reset");$finish;
 end
 initial begin #10000;$fatal(1,"watchdog");end
endmodule
