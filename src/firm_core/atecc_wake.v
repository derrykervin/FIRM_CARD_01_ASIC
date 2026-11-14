`default_nettype none
// Candidate ATECC608 wake waveform + exact response + STOP validation.
// Timing targets require checking against the final part/board datasheet.
module atecc_wake #(
    parameter integer EXTERNAL_TRANSPORT=0,
    parameter integer DIV=100,
    parameter integer WAKE_LOW_CYCLES=3200,
    parameter integer WAKE_HIGH_CYCLES=60000,
    parameter integer POLL_CYCLES=40000,
    parameter integer MAX_READ_ATTEMPTS=20,
    parameter integer BYTE_TIMEOUT=400000,
    parameter integer BUS_TIMEOUT=4000000,
    parameter integer TOTAL_TIMEOUT=2000000
)(
    input wire clk,rst_n,req,abort,
    input wire [6:0] address,
    input wire scl_in,sda_in,
    output wire scl_low,sda_low,
    output reg busy,done,wake_ok,
    output reg [2:0] err,detail_error,
    output wire ext_req,ext_reset_n,output wire [6:0] ext_address,
    input wire ext_busy,ext_done,ext_valid,ext_cleanup,ext_scl_low,ext_sda_low,
    input wire [7:0] ext_data,input wire [2:0] ext_error
);
    localparam [2:0] IDLE=0,WAIT_IDLE=1,PULSE=2,DELAY=3,READ=4,POLL=5;
    function integer width_for;
        input integer value;
        begin width_for=1;while((value>>width_for)>0) width_for=width_for+1;end
    endfunction
    localparam PHASE_MAX=(WAKE_LOW_CYCLES>WAKE_HIGH_CYCLES?WAKE_LOW_CYCLES:WAKE_HIGH_CYCLES)>POLL_CYCLES ?
        (WAKE_LOW_CYCLES>WAKE_HIGH_CYCLES?WAKE_LOW_CYCLES:WAKE_HIGH_CYCLES):POLL_CYCLES;
    reg [width_for(PHASE_MAX-1)-1:0] phase_count;
    reg [width_for(TOTAL_TIMEOUT-1)-1:0] elapsed;
    reg [width_for(MAX_READ_ATTEMPTS)-1:0] attempts;
    reg [2:0] state,received;
    // Exact suffix matcher for both four-byte tokens; no checksum collisions.
    // Keeping a four-byte shift bank is unnecessary for these two comparisons.
    (* fsm_encoding="none" *) reg [2:0] response_pattern;
    // BEGIN_WAKE_PATTERN_FUNCTION
    function [2:0] next_wake_pattern;
        input [2:0] prior;
        input [7:0] value;
        begin
            // Both tokens start with 04, which is absent from their interiors.
            if(value==8'h04) next_wake_pattern=1;
            else case(prior)
                1: if(value==8'h11) next_wake_pattern=2;
                   else if(value==8'h07) next_wake_pattern=5;
                   else next_wake_pattern=0;
                2: next_wake_pattern=(value==8'h33) ? 3:0;
                3: next_wake_pattern=(value==8'h43) ? 4:0;
                5: next_wake_pattern=(value==8'hc4) ? 6:0;
                6: next_wake_pattern=(value==8'h40) ? 7:0;
                default: next_wake_pattern=0;
            endcase
        end
    endfunction
    // END_WAKE_PATTERN_FUNCTION
    reg [6:0] saved_address;
    reg bus_req;
    reg scl_meta,scl_sync,sda_meta,sda_sync;
    reg [1:0] sample_valid;
    reg [1:0] settle_count;
    wire bus_busy,bus_done,bus_valid,bus_scl_low,bus_sda_low,bus_cleanup;
    wire [7:0] bus_data;wire [2:0] bus_err;
    wire expired=elapsed>=TOTAL_TIMEOUT-1;
    wire invalid_context=state==IDLE || state>POLL || received>4 ||
        (state==PULSE && phase_count>=WAKE_LOW_CYCLES) ||
        (state==DELAY && phase_count>=WAKE_HIGH_CYCLES) ||
        (state==POLL && phase_count>=POLL_CYCLES);
    wire active=busy && !abort && !expired && !invalid_context;
    wire read_active=active && state==READ;
    assign scl_low=read_active && bus_scl_low;
    assign sda_low=active && ((state==PULSE) || (state==READ && bus_sda_low));
    wire [2:0] pattern_next=bus_valid ? next_wake_pattern(response_pattern,bus_data):response_pattern;
    wire [2:0] count_next=received+(bus_valid ? 3'd1:3'd0);
    assign ext_req=bus_req;
    assign ext_reset_n=rst_n && read_active;
    assign ext_address=saved_address;
    generate if(EXTERNAL_TRANSPORT) begin: external_bus
        assign bus_busy=ext_busy;
        assign bus_done=ext_done;
        assign bus_valid=ext_valid;
        assign bus_cleanup=ext_cleanup;
        assign bus_data=ext_data;
        assign bus_err=ext_error;
        assign bus_scl_low=ext_scl_low;
        assign bus_sda_low=ext_sda_low;
    end else begin: internal_bus
    firm_i2c_transaction #(.DIV(DIV),.BYTE_TIMEOUT(BYTE_TIMEOUT),.TOTAL_TIMEOUT(BUS_TIMEOUT)) transport(
        .clk(clk),.rst_n(rst_n && read_active),.req(bus_req),.read_mode(1'b1),
        .address(saved_address),.length(8'd4),.tx_valid(1'b0),.tx_data(8'h00),.tx_ready(),
        .rx_valid(bus_valid),.rx_data(bus_data),.rx_ready(1'b1),.scl_in(scl_in),.sda_in(sda_in),
        .scl_low(bus_scl_low),.sda_low(bus_sda_low),.busy(bus_busy),.done(bus_done),
        .err(bus_err),.cleanup_failed(bus_cleanup));
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            scl_meta<=1;scl_sync<=1;sda_meta<=1;sda_sync<=1;sample_valid<=0;
        end else begin
            scl_meta<=scl_in;scl_sync<=scl_meta;sda_meta<=sda_in;sda_sync<=sda_meta;
            sample_valid<={sample_valid[0],1'b1};
        end
    end
    // Private elapsed is observed only while busy. Idle initializes it before
    // acceptance; at abort/error/expiry the FSM closes busy on this same edge.
    // No idle free-running switching, and no timer enable feedback mux.
    always @(posedge clk) begin
        if(!busy) elapsed<=0;
        else elapsed<=elapsed+1'b1;
    end
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            state<=IDLE;phase_count<=0;attempts<=0;received<=0;response_pattern<=0;
            saved_address<=0;bus_req<=0;busy<=0;done<=0;wake_ok<=0;err<=0;detail_error<=0;settle_count<=0;
        end else begin
            done<=0;bus_req<=0;
            if(abort) begin
                done<=busy;busy<=0;wake_ok<=0;err<=1;detail_error<=0;state<=IDLE;
            end else if(!busy) begin
                if(req) begin
                    state<=WAIT_IDLE;phase_count<=0;attempts<=0;received<=0;response_pattern<=0;
                    saved_address<=address;busy<=1;wake_ok<=0;err<=0;detail_error<=0;settle_count<=0;
                end
            end else if(invalid_context) begin
                busy<=0;done<=1;wake_ok<=0;err<=6;state<=IDLE;
            end else if(expired) begin
                busy<=0;done<=1;wake_ok<=0;err<=2;state<=IDLE;
            end else begin

                case(state)
                    WAIT_IDLE: begin
                        if(settle_count<3) settle_count<=settle_count+1'b1;
                        if(settle_count==3 && sample_valid[1] && scl_sync && sda_sync) begin state<=PULSE;phase_count<=0;end
                    end
                    PULSE: if(phase_count==WAKE_LOW_CYCLES-1) begin state<=DELAY;phase_count<=0;end
                           else phase_count<=phase_count+1'b1;
                    DELAY,POLL: begin
                        if(!sample_valid[1] || !scl_sync || !sda_sync) phase_count<=0;
                        else if(phase_count==((state==DELAY)?WAKE_HIGH_CYCLES-1:POLL_CYCLES-1)) begin
                            state<=READ;phase_count<=0;received<=0;response_pattern<=0;
                            attempts<=attempts+1'b1;bus_req<=1;
                        end else phase_count<=phase_count+1'b1;
                    end
                    READ: begin
                        if(bus_valid) begin received<=count_next;response_pattern<=pattern_next;end
                        if(bus_done) begin
                            if(bus_err==1 && !bus_cleanup && attempts<MAX_READ_ATTEMPTS) begin
                                state<=POLL;phase_count<=0;received<=0;response_pattern<=0;
                            end else begin
                                busy<=0;done<=1;state<=IDLE;
                                if(bus_err!=0 || bus_cleanup) begin err<=3;detail_error<=bus_err;wake_ok<=0;end
                                else if(count_next==4 && pattern_next==3'd4) begin wake_ok<=1;err<=0;end
                                else begin wake_ok<=0;err<=pattern_next==3'd7 ? 5:4;end
                            end
                        end
                    end
                endcase
            end
        end
    end
endmodule
`default_nettype wire
