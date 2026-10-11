// Simple SPI mode-0, 8-bit master.
module spi_master #(
    parameter CLK_DIV = 4
)(
    input  wire       clk,
    input  wire       reset_n,
    input  wire       start,
    input  wire [7:0] tx_data,
    output reg  [7:0] rx_data,
    output reg        busy,
    output reg        sclk,
    output reg        mosi,
    input  wire       miso,
    output reg        cs_n
);
    reg [15:0] div_count;
    reg [2:0]  bit_index;
    reg [7:0]  tx_shift;
    reg [7:0]  rx_shift;

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            rx_data   <= 8'h00;
            busy      <= 1'b0;
            sclk      <= 1'b0;
            mosi      <= 1'b0;
            cs_n      <= 1'b1;
            div_count <= 16'd0;
            bit_index <= 3'd7;
            tx_shift  <= 8'h00;
            rx_shift  <= 8'h00;
        end else begin
            if (!busy) begin
                sclk <= 1'b0;
                cs_n <= 1'b1;
                if (start) begin
                    busy      <= 1'b1;
                    cs_n      <= 1'b0;
                    div_count <= 16'd0;
                    bit_index <= 3'd7;
                    tx_shift  <= tx_data;
                    rx_shift  <= 8'h00;
                    mosi      <= tx_data[7];
                end
            end else begin
                if (div_count == CLK_DIV - 1) begin
                    div_count <= 16'd0;
                    if (!sclk) begin
                        // Rising edge: slave samples MOSI, master samples MISO.
                        sclk <= 1'b1;
                        rx_shift[bit_index] <= miso;
                    end else begin
                        // Falling edge: advance to next bit.
                        sclk <= 1'b0;
                        if (bit_index == 3'd0) begin
                            busy    <= 1'b0;
                            cs_n    <= 1'b1;
                            rx_data <= {rx_shift[7:1], miso};
                            mosi    <= 1'b0;
                        end else begin
                            bit_index <= bit_index - 3'd1;
                            mosi      <= tx_shift[bit_index - 3'd1];
                        end
                    end
                end else begin
                    div_count <= div_count + 16'd1;
                end
            end
        end
    end
endmodule
