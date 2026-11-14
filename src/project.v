`default_nettype none
// Functional CARD entry. Both ASICs use an external shared 40MHz clock.
// Local presence is a card-side supervisor input, not an added STARCORE contact.
module tt_um_derrykervin_firm_card_01 (
    input wire [7:0] ui_in, output wire [7:0] uo_out,
    input wire [7:0] uio_in, output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input wire ena,clk,rst_n
);
    wire enabled=ena && rst_n;
    wire uart_tx,spi_sclk,spi_mosi,spi_cs_n,halted,memory_fault;
    wire scl_low,sda_low,owner_busy,committed,expired,request_active;
    wire [1:0] timeout_cause;
    wire [7:0] gpio_out,debug_pc,debug_r0,rom_addr;
    firm_current_budget #(.UART_CLKS_PER_BIT(347)) core (
        .clk(clk),.reset_n(enabled),.card_present(ui_in[2]),
        .gpio_in(8'h00),.gpio_out(gpio_out),
        .uart_rx(ui_in[0]),.uart_tx(uart_tx),
        .spi_sclk(spi_sclk),.spi_mosi(spi_mosi),
        .spi_miso(ui_in[1]),.spi_cs_n(spi_cs_n),
        .halted(halted),.memory_fault(memory_fault),
        .debug_pc(debug_pc),.debug_r0(debug_r0),.rom_addr(rom_addr),
        .scl_in(uio_in[1]),.sda_in(uio_in[0]),
        .scl_low(scl_low),.sda_low(sda_low),
        .owner_busy(owner_busy),.transport_committed(committed),
        .request_expired(expired),.request_active(request_active),
        .request_timeout_cause(timeout_cause)
    );
    assign uo_out=enabled ? {debug_pc[2:0],halted,spi_cs_n,spi_mosi,spi_sclk,uart_tx} : 8'h09;
    // SCL/SDA data are permanently zero. OE asserts only to pull a wire low.
    assign uio_out=enabled ? {timeout_cause,expired,committed,owner_busy,memory_fault,2'b00} : 8'd0;
    assign uio_oe=enabled ? {6'b111111,scl_low,sda_low} : 8'd0;
    wire unused=&{1'b0,ui_in[7:3],uio_in[7:2],gpio_out,debug_pc[7:3],debug_r0,rom_addr,request_active};
endmodule
`default_nettype wire
