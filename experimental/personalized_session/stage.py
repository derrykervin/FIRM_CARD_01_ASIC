"""Stage the hash-locked RAM CARD with unified command and personalized observation session."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'experimental/personalized_session/base_source'
def stage(tree):
 tree=Path(tree);tree.mkdir(parents=True,exist_ok=True);lock=json.loads((ROOT/'experimental/personalized_session/source-lock.json').read_text());records={}
 for name,digest in lock['base_source'].items():
  raw=(BASE/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==digest
  if name.endswith(('/atecc_command_producer.v','/atecc_typed_exchange.v')):continue
  if name.endswith('/atecc_proof_session.v'):raw=(ROOT/'experimental/personalized_session/atecc_proof_session.v').read_bytes()
  target=tree/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);records[name]=hashlib.sha256(raw).hexdigest()
 for name,digest in lock['unified_sources'].items():
  raw=(ROOT/'experimental/unified_command'/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==digest
  target=tree/'experimental/i2c'/name;target.write_bytes(raw);records['experimental/i2c/'+name]=digest
 assert len(records)==22
 (tree/'source-records.json').write_text(json.dumps(records,indent=2)+'\n');return records
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(stage(a.output),indent=2))
