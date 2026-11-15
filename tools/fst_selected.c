/* Read-only extraction of six top-level wires from a retained FST.
 * Uses the separately pinned, unmodified CVC/GTKWave fstapi implementation. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <inttypes.h>
#include "fstapi.h"
static unsigned *widths;
static uint64_t previous_time=UINT64_MAX;
static void change(void *unused,uint64_t time,fstHandle handle,const unsigned char *value) {
 (void)unused;
 if(time!=previous_time){printf("#%" PRIu64 "\n",time);previous_time=time;}
 if(widths[handle]==1)printf("%c%u\n",value[0],handle);
 else printf("b%s %u\n",value,handle);
}
int main(int argc,char **argv) {
 if(argc!=3 || strcmp(argv[1],"-f")){fprintf(stderr,"usage: fst_selected -f input.fst\n");return 2;}
 void *reader=fstReaderOpen(argv[2]);if(!reader)return 3;
 widths=calloc((size_t)fstReaderGetMaxHandle(reader)+1,sizeof(*widths));if(!widths)return 4;
 int exponent=fstReaderGetTimescale(reader),depth=0,top=0,found=0;
 const char *unit="ps";int count=1;
 if(exponent>=-15 && exponent<=-13){unit="fs";exponent+=15;}
 else if(exponent>=-12 && exponent<=-10){unit="ps";exponent+=12;}
 else if(exponent>=-9 && exponent<=-7){unit="ns";exponent+=9;}
 else {fprintf(stderr,"unsupported timescale\n");return 5;}
 for(int i=0;i<exponent;i++)count*=10;
 printf("$timescale %d%s $end\n$scope module tb $end\n",count,unit);
 const char *wanted[]={"scl_line","sda_line","uart_tx","uio_in","uio_oe","uo_out"};
 fstReaderClrFacProcessMaskAll(reader);
 struct fstHier *row;
 while((row=fstReaderIterateHier(reader))) {
  if(row->htyp==FST_HT_SCOPE){depth++;if(depth==1)top=!strcmp(row->u.scope.name,"tb");}
  else if(row->htyp==FST_HT_UPSCOPE){depth--;if(!depth)top=0;}
  else if(row->htyp==FST_HT_VAR && depth==1 && top) {
   for(size_t i=0;i<sizeof(wanted)/sizeof(wanted[0]);i++) {
    size_t n=strlen(wanted[i]);const char *name=row->u.var.name;
    if(strncmp(name,wanted[i],n) || (name[n] && name[n]!=' ' && name[n]!='['))continue;
    fstHandle handle=row->u.var.handle;found++;widths[handle]=row->u.var.length;
    fstReaderSetFacProcessMask(reader,handle);
    printf("$var wire %u %u %s $end\n",row->u.var.length,handle,wanted[i]);
   }
  }
 }
 if(found!=6){fprintf(stderr,"expected6 wires,found%d\n",found);return 6;}
 printf("$upscope $end\n$enddefinitions $end\n");
 fstReaderIterBlocks(reader,change,NULL,NULL);
 printf("#%" PRIu64 "\n",fstReaderGetEndTime(reader));
 fstReaderClose(reader);free(widths);return 0;
}
