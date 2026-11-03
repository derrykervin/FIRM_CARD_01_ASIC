import json
import tempfile
from pathlib import Path
import unittest
from collect_signoff import collect


class CollectorTests(unittest.TestCase):
    def fixture(self,root):
        logs=root/'logs';sta=logs/'runs/wokwi/55-openroad-stapostpnr'
        corner=sta/'max_ss';corner.mkdir(parents=True)
        (sta/'state_out.json').write_text(json.dumps({'metrics':{'timing__setup__ws':1.2,'timing__hold__ws':0.1}}))
        (sta/'config.json').write_text(json.dumps({'CLOCK_PERIOD':25,'CLOCK_PORT':'clk'}))
        (sta/'design.sdc').write_text('create_clock -period 25 [get_ports clk]\n')
        for name in ('wns.max.rpt','wns.min.rpt','tns.max.rpt','tns.min.rpt'):
            (corner/name).write_text('0.0\n')
        sub=root/'submission';sub.mkdir()
        for ext in ('gds','oas'): (sub/('tt_example.'+ext)).write_bytes(b'SYNTHETIC_TEST_DATA')
        return logs,sub,sta

    def test_complete_fixture_keeps_scope_and_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);logs,sub,sta=self.fixture(root)
            value=collect(logs,sub,root/'output','a'*40,'123','tt_example')
            self.assertEqual(value['status'],'COLLECTED_REQUIRES_REVIEW')
            self.assertEqual(len(value['artifacts']),2)
            self.assertEqual(len(value['timing_reports']),4)
            self.assertEqual(value['clock_configs'][0]['values']['CLOCK_PERIOD'],25)

    def test_missing_sdc_or_artifact_is_failure(self):
        for missing in ('sdc','oas'):
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory);logs,sub,sta=self.fixture(root)
                (sta/'design.sdc' if missing=='sdc' else sub/'tt_example.oas').unlink()
                with self.assertRaises(ValueError): collect(logs,sub,root/'out','a'*40,'1','tt_example')

    def test_missing_timing_not_empty_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);logs,sub,sta=self.fixture(root)
            (sta/'state_out.json').write_text('{"metrics":{}}')
            with self.assertRaises(ValueError): collect(logs,sub,root/'out','a'*40,'1','tt_example')

    def test_nonfinite_metric_remains_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);logs,sub,sta=self.fixture(root)
            (sta/'state_out.json').write_text('{"metrics":{"timing__setup__ws":Infinity}}')
            value=collect(logs,sub,root/'out','a'*40,'1','tt_example')
            self.assertEqual(value['metrics']['timing__setup__ws'],'inf')


if __name__ == '__main__': unittest.main()
