`timescale 1ns/1ps

module uart_gl_tb;

    localparam integer CPB    = 347;
    localparam integer BIT_NS = CPB * 25;

    // 40 MHz clock
    reg clk = 0;
    always #12.5 clk = ~clk;

    reg rst_n = 0;
    reg ena   = 1;

    // ui_in[0] = UART RX
    // UART idle = HIGH
    reg [7:0] ui_in = 8'h01;
    reg [7:0] uio_in = 8'h00;

    wire [7:0] uo_out;
    wire [7:0] uio_out;
    wire [7:0] uio_oe;

    // uo_out[0] = UART TX
    wire uart_tx = uo_out[0];

    supply1 VPWR;
    supply0 VGND;

    tt_um_derrykervin_firm_card_01 dut (
        .clk(clk),
        .ena(ena),
        .rst_n(rst_n),
        .VPWR(VPWR),
        .VGND(VGND),
        .ui_in(ui_in),
        .uio_in(uio_in),
        .uio_oe(uio_oe),
        .uio_out(uio_out),
        .uo_out(uo_out)
    );

    reg [7:0] received [0:255];
    reg [7:0] sampled;

    integer count = 0;
    integer j;
    integer k;
    integer base;

    // ---------------------------------------------------------
    // UART TX decoder
    // ---------------------------------------------------------
    initial forever begin
        @(negedge uart_tx);

        // Move to middle of start bit
        #(BIT_NS/2);

        if (uart_tx !== 1'b0) begin
            $display("FAIL: bad UART start bit");
            $fatal;
        end

        // Sample 8 data bits, LSB first
        for (j = 0; j < 8; j = j + 1) begin
            #(BIT_NS);
            sampled[j] = uart_tx;
        end

        // Move into stop bit
        #(BIT_NS);

        if (uart_tx !== 1'b1) begin
            $display("FAIL: bad UART stop bit");
            $fatal;
        end

        received[count] = sampled;

        $display(
            "RX[%0d] = 0x%02h   time=%0t",
            count,
            sampled,
            $time
        );

        count = count + 1;
    end

    // ---------------------------------------------------------
    // Send one UART byte into ui_in[0]
    // ---------------------------------------------------------
    task uart_send;
        input [7:0] value;
        integer b;
        begin
            // Start bit
            @(negedge clk);
            ui_in[0] = 1'b0;

            #(BIT_NS);

            // 8 data bits, LSB first
            for (b = 0; b < 8; b = b + 1) begin
                ui_in[0] = value[b];
                #(BIT_NS);
            end

            // Stop bit
            ui_in[0] = 1'b1;
            #(BIT_NS);
        end
    endtask

    // ---------------------------------------------------------
    // Wait for and verify one received byte
    // ---------------------------------------------------------
    task expect_byte;
        input integer index;
        input [7:0] expected;
        begin
            wait(count > index);

            if (received[index] !== expected) begin
                $display(
                    "FAIL: RX[%0d] expected 0x%02h got 0x%02h",
                    index,
                    expected,
                    received[index]
                );
                $fatal;
            end
        end
    endtask

    // ---------------------------------------------------------
    // AUTH command test
    // ---------------------------------------------------------
    task auth_test;
        input [63:0] challenge;
        input [63:0] expected;
        integer n;
        integer start_count;
        begin
            start_count = count;

            $display(
                "AUTH challenge = %016h",
                challenge
            );

            uart_send(8'h10);

            for (n = 0; n < 8; n = n + 1)
                uart_send(challenge[63-n*8 -: 8]);

            for (n = 0; n < 8; n = n + 1)
                expect_byte(
                    start_count+n,
                    expected[63-n*8 -: 8]
                );

            $display(
                "PASS AUTH -> %016h",
                expected
            );

            #(BIT_NS*2);
        end
    endtask

    // Global timeout
    initial begin
        #10000000;
        $display("FAIL: global timeout");
        $fatal;
    end

    // ---------------------------------------------------------
    // Main test
    // ---------------------------------------------------------
    initial begin

        $dumpfile("test/uart_gl.vcd");
        $dumpvars(0, uart_gl_tb);

        $display("========================================");
        $display("FIRM_CARD_01 Gate-Level UART Test");
        $display("40 MHz / CPB=347");
        $display("Baud ~= 115274");
        $display("========================================");

        // Hold reset
        #1000;

        if (uart_tx !== 1'b1) begin
            $display("FAIL: UART TX not idle HIGH");
            $fatal;
        end

        @(negedge clk);
        rst_n = 1'b1;

        #(BIT_NS*2);

        // -----------------------------------------------------
        // GET_VERSION
        // -----------------------------------------------------
        $display("");
        $display("[1] GET_VERSION");

        uart_send(8'h01);
        expect_byte(0, 8'h01);

        $display("PASS GET_VERSION = 0x01");

        #(BIT_NS*2);

        // -----------------------------------------------------
        // GET_CARD_ID
        // Expected:
        // F1 00 00 00 00 00 00 01
        // -----------------------------------------------------
        $display("");
        $display("[2] GET_CARD_ID");

        uart_send(8'h02);

        expect_byte(1, 8'hF1);

        for (k = 2; k < 8; k = k + 1)
            expect_byte(k, 8'h00);

        expect_byte(8, 8'h01);

        $display(
            "PASS CARD_ID = F1 00 00 00 00 00 00 01"
        );

        #(BIT_NS*2);

        // -----------------------------------------------------
        // AUTH vector 1
        // -----------------------------------------------------
        $display("");
        $display("[3] AUTH vector 1");

        auth_test(
            64'h0000000000000000,
            64'hDD91E74836BD10A4
        );

        // -----------------------------------------------------
        // AUTH vector 2
        // -----------------------------------------------------
        $display("");
        $display("[4] AUTH vector 2");

        auth_test(
            64'h0123456789ABCDEF,
            64'hFED480C19D70FFA5
        );

        // -----------------------------------------------------
        // AUTH vector 3
        // -----------------------------------------------------
        $display("");
        $display("[5] AUTH vector 3");

        auth_test(
            64'hFFFFFFFFFFFFFFFF,
            64'h226E18B7C942EF5B
        );

        // -----------------------------------------------------
        // Unknown command
        // -----------------------------------------------------
        $display("");
        $display("[6] Unknown command 0xFF");

        base = count;

        uart_send(8'hFF);

        #(BIT_NS*20);

        if (count != base) begin
            $display(
                "FAIL: unknown command generated output"
            );
            $fatal;
        end

        $display("PASS unknown command ignored");

        // Verify recovery
        uart_send(8'h01);
        expect_byte(base, 8'h01);

        $display("PASS communication recovered");

        // -----------------------------------------------------
        // Partial AUTH + Reset
        // -----------------------------------------------------
        $display("");
        $display("[7] Partial AUTH + RESET");

        base = count;

        uart_send(8'h10);
        uart_send(8'h12);
        uart_send(8'h34);

        #(BIT_NS*2);

        if (count != base) begin
            $display(
                "FAIL: partial AUTH generated output"
            );
            $fatal;
        end

        // Reset
        @(negedge clk);
        rst_n = 1'b0;

        #(BIT_NS*2);

        @(negedge clk);
        rst_n = 1'b1;

        #(BIT_NS*2);

        uart_send(8'h01);
        expect_byte(base, 8'h01);

        $display("PASS reset recovery");

        $display("");
        $display("========================================");
        $display("PASS: FINAL GATE-LEVEL UART TEST");
        $display("PASS: VERSION");
        $display("PASS: CARD_ID");
        $display("PASS: AUTH x3");
        $display("PASS: UNKNOWN COMMAND");
        $display("PASS: PARTIAL AUTH RESET");
        $display("========================================");

        $finish;
    end

endmodule
