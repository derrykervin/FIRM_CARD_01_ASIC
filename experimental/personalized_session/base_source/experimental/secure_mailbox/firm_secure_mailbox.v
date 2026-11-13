`default_nettype none
// Experimental CPU mailbox. COMMITTED means child transport complete, NOT login.
// Signature reads are provisional; the host must discard them on any failure and
// verify the final signature against its fresh server challenge and card key.
module firm_secure_mailbox #(parameter integer OWNER_TIMEOUT=40000000)(
    input wire clk,rst_n,card_present,
    input wire io_re,io_we,input wire [7:0] io_addr,io_wdata,
    output reg [7:0] io_rdata,output wire io_selected,
    output wire session_req,session_abort,output wire [255:0] session_digest,
    input wire engine_ready,engine_done,engine_ok,input wire [2:0] engine_error,
    input wire signature_valid,input wire [7:0] signature_data,
    output wire signature_ready,output wire transport_committed,
    output wire [31:0] elapsed_ticks,
    output wire owner_busy
);
    function integer cw;
        input integer n;integer v;
        begin cw=1;v=n-1;while(v>1) begin v=v>>1;cw=cw+1;end end
    endfunction
    localparam [7:0] CTRL=8'h80,STATUS=8'h81,ERROR=8'h82,
        CHILD=8'h83,DATA=8'h84,COUNT=8'h85;
    localparam [3:0] E_NONE=0,E_INCOMPLETE=1,E_NOT_READY=2,E_ABORT=3,
        E_REMOVED=4,E_TIMEOUT=5,E_PROTOCOL=6,E_CHILD=7,E_LENGTH=8,E_PARAMETER=9;
    reg [255:0] digest_storage;
    reg [31:0] digest_valid;
    reg active,finished,committed,kill;
    reg [3:0] error;
    reg [2:0] child_error;
    reg [6:0] consumed;
    reg [cw(OWNER_TIMEOUT)-1:0] elapsed;
    assign elapsed_ticks=elapsed;
    wire digest_address=io_addr>=8'h90 && io_addr<=8'haf;
    wire [4:0] digest_index=io_addr[4:0]-5'd16;
    wire ctrl_write=io_we && io_addr==CTRL;
    wire abort_write=ctrl_write && io_wdata[1];
    wire clear_write=ctrl_write && io_wdata==8'h04;
    wire start_write=ctrl_write && io_wdata==8'h01;
    wire full_digest=&digest_valid;
    wire invalid_parameter=OWNER_TIMEOUT<1;
    assign io_selected=io_addr[7:6]==2'b10;
    // Every secure-region write while owned, except explicit abort, is rejected
    // by terminating the request. The challenged digest cannot be replaced.
    wire forbidden_write=active && io_we && io_selected && !abort_write;
    wire expired=active && elapsed>=OWNER_TIMEOUT-1;
    // MMIO is accepted only on clk. CPU opcode/address decode can settle through
    // intermediate values after an edge: never route those combinational
    // transients into the child's asynchronous reset tree. The registered kill
    // closes the child on the same accepted abort/write edge. Removal/deadline
    // retain their immediate gating, and abort intent still blocks a DATA take.
    wire abort_intent=active && (!card_present || abort_write || forbidden_write || expired);
    assign session_abort=kill || (active && (!card_present || expired));
    assign session_req=rst_n && card_present && !active && start_write &&
        full_digest && engine_ready && !engine_done && !kill && !invalid_parameter;
    assign session_digest=(rst_n && card_present && (active || full_digest) && !session_abort)
        ? digest_storage : 256'd0;
    assign signature_ready=active && card_present && !session_abort && !abort_intent &&
        io_re && io_addr==DATA && consumed<64;
    wire take=signature_ready && signature_valid;
    wire [7:0] total_consumed={1'b0,consumed}+take;
    assign transport_committed=committed && card_present && !session_abort;
    assign owner_busy=active;
    always @* begin
        io_rdata=0;
        case(io_addr)
            STATUS: io_rdata={1'b0,full_digest,engine_ready,
                (active && signature_valid && !session_abort),
                (error!=E_NONE),transport_committed,finished,active};
            ERROR: io_rdata={4'd0,error};
            CHILD: io_rdata={5'd0,child_error};
            DATA: if(active && signature_valid && !session_abort && consumed<64) io_rdata=signature_data;
            COUNT: io_rdata={1'b0,consumed};
            default: begin end
        endcase
    end
    // Public backing only. Valid bits, not physical erasure, gate its logical view.
    // Fixed byte lanes avoid a dynamic 256-bit write mask/data shift.
    // Address order, public backing, clock acceptance and logical validity stay
    // identical to the owner-timer reference. Never remove the owner checks.
    genvar digest_lane;
    generate for(digest_lane=0;digest_lane<32;digest_lane=digest_lane+1) begin: digest_write_lanes
        always @(posedge clk) begin
            if(rst_n && card_present && !active && io_we &&
                io_addr==(8'h90+digest_lane))
                digest_storage[(31-digest_lane)*8 +:8]<=io_wdata;
        end
    end endgenerate
    always @(posedge clk) begin
        if(!active) elapsed<=0;
        else elapsed<=elapsed+1'b1;
    end
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            active<=0;finished<=0;committed<=0;kill<=0;error<=0;child_error<=0;
            consumed<=0;digest_valid<=0;
        end else begin
          kill<=0;
          if(!card_present) begin
            active<=0;committed<=0;
            if(active || committed) begin
                finished<=1;error<=E_REMOVED;child_error<=0;
            end
            kill<=active;
            consumed<=0;digest_valid<=0;
        end else if(active) begin
            if(session_abort || abort_intent) begin
                active<=0;finished<=1;committed<=0;digest_valid<=0;
                kill<=1;
                if(abort_write) error<=E_ABORT;
                else if(forbidden_write) error<=E_PROTOCOL;
                else error<=E_TIMEOUT;
            end else if(signature_valid && consumed>=64) begin
                active<=0;finished<=1;committed<=0;digest_valid<=0;error<=E_LENGTH;kill<=1;
            end else begin
                if(take) consumed<=consumed+1'b1;
                if(engine_done) begin
                    active<=0;finished<=1;committed<=0;digest_valid<=0;
                    child_error<=engine_error;
                    if(!engine_ok || engine_error!=0) error<=E_CHILD;
                    else if(total_consumed!=64) error<=E_LENGTH;
                    else begin committed<=1;error<=E_NONE;end
                end
            end
        end else begin
            // Stray child done/ok while idle never creates a result.
            if(clear_write || abort_write) begin
                finished<=0;committed<=0;error<=0;child_error<=0;
                kill<=1;
                consumed<=0;digest_valid<=0;
            end else if(start_write) begin
                finished<=0;committed<=0;error<=0;child_error<=0;consumed<=0;
                if(!full_digest) begin finished<=1;error<=E_INCOMPLETE;digest_valid<=0;end
                else if(invalid_parameter) begin finished<=1;error<=E_PARAMETER;digest_valid<=0;end
                else if(!engine_ready || engine_done || kill) begin finished<=1;error<=E_NOT_READY;digest_valid<=0;end
                else active<=1;
            end else if(io_we && digest_address) begin
                digest_valid[digest_index]<=1'b1;
                finished<=0;committed<=0;error<=0;child_error<=0;consumed<=0;
            end else if(ctrl_write || (io_we && io_selected)) begin
                finished<=1;committed<=0;error<=E_PROTOCOL;digest_valid<=0;
            end
        end
        end
    end
endmodule
`default_nettype wire
