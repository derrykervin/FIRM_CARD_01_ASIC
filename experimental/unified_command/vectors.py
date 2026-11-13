"""Pinned original Microchip C packet/CRC oracle; no HAL or device cryptography."""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=Path(__file__).resolve().parents[2];out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
vendor=Path('/workspace/deliverables/unified-command/vendor/calib_command.c');raw=vendor.read_bytes();assert len(raw)==25944 and hashlib.sha1(b'blob 25944\0'+raw).hexdigest()=='d4e3643e89cbc88f23c51eca289ee7e01470cf0b'
devtypes=vendor.parent/'atca_devtypes.h';dr=devtypes.read_bytes();assert hashlib.sha1(b'blob '+str(len(dr)).encode()+b'\0'+dr).hexdigest()=='50ea2266da6e9d6e4489ceb42795305921171754'
status=vendor.parent/'atca_status.h';sr=status.read_bytes();assert hashlib.sha1(b'blob '+str(len(sr)).encode()+b'\0'+sr).hexdigest()=='40a665055c9ebcff0ae60de98bbc78743b1e2ea0'
assert 'typedef int ATCA_STATUS;'in sr.decode() and re.search(r'#define\s+ATCA_BAD_PARAM\s+\(-30\)',sr.decode()) and re.search(r'#define\s+ATCA_SUCCESS\s+\(0\)',sr.decode())
header_path=Path('/workspace/deliverables/unified-command/vendor/calib_command.h');hr=header_path.read_bytes();assert hashlib.sha256(hr).hexdigest()=='8d9733cc2da9502edc3cc26e68f55789ec865edc22bca4ad7631fcfc2ef950a1';header=hr.decode();source=raw.decode()
def function(signature):
 start=source.index(signature);pos=source.index('{',start);depth=0
 for end in range(pos,len(source)):
  if source[end]=='{':depth+=1
  elif source[end]=='}':
   depth-=1
   if not depth:return source[start:end+1]
 raise AssertionError('Unclosed original function')
