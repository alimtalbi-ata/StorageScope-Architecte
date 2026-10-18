"""Static integration regression for v5.48 UI actions. Author: Abdelhalim Talbi."""
import unittest
from pathlib import Path

SOURCE = Path(__file__).with_name('decision_workspace_ui_v543.py').read_text()

class QualificationUiIntegrationTests(unittest.TestCase):
    def test_qualification_import(self): self.assertIn('from decision_qualification_v547 import QualificationStore, CRITERIA', SOURCE)
    def test_human_button(self): self.assertIn("('Qualifier preuves','qualify')", SOURCE)
    def test_explicit_verdict(self): self.assertIn('guided_qualification_form', SOURCE)
    def test_criteria_complete(self): self.assertIn("'criteria':{key:var.get() for key,var in checks.items()}", Path(__file__).with_name('decision_guided_forms_v607.py').read_text())
    def test_cancel_criteria(self): self.assertIn('if values is None:return', SOURCE)
    def test_ledger_call(self): self.assertIn("qualification_store.qualify(ident,values['actor'],values['verdict'],values['criteria'],values['rationale'])", SOURCE)
    def test_stale_indicator(self): self.assertIn('À requalifier', SOURCE)
    def test_unreviewed_indicator(self): self.assertIn('Sans revue', SOURCE)
    def test_qualification_details(self): self.assertIn('qualification_cache.get', SOURCE)
    def test_no_auto_accept(self): self.assertNotIn("verdict='ACCEPT'", SOURCE)
