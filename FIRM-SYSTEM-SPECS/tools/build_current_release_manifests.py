"""Bind existing offline release policy to live current-source evidence.

This does not authenticate JSON, certify coverage/security, or submit a project.
Historic gate output is retained separately; missing/failed checks stay failed.
"""
import hashlib,importlib.util,json
from pathlib import Path

ROOT=Path('/workspace');OUT=ROOT/'deliverables/reader-final-gates'
read=lambda p:json.loads(p.read_text())
live=read(OUT/'live-sources.json')
prior=read(ROOT/'deliverables/paired-signoff/live-and-artifacts.json')
numeric=read(ROOT/'deliverables/paired-signoff/evidence.json')
gate_path=ROOT/'FIRM_CARD_01_ASIC/FIRM-SYSTEM-SPECS/tools/release_gate.py'
spec=importlib.util.spec_from_file_location('release_gate',gate_path)
gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
results={}
for label,repo,project,run in [('CARD','FIRM_CARD_01_ASIC','FIRM_CARD_01',43713543382),
                             ('Reader','FIRM_READER_01_ASIC','FIRM_READER_01',43714839904)]:
    data=live[label];sha=data['pr']['head']['sha'];assert prior[label]['pr']['head']['sha']==sha
    jobs={x['name']:x for x in data['jobs']['jobs']}
    def check(result,url,scope):
        return dict(result=result,source_sha=sha,evidence_url=url,scope=scope)
    job_url=lambda n:f'https://github.com/derrykervin/{repo}/actions/runs/{run}/job/{jobs[n]["id"]}'
    job_result=lambda n:'PASS' if jobs[n]['conclusion']=='success' else ('PENDING' if jobs[n]['status']!='completed' else 'FAIL')
    runs=prior[label]['runs']['workflow_runs']
    def workflow(name):
        hits=[x for x in runs if x['name']==name and x['head_sha']==sha]
        assert hits and all(x['conclusion']=='success' for x in hits),name
        return hits[0]['html_url']
    checks={
      'rtl_freeze':check('PASS',f'https://github.com/derrykervin/{repo}/commit/{sha}',
         'Immutable candidate snapshot only; not approval to merge/release/fabricate'),
      'functional':check('PASS',workflow('test'),'Exact candidate RTL fixture regression; not production security acceptance'),
      'joint':check('PASS','https://github.com/derrykervin/FIRM_READER_01_ASIC/actions/runs/43714839907',
         'Current CARD4ea/Readerbae pair CPB16/347 plus retained legacy/fault/async'),
      'coverage':check('PARTIAL',f'https://github.com/derrykervin/{repo}/tree/{sha}/test',
         'Controlled scenarios/mutants are qualified; current-source complete statement coverage is not established; older CVC coverage control failed. No 100% claim'),
      'lint':check(job_result('gds'),job_url('gds'),'Mandatory current GDS build checks'),
      'synthesis':check(job_result('gds'),job_url('gds'),'Current GDS flow synthesis'),
      'sta_40mhz':check(job_result('numeric_sta'),job_url('numeric_sta'),'Nine-corner numeric gate,39 content hashes independently checked; not complete constraint proof'),
      'pnr':check(job_result('gds'),job_url('gds'),'Current GDS placement/routing successful'),
      'drc':check(job_result('gds'),job_url('gds'),'Routing and Magic DRC clear in source-pinned log'),
      'lvs':check(job_result('gds'),job_url('gds'),'Circuits match uniquely and LVS errors clear in source-pinned log'),
      'precheck':check(job_result('precheck'),job_url('precheck'),'Official current Precheck job'),
      'gate_level':check(job_result('gl_test'),job_url('gl_test'),'Exact candidate gate-netlist functional regression'),
      'docs':check('PASS',workflow('docs'),'Current docs CI'),
      'required_ci':check('PASS' if all(x['conclusion']=='success' for x in jobs.values()) else
         ('PENDING' if any(x['status']!='completed' for x in jobs.values()) else 'FAIL'),
         f'https://github.com/derrykervin/{repo}/actions/runs/{run}',
         'All existing required checks retained, including Viewer; no disabled check or substituted old-source success'),
    }
    summary=numeric['chips'][label];assert summary['source_sha']==sha
    manifest=dict(project=project,source_sha=sha,checks=checks,artifacts=summary['artifacts'],
      artifact_scope=summary['artifact_scope'],official_submission=None,
      physical_tests='DEFERRED_BY_USER_NO_TEST_CAPABILITY',
      product_security_status='NOT_ASSESSED',
      production_security='Real device/factory binding/interactive production service acceptance remains incomplete',
      official_scope='No formal Project/Revision/inclusion/allocation/payment verified; artifact named tt_submission is not official submission')
    result=gate.check(manifest)
    assert result['status']=='INCOMPLETE' and 'coverage: missing or not PASS' in result['failures']
    if label=='Reader':assert checks['gate_level']['result']=='PASS' and checks['required_ci']['result']=='FAIL'
    (OUT/(label.lower()+'-release-manifest.json')).write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    (OUT/(label.lower()+'-release-check.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    root=ROOT/'deliverables'/(repo+'-release-gate.json');old=read(root)
    archive=OUT/(label.lower()+'-prior-gate.json')
    if not archive.exists():archive.write_text(json.dumps(old,ensure_ascii=False,indent=2)+'\n')
    old.update(result);old['checks']=checks;old['artifacts']=summary['artifacts']
    old['current_manifest']=str(OUT/(label.lower()+'-release-manifest.json'))
    old['legacy_failure_list_scope']='Prior top-level source/failures archived in reader-final-gates; top-level now evaluates exact current immutable candidate'
    root.write_text(json.dumps(old,ensure_ascii=False,indent=2)+'\n')
    results[label]=result
(OUT/'release-policy-review.json').write_text(json.dumps(dict(
    status='EXPECTED_INCOMPLETE_NOT_SUBMITTED',results=results,
    existing_gate_sha256=hashlib.sha256(gate_path.read_bytes()).hexdigest(),
    policy='Existing REQUIRED checks unchanged; coverage not upgraded and failed/pending CI not waived'),ensure_ascii=False,indent=2)+'\n')
print(json.dumps(results,ensure_ascii=False))
