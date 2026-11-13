"""Prepare source-bound 25ns clock-only STA inputs; never produces numeric STA or a timing PASS."""
import argparse,hashlib,json,math
from pathlib import Path
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def prepare(out,manifest):
 out=Path(out);out.mkdir(parents=True,exist_ok=True);d=json.loads(Path(manifest).read_text());base=Path(d['mapping']);records=d['source_records']
 assert d['expected_ff']==2150 and d['storage']==dict(header_bits=160,public_bits=512,changed_metadata_net_bits=28,remaining_named_state_bits=1446)
 assert len(records)==22
 required=[base/'comparison.json']+[base/'personalized/firm_current_budget'/n for n in ['flat.json','mapped.json','mapped.v']]
 assert set(d['artifact_sha256'])=={str(p)for p in required}
 for n,h in d['artifact_sha256'].items():assert sha(n)==h
 for n,h in records.items():assert sha(base/'personalized/source'/n)==h
 mapping=json.loads((base/'comparison.json').read_text());assert records==mapping['source_records']['personalized'];area=mapping['blocks']['personalized'];assert area['generic_ff']==area['sequential_cells']==2150 and area['all_generic_ff_retained']
 flat=json.loads((base/'personalized/firm_current_budget/flat.json').read_text())['modules']['firm_current_budget'];clock=flat['ports']['clk']['bits'];ff=[c for c in flat['cells'].values()if 'DFF'in c['type']];assert len(ff)==2150 and all(c['connections']['C']==clock for c in ff)
 for n,bits in [('pre_header',160),('pre_public',512)]:assert len(flat['netnames']['core.processor.endpoint.session.'+n]['bits'])==bits
 lib=Path('/workspace/toolchain/pr11-synthesis/pdk/liberty.lib');assert sha(lib)=='ec0e1067a35c8bf20b11e58d1e8ac53326067e4dac84a125cc1b917a3518d0d9'
 period=d['period_ns'];assert type(period)in(int,float)and math.isfinite(period)and period==25
 sdc=out/'clock.sdc';sdc.write_text('# Experimental CARD core, clock-only prelayout. IO/reset/RC budgets remain missing.\n# No false paths or disabled timing checks. NOT a release/timing PASS.\ncreate_clock -name firm_clk -period 25 [get_ports clk]\n')
 def quote(p):
  s=str(p);assert not any(c in s for c in '{}\\\n');return '{'+s+'}'
 netlist=base/'personalized/firm_current_budget/mapped.v';commands=[f'read_liberty {quote(lib)}',f'read_verilog {quote(netlist)}','link_design firm_current_budget',f'read_sdc {quote(sdc.resolve())}','puts "FIRM_STA_CLOCKS [llength [get_clocks *]]"','puts "FIRM_STA_REGISTERS [llength [all_registers]]"']
 for name,cmd in [('units','report_units'),('setup','check_setup -verbose'),('checks','report_checks -path_delay min_max -group_path_count 5 -format full_clock_expanded'),('unconstrained','report_checks -unconstrained -path_delay min_max -group_path_count 5 -format full_clock_expanded'),('wns_max','report_worst_slack -max -digits 6'),('wns_min','report_worst_slack -min -digits 6'),('tns_max','report_tns -max -digits 6'),('tns_min','report_tns -min -digits 6')]:commands.append(cmd+' > '+quote((out/(name+'.rpt')).resolve()))
 commands.append('puts "FIRM_STA_COMPLETE 1"');tcl=out/'audit.tcl';tcl.write_text('if {[catch {\n'+'\n'.join(commands)+'\n} error_message]} {\n puts stderr "FIRM_STA_FATAL $error_message"\n exit 2\n}\n')
 result=dict(status='PREPARED_NOT_EXECUTED',ff=2150,source_records=records,inputs_manifest_sha256=sha(manifest),sdc_sha256=sha(sdc),script_sha256=sha(tcl),netlist_sha256=sha(netlist),library_sha256=sha(lib),clock_period_ns=25,clock_model='IDEAL_PRELAYOUT',rc='NONE',io_reset_constraints='MISSING_NOT_WAIVED',native_sta_executed=False,wns_tns=None,release='INCOMPLETE');(out/'preparation.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.output,a.inputs)))
