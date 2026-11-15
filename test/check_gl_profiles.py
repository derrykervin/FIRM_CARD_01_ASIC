"""Failure controls for GL result aggregation, never a DUT or GL pass."""
import json
import asyncio
import importlib.util
import os
import sys
import types
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET
from run_gl_profiles import aggregate,PROFILES

rows=[]
for mode in ['pass','failure','error','missing','empty','skipped','nonzero','malformed','failed_nonzero']:
    with tempfile.TemporaryDirectory()as tmp:
        root=Path(tmp)
        for profile in PROFILES:
            folder=root/'output'/profile;folder.mkdir(parents=True)
            (folder/'returncode.txt').write_text('0')
            (folder/'results.xml').write_text('<testsuites><testsuite><testcase name="protocol"/></testsuite></testsuites>')
        folder=root/'output'/PROFILES[1]
        if mode in ['failure','failed_nonzero']:
            (folder/'results.xml').write_text('<testsuites><testsuite><testcase><failure message="actual assertion"/></testcase></testsuite></testsuites>')
        if mode=='error':
            (folder/'results.xml').write_text('<testsuites><testsuite><testcase><error message="actual error"/></testcase></testsuite></testsuites>')
        if mode=='missing':(folder/'results.xml').unlink()
        if mode=='empty':(folder/'results.xml').write_text('<testsuites/>')
        if mode=='skipped':(folder/'results.xml').write_text('<testsuites><testsuite><testcase><skipped/></testcase></testsuite></testsuites>')
        if mode in ['nonzero','failed_nonzero']:(folder/'returncode.txt').write_text('1')
        if mode=='malformed':(folder/'results.xml').write_text('<bad')
        rejected=aggregate(root)
        assert rejected==(mode!='pass'),mode
        tree=ET.parse(root/'results.xml')
        assert bool(list(tree.iter('failure'))or list(tree.iter('error')))==(mode!='pass'),mode
        if mode=='failed_nonzero':assert any(e.get('message')=='actual assertion'for e in tree.iter('failure'))
        rows.append(dict(control=mode,status='EXPECTED_OUTCOME'))
# Audit only the coroutine's control plan; these mock handles do not simulate a
# DUT and cannot produce the real GL XML. Check against the original full plan.
async def immediate(*args,**kwargs):pass
fake=types.ModuleType('cocotb');fake.test=lambda:lambda function:function;fake.start_soon=lambda task:None
clock=types.ModuleType('cocotb.clock')
class Clock:
    def __init__(self,*args,**kwargs):pass
    def start(self):return None
clock.Clock=Clock
triggers=types.ModuleType('cocotb.triggers')
for name in ['ClockCycles','FallingEdge','RisingEdge','Timer','with_timeout']:setattr(triggers,name,immediate)
for name,module in [('cocotb',fake),('cocotb.clock',clock),('cocotb.triggers',triggers)]:sys.modules[name]=module
spec=importlib.util.spec_from_file_location('profile_plan',Path(__file__).with_name('test.py'))
test=importlib.util.module_from_spec(spec);spec.loader.exec_module(test)
plans={};previous=os.environ.get('FIRM_GL_PROFILE')
for profile in ['full',*PROFILES]:
    events=[]
    async def transaction(dut,context,late_mismatch=False,identity=False,crc_bad=False):
        events.append(('transaction',context,late_mismatch,identity,crc_bad))
    async def uart_send(dut,value):events.append(('partial_uart',value))
    test.transaction=transaction;test.uart_send=uart_send
    handles={name:types.SimpleNamespace(value=value)for name,value in
             [('ena',1),('rst_n',0),('ui_in',5),('uio_in',255),('uo_out',9),('uio_oe',0),('uio_out',32)]}
    dut=types.SimpleNamespace(clk=None,_log=types.SimpleNamespace(info=lambda *args:None),**handles)
    os.environ['FIRM_GL_PROFILE']=profile;asyncio.run(test.firm_card_protocol_test(dut));plans[profile]=events
if previous is None:os.environ.pop('FIRM_GL_PROFILE',None)
else:os.environ['FIRM_GL_PROFILE']=previous
gold=[('transaction',0,False,True,False),('transaction',0,False,False,False),
      ('transaction',1,False,True,True),('transaction',1,False,True,False),
      ('transaction',1,True,False,False),('transaction',1,False,False,False),
      ('partial_uart',161),('partial_uart',85),('transaction',0,False,False,False)]
assert plans['full']==gold
assert plans['identity_crc']+plans['proof_recovery'][1:]==gold
assert plans['proof_recovery'][0]==gold[3]
print(json.dumps(dict(status='PASS_AGGREGATION_FAILURE_CONTROLS_ONLY',controls=rows,
                     plan='ORIGINAL_FULL_PLAN_PRESERVED_WITH_ONE_REPLAYED_PRECONDITION')))
