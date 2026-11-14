`default_nettype none
// Typed packet producer only. Fixed key SLOT is not a key or card identity.
// op0 Random, op1 Nonce(Message Digest Buffer), op2 external Sign,
// op3 Config32 READ block0..3, op4 slot-2 GenKey PUBLIC=0. One CRC/index/timer.
module atecc_unified_producer #(
    parameter integer KEY_SLOT=2,ENABLE_READBACK=1,
    // Disable only inside an owner that holds digest immutable through completion.
    // Standalone command producers retain request-time capture by default.
    parameter integer CAPTURE_DIGEST=1,
    parameter integer CASE_LOOKUP=2,
    parameter integer TIMEOUT_CYCLES=4000000
)(
    input wire clk,rst_n,req,abort,
    input wire [2:0] operation,input wire [1:0] config_block,input wire [255:0] digest,
    output wire ready,output reg busy,done,output reg [2:0] err,
    output wire [6:0] command_length,response_count,
    output wire tx_valid,output reg [7:0] tx_data,input wire tx_ready
);
    function integer cw;
        input integer limit;integer v;
        begin cw=1;v=limit-1;while(v>1) begin v=v>>1;cw=cw+1;end end
    endfunction
    function [7:0] selected_digest_byte;
        input [255:0] value;input [5:0] position;
        begin
            case(position)
            6'd5: selected_digest_byte=value[255:248];
            6'd6: selected_digest_byte=value[247:240];
            6'd7: selected_digest_byte=value[239:232];
            6'd8: selected_digest_byte=value[231:224];
            6'd9: selected_digest_byte=value[223:216];
            6'd10: selected_digest_byte=value[215:208];
            6'd11: selected_digest_byte=value[207:200];
            6'd12: selected_digest_byte=value[199:192];
            6'd13: selected_digest_byte=value[191:184];
            6'd14: selected_digest_byte=value[183:176];
            6'd15: selected_digest_byte=value[175:168];
            6'd16: selected_digest_byte=value[167:160];
            6'd17: selected_digest_byte=value[159:152];
            6'd18: selected_digest_byte=value[151:144];
            6'd19: selected_digest_byte=value[143:136];
            6'd20: selected_digest_byte=value[135:128];
            6'd21: selected_digest_byte=value[127:120];
            6'd22: selected_digest_byte=value[119:112];
            6'd23: selected_digest_byte=value[111:104];
            6'd24: selected_digest_byte=value[103:96];
            6'd25: selected_digest_byte=value[95:88];
            6'd26: selected_digest_byte=value[87:80];
            6'd27: selected_digest_byte=value[79:72];
            6'd28: selected_digest_byte=value[71:64];
            6'd29: selected_digest_byte=value[63:56];
            6'd30: selected_digest_byte=value[55:48];
            6'd31: selected_digest_byte=value[47:40];
            6'd32: selected_digest_byte=value[39:32];
            6'd33: selected_digest_byte=value[31:24];
            6'd34: selected_digest_byte=value[23:16];
            6'd35: selected_digest_byte=value[15:8];
            6'd36: selected_digest_byte=value[7:0];
                default: selected_digest_byte=8'd0;
            endcase
        end
    endfunction
    function [15:0] next_crc;
        input [15:0] prior;input [7:0] value;
        integer b;reg [15:0] c;
        begin
            c=prior;
            for(b=0;b<8;b=b+1) begin
                if(c[15]^value[b]) c={c[14:0],1'b0}^16'h8005;
                else c={c[14:0],1'b0};
            end
            next_crc=c;
        end
    endfunction
    reg [2:0] saved_operation;
    reg [1:0] saved_block;
    reg [255:0] saved_digest;
    wire [255:0] command_digest=CAPTURE_DIGEST ? saved_digest : digest;
    wire [255:0] lookup_input=command_digest;
    reg [5:0] index;
    // Nonce payload positions 5..36 map to byte 31..0 modulo 32.
    // The payload guard below excludes every other position.
    wire [4:0] digest_byte_index=5'd4-index[4:0];
    wire [7:0] digest_byte=(CASE_LOOKUP==1) ? selected_digest_byte(lookup_input,index) :
        ((CASE_LOOKUP==2) ? lookup_input[{digest_byte_index,3'b000} +:8] : lookup_input[(36-index)*8 +:8]);
    reg [15:0] crc;
    reg [cw(TIMEOUT_CYCLES)-1:0] elapsed;
    assign command_length=saved_operation==1?7'd39:((saved_operation==0 || saved_operation==2 || (ENABLE_READBACK && (saved_operation==3 || saved_operation==4)))?7'd7:7'd0);
    assign response_count=(saved_operation==0 || (ENABLE_READBACK && saved_operation==3))?7'd35:(saved_operation==1?7'd4:((saved_operation==2 || (ENABLE_READBACK && saved_operation==4))?7'd67:7'd0));
    wire expired=elapsed>=TIMEOUT_CYCLES-1;
    wire invalid_context=(ENABLE_READBACK ? saved_operation>4 : saved_operation>2) || index>=command_length || KEY_SLOT<0 || KEY_SLOT>15 || (saved_operation>=3 && KEY_SLOT!=2);
    assign ready=!busy && !abort;
    assign tx_valid=busy && !abort && !expired && !invalid_context;
    always @* begin
        tx_data=0;
        if(index==command_length-2) tx_data=crc[7:0];
        else if(index==command_length-1) tx_data=crc[15:8];
        else case(index)
            0: tx_data={1'b0,command_length};
            1: tx_data=saved_operation==0?8'h1b:(saved_operation==1?8'h16:(saved_operation==3 && ENABLE_READBACK?8'h02:(saved_operation==4 && ENABLE_READBACK?8'h40:8'h41)));
            2: tx_data=saved_operation==0?8'h00:(saved_operation==1?8'h43:(saved_operation==3 && ENABLE_READBACK?8'h80:(saved_operation==4 && ENABLE_READBACK?8'h00:8'ha0)));
            3: tx_data=(saved_operation==2 || (ENABLE_READBACK && saved_operation==4))?KEY_SLOT[7:0]:((ENABLE_READBACK && saved_operation==3)?{3'b000,saved_block,3'b000}:8'h00);
            4: tx_data=0;
            default: if(saved_operation==1 && index>=5 && index<=36) tx_data=digest_byte;
        endcase
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
            saved_operation<=0;saved_block<=0;saved_digest<=0;index<=0;crc<=0;
            busy<=0;done<=0;err<=0;
        end else begin
            done<=0;
            if(abort) begin
                busy<=0;done<=busy;err<=1;saved_digest<=0;index<=0;crc<=0;
            end else if(!busy) begin
                if(req && ready) begin
                    saved_operation<=operation;saved_block<=operation==3?config_block:2'd0;saved_digest<=(CAPTURE_DIGEST && operation==1)?digest:256'd0;
                    index<=0;crc<=0;err<=0;
                    if((ENABLE_READBACK ? operation>4 : operation>2) || KEY_SLOT<0 || KEY_SLOT>15 || (operation>=3 && KEY_SLOT!=2)) begin
                        done<=1;err<=2;saved_digest<=0;
                    end else busy<=1;
                end
            end else if(invalid_context) begin
                busy<=0;done<=1;err<=4;saved_digest<=0;index<=0;crc<=0;
            end else if(expired) begin
                busy<=0;done<=1;err<=3;saved_digest<=0;index<=0;crc<=0;
            end else begin

                if(tx_valid && tx_ready) begin
                    if(index==command_length-1) begin busy<=0;done<=1;saved_digest<=0;end
                    else begin
                        if(index<command_length-2) crc<=next_crc(crc,tx_data);
                        index<=index+1'b1;
                    end
                end
            end
        end
    end
endmodule
`default_nettype wire
