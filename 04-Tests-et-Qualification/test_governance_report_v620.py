import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'03-Sources'))
from governance_report_v620 import build_report,render_html
class GovernanceReportTests(unittest.TestCase):
    def test_empty(self):
        result=build_report([])
        self.assertEqual(result['quality']['score'],100)
        self.assertEqual(result['review_required'],0)
    def test_candidates(self):
        result=build_report([{'id':'a','name':'a','type':'nas','source':'x','serial':'A'},{'id':'b','name':'b','type':'nas','source':'y','serial':'a'}])
        self.assertEqual(result['review_required'],1)
        self.assertEqual(result['destructive_changes'],0)
    def test_escape_xss(self):
        result=build_report([{'id':'a','name':'x','type':'nas','source':'s','serial':'1'},{'id':'b','name':'x','type':'nas','source':'t','serial':'1','site':'<script>alert(1)</script>'}])
        page=render_html(result)
        self.assertNotIn('<script>alert(1)</script>',page)
        self.assertIn('REVIEW_REQUIRED',page)
    def test_no_external_assets(self):
        self.assertNotIn('src="http',render_html(build_report([])))
if __name__=='__main__':unittest.main()
