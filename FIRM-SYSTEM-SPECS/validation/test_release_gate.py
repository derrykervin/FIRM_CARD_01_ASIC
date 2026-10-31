import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from release_gate import check, REQUIRED


class ReleaseGateTests(unittest.TestCase):
    def fixture(self):
        # Synthetic evidence fixture, never a project signoff record.
        sha = 'a'*40
        return {'project': 'FIRM_CARD_01', 'source_sha': sha,
                'checks': {k: {'result': 'PASS', 'source_sha': sha,
                              'evidence_url': 'https://example.invalid/synthetic'} for k in REQUIRED},
                'artifacts': [{'kind': 'OAS', 'source_sha': sha, 'sha256': 'b'*64}]}

    def test_complete_offline_record_does_not_claim_submitted(self):
        self.assertEqual(check(self.fixture())['status'], 'EVIDENCE_COMPLETE_NOT_SUBMITTED')

    def test_old_green_ci_cannot_validate_new_source(self):
        data = self.fixture()
        data['checks']['gate_level']['source_sha'] = 'c'*40
        self.assertEqual(check(data)['status'], 'INCOMPLETE')

    def test_missing_or_failed_gates_block_release(self):
        for name in REQUIRED:
            data = self.fixture()
            del data['checks'][name]
            self.assertTrue(check(data)['failures'])
            data = self.fixture()
            data['checks'][name]['result'] = 'SKIPPED'
            self.assertTrue(check(data)['failures'])

    def test_artifact_and_link_checks(self):
        for mutation in ('no_artifact', 'bad_hash', 'stale_artifact', 'missing_link'):
            data = self.fixture()
            if mutation == 'no_artifact': data['artifacts'] = []
            if mutation == 'bad_hash': data['artifacts'][0]['sha256'] = 'abc'
            if mutation == 'stale_artifact': data['artifacts'][0]['source_sha'] = 'd'*40
            if mutation == 'missing_link': data['checks']['lint']['evidence_url'] = ''
            self.assertTrue(check(data)['failures'])

    def test_official_looking_json_still_needs_live_verification(self):
        data = self.fixture()
        data['official_submission'] = {'source_sha': 'a'*40, 'project_id': 999999,
            'project_url': 'https://app.tinytapeout.com/projects/999999',
            'merged_pr_url': 'https://github.com/TinyTapeout/tinytapeout-sky-26d/pull/999999',
            'merged': True, 'revision': 'synthetic'}
        self.assertEqual(check(data)['status'], 'OFFICIAL_EVIDENCE_REQUIRES_LIVE_VERIFICATION')
        data['official_submission']['source_sha'] = 'e'*40
        self.assertEqual(check(data)['status'], 'INCOMPLETE')


if __name__ == '__main__':
    unittest.main()
