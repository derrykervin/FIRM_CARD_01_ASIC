"""Two 13-command contexts with proposed-profile config, curve-valid public fixtures, signature-shaped bytes (NOT proofs)."""
import hashlib,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'FIRM-SYSTEM-SPECS/tools'))
from atecc608_codec import random_command,digest_command,sign_command,crc16
from personalized_device import config_read_command,public_key_command,configuration_facts
from cryptography.hazmat.primitives.asymmetric import ec
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True);commands=[];responses=[];digests=[];configs=[];pubs=[]
for context in [0,1]:
 digest=hashlib.sha256(f'FIRM session test context {context}'.encode()).digest();digests.append(digest)
 config=bytearray(128);config[:4]=bytes([1,0x23,7,context+9]);config[4:8]=bytes.fromhex('00006002');config[8:13]=bytes([context+6,4,7,2,0xee]);config[14]=1;config[16]=0xc0;config[19]=0;config[24:26]=bytes.fromhex('8720');config[100:102]=bytes.fromhex('3300');configuration_facts(bytes(config));configs.append(bytes(config))
 public=ec.derive_private_key(context+1,ec.SECP256R1()).public_key().public_numbers();xy=public.x.to_bytes(32,'big')+public.y.to_bytes(32,'big');pubs.append(xy)
 cmds=[config_read_command(b)for b in range(4)]+[public_key_command(2),random_command(),digest_command(digest),sign_command(2)]+[config_read_command(b)for b in range(4)]+[public_key_command(2)]
 payloads=[bytes(config[b*32:b*32+32])for b in range(4)]+[xy,bytes((j+context)&255 for j in range(32)),b'\0',bytes((j+context*3)&255 for j in range(64))]+[bytes(config[b*32:b*32+32])for b in range(4)]+[xy]
 commands+=cmds
 for payload in payloads:
  body=bytes([len(payload)+3])+payload;responses.append(body+crc16(body))
for name,packets in [('session_commands',commands),('session_responses',responses)]:
 raw=b''.join(p+bytes(128-len(p))for p in packets);assert len(raw)==3328;(out/(name+'.hex')).write_text('\n'.join(f'{b:02x}'for b in raw)+'\n')
(out/'session_digests.hex').write_text('\n'.join(f'{b:02x}'for d in digests for b in d)+'\n')
bad=bytes.fromhex('040f');(out/'bad_nonce.hex').write_text('\n'.join(f'{b:02x}'for b in bad+crc16(bad))+'\n')
(out/'vectors.json').write_text(json.dumps(dict(scope=__doc__,digests=[x.hex()for x in digests],configuration=[x.hex()for x in configs],public_xy=[x.hex()for x in pubs],commands=[x.hex()for x in commands],responses=[x.hex()for x in responses]),indent=2)+'\n')
