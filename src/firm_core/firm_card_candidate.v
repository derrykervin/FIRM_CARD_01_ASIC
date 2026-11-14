`default_nettype none
// Experimental single-CPU integration. Default ROM preserves legacy behavior;
// neither the legacy ROM nor external diagnostic ROM is product secure firmware.
module firm_card_candidate #(
    parameter integer EXTERNAL_ROM=0,UART_CLKS_PER_BIT=434,SPI_CLK_DIV=4,
    parameter integer REQUEST_GUARD=0,REQUEST_GAP=32*UART_CLKS_PER_BIT,
    REQUEST_FRAME=1024*UART_CLKS_PER_BIT,REQUEST_QUIET=14*UART_CLKS_PER_BIT,
    parameter [63:0] CARD_ID=64'hF100000000000001,
    parameter integer OWNER_DIGEST_DIRECT=1,
    parameter integer KEY_SLOT=2,DIV=100,SHARE_DIGEST=1,SHARE_TRANSPORT=1,
    parameter integer WAKE_LOW_CYCLES=3200,WAKE_HIGH_CYCLES=60000,
    parameter integer EXEC_WAIT_CYCLES=40000,POLL_CYCLES=40000,MAX_READ_ATTEMPTS=20,
    parameter integer BYTE_TIMEOUT=400000,BUS_TIMEOUT=4000000,READ_TIMEOUT=5000000,
    parameter integer PRODUCER_TIMEOUT=4000000,COMMAND_TIMEOUT=8000000,
    parameter integer WAKE_TIMEOUT=2000000,TOTAL_TIMEOUT=40000000,
    // Allow forwarding child done through the owner; no child budget is extended.
    parameter integer OWNER_TIMEOUT=TOTAL_TIMEOUT+2,
    parameter [6:0] DEVICE_ADDRESS=7'h60
)(
    input wire clk,reset_n,card_present,
    input wire [7:0] gpio_in,output wire [7:0] gpio_out,
    input wire uart_rx,output wire uart_tx,
    output wire spi_sclk,spi_mosi,spi_cs_n,input wire spi_miso,
    output wire halted,output wire memory_fault,output wire [7:0] debug_pc,debug_r0,
    output wire [7:0] rom_addr,input wire [15:0] external_rom_data,
    input wire scl_in,sda_in,output wire scl_low,sda_low,
    output wire owner_busy,transport_committed,
    output wire request_expired,request_active,
    output wire [1:0] request_timeout_cause
);
    wire [15:0] rom_data;
    wire io_re,io_we;
    wire [7:0] io_addr,io_wdata,io_rdata;
    wire core_reset_n;
    generate if (REQUEST_GUARD) begin: guarded_request
        firm_serial_request_guard #(.GAP_TIMEOUT(REQUEST_GAP),.FRAME_TIMEOUT(REQUEST_FRAME),
            .QUIET_CYCLES(REQUEST_QUIET)) guard(
            .clk(clk),.reset_n(reset_n),.uart_rx(uart_rx),.io_re(io_re),.io_addr(io_addr),
            .io_rdata(io_rdata),.core_reset_n(core_reset_n),
            .request_expired(request_expired),.request_active(request_active),
            .timeout_cause(request_timeout_cause));
    end else begin: unguarded_request
        assign core_reset_n=reset_n;
        assign request_expired=1'b0;
        assign request_active=1'b0;
        assign request_timeout_cause=2'd0;
    end endgenerate
    generate if (EXTERNAL_ROM) begin: external_program
        assign rom_data=external_rom_data;
    end else begin: legacy_program
        program_rom rom(.addr(rom_addr),.data(rom_data));
    end endgenerate
    firm_secure_cpu_port #(
        .KEY_SLOT(KEY_SLOT),
        .OWNER_DIGEST_DIRECT(OWNER_DIGEST_DIRECT),
        .DIV(DIV),
        .SHARE_DIGEST(SHARE_DIGEST),
        .SHARE_TRANSPORT(SHARE_TRANSPORT),
        .WAKE_LOW_CYCLES(WAKE_LOW_CYCLES),
        .WAKE_HIGH_CYCLES(WAKE_HIGH_CYCLES),
        .EXEC_WAIT_CYCLES(EXEC_WAIT_CYCLES),
        .POLL_CYCLES(POLL_CYCLES),
        .MAX_READ_ATTEMPTS(MAX_READ_ATTEMPTS),
        .BYTE_TIMEOUT(BYTE_TIMEOUT),
        .BUS_TIMEOUT(BUS_TIMEOUT),
        .READ_TIMEOUT(READ_TIMEOUT),
        .PRODUCER_TIMEOUT(PRODUCER_TIMEOUT),
        .COMMAND_TIMEOUT(COMMAND_TIMEOUT),
        .WAKE_TIMEOUT(WAKE_TIMEOUT),
        .TOTAL_TIMEOUT(TOTAL_TIMEOUT),
        .OWNER_TIMEOUT(OWNER_TIMEOUT),
        .DEVICE_ADDRESS(DEVICE_ADDRESS)) processor(
        .clk(clk),.rst_n(core_reset_n),.card_present(card_present),
        .rom_addr(rom_addr),.rom_data(rom_data),
        .legacy_io_re(io_re),.legacy_io_we(io_we),.legacy_io_addr(io_addr),
        .legacy_io_wdata(io_wdata),.legacy_io_rdata(io_rdata),
        .debug_pc(debug_pc),.debug_r0(debug_r0),.halted(halted),.memory_fault(memory_fault),
        .scl_in(scl_in),.sda_in(sda_in),.scl_low(scl_low),.sda_low(sda_low),
        .owner_busy(owner_busy),.transport_committed(transport_committed));
    firm_card_peripherals #(.UART_CLKS_PER_BIT(UART_CLKS_PER_BIT),
        .SPI_CLK_DIV(SPI_CLK_DIV),.CARD_ID(CARD_ID)) peripherals(
        .clk(clk),.reset_n(core_reset_n),.io_re(io_re),.io_we(io_we),
        .io_addr(io_addr),.io_wdata(io_wdata),.io_rdata(io_rdata),
        .gpio_in(gpio_in),.gpio_out(gpio_out),.uart_rx(uart_rx),.uart_tx(uart_tx),
        .spi_sclk(spi_sclk),.spi_mosi(spi_mosi),.spi_cs_n(spi_cs_n),.spi_miso(spi_miso));
endmodule
`default_nettype wire
