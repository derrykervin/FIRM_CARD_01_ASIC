// FIRM_CARD_01 / CardMCU C1 top-level SoC (C0 peripherals preserved)
// Memory-mapped I/O map:
//   0x00 GPIO_IN   (read)
//   0x01 GPIO_OUT  (read/write)
//   0x10 UART_STATUS bit0=TX ready, bit1=RX valid
//   0x11 UART_DATA   read RX / write TX
//   0x20 SPI_STATUS  bit0=busy
//   0x21 SPI_DATA    read RX / write TX buffer
//   0x30..0x33 TIMER free-running counter bytes [7:0]..[31:24]
//   0x34 TIMER_CTRL  write bit0=1 to clear timer
//   0x40 CARD_STATUS bit0=READY (1 when out of reset)
//   0x41..0x48 CARD_ID (read-only, MSB first)
//   0x50..0x57 AUTH_CHALLENGE (read/write, MSB first; write clears DONE)
//   0x58 AUTH_CTRL (write-only): bit0 START, bit1 CLEAR (CLEAR wins)
//   0x59 AUTH_STATUS bit0=DONE
//   0x5A..0x61 AUTH_RESPONSE (read-only, MSB first)
//   0x62 CARD_VERSION (read-only, 0x01)
module card #(
    parameter UART_CLKS_PER_BIT = 434,
    parameter SPI_CLK_DIV       = 4,
    parameter [63:0] CARD_ID = 64'hF100000000000001
)(
    input  wire       clk,
    input  wire       reset_n,

    input  wire [7:0] gpio_in,
    output reg  [7:0] gpio_out,

    input  wire       uart_rx,
    output wire       uart_tx,

    output wire       spi_sclk,
    output wire       spi_mosi,
    input  wire       spi_miso,
    output wire       spi_cs_n,

    output wire       halted,
    output wire [7:0] debug_pc,
    output wire [7:0] debug_r0
);
    wire [7:0]  rom_addr;
    wire [15:0] rom_data;
    wire        io_re;
    wire        io_we;
    wire [7:0]  io_addr;
    wire [7:0]  io_wdata;
    reg  [7:0]  io_rdata;

    // TEST ONLY: public fixed key and reversible XOR/rotate, NOT secure authentication.
    // All card multi-byte registers use MSB first (unlike the legacy timer).
    localparam [63:0] TEST_KEY = 64'hA52C91E74836BD10;
    localparam [7:0] CARD_VERSION = 8'h01;
    reg [63:0] auth_challenge;
    reg [63:0] auth_response;
    reg auth_done;
    wire [63:0] auth_mixed = auth_challenge ^ TEST_KEY;
    reg  [31:0] timer_counter;

    wire [7:0] uart_rx_data;
    wire       uart_rx_valid_pulse;
    reg  [7:0] uart_rx_latch;
    reg        uart_rx_pending;
    wire       uart_tx_busy;
    wire       uart_tx_start;

    reg  [7:0] spi_tx_buffer;
    wire [7:0] spi_rx_data;
    wire       spi_busy;
    wire       spi_start;

    assign uart_tx_start = io_we && (io_addr == 8'h11) && !uart_tx_busy;
    assign spi_start     = io_we && (io_addr == 8'h20) && io_wdata[0] && !spi_busy;

    program_rom u_rom(
        .addr(rom_addr),
        .data(rom_data)
    );

    card_cpu u_cpu(
        .clk(clk),
        .reset_n(reset_n),
        .rom_addr(rom_addr),
        .rom_data(rom_data),
        .io_re(io_re),
        .io_we(io_we),
        .io_addr(io_addr),
        .io_wdata(io_wdata),
        .io_rdata(io_rdata),
        .debug_pc(debug_pc),
        .debug_r0(debug_r0),
        .halted(halted)
    );

    uart_tx #(.CLKS_PER_BIT(UART_CLKS_PER_BIT)) u_uart_tx(
        .clk(clk),
        .reset_n(reset_n),
        .start(uart_tx_start),
        .data_in(io_wdata),
        .tx(uart_tx),
        .busy(uart_tx_busy)
    );

    uart_rx #(.CLKS_PER_BIT(UART_CLKS_PER_BIT)) u_uart_rx(
        .clk(clk),
        .reset_n(reset_n),
        .rx(uart_rx),
        .data_out(uart_rx_data),
        .valid(uart_rx_valid_pulse)
    );

    spi_master #(.CLK_DIV(SPI_CLK_DIV)) u_spi(
        .clk(clk),
        .reset_n(reset_n),
        .start(spi_start),
        .tx_data(spi_tx_buffer),
        .rx_data(spi_rx_data),
        .busy(spi_busy),
        .sclk(spi_sclk),
        .mosi(spi_mosi),
        .miso(spi_miso),
        .cs_n(spi_cs_n)
    );

    always @(*) begin
        case (io_addr)
            8'h00: io_rdata = gpio_in;
            8'h01: io_rdata = gpio_out;
            8'h10: io_rdata = {6'b000000, uart_rx_pending, ~uart_tx_busy};
            8'h11: io_rdata = uart_rx_latch;
            8'h20: io_rdata = {7'b0000000, spi_busy};
            8'h21: io_rdata = spi_rx_data;
            8'h30: io_rdata = timer_counter[7:0];
            8'h31: io_rdata = timer_counter[15:8];
            8'h32: io_rdata = timer_counter[23:16];
            8'h33: io_rdata = timer_counter[31:24];
            8'h40: io_rdata = 8'h01; // bit0 READY
            8'h41: io_rdata = CARD_ID[63:56];
            8'h42: io_rdata = CARD_ID[55:48];
            8'h43: io_rdata = CARD_ID[47:40];
            8'h44: io_rdata = CARD_ID[39:32];
            8'h45: io_rdata = CARD_ID[31:24];
            8'h46: io_rdata = CARD_ID[23:16];
            8'h47: io_rdata = CARD_ID[15:8];
            8'h48: io_rdata = CARD_ID[7:0];
            8'h50: io_rdata = auth_challenge[63:56];
            8'h51: io_rdata = auth_challenge[55:48];
            8'h52: io_rdata = auth_challenge[47:40];
            8'h53: io_rdata = auth_challenge[39:32];
            8'h54: io_rdata = auth_challenge[31:24];
            8'h55: io_rdata = auth_challenge[23:16];
            8'h56: io_rdata = auth_challenge[15:8];
            8'h57: io_rdata = auth_challenge[7:0];
            8'h5A: io_rdata = auth_response[63:56];
            8'h5B: io_rdata = auth_response[55:48];
            8'h5C: io_rdata = auth_response[47:40];
            8'h5D: io_rdata = auth_response[39:32];
            8'h5E: io_rdata = auth_response[31:24];
            8'h5F: io_rdata = auth_response[23:16];
            8'h60: io_rdata = auth_response[15:8];
            8'h61: io_rdata = auth_response[7:0];
            8'h59: io_rdata = {7'b0, auth_done};
            8'h62: io_rdata = CARD_VERSION;
            default: io_rdata = 8'h00;
        endcase
    end

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            auth_challenge <= 64'd0;
            auth_response <= 64'd0;
            auth_done <= 1'b0;
            gpio_out        <= 8'h00;
            timer_counter   <= 32'h00000000;
            uart_rx_latch   <= 8'h00;
            uart_rx_pending <= 1'b0;
            spi_tx_buffer   <= 8'h00;
        end else begin
            timer_counter <= timer_counter + 32'h00000001;

            if (uart_rx_valid_pulse) begin
                uart_rx_latch   <= uart_rx_data;
                uart_rx_pending <= 1'b1;
            end

            // Reading UART_DATA acknowledges the latched receive byte.
            if (io_re && (io_addr == 8'h11))
                uart_rx_pending <= 1'b0;

            if (io_we) begin
                case (io_addr)
                    8'h01: gpio_out <= io_wdata;
                    8'h21: spi_tx_buffer <= io_wdata;
                    8'h34: if (io_wdata[0]) timer_counter <= 32'h00000000;
                    8'h50: begin auth_challenge[63:56] <= io_wdata; auth_done <= 1'b0; end
                    8'h51: begin auth_challenge[55:48] <= io_wdata; auth_done <= 1'b0; end
                    8'h52: begin auth_challenge[47:40] <= io_wdata; auth_done <= 1'b0; end
                    8'h53: begin auth_challenge[39:32] <= io_wdata; auth_done <= 1'b0; end
                    8'h54: begin auth_challenge[31:24] <= io_wdata; auth_done <= 1'b0; end
                    8'h55: begin auth_challenge[23:16] <= io_wdata; auth_done <= 1'b0; end
                    8'h56: begin auth_challenge[15:8] <= io_wdata; auth_done <= 1'b0; end
                    8'h57: begin auth_challenge[7:0] <= io_wdata; auth_done <= 1'b0; end
                    8'h58: begin
                        // CLEAR wins over START; it clears challenge, result and DONE.
                        if (io_wdata[1]) begin
                            auth_challenge <= 64'd0;
                            auth_response <= 64'd0;
                            auth_done <= 1'b0;
                        end else if (io_wdata[0]) begin
                            // response = ROTL64(challenge XOR TEST_KEY, 8) XOR CARD_ID
                            auth_response <= {auth_mixed[55:0], auth_mixed[63:56]} ^ CARD_ID;
                            auth_done <= 1'b1;
                        end
                    end
                    default: begin
                    end
                endcase
            end
        end
    end
endmodule
