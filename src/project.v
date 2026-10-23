`default_nettype none
// TinyTapeout adapter: 40 MHz clock, UART divisor 347; GPIO input and SPI MISO tied low.
module tt_um_derrykervin_firm_card_01 (
    input wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input wire ena,
    input wire clk,
    input wire rst_n
);
    wire uart_tx, spi_sclk, spi_mosi, spi_cs_n, halted;
    wire [7:0] gpio_out, debug_pc, debug_r0;
    card #(.UART_CLKS_PER_BIT(347)) u_card (
        .clk(clk), .reset_n(rst_n),
        .gpio_in(8'h00), .gpio_out(gpio_out),
        .uart_rx(ui_in[0]), .uart_tx(uart_tx),
        .spi_sclk(spi_sclk), .spi_mosi(spi_mosi),
        .spi_miso(1'b0), .spi_cs_n(spi_cs_n),
        .halted(halted), .debug_pc(debug_pc), .debug_r0(debug_r0)
    );
    assign uo_out = {debug_pc[2:0], halted, spi_cs_n, spi_mosi, spi_sclk, uart_tx};
    // Never drive the bidirectional pads; unused output data is fixed low.
    assign uio_out = 8'h00;
    assign uio_oe = 8'h00;
    wire _unused = &{1'b0, ena, ui_in[7:1], uio_in,
                     gpio_out, debug_pc[7:3], debug_r0};
endmodule
`default_nettype wire
