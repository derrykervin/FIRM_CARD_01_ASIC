// Experimental streaming integrity checker. CRC is not authentication.
// Payload output is TENTATIVE until done && integrity_ok; caller discards on error.
module atecc_response_check #(parameter integer TIMEOUT_CYCLES=100000)(
    input wire clk,input wire rst_n,input wire start,input wire abort,
    input wire [6:0] expected_count,
    input wire rx_valid,input wire [7:0] rx_data,input wire rx_last,output wire rx_ready,
    output wire tentative_valid,output wire [7:0] tentative_data,input wire tentative_ready,
    output reg busy,output reg done,output reg integrity_ok,output reg [2:0] err);
    reg [6:0] count,index;
    reg [15:0] crc;
    reg [7:0] crc_low;
    function integer counter_width;
        input integer limit;integer value;
        begin counter_width=1;value=limit-1;
            while(value>1) begin value=value>>1;counter_width=counter_width+1;end
        end
    endfunction
    reg [counter_width(TIMEOUT_CYCLES)-1:0] elapsed;
    function [15:0] next_crc;
        input [15:0] prior;input [7:0] value;
        reg [15:0] v;integer bitno;
        begin
            v=prior;
            for(bitno=0;bitno<8;bitno=bitno+1) begin
                if(v[15]^value[bitno]) v={v[14:0],1'b0}^16'h8005;
                else v={v[14:0],1'b0};
            end
            next_crc=v;
        end
    endfunction
    wire invalid_context=(count!=4 && count!=35 && count!=67) || index>=count;
    wire payload=(index>0 && index<count-2 && count!=4);
    wire window_open=busy && !invalid_context && !abort && elapsed<TIMEOUT_CYCLES-1;
    assign rx_ready=window_open && (!payload || tentative_ready);
    assign tentative_valid=window_open && payload && rx_valid;
    assign tentative_data=rx_data;
    // Private elapsed is observed only while busy. Idle initializes it before
    // acceptance; at abort/error/expiry the FSM closes busy on this same edge.
    // No idle free-running switching, and no timer enable feedback mux.
    always @(posedge clk) begin
        if(!busy) elapsed<=0;
        else elapsed<=elapsed+1'b1;
    end
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            count<=0;index<=0;crc<=0;crc_low<=0;
            busy<=0;done<=0;integrity_ok<=0;err<=0;
        end else begin
            done<=0;
            if(abort) begin
                done<=busy;busy<=0;integrity_ok<=0;err<=6;
                index<=0;crc<=0;crc_low<=0;
            end else if(!busy) begin

                if(start) begin
                    integrity_ok<=0;err<=0;index<=0;crc<=0;crc_low<=0;count<=expected_count;
                    if(expected_count!=4 && expected_count!=35 && expected_count!=67) begin
                        done<=1;err<=1;
                    end else busy<=1;
                end
            end else if(invalid_context) begin
                busy<=0;done<=1;integrity_ok<=0;err<=5;
            end else if(elapsed>=TIMEOUT_CYCLES-1) begin
                busy<=0;done<=1;integrity_ok<=0;err<=7;
            end else begin

                if(rx_valid && rx_ready) begin
                    if((index==0 && rx_data!={1'b0,count})) begin
                        busy<=0;done<=1;err<=1;integrity_ok<=0;
                    end else if(rx_last!=(index==count-1)) begin
                        busy<=0;done<=1;err<=2;integrity_ok<=0;
                    end else if(count==4 && index==1 && rx_data!=0) begin
                        busy<=0;done<=1;err<=3;integrity_ok<=0;
                    end else if(index<count-2) begin
                        crc<=next_crc(crc,rx_data);index<=index+1'b1;
                    end else if(index==count-2) begin
                        crc_low<=rx_data;index<=index+1'b1;
                    end else begin
                        busy<=0;done<=1;
                        if({rx_data,crc_low}!=crc) begin err<=4;integrity_ok<=0;end
                        else begin err<=0;integrity_ok<=1;end
                    end
                end
            end
        end
    end
endmodule
