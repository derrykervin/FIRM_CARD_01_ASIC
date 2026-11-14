import copy,hashlib,unittest
from check_sta_gate import CORNERS,evaluate
SHA='a'*40
class NumericSTATests(unittest.TestCase):
 def fixture(self):
  d={'source_sha':SHA,'clock_configs':[{'values':{'CLOCK_PERIOD':25}}],'metrics':{},'timing_reports':[]}
  for c in CORNERS:
   for k in ['setup','hold']:
    for m in ['ws','wns','tns']:d['metrics'][f'timing__{k}__{m}__corner:{c}']=0
    d['metrics'][f'timing__{k}_vio__count__corner:{c}']=0
   for n in ['wns.min.rpt','wns.max.rpt','tns.min.rpt','tns.max.rpt']:
    s=f'{c}: 0.0\n';d['timing_reports'].append({'path':f'sta/{c}/{n}','content':s,'sha256':hashlib.sha256(s.encode()).hexdigest()})
  return d
 def test_complete_zero_case(self):self.assertEqual(evaluate(self.fixture(),SHA)['status'],'PASS_NUMERIC_STA_ONLY')
 def test_all_numeric_fields_fail_closed(self):
  base=self.fixture()
  for key in base['metrics']:
   for bad in [None,float('nan'),float('inf'),True,'0',-0.001]:
    d=copy.deepcopy(base);d['metrics'][key]=bad
    with self.subTest(key=key,bad=bad):self.assertEqual(evaluate(d,SHA)['status'],'FAIL')
 def test_missing_source_clock_corner_report_or_bad_hash(self):
  for field in ['source','clock','corner','report','hash']:
   d=self.fixture()
   if field=='source':d['source_sha']='b'*40
   if field=='clock':d['clock_configs'][0]['values']['CLOCK_PERIOD']=30
   if field=='corner':d['metrics'].pop(next(iter(d['metrics'])))
   if field=='report':d['timing_reports'].pop()
   if field=='hash':d['timing_reports'][0]['sha256']='0'*64
   self.assertEqual(evaluate(d,SHA)['status'],'FAIL',field)
 def test_report_negative_despite_zero_metrics(self):
  d=self.fixture();r=d['timing_reports'][0];s=r['content'].replace('0.0','-0.1');r['content']=s;r['sha256']=hashlib.sha256(s.encode()).hexdigest();self.assertEqual(evaluate(d,SHA)['status'],'FAIL')
if __name__=='__main__':unittest.main()
