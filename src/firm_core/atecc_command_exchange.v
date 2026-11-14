`default_nettype none
// Trusted command packet stream -> STOP -> execution wait -> checked response.
// Requires external wake/command-policy ownership. packet_ok is NOT authentication.
module atecc_command_exchange #(
    parameter integer SHARE_BUS=1,
    parameter integer EXTERNAL_TRANSPORT=0,
    parameter integer DIV=100,
    parameter integer EXEC_WAIT_CYCLES=40000,
    parameter integer POLL_CYCLES=40000,
    parameter integer MAX_READ_ATTEMPTS=20,
    parameter integer BYTE_TIMEOUT=400000,
    parameter integer BUS_TIMEOUT=4000000,
    parameter integer READ_TIMEOUT=5000000,
    parameter integer TOTAL_TIMEOUT=8000000
)(
    input wire clk,rst_n,req,abort,
    input wire [6:0] address,command_length,response_count,
    input wire tx_valid,input wire [7:0] tx_data,output wire tx_ready,
    output wire tentative_valid,output wire [7:0] tentative_data,input wire tentative_ready,
    input wire scl_in,sda_in,output wire scl_low,sda_low,
    output wire ready,output reg busy,done,packet_ok,
    output reg [2:0] err,detail_error,transport_detail,
    output wire ext_req,ext_reset_n,ext_read_mode,ext_tx_valid,ext_rx_ready,
    output wire [6:0] ext_address,output wire [7:0] ext_length,ext_tx_data,
    input wire ext_tx_ready,ext_busy,ext_done,ext_valid,ext_cleanup,ext_scl_low,ext_sda_low,
    input wire [7:0] ext_data,input wire [2:0] ext_error
);
    localparam [2:0] IDLE=0,WRITE=1,EXEC_WAIT=2,READ_START=3,READ=4,POLL=5;
    function integer cw;
        input integer limit;integer v;
        begin cw=1;v=limit-1;while(v>1) begin v=v>>1;cw=cw+1;end end
    endfunction
    localparam WAIT_MAX=EXEC_WAIT_CYCLES>POLL_CYCLES?EXEC_WAIT_CYCLES:POLL_CYCLES;
    reg [2:0] state;
    reg [6:0] saved_address,saved_length,saved_count;
    reg [cw(WAIT_MAX)-1:0] phase_count;
    reg [cw(TOTAL_TIMEOUT)-1:0] elapsed;
    reg [cw(MAX_READ_ATTEMPTS+1)-1:0] attempts;
    reg write_req,read_req;
    wire write_done,write_cleanup,write_scl,write_sda,write_ready;
    wire [2:0] write_err;
    wire read_ready,read_done,read_ok,read_retry,read_scl,read_sda,read_valid;
    wire [2:0] read_err,read_detail;
    wire read_bus_req,read_bus_reset_n,read_bus_rx_ready;
    wire [6:0] read_bus_address,read_bus_count;
    wire shared_busy,shared_done,shared_valid,shared_cleanup,shared_scl,shared_sda;
    wire [2:0] shared_error;
    wire [7:0] shared_data;
    wire expired=elapsed>=TOTAL_TIMEOUT-1;
    wire invalid_context=state==IDLE || state>POLL || saved_length<7 || saved_length>67 ||
        (saved_count!=4 && saved_count!=35 && saved_count!=67) || attempts>MAX_READ_ATTEMPTS ||
        (state==EXEC_WAIT && phase_count>=EXEC_WAIT_CYCLES) || (state==POLL && phase_count>=POLL_CYCLES);
    wire active=busy && !abort && !expired && !invalid_context;
    wire write_active=active && state==WRITE;
    wire read_active=active && (state==READ_START || state==READ);
    assign ext_reset_n=rst_n && (write_active || (read_active && read_bus_reset_n));
    assign ext_req=write_active ? write_req : (read_active && read_bus_req);
    assign ext_read_mode=read_active;
    assign ext_address=write_active ? saved_address : read_bus_address;
    assign ext_length=write_active ? {1'b0,saved_length} : {1'b0,read_bus_count};
    assign ext_tx_valid=write_active && tx_valid;
    assign ext_tx_data=tx_data;
    assign ext_rx_ready=read_active ? read_bus_rx_ready : 1'b1;
    assign ready=!busy && !abort;
    assign tx_ready=write_active && write_ready;
    assign tentative_valid=active && state==READ && read_valid;
    assign scl_low=SHARE_BUS ? ((write_active || read_active) && shared_scl) :
        ((write_active && write_scl) || (read_active && read_scl));
    assign sda_low=SHARE_BUS ? ((write_active || read_active) && shared_sda) :
        ((write_active && write_sda) || (read_active && read_sda));
    generate if(SHARE_BUS) begin: shared_bus
        // One owner at a time. Reset between write, execution wait and each read.
        // The checked reader retains authority to kill/reset an incomplete bus.
        if(EXTERNAL_TRANSPORT) begin: external_bus
            assign write_ready=ext_tx_ready;
            assign shared_busy=ext_busy;
            assign shared_done=ext_done;
            assign shared_valid=ext_valid;
            assign shared_cleanup=ext_cleanup;
            assign shared_error=ext_error;
            assign shared_data=ext_data;
            assign shared_scl=ext_scl_low;
            assign shared_sda=ext_sda_low;
        end else begin: internal_bus
        firm_i2c_transaction #(.DIV(DIV),.BYTE_TIMEOUT(BYTE_TIMEOUT),.TOTAL_TIMEOUT(BUS_TIMEOUT)) transport(
            .clk(clk),.rst_n(ext_reset_n),
            .req(ext_req),.read_mode(ext_read_mode),
            .address(ext_address),.length(ext_length),
            .tx_valid(ext_tx_valid),.tx_data(ext_tx_data),.tx_ready(write_ready),
            .rx_valid(shared_valid),.rx_data(shared_data),.rx_ready(ext_rx_ready),
            .scl_in(scl_in),.sda_in(sda_in),.scl_low(shared_scl),.sda_low(shared_sda),
            .busy(shared_busy),.done(shared_done),.err(shared_error),.cleanup_failed(shared_cleanup));
        end
        assign write_done=shared_done;
        assign write_err=shared_error;
        assign write_cleanup=shared_cleanup;
        assign write_scl=1'b0;
        assign write_sda=1'b0;
    end else begin: separate_buses
        assign shared_busy=1'b0;
        assign shared_done=1'b0;
        assign shared_valid=1'b0;
        assign shared_cleanup=1'b0;
        assign shared_error=3'd0;
        assign shared_data=8'd0;
        assign shared_scl=1'b0;
        assign shared_sda=1'b0;
    firm_i2c_transaction #(.DIV(DIV),.BYTE_TIMEOUT(BYTE_TIMEOUT),.TOTAL_TIMEOUT(BUS_TIMEOUT)) writer(
        .clk(clk),.rst_n(rst_n && write_active),.req(write_req),.read_mode(1'b0),
        .address(saved_address),.length({1'b0,saved_length}),.tx_valid(write_active && tx_valid),.tx_data(tx_data),
        .tx_ready(write_ready),.rx_valid(),.rx_data(),.rx_ready(1'b1),.scl_in(scl_in),.sda_in(sda_in),
        .scl_low(write_scl),.sda_low(write_sda),.busy(),.done(write_done),.err(write_err),.cleanup_failed(write_cleanup));
    end endgenerate
    atecc_read_checked #(.EXTERNAL_TRANSPORT(SHARE_BUS),.DIV(DIV),.BYTE_TIMEOUT(BYTE_TIMEOUT),.BUS_TIMEOUT(BUS_TIMEOUT),.TOTAL_TIMEOUT(READ_TIMEOUT)) reader(
        .clk(clk),.rst_n(rst_n && read_active),.req(read_req),.abort(1'b0),
        .address(saved_address),.expected_count(saved_count),.scl_in(scl_in),.sda_in(sda_in),
        .scl_low(read_scl),.sda_low(read_sda),.ready(read_ready),.tentative_valid(read_valid),
        .tentative_data(tentative_data),.tentative_ready(tentative_ready),.busy(),.done(read_done),
        .packet_ok(read_ok),.err(read_err),.detail_error(read_detail),.retryable_nack(read_retry),
        .ext_req(read_bus_req),.ext_reset_n(read_bus_reset_n),.ext_rx_ready(read_bus_rx_ready),
        .ext_address(read_bus_address),.ext_count(read_bus_count),.ext_busy(shared_busy),
        .ext_done(shared_done),.ext_valid(shared_valid),.ext_cleanup(shared_cleanup),
        .ext_error(shared_error),.ext_data(shared_data));
    // Private elapsed is observed only while busy. Idle initializes it before
    // acceptance; at abort/error/expiry the FSM closes busy on this same edge.
    // No idle free-running switching, and no timer enable feedback mux.
    always @(posedge clk) begin
        if(!busy) elapsed<=0;
        else elapsed<=elapsed+1'b1;
    end
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            state<=IDLE;saved_address<=0;saved_length<=0;saved_count<=0;
            phase_count<=0;attempts<=0;write_req<=0;read_req<=0;
            busy<=0;done<=0;packet_ok<=0;err<=0;detail_error<=0;transport_detail<=0;
        end else begin
            done<=0;write_req<=0;read_req<=0;
            if(abort) begin
                state<=IDLE;busy<=0;done<=busy;packet_ok<=0;err<=1;detail_error<=0;transport_detail<=0;
            end else if(!busy) begin
                if(req && ready) begin
                    saved_address<=address;saved_length<=command_length;saved_count<=response_count;
                    phase_count<=0;attempts<=0;packet_ok<=0;err<=0;detail_error<=0;transport_detail<=0;
                    if(command_length<7 || command_length>67 || (response_count!=4 && response_count!=35 && response_count!=67)) begin done<=1;err<=5;end
                    else begin state<=WRITE;busy<=1;write_req<=1;end
                end
            end else if(invalid_context) begin
                state<=IDLE;busy<=0;done<=1;packet_ok<=0;err<=6;
            end else if(expired) begin
                state<=IDLE;busy<=0;done<=1;packet_ok<=0;err<=4;
            end else begin

                case(state)
                    WRITE: if(write_done) begin
                        if(write_err!=0 || write_cleanup) begin state<=IDLE;busy<=0;done<=1;err<=2;detail_error<=write_err;end
                        else begin state<=EXEC_WAIT;phase_count<=0;end
                    end
                    EXEC_WAIT: if(phase_count==EXEC_WAIT_CYCLES-1) begin state<=READ_START;phase_count<=0;end
                               else phase_count<=phase_count+1'b1;
                    READ_START: if(read_ready) begin state<=READ;read_req<=1;attempts<=attempts+1'b1;end
                    READ: if(read_done) begin
                        if(read_ok && read_err==0) begin state<=IDLE;busy<=0;done<=1;packet_ok<=1;end
                        else if(read_retry && attempts<MAX_READ_ATTEMPTS) begin state<=POLL;phase_count<=0;end
                        else begin state<=IDLE;busy<=0;done<=1;packet_ok<=0;err<=3;detail_error<=read_err;transport_detail<=read_detail;end
                    end
                    POLL: if(phase_count==POLL_CYCLES-1) begin state<=READ_START;phase_count<=0;end
                          else phase_count<=phase_count+1'b1;
                endcase
            end
        end
    end
endmodule
`default_nettype wire
