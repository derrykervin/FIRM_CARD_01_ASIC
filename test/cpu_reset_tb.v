`timescale 1ns/1ps
module cpu_reset_tb;
    reg clk=0;always #5 clk=~clk;
    reg reset_n=0;
    wire [7:0] rom_addr,io_addr,io_wdata,debug_pc,debug_r0;
    wire io_re,io_we,halted;
    reg [15:0] rom[0:255];
    wire [15:0] rom_data=rom[rom_addr];
    integer reads=0,writes=0,i,op,rd;
    card_cpu dut(.clk(clk),.reset_n(reset_n),.rom_addr(rom_addr),.rom_data(rom_data),
        .io_re(io_re),.io_we(io_we),.io_addr(io_addr),.io_wdata(io_wdata),.io_rdata(8'ha5),
        .debug_pc(debug_pc),.debug_r0(debug_r0),.halted(halted));
    always @(posedge clk) begin
        if(!reset_n && (io_re || io_we)) $fatal(1,"I/O strobe during reset");
        if(reset_n && io_re) begin
            if(io_addr!==8'h11) $fatal(1,"read address");
            reads=reads+1;
        end
        if(reset_n && io_we) begin
            if(io_addr!==8'h12 || io_wdata!==8'ha5) $fatal(1,"write data after IN");
            writes=writes+1;
        end
    end
    initial begin #20000;$fatal(1,"CPU reset test watchdog");end
    initial begin
        for(i=0;i<256;i=i+1) rom[i]=16'h0000;
        repeat(3) @(negedge clk);
        rom[0]=16'he012;#1;
        if(io_re || io_we) $fatal(1,"reset must suppress decoded OUT");
        for(op=0;op<16;op=op+1) for(rd=0;rd<8;rd=rd+1) begin
            rom[0]=(op<<12)|(rd<<9)|8'h11;#1;
            if(io_re || io_we) $fatal(1,"reset decode op=%0d rd=%0d",op,rd);
        end
        rom[0]=16'hd011;rom[1]=16'he012;rom[2]=16'hf000;
        @(negedge clk);reset_n=1;
        wait(halted);#1;
        if(reads!==1 || writes!==1 || debug_r0!==8'ha5 || debug_pc!==2) $fatal(1,"normal IN OUT HLT sequence");
        repeat(3) @(negedge clk);
        if(io_re || io_we || reads!==1 || writes!==1) $fatal(1,"halt bus quiet");
        // Warm reset while PC/ROM point at I/O must not create another access.
        @(negedge clk);reset_n=0;#1;
        if(io_re || io_we || halted || debug_pc!==0) $fatal(1,"warm reset immediately suppresses IN");
        repeat(3) @(negedge clk);
        if(reads!==1 || writes!==1) $fatal(1,"reset external side effects");
        reset_n=1;
        @(negedge clk); // IN has executed; OUT is decoded but not sampled yet.
        if(!io_we) $fatal(1,"OUT cancellation setup");
        reset_n=0;#1;
        if(io_re || io_we) $fatal(1,"reset cancels pending OUT before sample edge");
        rom[0]=16'h0000;rom[1]=16'hf000;
        repeat(3) @(negedge clk);reset_n=1;
        wait(halted);#1;
        if(reads!==2 || writes!==1 || io_re || io_we) $fatal(1,"no ghost OUT after reset recovery");
        $display("PASS CPU reset strobes 128 opcode/register combinations and warm recovery");$finish;
    end
endmodule
