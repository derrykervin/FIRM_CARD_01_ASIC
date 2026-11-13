`default_nettype none
// Single-command owner; not wake/session control or signature verification.
module atecc_unified_exchange #(
    parameter integer KEY_SLOT=2,DIV=100,
    // 0 requires an enclosing immutable-digest owner; public default captures.
    parameter integer CAPTURE_DIGEST=1,
    parameter integer EXTERNAL_TRANSPORT=0,
    parameter integer EXEC_WAIT_CYCLES=40000,POLL_CYCLES=40000,MAX_READ_ATTEMPTS=128,
    parameter integer BYTE_TIMEOUT=400000,BUS_TIMEOUT=4000000,READ_TIMEOUT=5000000,
    parameter integer PRODUCER_TIMEOUT=4000000,TOTAL_TIMEOUT=8000000
)(
    input wire clk,rst_n,req,abort,
    input wire [2:0] operation,input wire [1:0] config_block,input wire [255:0] digest,input wire [6:0] address,
    input wire scl_in,sda_in,output wire scl_low,sda_low,
    output wire tentative_valid,output wire [7:0] tentative_data,input wire tentative_ready,
    output wire ready,output reg busy,done,packet_ok,
    output reg [2:0] err,detail_error,transport_detail,
    output wire ext_req,ext_reset_n,ext_read_mode,ext_tx_valid,ext_rx_ready,
    output wire [6:0] ext_address,output wire [7:0] ext_length,ext_tx_data,
    input wire ext_tx_ready,ext_busy,ext_done,ext_valid,ext_cleanup,ext_scl_low,ext_sda_low,
    input wire [7:0] ext_data,input wire [2:0] ext_error
);
    localparam [1:0] IDLE=0,LAUNCH=1,RUN=2;
    function integer cw;
        input integer limit;integer v;
        begin cw=1;v=limit-1;while(v>1) begin v=v>>1;cw=cw+1;end end
    endfunction
    reg [1:0] state;
    reg [6:0] saved_address;
    reg [cw(TOTAL_TIMEOUT)-1:0] elapsed;
    reg bus_req,kill,producer_complete;
    wire invalid_context=busy && (state==IDLE || state>RUN);
    wire expired=busy && elapsed>=TOTAL_TIMEOUT-1;
    wire active=busy && !abort && !expired && !invalid_context && !kill;
    wire producer_ready,producer_busy,producer_done,producer_valid;
    wire [2:0] producer_err;
    wire [6:0] command_length,response_count;
    wire [7:0] producer_data;
    wire bus_ready,bus_done,bus_ok,bus_tx_ready,bus_valid,bus_scl,bus_sda;
    wire [2:0] bus_err,bus_detail,bus_transport;
    wire child_abort=abort || kill || expired || invalid_context;
    assign ready=!busy && !abort && !kill && producer_ready && bus_ready && !producer_done && !bus_done;
    assign scl_low=active && bus_scl;
    assign sda_low=active && bus_sda;
    assign tentative_valid=active && bus_valid;
    atecc_unified_producer #(.KEY_SLOT(KEY_SLOT),.CAPTURE_DIGEST(CAPTURE_DIGEST),.TIMEOUT_CYCLES(PRODUCER_TIMEOUT)) generator(
        .clk(clk),.rst_n(rst_n && !kill),.req(req && ready),.abort(child_abort),
        .operation(operation),.config_block(config_block),.digest(digest),.ready(producer_ready),.busy(producer_busy),
        .done(producer_done),.err(producer_err),.command_length(command_length),.response_count(response_count),
        .tx_valid(producer_valid),.tx_data(producer_data),.tx_ready(active && bus_tx_ready));
    atecc_command_exchange #(.EXTERNAL_TRANSPORT(EXTERNAL_TRANSPORT),.DIV(DIV),.EXEC_WAIT_CYCLES(EXEC_WAIT_CYCLES),.POLL_CYCLES(POLL_CYCLES),
        .MAX_READ_ATTEMPTS(MAX_READ_ATTEMPTS),.BYTE_TIMEOUT(BYTE_TIMEOUT),.BUS_TIMEOUT(BUS_TIMEOUT),
        .READ_TIMEOUT(READ_TIMEOUT),.TOTAL_TIMEOUT(TOTAL_TIMEOUT)) transport(
        .clk(clk),.rst_n(rst_n && !kill),.req(bus_req),.abort(child_abort),
        .address(saved_address),.command_length(command_length),.response_count(response_count),
        .tx_valid(active && producer_valid),.tx_data(producer_data),.tx_ready(bus_tx_ready),
        .tentative_valid(bus_valid),.tentative_data(tentative_data),.tentative_ready(active && tentative_ready),
        .scl_in(scl_in),.sda_in(sda_in),.scl_low(bus_scl),.sda_low(bus_sda),.ready(bus_ready),
        .busy(),.done(bus_done),.packet_ok(bus_ok),.err(bus_err),.detail_error(bus_detail),.transport_detail(bus_transport),
        .ext_req(ext_req),.ext_reset_n(ext_reset_n),.ext_read_mode(ext_read_mode),
        .ext_tx_valid(ext_tx_valid),.ext_rx_ready(ext_rx_ready),.ext_address(ext_address),
        .ext_length(ext_length),.ext_tx_data(ext_tx_data),.ext_tx_ready(ext_tx_ready),
        .ext_busy(ext_busy),.ext_done(ext_done),.ext_valid(ext_valid),.ext_cleanup(ext_cleanup),
        .ext_scl_low(ext_scl_low),.ext_sda_low(ext_sda_low),.ext_data(ext_data),.ext_error(ext_error));
    // Private elapsed is observed only while busy. Idle initializes it before
    // acceptance; at abort/error/expiry the FSM closes busy on this same edge.
    // No idle free-running switching, and no timer enable feedback mux.
    always @(posedge clk) begin
        if(!busy) elapsed<=0;
        else elapsed<=elapsed+1'b1;
    end
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            state<=IDLE;saved_address<=0;bus_req<=0;kill<=0;producer_complete<=0;
            busy<=0;done<=0;packet_ok<=0;err<=0;detail_error<=0;transport_detail<=0;
        end else begin
            done<=0;bus_req<=0;kill<=0;
            if(abort) begin
                state<=IDLE;busy<=0;done<=busy;packet_ok<=0;err<=1;detail_error<=0;transport_detail<=0;kill<=1;
            end else if(!busy) begin
                if(req && ready) begin
                    state<=LAUNCH;saved_address<=address;producer_complete<=0;
                    busy<=1;packet_ok<=0;err<=0;detail_error<=0;transport_detail<=0;
                end
            end else if(invalid_context) begin
                state<=IDLE;busy<=0;done<=1;packet_ok<=0;err<=6;kill<=1;
            end else if(expired) begin
                state<=IDLE;busy<=0;done<=1;packet_ok<=0;err<=4;kill<=1;
            end else if(producer_done && producer_err!=0) begin
                state<=IDLE;busy<=0;done<=1;packet_ok<=0;err<=7;detail_error<=producer_err;transport_detail<=0;kill<=1;
            end else begin

                if(producer_done && producer_err==0) producer_complete<=1;
                case(state)
                    LAUNCH: if(producer_busy && bus_ready) begin bus_req<=1;state<=RUN;end
                    RUN: if(bus_done) begin
                        state<=IDLE;busy<=0;done<=1;kill<=1;
                        detail_error<=bus_detail;transport_detail<=bus_transport;
                        if(bus_err!=0 || !bus_ok) begin packet_ok<=0;err<=bus_err==0?6:bus_err;end
                        else if(!(producer_complete || (producer_done && producer_err==0))) begin packet_ok<=0;err<=6;end
                        else begin packet_ok<=1;err<=0;end
                    end
                endcase
            end
        end
    end
endmodule
`default_nettype wire
