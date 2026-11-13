`timescale 1ns/1ps
module tb_unified_exchange;
    parameter DIV=2;
    parameter ATTEMPTS=3;
    parameter EXTERNAL=0;
    parameter CAPTURE=1;

    localparam EXEC=17,POLL=80,TOTAL=100000+10000*DIV;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,req=0,abort=0,slave_scl=0,slave_sda=0,tentative_ready=1;
    reg [6:0] command_length=7,response_count=35;
    reg [2:0] operation=0;
    reg [255:0] digest=0;
    reg [1:0] config_block=0;
    reg [6:0] address=7'h60;
    wire scl_low,sda_low,ready,busy,done,packet_ok,tentative_valid;
    wire [7:0] tentative_data;wire [2:0] err,detail,transport_detail;
    tri1 scl,sda;
    assign scl=(slave_scl||scl_low)?1'b0:1'bz;
    assign sda=(slave_sda||sda_low)?1'b0:1'bz;
    reg [7:0] commands[0:1023],responses[0:1023];
    integer tick=0,write_stop_tick,read_stop_tick,seen=0,offset=0,reads=0,completed=0;
    reg write_stop=0,read_stop=0;
    wire x_req,x_reset_n,x_read,x_tx_valid,x_rx_ready,x_tx_ready,x_busy,x_done,x_valid,x_cleanup,x_scl,x_sda;
    wire [6:0] x_address;wire [7:0] x_length,x_tx_data,x_data;wire [2:0] x_error;
    generate if(EXTERNAL)begin: external_transport
      firm_i2c_transaction #(.DIV(DIV),.BYTE_TIMEOUT(400+100*DIV),.TOTAL_TIMEOUT(20000+3000*DIV)) bus(
       .clk(clk),.rst_n(rst_n && x_reset_n),.req(x_req),.read_mode(x_read),.address(x_address),.length(x_length),
       .tx_valid(x_tx_valid),.tx_data(x_tx_data),.tx_ready(x_tx_ready),.rx_valid(x_valid),.rx_data(x_data),.rx_ready(x_rx_ready),
       .scl_in(scl),.sda_in(sda),.scl_low(x_scl),.sda_low(x_sda),.busy(x_busy),.done(x_done),.err(x_error),.cleanup_failed(x_cleanup));
    end else begin: no_external_transport
      assign x_tx_ready=0;assign x_busy=0;assign x_done=0;assign x_valid=0;assign x_cleanup=0;
      assign x_scl=0;assign x_sda=0;assign x_error=0;assign x_data=0;
    end endgenerate
    atecc_unified_exchange #(.CAPTURE_DIGEST(CAPTURE),.EXTERNAL_TRANSPORT(EXTERNAL),.DIV(DIV),.EXEC_WAIT_CYCLES(EXEC),.POLL_CYCLES(POLL),
        .MAX_READ_ATTEMPTS(ATTEMPTS),.BYTE_TIMEOUT(400+100*DIV),
        .BUS_TIMEOUT(20000+3000*DIV),.READ_TIMEOUT(30000+4000*DIV),
        .PRODUCER_TIMEOUT(2*TOTAL),.TOTAL_TIMEOUT(TOTAL)) dut(
        .clk(clk),.rst_n(rst_n),.req(req),.abort(abort),.operation(operation),.digest(digest),.config_block(config_block),.address(address),
        .tentative_valid(tentative_valid),.tentative_data(tentative_data),.tentative_ready(tentative_ready),
        .scl_in(scl),.sda_in(sda),.scl_low(scl_low),.sda_low(sda_low),.ready(ready),
        .busy(busy),.done(done),.packet_ok(packet_ok),.err(err),.detail_error(detail),.transport_detail(transport_detail),
        .ext_req(x_req),.ext_reset_n(x_reset_n),.ext_read_mode(x_read),.ext_tx_valid(x_tx_valid),.ext_rx_ready(x_rx_ready),
        .ext_address(x_address),.ext_length(x_length),.ext_tx_data(x_tx_data),.ext_tx_ready(x_tx_ready),
        .ext_busy(x_busy),.ext_done(x_done),.ext_valid(x_valid),.ext_cleanup(x_cleanup),.ext_scl_low(x_scl),.ext_sda_low(x_sda),.ext_data(x_data),.ext_error(x_error));
    always @(posedge clk) begin
        tick=tick+1;
        if(packet_ok && busy) $fatal(1,"command early success");
        if(tentative_valid && tentative_ready) begin
            if(tentative_data!==responses[offset+1+seen]) $fatal(1,"command tentative payload");
            seen=seen+1;
        end
    end
    always @(posedge sda) begin #1;
        if(scl && rst_n && dut.transport.state==1) begin write_stop=1;write_stop_tick=tick;end
        if(scl && rst_n && dut.transport.state==4) begin read_stop=1;read_stop_tick=tick;end
    end
    task receive_byte;
        input [7:0] expected;input ack;
        integer b;reg [7:0] value;
        begin
            for(b=7;b>=0;b=b-1) begin @(posedge scl);value[b]=sda;end
            if(value!==expected) $fatal(1,"command wire byte=%h expected=%h",value,expected);
            @(negedge scl);slave_sda=ack;@(posedge scl);@(negedge scl);slave_sda=0;
        end
    endtask
    task wait_start;
        begin : search
            forever begin @(negedge sda);if(scl===1'b1) disable search;end
        end
    endtask
    task send_byte;
        input [7:0] value;input ack;integer b;
        begin
            slave_sda=!value[7];
            for(b=7;b>=0;b=b-1) begin @(posedge scl);@(negedge scl);
                if(b>0) slave_sda=!value[b-1];else slave_sda=0;
            end
            @(posedge scl);#1;if(sda!==!ack) $fatal(1,"command read ACK/NACK");@(negedge scl);
        end
    endtask
    task run_case;
        input integer kind,fault;input [2:0] expected,expected_detail,expected_transport;
        integer slave_index,attempt,j;reg nack;
        begin
            wait(ready);offset=128*kind;seen=0;reads=0;write_stop=0;read_stop=0;
            slave_scl=0;slave_sda=0;tentative_ready=1;
            @(negedge clk);command_length=kind==1?39:7;response_count=kind==1?4:((kind==2 || kind==7)?67:35);
            operation=kind<3?kind:(kind==7?4:3);config_block=kind-3;address=7'h60;
            for(j=0;j<32;j=j+1) digest[255-j*8-:8]=j;
            if(fault==14) operation=7;
            req=1;@(negedge clk);req=0;
            operation=7;if(CAPTURE)digest=~digest;config_block=~config_block;address=7'h61;
            if(packet_ok) $fatal(1,"command stale result");
            fork : transaction
                begin : slave
                    wait_start;@(negedge scl);receive_byte(8'hc0,fault!=2);
                    if(fault!=2) begin
                        receive_byte(8'h03,fault!=3);
                        if(fault!=3) begin
                            for(slave_index=0;slave_index<command_length;slave_index=slave_index+1) begin
                                receive_byte(commands[offset+slave_index],!(fault==4 && slave_index==0));
                                if(fault==4 && slave_index==0) disable slave;
                            end
                            wait(write_stop);
                            for(attempt=0;attempt<ATTEMPTS;attempt=attempt+1) begin
                                wait_start;read_stop=0;
                                if(attempt==0 && tick-write_stop_tick<EXEC) $fatal(1,"command execution wait too short");
                                if(attempt>0 && tick-read_stop_tick<POLL) $fatal(1,"command polling interval too short");
                                @(negedge scl);reads=reads+1;
                                nack=fault==6 || fault==8 || (fault==1 && attempt==0);
                                receive_byte(8'hc1,!nack);
                                if(fault==8) slave_scl=1;
                                if(!nack) begin
                                    for(slave_index=0;slave_index<response_count;slave_index=slave_index+1)
                                        send_byte(responses[offset+slave_index]^((fault==7 && slave_index==response_count-1)?8'h01:8'h00),slave_index!=response_count-1);
                                    if(fault==9) slave_scl=1;
                                    wait(done);
                                end
                            end
                        end
                    end
                end
                begin
                    if(fault==10) begin wait(dut.transport.state==2);@(negedge clk);abort=1;end
                    if(fault==12) begin wait(dut.transport.state==4);@(negedge clk);abort=1;end
                    if(fault==13) begin wait(dut.transport.state==2);@(negedge clk);dut.elapsed=TOTAL-1;end
                    if(fault==16) begin wait(dut.transport.state==2);@(negedge clk);dut.state=3;end
                    if(fault==17) begin wait(dut.transport.state==1);@(negedge clk);abort=1;end
                    if(fault==18) begin wait(dut.transport.state==1);@(negedge clk);req=1;@(negedge clk);req=0;end
                    if(fault==19) begin wait(dut.bus_done);@(negedge clk);dut.generator.done=1;dut.generator.err=4;end
                    if(fault==20) begin wait(dut.transport.state==1);@(negedge clk);dut.generator.elapsed=2*TOTAL-1;end
                    if(fault==21) begin wait(dut.bus_done);@(negedge clk);dut.producer_complete=0;end
                    if(fault==22) begin wait(dut.transport.state==4);@(negedge clk);req=1;@(negedge clk);req=0;end
                    wait(done);#1;disable transaction;
                end
                begin
                    if(fault==13) begin
                        wait(dut.elapsed==TOTAL-1);repeat(8) @(negedge clk);
                        $fatal(1,"command parent deadline missing");
                    end
                end
            join
            if(err!==expected || detail!==expected_detail || transport_detail!==expected_transport || busy || packet_ok!==(expected==0))
                $fatal(1,"command completion fault=%0d err=%0d detail=%0d transport=%0d",fault,err,detail,transport_detail);
            if(expected==0 && (!write_stop || !read_stop || scl!==1 || sda!==1)) $fatal(1,"command missing STOP");
            if(expected==0 && seen!==(response_count==4?0:response_count-3)) $fatal(1,"command payload length");
            if(fault==1 && reads!=2) $fatal(1,"command NACK retry missing");
            if(fault==6 && reads!=ATTEMPTS) $fatal(1,"command retry unbounded");
            if((fault==19 || fault==21) && seen!=64) $fatal(1,"owner failure must follow full tentative payload");
            if(fault==8 && reads!=1) $fatal(1,"command unsafe cleanup retry");
            slave_scl=0;slave_sda=0;abort=0;req=0;completed=completed+1;
            repeat(6) @(negedge clk);
            if(!ready) $fatal(1,"owner cleanup not ready");
            if(dut.generator.saved_digest!==0) $fatal(1,"digest cleanup missing");
        end
    endtask
    initial begin #50000000;$fatal(1,"command watchdog");end
    initial begin
        $readmemh("commands.hex",commands,0,1023);$readmemh("command_responses.hex",responses,0,1023);
        repeat(5) @(negedge clk);rst_n=1;repeat(5) @(negedge clk);
        run_case(0,0,0,0,0);
        run_case(1,0,0,0,0);
        run_case(2,0,0,0,0);
        run_case(3,0,0,0,0);
        run_case(4,0,0,0,0);
        run_case(5,0,0,0,0);
        run_case(6,0,0,0,0);
        run_case(7,0,0,0,0);
        if(ATTEMPTS>1) run_case(7,1,0,0,0);
        run_case(0,2,2,1,0);run_case(0,3,2,1,0);run_case(0,4,2,1,0);
        run_case(0,6,3,1,1);run_case(7,7,3,2,4);run_case(0,8,3,1,1);
        run_case(7,9,3,1,2);run_case(0,10,1,0,0);
        run_case(7,12,1,0,0);run_case(0,13,4,0,0);
        run_case(0,14,7,2,0);run_case(0,16,6,0,0);run_case(0,17,1,0,0);
        run_case(0,18,0,0,0);run_case(7,19,7,4,0);
        run_case(0,20,7,3,0);run_case(7,21,6,0,0);run_case(0,22,0,0,0);
        run_case(0,0,0,0,0);
        $display("PASS ATECC unified owner DIV=%0d ATTEMPTS=%0d completed=%0d",DIV,ATTEMPTS,completed);$finish;
    end
endmodule
