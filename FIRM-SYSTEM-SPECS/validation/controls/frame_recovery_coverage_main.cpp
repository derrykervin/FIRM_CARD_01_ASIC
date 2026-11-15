#include "Vtb_frame_recovery.h"
#include "verilated.h"
#include "verilated_cov.h"
#include <iostream>
int main(int argc,char** argv) {
 VerilatedContext context;context.commandArgs(argc,argv);
 Vtb_frame_recovery top{&context};
 while(!context.gotFinish() && context.time()<10000000000ULL) {
  top.eval();
  if(!top.eventsPending() && !context.gotFinish())return 2;
  if(!context.gotFinish())context.time(top.nextTimeSlot());
 }
 if(!context.gotFinish())return 3;
 top.final();context.coveragep()->write("coverage.dat");
 std::cout<<"PASS independent frame recovery coverage harness\n";
}
