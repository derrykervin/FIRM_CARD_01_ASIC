`default_nettype none
`timescale 1ns/1ps

module tb();

    initial begin
        $dumpfile("tb.fst");
        $dumpvars(0, tb);
        #1;
    end

    reg clk;
    reg rst_n;
    reg ena;

    reg  [7:0] ui_in;
    reg  [7:0] uio_in;

    wire [7:0] uo_out;
    wire [7:0] uio_out;
    wire [7:0] uio_oe;

    // Scalar alias for UART TX.
    // This avoids an Icarus VPI limitation on callbacks to uo_out[0].
    wire uart_tx;
    assign uart_tx = uo_out[0];

`ifdef GL_TEST
    wire VPWR = 1'b1;
    wire VGND = 1'b0;
`endif

    tt_um_derrykervin_firm_card_01 user_project (

`ifdef GL_TEST
        .VPWR(VPWR),
        .VGND(VGND),
`endif

        .ui_in(ui_in),
        .uo_out(uo_out),

        .uio_in(uio_in),
        .uio_out(uio_out),
        .uio_oe(uio_oe),

        .ena(ena),
        .clk(clk),
        .rst_n(rst_n)
    );

endmodule

`default_nettype wire
