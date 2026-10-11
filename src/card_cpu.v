// CardMCU v1.0 - 8-bit CPU core
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
    output reg         halted
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

    wire [3:0] opcode = rom_data[15:12];
    wire [2:0] rd     = rom_data[11:9];
    wire [2:0] rs     = rom_data[8:6];
    wire [7:0] imm8   = rom_data[7:0];

    reg [8:0] alu_tmp;
    integer i;

    assign rom_addr = pc;
    assign debug_pc = pc;
    assign debug_r0 = regs[0];

    // I/O bus is combinational; peripherals sample io_we/io_re on clk edge.
    assign io_re    = (!halted && opcode == OP_IN);
    assign io_we    = (!halted && opcode == OP_OUT);
    assign io_addr  = imm8;
    assign io_wdata = regs[rd];

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            pc      <= 8'h00;
            halted  <= 1'b0;
            flag_z  <= 1'b1;
            flag_c  <= 1'b0;
            for (i = 0; i < 8; i = i + 1)
                regs[i] <= 8'h00;
        end else if (!halted) begin
            // Default: next sequential instruction.
            pc <= pc + 8'h01;

            case (opcode)
                OP_NOP: begin
                end

                OP_LDI: begin
                    regs[rd] <= imm8;
                    flag_z   <= (imm8 == 8'h00);
                end

                OP_MOV: begin
                    regs[rd] <= regs[rs];
                    flag_z   <= (regs[rs] == 8'h00);
                end

                OP_ADD: begin
                    alu_tmp  = {1'b0, regs[rd]} + {1'b0, regs[rs]};
                    regs[rd] <= alu_tmp[7:0];
                    flag_z   <= (alu_tmp[7:0] == 8'h00);
                    flag_c   <= alu_tmp[8];
                end

                OP_SUB: begin
                    alu_tmp  = {1'b0, regs[rd]} - {1'b0, regs[rs]};
                    regs[rd] <= alu_tmp[7:0];
                    flag_z   <= (alu_tmp[7:0] == 8'h00);
                    flag_c   <= ~alu_tmp[8];
                end

                OP_AND: begin
                    regs[rd] <= regs[rd] & regs[rs];
                    flag_z   <= ((regs[rd] & regs[rs]) == 8'h00);
                end

                OP_OR: begin
                    regs[rd] <= regs[rd] | regs[rs];
                    flag_z   <= ((regs[rd] | regs[rs]) == 8'h00);
                end

                OP_XOR: begin
                    regs[rd] <= regs[rd] ^ regs[rs];
                    flag_z   <= ((regs[rd] ^ regs[rs]) == 8'h00);
                end

                OP_LD: begin
                    regs[rd] <= 8'h00;
                    flag_z   <= 1'b1;
                end

                OP_ST: begin
                    // Tapeout edition: no data RAM; store is a no-op.
                end

                OP_JMP: begin
                    pc <= imm8;
                end

                OP_JZ: begin
                    if (flag_z)
                        pc <= imm8;
                end

                OP_JNZ: begin
                    if (!flag_z)
                        pc <= imm8;
                end

                OP_IN: begin
                    regs[rd] <= io_rdata;
                    flag_z   <= (io_rdata == 8'h00);
                end

                OP_OUT: begin
                    // The I/O peripheral sees io_we/io_addr/io_wdata on this edge.
                end

                OP_HLT: begin
                    halted <= 1'b1;
                    pc     <= pc;
                end

                default: begin
                    halted <= 1'b1;
                end
            endcase
        end
    end
endmodule
