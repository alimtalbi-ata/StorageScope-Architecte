import unittest
from pathlib import Path
from unittest.mock import MagicMock
from desktop import GovernanceWindow

class ProgressiveRenderingTests(unittest.TestCase):
    def test_batch_limit_and_reschedule(self):
        obj=object.__new__(GovernanceWindow)
        obj.graph=MagicMock()
        obj.graph.create_rectangle.side_effect=range(1,1000)
        obj.graph.create_text.side_effect=range(1001,2000)
        obj._card_render_generation=1
        obj.after=MagicMock(return_value='job')
        obj.after_idle=MagicMock()
        positions=[(('ACTION',str(i),'OPEN',False),100,150+i*60) for i in range(100)]
        obj._render_card_batch(1,positions,1.0)
        self.assertEqual(obj.graph.create_rectangle.call_count,40)
        self.assertEqual(obj.after.call_count,1)
        self.assertEqual(obj._card_render_job,'job')
    def test_stale_batch_ignored(self):
        obj=object.__new__(GovernanceWindow);obj.graph=MagicMock();obj._card_render_generation=2
        obj._render_card_batch(1,[(('ACTION','x','OPEN',False),100,100)],1)
        obj.graph.create_rectangle.assert_not_called()
    def test_final_batch_schedules_minimap(self):
        obj=object.__new__(GovernanceWindow);obj.graph=MagicMock();obj._card_render_generation=1
        obj.after_idle=MagicMock()
        obj._render_card_batch(1,[],1)
        self.assertIsNone(obj._card_render_job)
        obj.after_idle.assert_called_once()
    def test_source_wiring(self):
        source=Path(__file__).with_name('desktop.py').read_text()
        self.assertIn('self._cancel_card_render()',source)
        self.assertIn('self._render_card_batch(self._card_render_generation,cards,zoom)',source)
