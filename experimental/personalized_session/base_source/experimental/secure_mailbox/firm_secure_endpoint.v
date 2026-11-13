`default_nettype none
// Experimental MMIO -> real RTL session -> I2C connection. Transport only.
// Provisional bytes and COMMITTED do not authorize login or verify a signature.
module firm_secure_endpoint #(
    parameter integer SHARE_OWNER_TIMER=1,
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
    input wire clk,rst_n,card_present,input wire io_re,io_we,
    input wire [7:0] io_addr,io_wdata,output wire [7:0] io_rdata,
    output wire io_selected,owner_busy,transport_committed,
    input wire scl_in,sda_in,output wire scl_low,sda_low
);
    wire [31:0] owner_elapsed;
    wire owner_req,owner_abort,session_ready,session_done,session_ok;
    wire [255:0] owner_digest;
    wire session_busy,session_valid,session_accept;
    wire [7:0] session_data;
    wire [1:0] session_phase;
    wire [2:0] session_error,session_child,session_detail,session_transport;
    firm_secure_mailbox #(.OWNER_TIMEOUT(OWNER_TIMEOUT)) owner(
        .clk(clk),.rst_n(rst_n),.card_present(card_present),
        .io_re(io_re),.io_we(io_we),.io_addr(io_addr),.io_wdata(io_wdata),
        .io_rdata(io_rdata),.io_selected(io_selected),.owner_busy(owner_busy),
        .elapsed_ticks(owner_elapsed),
        .session_req(owner_req),.session_abort(owner_abort),.session_digest(owner_digest),
        .engine_ready(session_ready),.engine_done(session_done),.engine_ok(session_ok),.engine_error(session_error),
        .signature_valid(session_valid),.signature_data(session_data),.signature_ready(session_accept),
        .transport_committed(transport_committed));
    atecc_proof_session #(
        .EXTERNAL_ELAPSED(SHARE_OWNER_TIMER),.KEY_SLOT(KEY_SLOT),.DIV(DIV),.CAPTURE_DIGEST(OWNER_DIGEST_DIRECT ? 0 : 1),.SHARE_DIGEST(SHARE_DIGEST),.SHARE_TRANSPORT(SHARE_TRANSPORT),
        .WAKE_LOW_CYCLES(WAKE_LOW_CYCLES),.WAKE_HIGH_CYCLES(WAKE_HIGH_CYCLES),
        .EXEC_WAIT_CYCLES(EXEC_WAIT_CYCLES),.POLL_CYCLES(POLL_CYCLES),.MAX_READ_ATTEMPTS(MAX_READ_ATTEMPTS),
        .BYTE_TIMEOUT(BYTE_TIMEOUT),.BUS_TIMEOUT(BUS_TIMEOUT),.READ_TIMEOUT(READ_TIMEOUT),
        .PRODUCER_TIMEOUT(PRODUCER_TIMEOUT),.COMMAND_TIMEOUT(COMMAND_TIMEOUT),
        .WAKE_TIMEOUT(WAKE_TIMEOUT),.TOTAL_TIMEOUT(TOTAL_TIMEOUT)) session(
        .external_elapsed(owner_elapsed),
        .clk(clk),.rst_n(rst_n),.req(owner_req),.abort(owner_abort),.card_present(card_present),
        .digest(owner_digest),.address(DEVICE_ADDRESS),.scl_in(scl_in),.sda_in(sda_in),
        .scl_low(scl_low),.sda_low(sda_low),.signature_valid(session_valid),.signature_data(session_data),
        .signature_ready(session_accept),.ready(session_ready),.transport_ok(session_ok),
        .busy(session_busy),.done(session_done),.phase(session_phase),.err(session_error),
        .child_error(session_child),.detail_error(session_detail),.transport_detail(session_transport));
endmodule
`default_nettype wire
