"""Run both complete GL chains concurrently and preserve every child failure.

The unmodified official GL action still runs GATES=yes make, checks aggregate
results.xml and uploads output/** including each child waveform and XML.
"""
from concurrent.futures import ThreadPoolExecutor
import copy
import os
from pathlib import Path
import shutil
import signal
import subprocess
import xml.etree.ElementTree as ET

PROFILES=('identity_crc','proof_recovery')


def aggregate(root, profiles=PROFILES):
    suites=ET.Element('testsuites')
    failed=False
    for profile in profiles:
        folder=root/'output'/profile
        try:
            status=(folder/'returncode.txt').read_text().strip()
            tree=ET.parse(folder/'results.xml').getroot()
            cases=list(tree.iter('testcase'))
            if not cases or any(list(c.iter('skipped')) for c in cases):
                raise ValueError('child unsuccessful, empty or skipped: '+status)
            rows=[tree]if tree.tag=='testsuite'else list(tree.findall('testsuite'))
            if not rows:raise ValueError('no child test suite')
            for row in rows:
                result=copy.deepcopy(row);result.set('name',profile+'.'+result.get('name','GL'))
                suites.append(result)
            child_failed=any(c.find('failure')is not None or c.find('error')is not None for c in cases)
            failed|=child_failed
            if status!='0'and not child_failed:raise ValueError('child exit status '+status)
        except (OSError,ET.ParseError,ValueError)as error:
            failed=True
            suite=ET.SubElement(suites,'testsuite',name=profile,tests='1',failures='1')
            case=ET.SubElement(suite,'testcase',name='required_child_completion',classname=profile)
            ET.SubElement(case,'failure',message=str(error))
    ET.ElementTree(suites).write(root/'results.xml',encoding='utf-8',xml_declaration=True)
    return failed


def run(root,profile):
    folder=root/'output'/profile;folder.mkdir(parents=True,exist_ok=True)
    for name in ['Makefile','tb.v','test.py','proof_vectors.json']:
        shutil.copyfile(root/name,folder/name)
    target=folder/'gate_level_netlist.v'
    if target.is_symlink()or target.exists():target.unlink()
    target.symlink_to(root/'gate_level_netlist.v')
    # A stale XML can never qualify an interrupted or failed new subprocess.
    for name in ['results.xml','returncode.txt']:
        p=folder/name
        if p.exists():p.unlink()
    env=dict(os.environ,FIRM_GL_CHILD='1',FIRM_GL_PROFILE=profile)
    command=['make','GATES=yes','FIRM_GL_CHILD=1','SRC_DIR='+str(root.parent/'src')]
    with(folder/'process.log').open('w')as log:
        process=subprocess.Popen(command,cwd=folder,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            code=process.wait(timeout=19800)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGTERM)
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGKILL);process.wait()
            code=124;log.write('\nHOST_EXECUTION_TIMEOUT_NOT_PASS\n')
    (folder/'returncode.txt').write_text(str(code)+'\n')
    print(profile,'child returncode',code,flush=True)


if __name__=='__main__':
    root=Path(__file__).resolve().parent
    with ThreadPoolExecutor(max_workers=2)as pool:
        list(pool.map(lambda profile:run(root,profile),PROFILES))
    raise SystemExit(aggregate(root))
