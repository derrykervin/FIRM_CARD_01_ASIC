module uart_rx #(
    parameter CLKS_PER_BIT = 434
)(
    input  wire       clk,
    input  wire       reset_n,
    input  wire       rx,
    output reg  [7:0] data_out,
    output reg        valid
);
    localparam S_IDLE    = 3'd0;
    localparam S_START   = 3'd1;
    localparam S_DATA    = 3'd2;
    localparam S_STOP    = 3'd3;
    localparam S_RECOVER = 3'd4;

    reg [2:0]  state;
    reg [15:0] clk_count;
    reg [2:0]  bit_index;
    reg [7:0]  shift_reg;
    // Only the first stage samples the pad. FSM/data sampling use stage two.
    // This reduces CDC risk; digital simulation does not establish an MTBF.
`ifndef FIRM_CVC_NO_ASYNC_ATTR
    (* ASYNC_REG = "TRUE" *)
`endif
    reg rx_meta, rx_sync;
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin rx_meta<=1'b1; rx_sync<=1'b1; end
        else begin rx_meta<=rx; rx_sync<=rx_meta; end
    end

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            state     <= S_IDLE;
            clk_count <= 16'd0;
            bit_index <= 3'd0;
            shift_reg <= 8'h00;
            data_out  <= 8'h00;
            valid     <= 1'b0;
        end else begin
            valid <= 1'b0;
            case (state)
                S_IDLE: begin
                    clk_count <= 16'd0;
                    bit_index <= 3'd0;
                    if (!rx_sync)
                        state <= S_START;
                end

                S_START: begin
                    if (clk_count == (CLKS_PER_BIT/2)) begin
                        clk_count <= 16'd0;
                        if (!rx_sync)
                            state <= S_DATA;
                        else
                            state <= S_IDLE;
                    end else begin
                        clk_count <= clk_count + 16'd1;
                    end
                end

                S_DATA: begin
                    if (clk_count == CLKS_PER_BIT - 1) begin
                        clk_count <= 16'd0;
                        shift_reg[bit_index] <= rx_sync;
                        if (bit_index == 3'd7) begin
                            bit_index <= 3'd0;
                            state <= S_STOP;
                        end else begin
                            bit_index <= bit_index + 3'd1;
                        end
                    end else begin
                        clk_count <= clk_count + 16'd1;
                    end
                end

                S_STOP: begin
                    if (clk_count == CLKS_PER_BIT - 1) begin
                        clk_count <= 16'd0;
                        // A low stop bit is not a byte. Wait for idle high
                        // before rearming so a sustained BREAK cannot emit
                        // fabricated zero bytes.
                        if (rx_sync) begin
                            data_out <= shift_reg;
                            valid <= 1'b1;
                            state <= S_IDLE;
                        end else begin
                            state <= S_RECOVER;
                        end
                    end else begin
                        clk_count <= clk_count + 16'd1;
                    end
                end
                S_RECOVER: begin
                    clk_count <= 16'd0;
                    if (rx_sync) state <= S_IDLE;
                end
                default: begin
                    state <= S_IDLE;
                    clk_count <= 16'd0;
                end
            endcase
        end
    end
endmodule
