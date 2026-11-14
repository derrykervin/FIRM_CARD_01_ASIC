`default_nettype none
// Experimental CPU/MMIO routing. ROM and legacy peripherals remain external.
// Test firmware and transport completion do NOT authorize a product login.
module firm_secure_cpu_port #(
    parameter integer OWNER_DIGEST_DIRECT=1,
    parameter integer KEY_SLOT=2,DIV=100,SHARE_DIGEST=1,SHARE_TRANSPORT=1,
    parameter integer WAKE_LOW_CYCLES=3200,WAKE_HIGH_CYCLES=60000,
    parameter integer EXEC_WAIT_CYCLES=40000,POLL_CYCLES=40000,MAX_READ_ATTEMPTS=20,
    parameter integer BYTE_TIMEOUT=400000,BUS_TIMEOUT=4000000,READ_TIMEOUT=5000000,
    parameter integer PRODUCER_TIMEOUT=4000000,COMMAND_TIMEOUT=8000000,
    parameter integer WAKE_TIMEOUT=2000000,TOTAL_TIMEOUT=40000000,
    // Allow forwarding child done through the owner; no child budget is extended.
    parameter integer OWNER_TIMEOUT=TOTAL_TIMEOUT+2,
    parameter [6:0] DEVICE_ADDRESS=7'h60
)(
    input wire clk,rst_n,card_present,
    output wire [7:0] rom_addr,input wire [15:0] rom_data,
    output wire legacy_io_re,legacy_io_we,output wire [7:0] legacy_io_addr,legacy_io_wdata,
    input wire [7:0] legacy_io_rdata,
    output wire [7:0] debug_pc,debug_r0,output wire halted,
    output wire memory_fault,
    output wire owner_busy,transport_committed,
    input wire scl_in,sda_in,output wire scl_low,sda_low
);
    wire cpu_io_re,cpu_io_we,secure_selected;
    wire [7:0] cpu_io_addr,cpu_io_wdata,cpu_rdata,endpoint_rdata;
    wire bus_live=rst_n && !halted && !memory_fault;
    wire endpoint_committed;
    assign transport_committed=!memory_fault && endpoint_committed;
    wire [7:0] endpoint_wdata=cpu_io_wdata;
    assign legacy_io_re=bus_live && cpu_io_re && !secure_selected;
    assign legacy_io_we=bus_live && cpu_io_we && !secure_selected;
    assign legacy_io_addr=cpu_io_addr;
    assign legacy_io_wdata=cpu_io_wdata;
    assign cpu_rdata=secure_selected ? endpoint_rdata : legacy_io_rdata;
    card_cpu cpu(.clk(clk),.reset_n(rst_n),.rom_addr(rom_addr),.rom_data(rom_data),
        .io_re(cpu_io_re),.io_we(cpu_io_we),.io_addr(cpu_io_addr),.io_wdata(cpu_io_wdata),
        .io_rdata(cpu_rdata),.debug_pc(debug_pc),.debug_r0(debug_r0),.halted(halted),.memory_fault(memory_fault));
    firm_secure_endpoint #(
        .KEY_SLOT(KEY_SLOT),
        .OWNER_DIGEST_DIRECT(OWNER_DIGEST_DIRECT),
        .DIV(DIV),
        .SHARE_DIGEST(SHARE_DIGEST),
        .SHARE_TRANSPORT(SHARE_TRANSPORT),
        .WAKE_LOW_CYCLES(WAKE_LOW_CYCLES),
        .WAKE_HIGH_CYCLES(WAKE_HIGH_CYCLES),
        .EXEC_WAIT_CYCLES(EXEC_WAIT_CYCLES),
        .POLL_CYCLES(POLL_CYCLES),
        .MAX_READ_ATTEMPTS(MAX_READ_ATTEMPTS),
        .BYTE_TIMEOUT(BYTE_TIMEOUT),
        .BUS_TIMEOUT(BUS_TIMEOUT),
        .READ_TIMEOUT(READ_TIMEOUT),
        .PRODUCER_TIMEOUT(PRODUCER_TIMEOUT),
        .COMMAND_TIMEOUT(COMMAND_TIMEOUT),
        .WAKE_TIMEOUT(WAKE_TIMEOUT),
        .TOTAL_TIMEOUT(TOTAL_TIMEOUT),
        .OWNER_TIMEOUT(OWNER_TIMEOUT),
        .DEVICE_ADDRESS(DEVICE_ADDRESS)) endpoint(
        .clk(clk),.rst_n(rst_n && !memory_fault),.card_present(card_present),
        .io_re(bus_live && cpu_io_re && secure_selected),.io_we(bus_live && cpu_io_we && secure_selected),
        .io_addr(cpu_io_addr),.io_wdata(endpoint_wdata),.io_rdata(endpoint_rdata),.io_selected(secure_selected),
        .owner_busy(owner_busy),.transport_committed(endpoint_committed),
        .scl_in(scl_in),.sda_in(sda_in),.scl_low(scl_low),.sda_low(sda_low));
endmodule
`default_nettype wire
