module uart_tx #(
    parameter CLKS_PER_BIT = 434
)(
    input  wire       clk,
    input  wire       reset_n,
    input  wire       start,
    input  wire [7:0] data_in,
    output reg        tx,
    output reg        busy
);
    reg [15:0] clk_count;
    reg [3:0]  bit_index;
    reg [9:0]  shift_reg;

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            tx        <= 1'b1;
            busy      <= 1'b0;
            clk_count <= 16'd0;
            bit_index <= 4'd0;
            shift_reg <= 10'h3FF;
        end else begin
            if (!busy) begin
                tx <= 1'b1;
                if (start) begin
                    // start, 8 data bits LSB-first, stop
                    shift_reg <= {1'b1, data_in, 1'b0};
                    busy      <= 1'b1;
                    clk_count <= 16'd0;
                    bit_index <= 4'd0;
                    tx        <= 1'b0;
                end
            end else begin
                if (clk_count == CLKS_PER_BIT - 1) begin
                    clk_count <= 16'd0;
                    if (bit_index == 4'd9) begin
                        busy      <= 1'b0;
                        tx        <= 1'b1;
                        bit_index <= 4'd0;
                    end else begin
                        bit_index <= bit_index + 4'd1;
                        shift_reg <= {1'b1, shift_reg[9:1]};
                        tx        <= shift_reg[1];
                    end
                end else begin
                    clk_count <= clk_count + 16'd1;
                end
            end
        end
    end
endmodule
