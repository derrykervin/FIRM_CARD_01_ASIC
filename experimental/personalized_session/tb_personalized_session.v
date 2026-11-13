`timescale 1ns/1ps
module tb_personalized_session;
    parameter DIV=2;
    parameter ATTEMPTS=3;
    parameter SHARE_DIGEST=1;
    parameter SHARE_TRANSPORT=1;
    localparam TOTAL=1500000+150000*DIV;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,req=0,abort=0,card_present=1,slave_scl=0,slave_sda=0,sig_ready=1;
    reg [255:0] digest=0;reg [6:0] address=7'h60;
    wire ready,busy,done,ok,sl,dl,sig_valid;wire [7:0] sig_data;wire [1:0] phase;
    wire [2:0] err,child,detail,transport;
    tri1 scl,sda;
    assign scl=(sl||slave_scl)?1'b0:1'bz;
    assign sda=(dl||slave_sda)?1'b0:1'bz;
    reg [7:0] commands[0:3327],responses[0:3327],digests[0:63],bad_nonce[0:3];
    integer bank=0,seen=0,writes=0,wake_reads=0,sign_reads=0,completed=0;
    reg stop_seen=0;
    atecc_proof_session #(.DIV(DIV),.SHARE_DIGEST(SHARE_DIGEST),.SHARE_TRANSPORT(SHARE_TRANSPORT),.WAKE_LOW_CYCLES(7),.WAKE_HIGH_CYCLES(13),
        .EXEC_WAIT_CYCLES(17),.POLL_CYCLES(80),.MAX_READ_ATTEMPTS(ATTEMPTS),
        .BYTE_TIMEOUT(400+100*DIV),.BUS_TIMEOUT(20000+3000*DIV),.READ_TIMEOUT(30000+4000*DIV),
        .PRODUCER_TIMEOUT(200000+20000*DIV),.COMMAND_TIMEOUT(100000+10000*DIV),
        .WAKE_TIMEOUT(30000+4000*DIV),.TOTAL_TIMEOUT(TOTAL)) dut(
        .external_elapsed(32'd0),.clk(clk),.rst_n(rst_n),.req(req),.abort(abort),.card_present(card_present),.digest(digest),.address(address),
        .scl_in(scl),.sda_in(sda),.scl_low(sl),.sda_low(dl),.signature_valid(sig_valid),.signature_data(sig_data),
        .signature_ready(sig_ready),.ready(ready),.transport_ok(ok),.busy(busy),.done(done),.phase(phase),
        .err(err),.child_error(child),.detail_error(detail),.transport_detail(transport));
    always @(negedge clk) sig_ready<=~sig_ready;
    always @(negedge clk) begin
        if(rst_n && busy && SHARE_DIGEST && dut.command_engine.generator.saved_digest!==0)
            $fatal(1,"session redundant digest storage active");
        if(rst_n && SHARE_TRANSPORT &&
           ((dut.wake_enabled && !dut.wake_bus_reset_n) || (dut.command_enabled && !dut.command_bus_reset_n)) &&
           (dut.bus_scl || dut.bus_sda))
            $fatal(1,"session child reset not honored");
    end
    always @(posedge clk) begin
        if(sig_valid && sig_ready) begin
            if(sig_data!==responses[bank+897+seen] || phase!=2 || seen>=64) $fatal(1,"session signature stream");
            seen=seen+1;
        end
        if(ok && busy) $fatal(1,"session early transport success");
    end
    always @(posedge sda) begin #1;if(scl && rst_n && dut.state==4) stop_seen=1;end
    always @(posedge clk) begin
        if(rst_n && busy && dut.command_done && dut.command_err!=0 && !abort && card_present) begin
            #1;if(busy || ok) $fatal(1,"session continued after command error");
        end
    end
    always @(negedge card_present) begin
        @(posedge clk);#1;if(busy || ok || sig_valid) $fatal(1,"session removal did not terminate");
    end
    task wait_start;
        begin : search
            forever begin @(negedge sda);if(scl===1'b1) disable search;end
        end
    endtask
    task receive_byte;
        input [7:0] expected;input ack;reg [7:0] value;integer b;
        begin
            for(b=7;b>=0;b=b-1) begin @(posedge scl);value[b]=sda;end
            if(value!==expected) $fatal(1,"session command wire byte=%h expected=%h",value,expected);
            @(negedge scl);slave_sda=ack;@(posedge scl);@(negedge scl);slave_sda=0;
        end
    endtask
    task send_byte;
        input [7:0] value;input ack;integer b;
        begin
            slave_sda=!value[7];
            for(b=7;b>=0;b=b-1) begin @(posedge scl);@(negedge scl);
                if(b>0) slave_sda=!value[b-1];else slave_sda=0;
            end
            @(posedge scl);#1;if(sda!==!ack) $fatal(1,"session read ACK/NACK");@(negedge scl);
        end
    endtask
    function [15:0] next_crc;
      input [15:0] prior;input [7:0] value;integer k;reg [15:0] c;
      begin c=prior;for(k=0;k<8;k=k+1) c=(c[15]^value[k])?{c[14:0],1'b0}^16'h8005:{c[14:0],1'b0};next_crc=c;end
    endfunction
    task run_case;
        input integer context_id,fault;input [2:0] expected,c,d,t;
        integer j,stage,offset,length,count,attempt;reg nack;reg [7:0] sent;reg [15:0] response_crc;
        begin
            wait(ready);bank=1664*context_id;seen=0;writes=0;wake_reads=0;sign_reads=0;stop_seen=0;
            slave_scl=0;slave_sda=0;
            $display("CASE session context=%0d fault=%0d at=%0t",context_id,fault,$time);
            @(negedge clk);for(j=0;j<32;j=j+1) digest[(31-j)*8 +: 8]=digests[32*context_id+j];
            address=7'h60;req=1;@(negedge clk);req=0;digest=~digest;address=7'h61;
            if(ok) $fatal(1,"session stale result");
            fork : session_case
                begin
                    repeat(TOTAL+2000) @(negedge clk);
                    $fatal(1,"case deadline fault=%0d state=%0d step=%0d busy=%0d childstate=%0d scl=%b sda=%b",fault,dut.state,dut.step,busy,dut.command_engine.state,scl,sda);
                end
                begin : device
                    wait(dut.wake_engine.state==2);@(posedge sda);
                    begin : wake_read_loop
                    for(attempt=0;attempt<ATTEMPTS;attempt=attempt+1) begin
                        wait_start;@(negedge scl);wake_reads=wake_reads+1;
                        nack=fault==12 && attempt==0;
                        receive_byte(8'hc1,!nack);
                        if(!nack) begin
                            send_byte(8'h04,1);send_byte(fault==1?8'h00:8'h11,1);
                            send_byte(fault==1?8'h03:8'h33,1);send_byte(fault==1?8'h40:8'h43,0);
                            disable wake_read_loop;
                        end
                    end
                    end
                    for(stage=0;stage<13;stage=stage+1) begin
                        offset=bank+128*stage;length=commands[offset];count=responses[offset];
                        wait_start;@(negedge scl);writes=writes+1;
                        receive_byte(8'hc0,1);receive_byte(8'h03,1);
                        for(j=0;j<length;j=j+1) receive_byte(commands[offset+j],1);
                        // The command STOP must precede every response START.
                        begin : command_read_loop
                        for(attempt=0;attempt<ATTEMPTS;attempt=attempt+1) begin
                            wait_start;stop_seen=0;@(negedge scl);
                            if(stage==7) sign_reads=sign_reads+1;
                            nack=fault==2 && stage==7 && attempt==0;
                            receive_byte(8'hc1,!nack);
                            if(!nack) begin
                                for(j=0;j<count;j=j+1) begin
                                    if(fault==3 && stage==6) send_byte(bad_nonce[j],j!=count-1);
                                    else begin
                                      sent=responses[offset+j];
                                      if(j>0 && j<count-2)begin
                                        if((fault==20 || fault==23) && stage==8 && j==2)sent=sent^1;
                                        if((fault==21 || fault==24) && stage==12 && j==64)sent=sent^1;
                                        if(fault==22 && stage==0 && j==25)sent=sent^1;
                                        if(fault==25 && stage==3 && j==5)sent=8'h13;
                                        if(fault==26 && stage==2 && j==25)sent=sent|4;
                                        if(fault==27 && (stage==0 || stage==8) && (j<=4 || (j>=9 && j<=13)))sent=0;
                                        if(fault==28 && (stage==0 || stage==8) && j==20)sent=8'h08;
                                      end
                                      if(j==0)response_crc=0;
                                      if(j<count-2)response_crc=next_crc(response_crc,sent);
                                      else sent=j==count-2?response_crc[7:0]:response_crc[15:8];
                                      if(((fault==4 && stage==7)||(fault==15 && stage==5)) && j==count-1)sent=sent^1;
                                      send_byte(sent,j!=count-1);
                                    end
                                end
                                if(fault==5 && stage==7) slave_scl=1;
                                disable command_read_loop;
                            end
                        end
                        end
                    end
                end
                begin
                    if(fault==29)begin wait(dut.state==3 && dut.step==8);@(negedge clk);dut.step=12;end
                    if(fault==30)begin wait(dut.state==4 && dut.step==12);@(negedge clk);abort=1;end
                    if(fault==8) begin wait(dut.wake_engine.state==2);@(negedge clk);abort=1;end
                    if(fault==6 || fault==7) begin
                        wait(seen>=12);@(negedge clk);
                        if(fault==6) abort=1;else card_present=0;
                        #1;if(sig_valid || ok || sl || dl) $fatal(1,"session cancel/removal masking");
                    end
                    if(fault==9) begin wait(dut.state==4 && phase==2);@(negedge clk);dut.elapsed=TOTAL-1;end
                    if(fault==10) begin wait(dut.state==4 && phase==1);@(negedge clk);dut.step=13;end
                    if(fault==11) begin
                        wait(dut.state==4 && phase==1);@(negedge clk);req=1;@(negedge clk);req=0;
                        if(dut.phase!=1 || dut.saved_address!=7'h60) $fatal(1,"session busy request replaced context");
                    end
                    if(fault==13) begin wait(dut.state==3 && dut.step==8);@(negedge clk);dut.signature_count=63;end
                    if(fault==14) begin wait(seen>=12);@(negedge clk);dut.signature_count=65;end
                end
                begin wait(done);#1;disable session_case;end
                begin
                    if(fault==9) begin wait(dut.elapsed==TOTAL-1);repeat(8) @(negedge clk);$fatal(1,"session parent deadline missing");end
                end
            join
            if(err!==expected || child!==c || detail!==d || transport!==t || busy || ok!==(expected==0))
                $fatal(1,"session result fault=%0d err=%0d child=%0d detail=%0d transport=%0d",fault,err,child,detail,transport);
            if(expected==0 && (seen!=64 || writes!=13 || !stop_seen || scl!==1 || sda!==1)) $fatal(1,"session final qualification");
            if(((fault==22 || fault==27 || fault==28) && writes!=1) || (fault==25 && writes!=4) || (fault==26 && writes!=3))
                $fatal(1,"session profile failure reached later command fault=%0d writes=%0d",fault,writes);
            if(fault==1 && writes!=0) $fatal(1,"session continued after bad wake");
            if(fault==15 && writes!=6) $fatal(1,"session continued after Random failure");
            if(fault==3 && writes!=7) $fatal(1,"session continued after Nonce failure");
            if((fault==4 || fault==5 || fault==13 || fault==20 || fault==21 || fault==30) && seen!=64) $fatal(1,"session failure must follow full signature payload");
            slave_scl=0;slave_sda=0;abort=0;card_present=1;req=0;completed=completed+1;
            repeat(6) @(negedge clk);
            if(!ready || dut.saved_digest!==0) $fatal(1,"session cleanup not ready");
        end
    endtask
    initial begin #1000000000;$fatal(1,"session watchdog");end
    initial begin
        $readmemh("session_commands.hex",commands,0,3327);$readmemh("session_responses.hex",responses,0,3327);
        $readmemh("session_digests.hex",digests,0,63);
        $readmemh("bad_nonce.hex",bad_nonce,0,3);
        repeat(4) @(negedge clk);rst_n=1;repeat(4) @(negedge clk);
        run_case(0,0,0,0,0,0);run_case(1,0,0,0,0,0);
        run_case(0,1,3,4,0,0);
        if(ATTEMPTS>1) run_case(0,2,0,0,0,0);
        run_case(1,3,4,3,2,3);run_case(0,4,4,3,2,4);run_case(1,5,4,3,1,2);
        run_case(0,6,1,0,0,0);run_case(1,7,2,0,0,0);run_case(0,8,1,0,0,0);
        run_case(0,9,5,0,0,0);run_case(1,10,6,0,0,0);run_case(1,11,0,0,0,0);
        if(ATTEMPTS>1) run_case(1,12,0,0,0,0);
        run_case(0,13,7,0,0,0);run_case(0,14,6,0,0,0);run_case(1,15,4,3,2,4);
        run_case(0,20,7,0,0,0);run_case(1,21,7,0,0,0);
        run_case(0,22,7,0,0,0);run_case(1,25,7,0,0,0);run_case(0,26,7,0,0,0);
        run_case(0,27,7,0,0,0);run_case(0,28,7,0,0,0);run_case(1,29,6,0,0,0);run_case(0,30,1,0,0,0);
        run_case(1,0,0,0,0,0);
        // A non-0x60 address now rejects before wake; explicitly test that contract.
        @(negedge clk);address=7'h61;req=1;@(negedge clk);req=0;
        if(!done || err!=6 || busy || ok || sl || dl)$fatal(1,"unsupported address accepted");
        repeat(6)@(negedge clk);
        @(negedge clk);address=7'h60;req=1;@(negedge clk);req=0;
        wait(dut.wake_engine.state==2);@(negedge clk);rst_n=0;#1;
        if(busy || ok || sig_valid || sl || dl || dut.saved_digest!==0) $fatal(1,"session reset during wake");
        repeat(3) @(negedge clk);rst_n=1;repeat(6) @(negedge clk);
        run_case(0,0,0,0,0,0);
        @(negedge clk);card_present=0;#1;if(ok || ready) $fatal(1,"session idle removal retained result");
        @(negedge clk);card_present=1;
        $display("PASS personalized session DIV=%0d ATTEMPTS=%0d completed=%0d",DIV,ATTEMPTS,completed);$finish;
    end
endmodule
