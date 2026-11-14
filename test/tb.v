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
    // External driver: 1 releases a line, 0 pulls it low. Actual TT pads resolve
    // against DUT OE/data and pullups; this is a digital model, not electrical acceptance.
    tri1 [7:0] uio_pads;
    genvar pad;
    generate for(pad=0;pad<8;pad=pad+1)begin: pad_resolution
        assign uio_pads[pad]=uio_oe[pad] ? uio_out[pad] : 1'bz;
        assign uio_pads[pad]=uio_in[pad] ? 1'bz : 1'b0;
    end endgenerate
    wire scl_line=uio_pads[1];
    wire sda_line=uio_pads[0];

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

        .uio_in(uio_pads),
        .uio_out(uio_out),
        .uio_oe(uio_oe),

        .ena(ena),
        .clk(clk),
        .rst_n(rst_n)
    );

endmodule

`default_nettype wire
