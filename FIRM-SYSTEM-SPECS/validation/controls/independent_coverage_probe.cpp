#include "Vindependent_coverage_probe.h"
#include "verilated.h"
#include "verilated_cov.h"
#include <iostream>
#include <string>
int main(int argc,char** argv) {
 VerilatedContext context; context.commandArgs(argc,argv);
 Vindependent_coverage_probe top{&context};
 const bool hit=argc>1 && std::string(argv[1])=="hit";
 auto tick=[&](bool reset,bool gate,unsigned value) {
  top.rst_n=reset;top.gate=gate;top.value=value;
  top.clk=0;top.eval();context.timeInc(1);
  top.clk=1;top.eval();context.timeInc(1);
 };
 tick(false,false,0);tick(false,false,0);
 if(top.observed!=0 || top.peek0!=0 || top.peek1!=0)return 2;
 for(unsigned value:{0x55U,0xaaU,0x5aU,0x00U,0xffU,0x00U}) {
  tick(true,hit,value);
  if(hit && (top.observed!=value || top.peek0!=value || top.peek1!=(value^255U)))return 3;
  if(!hit && (top.observed!=0 || top.peek0!=0 || top.peek1!=0))return 4;
 }
 top.final();context.coveragep()->write("coverage.dat");
 std::cout<<"PASS independent coverage probe "<<(hit?"hit":"miss")<<"\n";
}
