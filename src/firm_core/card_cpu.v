// Experimental shared-writeback CPU with 16-byte public scratch RAM.
// Verilog-2001, intended for Quartus II 13.1 / Cyclone IV E
module card_cpu(
    input  wire        clk,
    input  wire        reset_n,

    output wire [7:0]  rom_addr,
    input  wire [15:0] rom_data,

    output wire        io_re,
    output wire        io_we,
    output wire [7:0]  io_addr,
    output wire [7:0]  io_wdata,
    input  wire [7:0]  io_rdata,

    output wire [7:0]  debug_pc,
    output wire [7:0]  debug_r0,
    output reg         halted,
    output reg         memory_fault
);

    // Instruction set
    localparam OP_NOP = 4'h0;
    localparam OP_LDI = 4'h1;
    localparam OP_MOV = 4'h2;
    localparam OP_ADD = 4'h3;
    localparam OP_SUB = 4'h4;
    localparam OP_AND = 4'h5;
    localparam OP_OR  = 4'h6;
    localparam OP_XOR = 4'h7;
    localparam OP_LD  = 4'h8;
    localparam OP_ST  = 4'h9;
    localparam OP_JMP = 4'hA;
    localparam OP_JZ  = 4'hB;
    localparam OP_JNZ = 4'hC;
    localparam OP_IN  = 4'hD;
    localparam OP_OUT = 4'hE;
    localparam OP_HLT = 4'hF;

    reg [7:0] pc;
    reg [7:0] regs [0:7];
    reg       flag_z;
    reg       flag_c;
    reg [7:0] scratch [0:15];
    reg [15:0] scratch_valid;

    wire [3:0] opcode = rom_data[15:12];
    wire [2:0] rd     = rom_data[11:9];
    wire [2:0] rs     = rom_data[8:6];
    wire [7:0] imm8   = rom_data[7:0];
    wire ram_address_valid=(imm8[7:4]==0);
    wire [7:0] ram_read=scratch_valid[imm8[3:0]] ? scratch[imm8[3:0]] : 8'h00;


    assign rom_addr = pc;
    assign debug_pc = pc;
    assign debug_r0 = regs[0];

    // I/O bus is combinational; peripherals sample io_we/io_re on clk edge.
    assign io_re    = (reset_n && !halted && opcode == OP_IN);
    assign io_we    = (reset_n && !halted && opcode == OP_OUT);
    assign io_addr  = imm8;
    assign io_wdata = regs[rd];

    // Shared write data is selected once; each register has one fixed lane.
    // Preserve every opcode, architectural register and flag transition.
    wire [8:0] add_value = {1'b0,regs[rd]} + {1'b0,regs[rs]};
    wire [8:0] sub_value = {1'b0,regs[rd]} - {1'b0,regs[rs]};
    reg write_enable;
    reg [7:0] write_data;
    always @* begin
        write_enable=1'b1;
        write_data=0;
        case(opcode)
            OP_LDI: write_data=imm8;
            OP_MOV: write_data=regs[rs];
            OP_ADD: write_data=add_value[7:0];
            OP_SUB: write_data=sub_value[7:0];
            OP_AND: write_data=regs[rd] & regs[rs];
            OP_OR: write_data=regs[rd] | regs[rs];
            OP_XOR: write_data=regs[rd] ^ regs[rs];
            OP_LD: begin write_data=ram_read; if(!ram_address_valid) write_enable=0; end
            OP_IN: write_data=io_rdata;
            default: write_enable=1'b0;
        endcase
    end
    // Data is public scratch only. Reset invalidates its logical view; it does
    // not physically erase retained bank bits. Match reference conditional semantics.
    always @(posedge clk) begin
        if(reset_n && !halted && opcode==OP_ST) begin
            if(!ram_address_valid) begin end
            else scratch[imm8[3:0]] <= regs[rd];
        end
    end
    genvar lane;
    generate for(lane=0;lane<8;lane=lane+1) begin : register_lane
        always @(posedge clk or negedge reset_n) begin
            if(!reset_n) regs[lane]<=0;
            else if(!halted && write_enable && rd==lane) regs[lane]<=write_data;
        end
    end endgenerate
    always @(posedge clk or negedge reset_n) begin
        if(!reset_n) begin
            pc<=0;halted<=0;flag_z<=1;flag_c<=0;
            scratch_valid <= 16'h0000; memory_fault<=0;
        end else if(!halted) begin
            pc<=pc+8'h01;
            if(write_enable) flag_z<=(write_data==0);
            if(opcode==OP_ADD) flag_c<=add_value[8];
            if(opcode==OP_SUB) flag_c<=~sub_value[8];
            case(opcode)
                OP_LD: if(!ram_address_valid) begin memory_fault<=1;halted<=1;pc<=pc;end
                OP_ST: begin
                    if(!ram_address_valid) begin memory_fault<=1;halted<=1;pc<=pc;end
                    else scratch_valid[imm8[3:0]]<=1'b1;
                end
                OP_JMP: pc<=imm8;
                OP_JZ: if(flag_z) pc<=imm8;
                OP_JNZ: if(!flag_z) pc<=imm8;
                OP_HLT: begin halted<=1;pc<=pc;end
                OP_NOP,OP_LDI,OP_MOV,OP_ADD,OP_SUB,OP_AND,OP_OR,OP_XOR,OP_IN,OP_OUT: begin end
                default: halted<=1'b1;
            endcase
        end
    end
endmodule