functions=[function(x) for x in ['void atCRC(','void atCalcCrc(','ATCA_STATUS atRead(','ATCA_STATUS atGenKey(','ATCA_STATUS atRandom(','ATCA_STATUS atNonce(','ATCA_STATUS atSign(']]
packet=header[header.index('#ifdef ATCA_NO_PRAGMA_PACK'):header.index('#if CALIB_CHECKMAC_EN')]
names=['ATCA_CMD_SIZE_MIN','ATCA_CRC_SIZE','ATCA_READ','ATCA_GENKEY','GENKEY_COUNT','GENKEY_COUNT_DATA','GENKEY_MODE_PUBKEY_DIGEST','READ_COUNT','ATCA_NONCE','ATCA_RANDOM','ATCA_SIGN','NONCE_MODE_MASK','NONCE_MODE_SEED_UPDATE','NONCE_MODE_NO_SEED_UPDATE','NONCE_MODE_GEN_SESSION_KEY','NONCE_MODE_PASSTHROUGH','NONCE_MODE_INPUT_LEN_MASK','NONCE_MODE_INPUT_LEN_64','NONCE_COUNT_SHORT','NONCE_COUNT_LONG','NONCE_COUNT_LONG_64','RANDOM_COUNT','SIGN_COUNT','ATCA_SHA_DIGEST_SIZE']
defines='\n'.join(next(x for x in header.splitlines() if re.match(r'#define\s+'+n+r'\s',x))for n in names)
prefix=source[:source.index('#include')]+'''\n#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
typedef int ATCA_STATUS;
#include "atca_devtypes.h"
#define ATCA_BAD_PARAM (-30)
#define ATCA_TRACE(status,message) (status)
#define ATCA_SUCCESS 0
#define CA_MAX_PACKET_SIZE 155u
#if __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__
#error This oracle harness requires a verified little-endian host
#endif
#define ATCA_UINT16_HOST_TO_LE(x) (x)
'''+defines+'\n'+packet+'\n'
main='''
int main(int argc,char **argv){
 if(argc!=3 || offsetof(ATCAPacket,txsize)!=1 || offsetof(ATCAPacket,param2)!=4 || offsetof(ATCAPacket,data)!=6)return 1;
 FILE *commands=fopen(argv[1],"wb"),*responses=fopen(argv[2],"wb");if(!commands||!responses)return 2;
 for(unsigned kind=0;kind<8;kind++){
  ATCAPacket packet;memset(&packet,0,sizeof packet);packet.param1=kind==1?0x43:kind==2?0xa0:(kind>=3 && kind<=6?0x80:0);packet.param2=(kind==2 || kind==7)?2:(kind>=3 && kind<=6?(kind-3)*8:0);
  for(unsigned j=0;j<32;j++)packet.data[j]=j;
  ATCA_STATUS status=kind==0?atRandom(ATECC608,&packet):kind==1?atNonce(ATECC608,&packet):kind==2?atSign(ATECC608,&packet):kind==7?atGenKey(ATECC608,&packet):atRead(ATECC608,&packet);
  if(status!=ATCA_SUCCESS || packet.txsize!=(kind==1?39:7))return 3;
  uint8_t frame[128]={0};memcpy(frame,&packet.txsize,packet.txsize);if(fwrite(frame,1,128,commands)!=128)return 4;
  uint8_t response[128]={0};unsigned count=kind==1?4:(kind==2 || kind==7?67:35);response[0]=count;
  for(unsigned j=0;j<count-3;j++)response[j+1]=kind==7?j*29+7:(kind>=3?(kind-3)*32+j:(kind==1?0:j));
  atCRC(count-2,response,&response[count-2]);if(fwrite(response,1,128,responses)!=128)return 5;
 }
 return fclose(commands)!=0 || fclose(responses)!=0;
}
'''
c=out/'oracle.c';c.write_text(prefix+'\n'.join(functions)+main)
cmd=['cc','-std=c99','-O2','-Wall','-Wextra','-Werror','-I'+str(vendor.parent),str(c),'-o',str(out/'oracle')];r=subprocess.run(cmd,capture_output=True,text=True);(out/'compile.log').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr
subprocess.run([str(out/'oracle'),str(out/'commands.bin'),str(out/'responses.bin')],check=True)
sys.path.insert(0,str(root/'FIRM-SYSTEM-SPECS/tools'));from personalized_device import config_read_command,public_key_command
from atecc608_codec import crc16,random_command,digest_command,sign_command
packets=[random_command(),digest_command(bytes(range(32))),sign_command(2)]+[config_read_command(i)for i in range(4)]+[public_key_command(2)];commands=(out/'commands.bin').read_bytes();responses=(out/'responses.bin').read_bytes();assert len(commands)==len(responses)==1024
for i,packet in enumerate(packets):
 assert commands[i*128:i*128+len(packet)]==packet
 count=responses[i*128];body=responses[i*128:i*128+count];assert crc16(body[:-2])==body[-2:]
for file,data in [('commands',commands),('command_responses',responses)]:
 (out/(file+'.hex')).write_text('\n'.join(f'{b:02x}'for b in data)+'\n')
result=dict(status='PASS_ORIGINAL_MICROCHIP_C_AND_SOFTWARE_PACKET_ORACLE_ONLY',vendor_commit='d49c7d578efb09d4a498d5ab86839d4c17812f15',vendor_blob='d4e3643e89cbc88f23c51eca289ee7e01470cf0b',vendor_sha256=hashlib.sha256(raw).hexdigest(),helper_sha256=[hashlib.sha256(f.encode()).hexdigest()for f in functions],header_sha256=hashlib.sha256(hr).hexdigest(),device_types_sha256=hashlib.sha256(dr).hexdigest(),status_sha256=hashlib.sha256(sr).hexdigest(),harness_sha256=hashlib.sha256(c.read_bytes()).hexdigest(),compiler=subprocess.check_output(['cc','--version'],text=True).splitlines()[0],compiler_flags=cmd[1:6],commands=[p.hex()for p in packets],response_counts=[35,4,67,35,35,35,35,67],scope=__doc__+' Response bytes are arbitrary wire fixtures, including a nonvalidated public-key payload. Not real configuration or a curve-valid/device-generated key.')
(out/'vectors.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS original C packet oracle:',result['commands'])
