"""Offline evidence consistency/completeness gate, NOT authenticity verification.

Actual submission still requires freshly checked official records. This checker
must never turn unverified input JSON into an assertion of official submission.
"""
import argparse
import json
import re
from urllib.parse import urlparse

REQUIRED = ('rtl_freeze', 'functional', 'joint', 'coverage', 'lint', 'synthesis',
            'sta_40mhz', 'pnr', 'drc', 'lvs', 'precheck', 'gate_level', 'docs', 'required_ci')


def check(record):
    failures = []
    project = record.get('project')
    if project not in ('FIRM_CARD_01', 'FIRM_READER_01'):
        failures.append('unknown formal ASIC project')
    commit = record.get('source_sha', '')
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        failures.append('source_sha must be full lowercase Git SHA')
    for name in REQUIRED:
        item = record.get('checks', {}).get(name, {})
        if item.get('result') != 'PASS':
            failures.append(name + ': missing or not PASS')
        if item.get('source_sha') != commit:
            failures.append(name + ': source revision mismatch')
        url = urlparse(item.get('evidence_url', ''))
        if url.scheme != 'https' or not url.netloc or url.username or url.password:
            failures.append(name + ': missing HTTPS evidence reference')
    artifacts = record.get('artifacts', [])
    if not any(a.get('kind') in ('GDS', 'OAS') for a in artifacts):
        failures.append('no GDS/OAS artifact')
    for artifact in artifacts:
        if artifact.get('source_sha') != commit:
            failures.append('artifact revision mismatch')
        if not re.fullmatch(r'[0-9a-f]{64}', artifact.get('sha256', '')):
            failures.append('artifact missing SHA256')
    official = record.get('official_submission')
    official_consistent = False
    if official:
        project_url = urlparse(official.get('project_url', ''))
        pr_url = urlparse(official.get('merged_pr_url', ''))
        official_consistent = (
            official.get('source_sha') == commit
            and type(official.get('project_id')) is int and official['project_id'] > 0
            and project_url.scheme == 'https' and project_url.netloc == 'app.tinytapeout.com'
            and project_url.path == f"/projects/{official['project_id']}"
            and pr_url.scheme == 'https' and pr_url.netloc == 'github.com'
            and re.fullmatch(r'/TinyTapeout/tinytapeout-sky-26d/pull/[1-9][0-9]*', pr_url.path)
            and official.get('merged') is True
            and bool(official.get('revision')))
        if not official_consistent:
            failures.append('official submission references inconsistent')
    return {
        'project': project,
        'source_sha': commit,
        'status': 'INCOMPLETE' if failures else (
            'OFFICIAL_EVIDENCE_REQUIRES_LIVE_VERIFICATION' if official_consistent
            else 'EVIDENCE_COMPLETE_NOT_SUBMITTED'),
        'failures': failures,
        'product_security_status': 'NOT_ASSESSED',
        'scope': 'offline consistency only; no evidence authenticity, silicon or security certification',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest')
    args = parser.parse_args()
    with open(args.manifest) as source:
        result = check(json.load(source))
    print(json.dumps(result, indent=2))
    raise SystemExit(1 if result['failures'] else 0)
