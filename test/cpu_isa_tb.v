`timescale 1ns/1ps
module cpu_isa_tb;
    `include "cpu_isa_info.vh"
    reg clk=0;always #5 clk=~clk;
    reg reset_n=0;
    wire [7:0] rom_addr,io_addr,io_wdata,debug_pc,debug_r0;
    wire io_re,io_we,halted;
    reg [15:0] rom[0:255];
    reg [15:0] vectors[0:2999999];
    wire [15:0] rom_data=rom[rom_addr];
    wire [7:0] io_rdata=io_addr^8'h5a;
    integer cursor=0,case_no,program_size,trace_steps,step_no,r,base,steps=0;
    reg [7:0] halt_pc;
    card_cpu dut(.clk(clk),.reset_n(reset_n),.rom_addr(rom_addr),.rom_data(rom_data),
        .io_re(io_re),.io_we(io_we),.io_addr(io_addr),.io_wdata(io_wdata),.io_rdata(io_rdata),
        .debug_pc(debug_pc),.debug_r0(debug_r0),.halted(halted));
    initial begin #100000000;$fatal(1,"CPU ISA watchdog");end
    initial begin
        $readmemh("cpu_isa.hex",vectors,0,VECTOR_WORDS-1);
        for(case_no=0;case_no<CASES;case_no=case_no+1) begin
            @(negedge clk);reset_n=0;
            program_size=vectors[cursor];trace_steps=vectors[cursor+1];cursor=cursor+2;
            for(r=0;r<256;r=r+1) rom[r]=16'hf000;
            for(r=0;r<program_size;r=r+1) rom[r]=vectors[cursor+r];
            cursor=cursor+program_size;
            repeat(2) @(negedge clk);
            for(r=0;r<8;r=r+1) if(dut.regs[r]!==0) $fatal(1,"register reset mismatch");
            if(io_re || io_we || debug_pc!==0 || halted) $fatal(1,"CPU reset state mismatch");
            reset_n=1;
            for(step_no=0;step_no<trace_steps;step_no=step_no+1) begin
                base=cursor+step_no*14;#1;
                if(rom_addr!==vectors[base][7:0] || debug_pc!==vectors[base][7:0] || halted)
                    $fatal(1,"fetch state mismatch case=%0d step=%0d",case_no,step_no);
                if(io_re!==vectors[base+1][0] || io_we!==vectors[base+1][1]) $fatal(1,"I/O strobe mismatch");
                if((io_re || io_we) && io_addr!==vectors[base+2][7:0]) $fatal(1,"I/O address mismatch");
                if(io_we && io_wdata!==vectors[base+3][7:0]) $fatal(1,"OUT register data mismatch");
                @(posedge clk);#1;
                if(debug_pc!==vectors[base+4][7:0] || dut.flag_z!==vectors[base+5][0] || dut.flag_c!==vectors[base+5][1] || halted!==vectors[base+5][2])
                    $fatal(1,"post state mismatch case=%0d step=%0d",case_no,step_no);
                for(r=0;r<8;r=r+1) if(dut.regs[r]!==vectors[base+6+r][7:0])
                    $fatal(1,"register mismatch case=%0d step=%0d r=%0d",case_no,step_no,r);
                if(debug_r0!==vectors[base+6][7:0]) $fatal(1,"debug R0 mismatch");
                steps=steps+1;
                @(negedge clk);
            end
            cursor=cursor+trace_steps*14;halt_pc=debug_pc;
            repeat(2) begin @(posedge clk);#1;
                if(!halted || debug_pc!==halt_pc || io_re || io_we) $fatal(1,"halt not stable");
            end
        end
        if(cursor!==VECTOR_WORDS || steps!==EXPECTED_STEPS) $fatal(1,"trace was not fully executed");
        $display("PASS CPU ISA cases=%0d steps=%0d",CASES,steps);$finish;
    end
endmodule
