`timescale 1ns/1ps
// Actual serial pads -> CPU firmware -> mailbox -> real I2C RTL, synthetic device bytes.
module tb_personalized_card;
 parameter CPB=16,DIV=2;
 // 64 bytes x (tag + payload) x 10 UART bits = 1280*CPB cycles.
 // 1600*CPB + 10000 includes 25% serialization and software margin.
 localparam SERIAL_DRAIN=1600*CPB+10000;
 localparam TOTAL=3000000+30000*DIV;
 reg clk=0;always #12.5 clk=~clk;
 reg rst_n=0,present=1,rx=1,slave_scl=0,slave_sda=0;
 wire [7:0] rom_addr,pc,r0,gpio;
 reg [15:0] rom[0:255];wire [15:0] rom_data=rom[rom_addr];
 wire halted,busy,ok,sl,dl,tx,request_expired,request_active;
 wire [1:0] request_timeout_cause;
 tri1 scl,sda;
 assign scl=(sl||slave_scl)?1'b0:1'bz;
 assign sda=(dl||slave_sda)?1'b0:1'bz;
 reg [7:0] commands[0:3327],responses[0:3327],digests[0:63],bad_nonce[0:3];
 reg [7:0] probe_addr=8'hxx;
 wire [15:0] probe_data;
 integer word_index;
 firm_serial_rom rom_probe(.addr(probe_addr),.data(probe_data));
 integer bank=0,seen=0,writes=0,completed=0,current_fault=0,tx_records=0;
 reg stop_seen=0,terminal=0;
 reg [7:0] status=0,error=0,consumed=0;
 firm_current_budget #(.UART_CLKS_PER_BIT(CPB),.DIV(DIV),
  .REQUEST_FRAME(640*CPB),
  .WAKE_LOW_CYCLES(7),.WAKE_HIGH_CYCLES(13),.EXEC_WAIT_CYCLES(17),.POLL_CYCLES(80),.MAX_READ_ATTEMPTS(3),
  .BYTE_TIMEOUT(400+100*DIV),.BUS_TIMEOUT(SERIAL_DRAIN+20000+3000*DIV),.READ_TIMEOUT(SERIAL_DRAIN+30000+4000*DIV),
  .PRODUCER_TIMEOUT(200000+20000*DIV),.COMMAND_TIMEOUT(SERIAL_DRAIN+100000+10000*DIV),
  .WAKE_TIMEOUT(30000+4000*DIV),.TOTAL_TIMEOUT(TOTAL)) dut(
  .clk(clk),.reset_n(rst_n),.card_present(present),.rom_addr(rom_addr),
  .gpio_in(8'h00),.gpio_out(gpio),.uart_rx(rx),.uart_tx(tx),
  .spi_miso(1'b0),.halted(halted),.debug_pc(pc),.debug_r0(r0),
  .request_expired(request_expired),.request_active(request_active),.request_timeout_cause(request_timeout_cause),
  .owner_busy(busy),.transport_committed(ok),.scl_in(scl),.sda_in(sda),.scl_low(sl),.sda_low(dl));
 always @(posedge clk)if(rst_n && busy && ok)$fatal(1,"card committed before session complete");
 // No test controls or diagnostics are implemented on the legacy bus.
 always @(posedge clk) if(rst_n && dut.core.io_we && dut.core.io_addr!=8'h11)
  $fatal(1,"serial unexpected legacy write");
 always @(posedge sda) begin #1;if(scl && rst_n && dut.core.processor.endpoint.session.state==4) stop_seen=1;end
 task send_uart;
  input [7:0] v;integer j;
  begin
   @(negedge clk);#1;rx=0;repeat(CPB) @(negedge clk);
   for(j=0;j<8;j=j+1) begin #1;rx=v[j];repeat(CPB) @(negedge clk);end
   #1;rx=1;repeat(CPB*3) @(negedge clk);
  end
 endtask
 task read_uart;
  output [7:0] v;integer j;
  begin
   @(negedge tx);repeat(CPB/2) @(posedge clk);#1;
   if(tx!==0) $fatal(1,"serial UART start");
   for(j=0;j<8;j=j+1) begin repeat(CPB) @(posedge clk);#1;v[j]=tx;end
   repeat(CPB) @(posedge clk);#1;if(tx!==1) $fatal(1,"serial UART stop");
   $display("UART_RX %02h",v);
  end
 endtask
 task records;
  reg [7:0] tag,value;
  begin : decode
   forever begin
    read_uart(tag);
    if(tag==8'hd0) begin
     read_uart(value);
     if(seen>=64 || value!==responses[bank+897+seen]) $fatal(1,"serial provisional byte mismatch");
     seen=seen+1;tx_records=tx_records+1;
    end else if(tag==8'hf0) begin
     read_uart(status);read_uart(error);read_uart(consumed);terminal=1;disable decode;
    end else $fatal(1,"serial record tag mismatch");
   end
  end
 endtask
    task wait_start;
        begin : search
            forever begin @(negedge sda);if(scl===1'b1) disable search;end
        end
    endtask
    task receive_byte;
        input [7:0] expected;input ack;reg [7:0] value;integer b;
        begin
            for(b=7;b>=0;b=b-1) begin @(posedge scl);value[b]=sda;end
            if(value!==expected) $fatal(1,"CPU endpoint command wire byte got=%h expected=%h",value,expected);
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
            @(posedge scl);#1;if(sda!==!ack) $fatal(1,"CPU endpoint response ACK/NACK");@(negedge scl);
        end
    endtask
    function [15:0] next_crc;
      input [15:0] prior;input [7:0] value;integer k;reg [15:0] c;
      begin c=prior;for(k=0;k<8;k=k+1) c=(c[15]^value[k])?{c[14:0],1'b0}^16'h8005:{c[14:0],1'b0};next_crc=c;end
    endfunction
    task device;
        input integer fault;integer stage,offset,length,count,attempt,j;reg nack;reg [7:0] sent;reg [15:0] response_crc;
        begin
            wait(dut.core.processor.endpoint.session.wake_engine.state==2);@(posedge sda);
            begin : wake_response
                for(attempt=0;attempt<3;attempt=attempt+1) begin
                    wait_start;@(negedge scl);nack=(fault==12 && attempt==0);receive_byte(8'hc1,!nack);
                    if(!nack) begin
                        send_byte(4,1);send_byte(fault==1?8'h00:8'h11,1);
                        send_byte(fault==1?8'h03:8'h33,1);send_byte(fault==1?8'h40:8'h43,0);
                        disable wake_response;
                    end
                end
            end
            for(stage=0;stage<13;stage=stage+1) begin
                offset=bank+128*stage;length=commands[offset];count=responses[offset];
                wait_start;@(negedge scl);writes=writes+1;receive_byte(8'hc0,1);receive_byte(3,1);
                for(j=0;j<length;j=j+1) receive_byte(commands[offset+j],1);
                begin : command_response
                    for(attempt=0;attempt<3;attempt=attempt+1) begin
                        wait_start;stop_seen=0;@(negedge scl);
                        nack=(fault==2 && stage==7 && attempt==0);receive_byte(8'hc1,!nack);
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
                            disable command_response;
                        end
                    end
                end
            end
        end
    endtask
 task run_case;
  input integer context_id,fault,expected,fresh;
  integer j;
  begin
   if(fresh) begin rst_n=0;repeat(5) @(negedge clk);end
   present=1;slave_scl=0;slave_sda=0;bank=context_id*1664;seen=0;writes=0;terminal=0;status=0;error=0;consumed=0;current_fault=fault;stop_seen=0;
   $display("CASE SERIAL CPB=%0d DIV=%0d context=%0d fault=%0d fresh=%0d",CPB,DIV,context_id,fault,fresh);
   @(negedge clk);rst_n=1;repeat(10) @(negedge clk);
   fork : attempt
    device(fault);
    records;
    begin
     send_uart(8'ha1);
     for(j=0;j<32;j=j+1) send_uart(digests[context_id*32+j]);
    end
    begin
     if(fault==7) begin wait(seen>=12);@(negedge clk);present=0;end
     wait(terminal);disable attempt;
    end
   join
   if(request_timeout_cause!==0 || request_expired || request_active || !terminal || busy || error!==expected || !status[1] || status[2]!==(expected==0) || halted)
    $fatal(1,"serial final qualification fault=%0d status=%h error=%0d expected=%0d",fault,status,error,expected);
   if(expected==0 && (seen!=64 || consumed!=64 || writes!=13 || !stop_seen || !ok)) $fatal(1,"serial successful stream qualification");
   if(((fault==22 || fault==27 || fault==28) && writes!=1) || (fault==25 && writes!=4) || (fault==26 && writes!=3))
    $fatal(1,"card profile failure reached later command fault=%0d writes=%0d",fault,writes);
   if(expected!=0 && ok) $fatal(1,"serial failed stream committed");
   if((fault==4 || fault==5 || fault==20 || fault==21) && seen!=64) $fatal(1,"serial failed late stream missing");
   $display("RESULT SERIAL fault=%0d bytes=%0d status=%h error=%h count=%0d",fault,seen,status,error,consumed);
   slave_scl=0;slave_sda=0;present=1;repeat(CPB*3) @(negedge clk);
   if(dut.core.processor.endpoint.session_busy || sl || dl) $fatal(1,"serial cleanup failed");
   completed=completed+1;
  end
 endtask
 task incomplete_request;
  input integer count,mode;
  integer j,elapsed_cycles;
  begin
   $display("CASE GUARD count=%0d mode=%0d",count,mode);
   send_uart(8'ha1);
   if(mode==1) begin : trickle
    fork : slow_writer
     begin for(j=0;j<32;j=j+1) begin send_uart(digests[j]);repeat(CPB*14) @(negedge clk);end end
     begin wait(request_expired);disable slow_writer;end
    join
    @(negedge clk);rx=1;
   end else begin
    for(j=0;j<count;j=j+1) send_uart(digests[j]);
    if(mode==2) begin
     // Sustained BREAK is not a valid UART byte and cannot release quarantine.
     @(negedge clk);rx=0;
    end
    elapsed_cycles=0;
    while(!request_expired && elapsed_cycles<CPB*40) begin @(negedge clk);elapsed_cycles=elapsed_cycles+1;end
   end
   if(!request_expired || dut.core.core_reset_n || request_active || busy || ok || sl || dl || pc!==0)
    $fatal(1,"serial request deadline not asserted");
   if(request_timeout_cause!==(mode==1?2:1)) $fatal(1,"serial wrong deadline cause");
   if(dut.core.processor.endpoint.owner.digest_valid!==0) $fatal(1,"serial partial digest survived timeout");
   if(mode==2) begin
    repeat(CPB*20) @(negedge clk);
    if(dut.core.core_reset_n) $fatal(1,"serial BREAK escaped quarantine");
    rx=1;
   end
   // Late payload containing an A1 is drained, not treated as a fresh command.
   send_uart(8'ha1);send_uart(8'hff);send_uart(8'h00);
   if(dut.core.core_reset_n) $fatal(1,"serial late bytes escaped quarantine");
   repeat(CPB*16) @(negedge clk);
   if(!dut.core.core_reset_n || busy || ok || sl || dl || halted || !request_expired)
    $fatal(1,"serial quiet recovery failed");
   if(dut.core.peripherals.uart_rx_pending) $fatal(1,"serial stale UART pending");
   $display("PASS GUARD count=%0d mode=%0d cause=%0d recovered_without_external_reset=1",count,mode,request_timeout_cause);
   completed=completed+1;
  end
 endtask
 initial begin repeat(120000000) @(posedge clk);$fatal(1,"serial watchdog");end
 initial begin
  $readmemh("serial_secure_rom.hex",rom,0,255);
  $readmemh("session_commands.hex",commands,0,3327);$readmemh("session_responses.hex",responses,0,3327);
  $readmemh("session_digests.hex",digests,0,63);$readmemh("bad_nonce.hex",bad_nonce,0,3);
  for(word_index=0;word_index<256;word_index=word_index+1) begin
   #1;probe_addr=word_index;#1;
   if(probe_data!==rom[word_index]) $fatal(1,"budget ROM word mismatch");
  end
  run_case(0,0,0,1);run_case(1,0,0,0); // consecutive, no reset; new digest must replace all old bytes.
  run_case(0,1,7,0);run_case(0,2,0,0);run_case(1,3,7,0);
  run_case(0,4,7,0);run_case(1,5,7,0);run_case(0,7,4,0);
  run_case(1,12,0,0);
  run_case(0,20,7,0);run_case(1,0,0,0);
  run_case(1,21,7,0);run_case(0,0,0,0);
  run_case(0,22,7,0);run_case(1,25,7,0);run_case(0,26,7,0);
  run_case(0,27,7,0);run_case(0,28,7,0);run_case(1,0,0,0);
  incomplete_request(0,0);run_case(1,0,0,0);
  incomplete_request(1,0);run_case(0,0,0,0);
  incomplete_request(7,0);run_case(1,0,0,0);
  incomplete_request(31,0);run_case(0,0,0,0);
  incomplete_request(7,2);run_case(1,0,0,0);
  incomplete_request(0,1);run_case(0,0,0,0);
  $display("PASS current budget CPB=%0d DIV=%0d completed=%0d ROM=256",CPB,DIV,completed);$finish;
 end
endmodule
