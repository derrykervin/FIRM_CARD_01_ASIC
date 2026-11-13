"""Source-bound observation-session evidence only; fail closed on missing checks, no release/security certification."""
import argparse,hashlib,json
from decimal import Decimal
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',type=Path,default=Path('/workspace/deliverables/personalized-session'));p.add_argument('--output',type=Path,required=True);a=p.parse_args();b=a.base;root=Path(__file__).resolve().parents[2];rd=lambda n:json.loads((b/n).read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();mapping=rd('mapping/comparison.json');expected=mapping['source_records']['personalized'];assert len(expected)==22
for n,h in expected.items():assert sha(b/'mapping/personalized/source'/n)==h
assert expected['experimental/i2c/atecc_proof_session.v']==sha(root/'experimental/personalized_session/atecc_proof_session.v')
mutations={
'header_compare':('step==8 && payload_count<20 && command_data!=header_byte',"1'b0"),
'public_compare':('step==12 && command_data!=public_byte',"1'b0"),
'slot_policy':("24:profile_bad=value!=8'h87;","24:profile_bad=1'b0;"),
'slot_lock':('24:profile_bad=value[2];',"24:profile_bad=1'b0;"),
'serial_reject':('(step==0 && (serial_zero || serial_ff))',"1'b0"),
'm0_reject':("19:profile_bad=(value&8'hf9)!=0;","19:profile_bad=1'b0;"),
'sequence_check':('completed_steps!=preceding_steps',"1'b0"),
'early_sign_success':('else if(step==12) begin','else if(step==7) begin')}
summary={}
for sim in ['icarus','cvc']:
 sets=['final-session-'+sim,'session-tail-'+sim]+(['session-remaining-icarus','session-heavy-icarus']if sim=='icarus'else[]);qualified={}
 for group in sets:
  path=b/group/'results.json'
  if not path.exists():continue
  for row in json.loads(path.read_text())['results']:
   if row['result']=='PASS':qualified[(row['divider'],row['attempts'],row['share_digest'],row['share_transport'],row['control'])]=row
 rows=list(qualified.values())
 assert len(rows)==14 and all(r['result']=='PASS'for r in rows);normal=[r for r in rows if r['control']=='normal'];assert len(normal)==6 and sum(r['completed']for r in normal)==166
 assert {r['control']for r in rows if r['control']!='normal'}==set(mutations)
 aliases={Path(n).name:h for n,h in expected.items()if n.startswith('experimental/i2c/')}
 for row in rows:
  hashes=dict(aliases)
  if row['control']in mutations:
   text=(root/'experimental/personalized_session/atecc_proof_session.v').read_text();old,new=mutations[row['control']];assert text.count(old)==1;hashes['atecc_proof_session.v']=hashlib.sha256(text.replace(old,new).encode()).hexdigest()
  assert row['source_sha256']==hashes
  text=(root/'experimental/personalized_session/tb_personalized_session.v').read_text().replace('parameter DIV=2;',f"parameter DIV={row['divider']};").replace('parameter ATTEMPTS=3;',f"parameter ATTEMPTS={row['attempts']};").replace('parameter SHARE_DIGEST=1;',f"parameter SHARE_DIGEST={row['share_digest']};").replace('parameter SHARE_TRANSPORT=1;',f"parameter SHARE_TRANSPORT={row['share_transport']};")
  assert hashlib.sha256(text.encode()).hexdigest()==row['bench_sha256']
 profile=rd('profile-'+sim+'/results.json');assert profile['single_byte_cases']==32768 and profile['comparison_bits']==672 and profile['source_records']==expected
 summary[sim]=dict(session_configurations=14,normal_session_configurations=6,completed_session_scenarios=166,real_rtl_defect_controls=8,profile_single_byte_cases=32768,exact_comparison_bits=672,qualification_source_sets=sets)
card=rd('final-card-cvc/results.json');assert len(card['results'])==6 and all(r['result']=='PASS'for r in card['results']);positive=[r for r in card['results']if r['control']=='normal'];assert len(positive)==3 and sum(r['completed']for r in positive)==93 and all(r['source_records']==expected for r in positive)
card_mutations={
 'early_commit':('/firm_secure_mailbox.v','assign transport_committed=committed && card_present && !session_abort;',"assign transport_committed=1'b1;"),
 'wrong_digest':('/firm_secure_cpu_port.v','wire [7:0] endpoint_wdata=cpu_io_wdata;',"wire [7:0] endpoint_wdata=cpu_io_addr>=8'h90 ?(cpu_io_wdata^8'h01):cpu_io_wdata;"),
 'skip_post':('/atecc_proof_session.v',"step<=step+1'b1;payload_count<=0;","step<=step==7?4'd12:step+1'b1;payload_count<=0;")}
