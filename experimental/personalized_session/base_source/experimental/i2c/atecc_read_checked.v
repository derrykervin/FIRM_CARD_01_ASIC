// Experimental read transport + integrity checker. packet_ok is NOT authentication.
module atecc_read_checked #(
    parameter integer EXTERNAL_TRANSPORT=0,
    parameter integer DIV=100,
    parameter integer BYTE_TIMEOUT=400000,
    parameter integer BUS_TIMEOUT=4000000,
    parameter integer TOTAL_TIMEOUT=5000000
)(input wire clk,input wire rst_n,input wire req,input wire abort,
  input wire [6:0] address,input wire [6:0] expected_count,
  input wire scl_in,input wire sda_in,output wire scl_low,output wire sda_low,
  output wire ready,output wire tentative_valid,output wire [7:0] tentative_data,
  input wire tentative_ready,output reg busy,output reg done,output reg packet_ok,
  output reg [2:0] err,output reg [2:0] detail_error,output reg retryable_nack,
  // Optional private transport boundary, used by the exclusive command owner.
  output wire ext_req,ext_reset_n,ext_rx_ready,
  output wire [6:0] ext_address,ext_count,
  input wire ext_busy,ext_done,ext_valid,ext_cleanup,
  input wire [2:0] ext_error,input wire [7:0] ext_data);
    reg child_start,kill_bus,bus_seen,checker_seen;
    reg [6:0] saved_count,saved_address,rx_index;
    wire bus_busy,bus_done,bus_valid,bus_cleanup,checker_busy,checker_done,checker_ok,checker_ready,checker_tentative;
    wire [2:0] bus_error,checker_error;
    wire [7:0] bus_data;
    function integer counter_width;
        input integer limit;integer value;
        begin counter_width=1;value=limit-1;
            while(value>1) begin value=value>>1;counter_width=counter_width+1;end
        end
    endfunction
    reg [counter_width(TOTAL_TIMEOUT)-1:0] elapsed;
    wire invalid_context=(saved_count!=4 && saved_count!=35 && saved_count!=67) || rx_index>=saved_count;
    wire active=busy && !abort && !kill_bus && !invalid_context && elapsed<TOTAL_TIMEOUT-1;
    wire bridge_ready=active && checker_ready;
    assign ready=!busy && !abort && !kill_bus && !child_start && !bus_busy && !checker_busy && !bus_done && !checker_done;
    assign tentative_valid=active && checker_tentative;
    assign ext_req=child_start;
    assign ext_reset_n=rst_n && !kill_bus;
    assign ext_rx_ready=bridge_ready;
    assign ext_address=saved_address;
    assign ext_count=saved_count;
    generate if(EXTERNAL_TRANSPORT) begin: external_bus
        assign bus_busy=ext_busy;
        assign bus_done=ext_done;
        assign bus_valid=ext_valid;
        assign bus_cleanup=ext_cleanup;
        assign bus_error=ext_error;
        assign bus_data=ext_data;
        assign scl_low=1'b0;
        assign sda_low=1'b0;
    end else begin: internal_bus
    firm_i2c_transaction #(.DIV(DIV),.BYTE_TIMEOUT(BYTE_TIMEOUT),.TOTAL_TIMEOUT(BUS_TIMEOUT)) transport(
        .clk(clk),.rst_n(rst_n && !kill_bus),.req(child_start),.read_mode(1'b1),
        .address(saved_address),.length({1'b0,saved_count}),.tx_valid(1'b0),.tx_data(8'h0),.tx_ready(),
        .rx_valid(bus_valid),.rx_data(bus_data),.rx_ready(bridge_ready),
        .scl_in(scl_in),.sda_in(sda_in),.scl_low(scl_low),.sda_low(sda_low),
        .busy(bus_busy),.done(bus_done),.err(bus_error),.cleanup_failed(bus_cleanup));
    end endgenerate
    atecc_response_check #(.TIMEOUT_CYCLES(TOTAL_TIMEOUT)) response_parser(
        .clk(clk),.rst_n(rst_n),.start(child_start),.abort(abort || kill_bus),
        .expected_count(saved_count),.rx_valid(active && bus_valid),.rx_data(bus_data),
        .rx_last(rx_index==saved_count-1),.rx_ready(checker_ready),
        .tentative_valid(checker_tentative),.tentative_data(tentative_data),.tentative_ready(tentative_ready),
        .busy(checker_busy),.done(checker_done),.integrity_ok(checker_ok),.err(checker_error));
    // Private elapsed is observed only while busy. Idle initializes it before
    // acceptance; at abort/error/expiry the FSM closes busy on this same edge.
    // No idle free-running switching, and no timer enable feedback mux.
    always @(posedge clk) begin
        if(!busy) elapsed<=0;
        else elapsed<=elapsed+1'b1;
    end
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            child_start<=0;kill_bus<=0;bus_seen<=0;checker_seen<=0;
            saved_count<=0;saved_address<=0;rx_index<=0;
            busy<=0;done<=0;packet_ok<=0;err<=0;detail_error<=0;retryable_nack<=0;
        end else begin
            child_start<=0;kill_bus<=0;done<=0;
            if(abort) begin
                kill_bus<=1;done<=busy;busy<=0;packet_ok<=0;err<=3;detail_error<=0;retryable_nack<=0;
            end else if(!busy) begin

                if(req && ready) begin
                    packet_ok<=0;err<=0;detail_error<=0;rx_index<=0;retryable_nack<=0;
                    bus_seen<=0;checker_seen<=0;saved_count<=expected_count;saved_address<=address;
                    if(expected_count!=4 && expected_count!=35 && expected_count!=67) begin done<=1;err<=5;end
                    else begin busy<=1;child_start<=1;end
                end
            end else if(invalid_context) begin
                kill_bus<=1;done<=1;busy<=0;packet_ok<=0;err<=6;detail_error<=0;
            end else if(elapsed>=TOTAL_TIMEOUT-1) begin
                kill_bus<=1;done<=1;busy<=0;packet_ok<=0;err<=4;detail_error<=0;
            end else if(bus_done && bus_error!=0) begin
                kill_bus<=1;done<=1;busy<=0;packet_ok<=0;err<=1;detail_error<=bus_error;
                // Address NACK means device-busy only if cleanup STOP really completed.
                retryable_nack<=bus_error==1 && !bus_cleanup;
            end else if(checker_done && (checker_error!=0 || !checker_ok)) begin
                kill_bus<=1;done<=1;busy<=0;packet_ok<=0;err<=2;detail_error<=checker_error;
            end else begin

                if(active && bus_valid && bridge_ready && rx_index<saved_count-1) rx_index<=rx_index+1'b1;
                if(bus_done) bus_seen<=1;
                if(checker_done) checker_seen<=1;
                // A valid CRC cannot override a failed or incomplete final STOP.
                if((bus_seen || bus_done) && (checker_seen || checker_done)) begin
                    done<=1;busy<=0;packet_ok<=1;err<=0;detail_error<=0;
                end
            end
        end
    end
endmodule
