import tempfile, unittest
from pathlib import Path
from benchmark_v523 import run

class BenchmarkV523Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.report=run(cls.tmp.name,repetitions=1)
    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()
    def test_actual_equal_routes(self): self.assertTrue(self.report['all_routes_equal'])
    def test_16_paired_cases(self): self.assertEqual(self.report['comparison_count'],16)
    def test_report_files(self):
        self.assertTrue((Path(self.tmp.name)/'benchmark-v523.json').exists())
        self.assertTrue((Path(self.tmp.name)/'benchmark-v523.csv').exists())
    def test_fail_closed_with_inadequate_sample(self):
        from routing_policy_performance import evaluate_performance
        self.assertEqual(evaluate_performance(self.report['pairs'][:4])['reason'], 'insufficient_paired_measurements')
