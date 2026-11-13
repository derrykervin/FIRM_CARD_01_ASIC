`default_nettype none
// Wake -> Random -> Nonce digest -> Sign transport. NOT signature verification.
module atecc_proof_session #(
    parameter integer KEY_SLOT=2,DIV=100,
    // Default preserves independent live-input capture. Only a stable owner may bypass it.
    parameter integer EXTERNAL_ELAPSED=0,
    parameter integer CAPTURE_DIGEST=1,
    parameter integer SHARE_DIGEST=1,
    parameter integer SHARE_TRANSPORT=1,
    parameter integer WAKE_LOW_CYCLES=3200,WAKE_HIGH_CYCLES=60000,
    parameter integer EXEC_WAIT_CYCLES=40000,POLL_CYCLES=40000,MAX_READ_ATTEMPTS=20,
    parameter integer BYTE_TIMEOUT=400000,BUS_TIMEOUT=4000000,READ_TIMEOUT=5000000,
    parameter integer PRODUCER_TIMEOUT=4000000,COMMAND_TIMEOUT=8000000,
    parameter integer WAKE_TIMEOUT=2000000,TOTAL_TIMEOUT=40000000
)(
    input wire clk,rst_n,req,abort,card_present,
    input wire [31:0] external_elapsed,
    input wire [255:0] digest,input wire [6:0] address,
    input wire scl_in,sda_in,output wire scl_low,sda_low,
    output wire signature_valid,output wire [7:0] signature_data,input wire signature_ready,
    output wire ready,transport_ok,output reg busy,done,
    output reg [1:0] phase,
    output reg [2:0] err,child_error,detail_error,transport_detail
);
    localparam [2:0] IDLE=0,WAKE_START=1,WAKE_WAIT=2,COMMAND_START=3,COMMAND_WAIT=4;
    function integer cw;
        input integer limit;integer v;
        begin cw=1;v=limit-1;while(v>1) begin v=v>>1;cw=cw+1;end end
    endfunction
    reg [2:0] state;
    // Public challenge digest only: private keys never reside in this bank.
    // Invalidating the logical view is not physical erasure of digest_storage.
    reg [255:0] digest_storage;
    reg digest_valid;
    wire [255:0] saved_digest=digest_valid ? (CAPTURE_DIGEST ? digest_storage : digest) : 256'd0;
    wire capture_digest=rst_n && req && ready && KEY_SLOT>=0 && KEY_SLOT<=15;
    always @(posedge clk) begin
        if(CAPTURE_DIGEST && capture_digest) digest_storage<=digest;
    end
    reg [6:0] saved_address,signature_count;
    reg [cw(TOTAL_TIMEOUT)-1:0] elapsed;
    wire timer_fault,timer_fault_observed;
    generate if(EXTERNAL_ELAPSED) begin: shared_elapsed
        always @* elapsed=external_elapsed;
        // Predict two independent check bits before the owner bank advances.
        // This detects a single-bit upset and a stopped bank after acceptance.
        // It is not a claim of arbitrary multi-bit/common-clock fault coverage.
        reg armed,expected_lsb,expected_parity,fault_latched;
        wire [31:0] predicted_next=external_elapsed+32'd1;
        always @(posedge clk or negedge rst_n) begin
            if(!rst_n) begin armed<=0;expected_lsb<=0;expected_parity<=0;fault_latched<=0;end
            else if(!busy) begin armed<=0;expected_lsb<=0;expected_parity<=0;fault_latched<=0;end
            else begin
                armed<=1;
                fault_latched<=fault_latched || timer_fault_observed;
                expected_lsb<=~external_elapsed[0];
                expected_parity<=^predicted_next;
            end
        end
        // Only sampled state may enter the asynchronous child-reset gates.
        assign timer_fault=fault_latched;
        assign timer_fault_observed=busy && rst_n && card_present && !abort &&
            ((!armed && external_elapsed!=0) ||
             (armed && ((external_elapsed[0]!=expected_lsb) ||
                        ((^external_elapsed)!=expected_parity))));
    end else begin: private_elapsed
        assign timer_fault=1'b0;
        assign timer_fault_observed=1'b0;
        always @(posedge clk) begin
            if(!busy) elapsed<=0;else elapsed<=elapsed+1'b1;
        end
    end endgenerate
    reg wake_req,command_req,kill,result_ok;
    wire invalid_context=busy && (state==IDLE || state>COMMAND_WAIT || phase>2 || signature_count>64 || timer_fault);
    wire expired=busy && elapsed>=TOTAL_TIMEOUT-1;
    wire active=busy && card_present && !abort && !kill && !expired && !invalid_context;
    wire wake_enabled=active && (state==WAKE_START || state==WAKE_WAIT);
    wire command_enabled=active && (state==COMMAND_START || state==COMMAND_WAIT);
    wire wake_done,wake_ok,wake_scl,wake_sda;
    wire [2:0] wake_err,wake_detail;
    wire command_ready,command_done,command_ok,command_valid,command_scl,command_sda;
    wire [2:0] command_err,command_detail,command_transport;
    wire command_accept=command_enabled && (phase!=2 || (signature_ready && signature_count<64));
    wire wake_bus_req,wake_bus_reset_n,command_bus_req,command_bus_reset_n;
    wire command_bus_read,command_bus_tx_valid,command_bus_rx_ready;
    wire [6:0] wake_bus_address,command_bus_address;
    wire [7:0] command_bus_length,command_bus_tx_data;
    wire bus_tx_ready,bus_busy,bus_done,bus_valid,bus_cleanup,bus_scl,bus_sda;
    wire [7:0] bus_data;wire [2:0] bus_error;
    wire selected_bus_reset_n=rst_n && ((wake_enabled && wake_bus_reset_n) ||
        (command_enabled && command_bus_reset_n));
    generate if(SHARE_TRANSPORT) begin: shared_bus
        // Exclusive phase ownership; child reset authority is never bypassed.
        firm_i2c_transaction #(.DIV(DIV),.BYTE_TIMEOUT(BYTE_TIMEOUT),.TOTAL_TIMEOUT(BUS_TIMEOUT)) transport(
            .clk(clk),.rst_n(selected_bus_reset_n),
            .req(wake_enabled ? wake_bus_req : (command_enabled && command_bus_req)),
            .read_mode(wake_enabled ? 1'b1 : command_bus_read),
            .address(wake_enabled ? wake_bus_address : command_bus_address),
            .length(wake_enabled ? 8'd4 : command_bus_length),
            .tx_valid(command_enabled && command_bus_tx_valid),.tx_data(command_bus_tx_data),.tx_ready(bus_tx_ready),
            .rx_valid(bus_valid),.rx_data(bus_data),.rx_ready(wake_enabled ? 1'b1 : command_bus_rx_ready),
            .scl_in(scl_in),.sda_in(sda_in),.scl_low(bus_scl),.sda_low(bus_sda),
            .busy(bus_busy),.done(bus_done),.err(bus_error),.cleanup_failed(bus_cleanup));
    end else begin: separate_buses
        assign bus_tx_ready=1'b0;assign bus_busy=1'b0;assign bus_done=1'b0;
        assign bus_valid=1'b0;assign bus_cleanup=1'b0;assign bus_data=8'd0;
        assign bus_error=3'd0;assign bus_scl=1'b0;assign bus_sda=1'b0;
    end endgenerate
    assign ready=!busy && card_present && !abort && !kill;
    assign transport_ok=result_ok && card_present && !abort;
    assign scl_low=(wake_enabled && wake_scl) || (command_enabled && command_scl);
    assign sda_low=(wake_enabled && wake_sda) || (command_enabled && command_sda);
    assign signature_valid=active && state==COMMAND_WAIT && phase==2 && signature_count<64 && command_valid;
    atecc_wake #(.EXTERNAL_TRANSPORT(SHARE_TRANSPORT),.DIV(DIV),.WAKE_LOW_CYCLES(WAKE_LOW_CYCLES),.WAKE_HIGH_CYCLES(WAKE_HIGH_CYCLES),
        .POLL_CYCLES(POLL_CYCLES),.MAX_READ_ATTEMPTS(MAX_READ_ATTEMPTS),.BYTE_TIMEOUT(BYTE_TIMEOUT),
        .BUS_TIMEOUT(BUS_TIMEOUT),.TOTAL_TIMEOUT(WAKE_TIMEOUT)) wake_engine(
        .clk(clk),.rst_n(rst_n && wake_enabled),.req(wake_req),.abort(1'b0),.address(saved_address),
        .scl_in(scl_in),.sda_in(sda_in),.scl_low(wake_scl),.sda_low(wake_sda),.busy(),
        .done(wake_done),.wake_ok(wake_ok),.err(wake_err),.detail_error(wake_detail),
        .ext_req(wake_bus_req),.ext_reset_n(wake_bus_reset_n),.ext_address(wake_bus_address),
        .ext_busy(bus_busy),.ext_done(bus_done),.ext_valid(bus_valid),.ext_cleanup(bus_cleanup),
        .ext_scl_low(bus_scl),.ext_sda_low(bus_sda),.ext_data(bus_data),.ext_error(bus_error));
    // Capture by default; direct mode requires the parent to hold digest through Nonce.
    // No child captures external/live request pins in shared mode.
    atecc_typed_exchange #(.EXTERNAL_TRANSPORT(SHARE_TRANSPORT),.KEY_SLOT(KEY_SLOT),.DIV(DIV),.CAPTURE_DIGEST(SHARE_DIGEST ? 0 : 1),.EXEC_WAIT_CYCLES(EXEC_WAIT_CYCLES),
        .POLL_CYCLES(POLL_CYCLES),.MAX_READ_ATTEMPTS(MAX_READ_ATTEMPTS),.BYTE_TIMEOUT(BYTE_TIMEOUT),
        .BUS_TIMEOUT(BUS_TIMEOUT),.READ_TIMEOUT(READ_TIMEOUT),.PRODUCER_TIMEOUT(PRODUCER_TIMEOUT),.TOTAL_TIMEOUT(COMMAND_TIMEOUT)) command_engine(
        .clk(clk),.rst_n(rst_n && command_enabled),.req(command_req),.abort(1'b0),.operation(phase),
        .digest(saved_digest),.address(saved_address),.scl_in(scl_in),.sda_in(sda_in),
        .scl_low(command_scl),.sda_low(command_sda),.tentative_valid(command_valid),.tentative_data(signature_data),
        .tentative_ready(command_accept),.ready(command_ready),.busy(),.done(command_done),.packet_ok(command_ok),
        .err(command_err),.detail_error(command_detail),.transport_detail(command_transport),
        .ext_req(command_bus_req),.ext_reset_n(command_bus_reset_n),.ext_read_mode(command_bus_read),
        .ext_tx_valid(command_bus_tx_valid),.ext_rx_ready(command_bus_rx_ready),.ext_address(command_bus_address),
        .ext_length(command_bus_length),.ext_tx_data(command_bus_tx_data),.ext_tx_ready(bus_tx_ready),
        .ext_busy(bus_busy),.ext_done(bus_done),.ext_valid(bus_valid),.ext_cleanup(bus_cleanup),
        .ext_scl_low(bus_scl),.ext_sda_low(bus_sda),.ext_data(bus_data),.ext_error(bus_error));
    // Private elapsed is observed only while busy. Idle initializes it before
    // acceptance; at abort/error/expiry the FSM closes busy on this same edge.
    // No idle free-running switching, and no timer enable feedback mux.
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            state<=IDLE;phase<=0;digest_valid<=0;saved_address<=0;signature_count<=0;
            wake_req<=0;command_req<=0;kill<=0;result_ok<=0;busy<=0;done<=0;
            err<=0;child_error<=0;detail_error<=0;transport_detail<=0;
        end else begin
            done<=0;wake_req<=0;command_req<=0;kill<=0;
            if(abort || !card_present) begin
                state<=IDLE;busy<=0;done<=busy;result_ok<=0;digest_valid<=0;kill<=1;
                err<=abort?1:2;child_error<=0;detail_error<=0;transport_detail<=0;
            end else if(!busy) begin
                if(req && ready) begin
                    saved_address<=address;digest_valid<=1;signature_count<=0;phase<=0;
                    result_ok<=0;err<=0;child_error<=0;detail_error<=0;transport_detail<=0;
                    if(KEY_SLOT<0 || KEY_SLOT>15) begin done<=1;err<=6;digest_valid<=0;end
                    else begin state<=WAKE_START;busy<=1;end
                end
            end else if(invalid_context || timer_fault_observed) begin
                state<=IDLE;busy<=0;done<=1;result_ok<=0;digest_valid<=0;err<=6;kill<=1;
            end else if(expired) begin
                state<=IDLE;busy<=0;done<=1;result_ok<=0;digest_valid<=0;err<=5;kill<=1;
            end else begin

                if(signature_valid && signature_ready) signature_count<=signature_count+1'b1;
                case(state)
                    WAKE_START: begin wake_req<=1;state<=WAKE_WAIT;end
                    WAKE_WAIT: if(wake_done) begin
                        if(wake_err!=0 || !wake_ok) begin
                            state<=IDLE;busy<=0;done<=1;result_ok<=0;digest_valid<=0;kill<=1;
                            err<=3;child_error<=wake_err;detail_error<=wake_detail;
                        end else state<=COMMAND_START;
                    end
                    COMMAND_START: if(command_ready && !command_done) begin command_req<=1;state<=COMMAND_WAIT;end
                    COMMAND_WAIT: if(command_done) begin
                        if(command_err!=0 || !command_ok) begin
                            state<=IDLE;busy<=0;done<=1;result_ok<=0;digest_valid<=0;kill<=1;err<=4;
                            child_error<=command_err;detail_error<=command_detail;transport_detail<=command_transport;
                        end else if(phase==2) begin
                            state<=IDLE;busy<=0;done<=1;digest_valid<=0;kill<=1;
                            if(signature_count==64) begin result_ok<=1;err<=0;end
                            else begin result_ok<=0;err<=7;end
                        end else begin
                            if(phase==1) digest_valid<=0;
                            phase<=phase+1'b1;state<=COMMAND_START;
                        end
                    end
                endcase
            end
        end
    end
endmodule
`default_nettype wire