for row in card['results']:
 hashes=dict(expected)
 if row['control']in card_mutations:
  suffix,old,new=card_mutations[row['control']];n=next(n for n in expected if n.endswith(suffix));text=(b/'mapping/personalized/source'/n).read_text();assert text.count(old)==1;hashes[n]=hashlib.sha256(text.replace(old,new).encode()).hexdigest()
 assert row['source_records']==hashes
 text=(root/'experimental/personalized_session/tb_personalized_card.v').read_text().replace('parameter CPB=16,DIV=2;',f"parameter CPB={row['cpb']},DIV={row['divider']};")
 assert hashlib.sha256(text.encode()).hexdigest()==row['bench_sha256']
icarus=rd('final-card-icarus/results.json');assert len(icarus['results'])==1 and icarus['results'][0]['completed']==31 and icarus['results'][0]['source_records']==expected
slow=rd('slow-card-cvc/results.json');assert len(slow['results'])==4 and all(r['result']=='PASS'for r in slow['results']);ms=[5,5,5,5,115,23,20,115,5,5,5,5,115]
assert len(slow['results'][0]['ack'])==13 and all(x['cycles']>=ms[x['stage']]*40000 for x in slow['results'][0]['ack']);assert all(len(x['source_records'])==22 for x in slow['results']);assert slow['results'][3]['completed']==2
clock=rd('clock-preparation/preparation.json');controls=rd('clock-controls.json');assert clock['status']=='PREPARED_NOT_EXECUTED'and clock['ff']==2150 and clock['source_records']==expected and clock['clock_period_ns']==25 and clock['native_sta_executed']is False
assert len(controls['results'])==9 and all(x['result']=='REJECTED_AS_EXPECTED'for x in controls['results'])
uart=rd('reader-baud-card-cvc/results.json');assert len(uart['results'])==1 and uart['results'][0]['cpb']==347 and uart['results'][0]['slow_m0']and uart['results'][0]['result']=='PASS'and len(uart['results'][0]['ack'])==13 and uart['results'][0]['source_records']==expected
vendor=rd('vendor-packets/results.json');assert vendor['status']=='PASS_NATIVE_VENDOR_C_ALL_26_SESSION_COMMANDS'
for mode,v in mapping['blocks'].items():assert v['generic_ff']==v['sequential_cells']and v['all_generic_ff_retained']
assert mapping['blocks']['reference']['generic_ff']==1450 and mapping['blocks']['personalized']['generic_ff']==2150
storage=rd('mapping/storage-accounting.json');assert storage['remaining_named_state_bits']==1446 and storage['ff_increase']==700
area=Decimal(str(mapping['blocks']['personalized']['area_um2']));rects={'1x2':Decimal('36347.36'),'2x2':Decimal('75602.5088'),'3x2':Decimal('114857.6576'),'4x2':Decimal('154112.8064')}
r=dict(status='PASS_INTEGRATED_13_COMMAND_OBSERVATION_CANDIDATE_ONLY',tests=summary,full_card_cvc_normal_configurations=3,full_card_cvc_completed_scenarios=93,full_card_cvc_mutants=3,full_card_icarus_completed_scenarios=31,slow_card_cvc_configurations=4,slow_13_commands=True,reader_40mhz_cpb347_card_model_checked=True,formal_uart_alignment_pending=True,late_key_mismatch_then_no_reset_recovery=True,original_c_commands=26,full_card_ff=2150,full_card_area_um2=str(area),prior_card_ff=1450,prior_card_area_um2=str(mapping['blocks']['reference']['area_um2']),area_increase_um2=str(area-Decimal(str(mapping['blocks']['reference']['area_um2']))),storage_accounting=storage,rectangle_area_percent={n:str(area/a*100)for n,a in rects.items()},rectangle_is_not_physical_fit=True,proposed_profile_approval=False,registered_factory_facts_compared=False,physical_device_validated=False,p256_or_signature_verified_in_rtl=False,current_reader_rtl_joint_run=False,final_tt_wrapper_integrated=False,clock_sdc_prepared=True,clock_input_controls=9,native_sta_executed=False,wns_tns=None,physical_signoff='NOT_COMPLETE',hardware_tests='DEFERRED_BY_USER',formal_card='INCOMPLETE_NOT_SUBMITTED',formal_reader='INCOMPLETE_NOT_SUBMITTED')
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
