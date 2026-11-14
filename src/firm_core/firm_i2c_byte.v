// Experimental open-drain byte primitive; not in the tapeout source list.
// op: START=0, WRITE=1, READ_ACK=2, READ_NACK=3, STOP=4.
// err: OK=0, NACK=1, TIMEOUT=2, BUS_BUSY=3, BAD_OP=4, ARB_LOST=5.
module firm_i2c_byte #(
    parameter integer DIV = 100,
    parameter integer TIMEOUT_CYCLES = 400000
)(input wire clk, input wire rst_n,
  input wire req, input wire [2:0] op, input wire [7:0] tx,
  input wire scl_in, input wire sda_in,
  output reg scl_low, output reg sda_low,
  output reg busy, output reg done, output reg [2:0] err,
  output reg [7:0] rx);
    reg scl_meta, scl_sync, sda_meta, sda_sync;
    reg [1:0] sample_valid;
    reg [3:0] state;
    reg [2:0] command, bit_index;
    reg [7:0] data;
    reg ack_bit;
    // Guard the one-cycle case: Verilog vectors must never have width zero.
    function integer counter_width;
        input integer limit;
        integer value;
        begin
            counter_width=1;
            value=limit-1;
            while(value>1) begin value=value>>1;counter_width=counter_width+1;end
        end
    endfunction
    localparam integer DIV_WIDTH=counter_width(DIV);
    localparam integer TIME_WIDTH=counter_width(TIMEOUT_CYCLES);
    reg [DIV_WIDTH-1:0] divider;
    reg [TIME_WIDTH-1:0] elapsed;
    localparam IDLE=0, START_WAIT=1, START_HOLD=2, PREP=3,
               RAISE=4, WAIT_HIGH=5, SAMPLE=6, STOP_LOW=7,
               STOP_RAISE=8, STOP_WAIT=9, STOP_RELEASE=10;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            scl_meta<=1; scl_sync<=1; sda_meta<=1; sda_sync<=1;
            sample_valid<=0;
        end else begin
            sample_valid<={sample_valid[0],1'b1};
            scl_meta<=scl_in; scl_sync<=scl_meta;
            sda_meta<=sda_in; sda_sync<=sda_meta;
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
        if (!rst_n) begin
            state<=IDLE; command<=0; bit_index<=7; data<=0; ack_bit<=0;
            scl_low<=0; sda_low<=0; busy<=0; done<=0; err<=0; rx<=0;
            divider<=0;
        end else begin
            done<=0;
            if (!busy) begin
                divider<=0;
                if (req) begin
                    command<=op; data<=tx; bit_index<=7; ack_bit<=0;
                    err<=0; rx<=0; busy<=1;
                    case (op)
                        0: begin scl_low<=0; sda_low<=0; state<=START_WAIT; end
                        1,2,3: begin scl_low<=1; state<=PREP; end
                        4: state<=STOP_LOW;
                        default: begin
                            scl_low<=0; sda_low<=0; busy<=0; done<=1; err<=4;
                        end
                    endcase
                end
            end else if (elapsed >= TIMEOUT_CYCLES-1) begin
                scl_low<=0; sda_low<=0; busy<=0; done<=1;
                err<=(command==0) ? 3 : 2; state<=IDLE;
            end else begin

                if (divider >= DIV-1) begin
                    divider<=0;
                    case (state)
                        START_WAIT: if (sample_valid[1] && scl_sync && sda_sync) begin
                            sda_low<=1; state<=START_HOLD;
                        end
                        START_HOLD: begin
                            scl_low<=1; busy<=0; done<=1; state<=IDLE;
                        end
                        PREP: begin
                            scl_low<=1;
                            if (ack_bit) sda_low<=(command==2);
                            else sda_low<=(command==1) && !data[bit_index];
                            state<=RAISE;
                        end
                        RAISE: begin scl_low<=0; state<=WAIT_HIGH; end
                        WAIT_HIGH: if (sample_valid[1] && scl_sync) state<=SAMPLE;
                        SAMPLE: begin
                            // Arbitration: a transmitted '1' must stay released.
                            if (command==1 && !ack_bit && data[bit_index] && !sda_sync) begin
                                scl_low<=0; sda_low<=0; busy<=0; done<=1;
                                err<=5; state<=IDLE;
                            end else begin
                                scl_low<=1;
                                if (ack_bit) begin
                                    if (command==1 && sda_sync) err<=1;
                                    sda_low<=0; busy<=0; done<=1; state<=IDLE;
                                end else begin
                                    if (command!=1) rx[bit_index]<=sda_sync;
                                    if (bit_index==0) ack_bit<=1;
                                    else bit_index<=bit_index-1'b1;
                                    state<=PREP;
                                end
                            end
                        end
                        STOP_LOW: begin scl_low<=1; sda_low<=1; state<=STOP_RAISE; end
                        STOP_RAISE: begin scl_low<=0; state<=STOP_WAIT; end
                        STOP_WAIT: if (sample_valid[1] && scl_sync) state<=STOP_RELEASE;
                        STOP_RELEASE: begin
                            sda_low<=0; busy<=0; done<=1; state<=IDLE;
                        end
                        default: begin
                            scl_low<=0; sda_low<=0; busy<=0; done<=1;
                            err<=4; state<=IDLE;
                        end
                    endcase
                end else divider<=divider+1;
            end
        end
    end
endmodule
