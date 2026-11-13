// Experimental streaming ATECC-style transaction, no wake/CRC or device policy.
// write: START addressW word03 payload STOP; read: START addressR bytes STOP.
module firm_i2c_transaction #(
    parameter integer DIV=100,
    parameter integer BYTE_TIMEOUT=400000,
    parameter integer TOTAL_TIMEOUT=4000000
)(input wire clk,input wire rst_n,input wire req,input wire read_mode,
  input wire [6:0] address,input wire [7:0] length,
  input wire tx_valid,input wire [7:0] tx_data,output wire tx_ready,
  output reg rx_valid,output reg [7:0] rx_data,input wire rx_ready,
  input wire scl_in,input wire sda_in,output wire scl_low,output wire sda_low,
  output reg busy,output reg done,output reg [2:0] err,
  output reg cleanup_failed);
    localparam IDLE=0, ISSUE=1, WAIT_BYTE=2, TX_WAIT=3, RX_WAIT=4;
    localparam START=0, ADDR=1, WORD=2, DATA=3, STOP=4;
    (* fsm_encoding="none" *) reg [2:0] state;
    reg [2:0] phase;
    reg direction;
    reg [6:0] saved_address;
    reg [7:0] count,index;
    reg byte_req,abort_byte;
    reg [2:0] byte_op;
    reg [7:0] byte_tx;
    wire byte_busy,byte_done;
    wire [2:0] byte_err;
    wire [7:0] byte_rx;
    function integer counter_width;
        input integer limit;
        integer value;
        begin
            counter_width=1;
            value=limit-1;
            while(value>1) begin value=value>>1;counter_width=counter_width+1;end
        end
    endfunction
    localparam integer TOTAL_WIDTH=counter_width(TOTAL_TIMEOUT);
    reg [TOTAL_WIDTH-1:0] elapsed;
    wire invalid_context;
    assign invalid_context=(state>RX_WAIT || phase>STOP || count==0 || count>67 ||
        index>=count || (direction && phase==WORD) ||
        (state==TX_WAIT && (direction || phase!=DATA)) ||
        (state==RX_WAIT && (!direction || phase!=DATA || !rx_valid)) ||
        (rx_valid && (state!=RX_WAIT || !direction || phase!=DATA)));
    assign tx_ready=busy && state==TX_WAIT && !invalid_context;
    firm_i2c_byte #(.DIV(DIV),.TIMEOUT_CYCLES(BYTE_TIMEOUT)) engine(
        .clk(clk),.rst_n(rst_n && !abort_byte),.req(byte_req),
        .op(byte_op),.tx(byte_tx),.scl_in(scl_in),.sda_in(sda_in),
        .scl_low(scl_low),.sda_low(sda_low),.busy(byte_busy),
        .done(byte_done),.err(byte_err),.rx(byte_rx));
    // Private elapsed is observed only while busy. Idle initializes it before
    // acceptance; at abort/error/expiry the FSM closes busy on this same edge.
    // No idle free-running switching, and no timer enable feedback mux.
    always @(posedge clk) begin
        if(!busy) elapsed<=0;
        else elapsed<=elapsed+1'b1;
    end
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            state<=IDLE;phase<=START;direction<=0;saved_address<=0;
            count<=0;index<=0;byte_req<=0;byte_op<=0;byte_tx<=0;
            abort_byte<=0;busy<=0;done<=0;err<=0;
            cleanup_failed<=0;rx_valid<=0;rx_data<=0;
        end else begin
            done<=0;byte_req<=0;abort_byte<=0;
            if(!busy) begin

                if(req) begin
                    err<=0;cleanup_failed<=0;rx_valid<=0;rx_data<=0;
                    if(length==0 || length>67) begin err<=6;done<=1;end
                    else begin
                        busy<=1;direction<=read_mode;saved_address<=address;
                        count<=length;index<=0;phase<=START;state<=ISSUE;
                    end
                end
            end else if(invalid_context) begin
                // Highest priority: no normal byte completion can overwrite this fault.
                abort_byte<=1;busy<=0;done<=1;err<=4;
                cleanup_failed<=1;rx_valid<=0;state<=IDLE;
            end else if(elapsed>=TOTAL_TIMEOUT-1) begin
                abort_byte<=1;busy<=0;done<=1;err<=7;
                cleanup_failed<=1;rx_valid<=0;state<=IDLE;
            end else begin

                case(state)
                    ISSUE: begin
                        byte_req<=1;state<=WAIT_BYTE;
                        case(phase)
                            START: byte_op<=0;
                            ADDR: begin byte_op<=1;byte_tx<={saved_address,direction};end
                            WORD: begin byte_op<=1;byte_tx<=8'h03;end
                            DATA: if(direction) byte_op<=(index==count-1) ? 3 : 2;
                                  else byte_op<=1;
                            default: byte_op<=4;
                        endcase
                    end
                    WAIT_BYTE: if(byte_done) begin
                        if(phase==STOP) begin
                            if(byte_err!=0) begin
                                cleanup_failed<=1;
                                if(err==0) err<=byte_err;
                            end
                            busy<=0;done<=1;state<=IDLE;
                        end else if(byte_err!=0) begin
                            err<=byte_err;rx_valid<=0;
                            if(byte_err==1) begin phase<=STOP;state<=ISSUE;end
                            else begin
                                // No STOP after arbitration loss: another owner may be active.
                                abort_byte<=1;busy<=0;done<=1;state<=IDLE;
                                cleanup_failed<=1;
                            end
                        end else case(phase)
                            START: begin phase<=ADDR;state<=ISSUE;end
                            ADDR: if(direction) begin phase<=DATA;state<=ISSUE;end
                                  else begin phase<=WORD;state<=ISSUE;end
                            WORD: begin phase<=DATA;state<=TX_WAIT;end
                            default: if(direction) begin
                                rx_data<=byte_rx;rx_valid<=1;state<=RX_WAIT;
                            end else if(index==count-1) begin phase<=STOP;state<=ISSUE;end
                            else begin index<=index+1'b1;state<=TX_WAIT;end
                        endcase
                    end
                    TX_WAIT: if(tx_valid) begin byte_tx<=tx_data;phase<=DATA;state<=ISSUE;end
                    RX_WAIT: if(rx_ready) begin
                        rx_valid<=0;
                        if(index==count-1) begin phase<=STOP;state<=ISSUE;end
                        else begin index<=index+1'b1;state<=ISSUE;end
                    end
                    default: begin
                        abort_byte<=1;busy<=0;done<=1;err<=4;
                        rx_valid<=0;cleanup_failed<=1;state<=IDLE;
                    end
                endcase
            end
        end
    end
endmodule
