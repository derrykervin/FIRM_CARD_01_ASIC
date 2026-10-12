`timescale 1ns/1ps

module wrapper_gl_tb;

    // 40 MHz = 25 ns period
    reg clk = 0;
    always #12.5 clk = ~clk;

    reg rst_n = 0;
    reg ena = 1;

    // ui_in[0] = UART RX, idle state must be HIGH
    reg [7:0] ui_in = 8'h01;
    reg [7:0] uio_in = 8'h00;

    wire [7:0] uo_out;
    wire [7:0] uio_out;
    wire [7:0] uio_oe;

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

    integer i;

    initial begin
        $dumpfile("test/wrapper_gl.fst");
        $dumpvars(0, wrapper_gl_tb);

        $display("========================================");
        $display("FIRM_CARD_01 Gate-Level Smoke Test");
        $display("Clock: 40 MHz");
        $display("========================================");

        // Keep reset active long enough for gate propagation
        #1000;

        // UART TX should idle high
        if (uo_out[0] !== 1'b1) begin
            $display("FAIL: UART TX not idle high during reset: %b", uo_out[0]);
            $fatal;
        end

        if (uio_out !== 8'h00) begin
            $display("FAIL: uio_out should be 00, got %02h", uio_out);
            $fatal;
        end

        if (uio_oe !== 8'h00) begin
            $display("FAIL: uio_oe should be 00, got %02h", uio_oe);
            $fatal;
        end

        // Release reset synchronously away from rising edge
        @(negedge clk);
        rst_n = 1'b1;

        // Run for 20,000 clocks
        for (i = 0; i < 20000; i = i + 1) begin
            @(negedge clk);

            // Check outputs never become X/Z
            if ((^uo_out) === 1'bx) begin
                $display("FAIL: X/Z detected in uo_out at cycle %0d: %b", i, uo_out);
                $fatal;
            end

            if (uio_out !== 8'h00) begin
                $display("FAIL: uio_out changed at cycle %0d: %02h", i, uio_out);
                $fatal;
            end

            if (uio_oe !== 8'h00) begin
                $display("FAIL: uio_oe changed at cycle %0d: %02h", i, uio_oe);
                $fatal;
            end
        end

        $display("PASS: Gate-level wrapper smoke test");
        $display("PASS: 40 MHz / 20,000 cycles");
        $display("PASS: No X/Z outputs");
        $display("PASS: UART TX idle correctly");
        $display("PASS: Bidirectional pads remain inputs");

        $finish;
    end

endmodule
