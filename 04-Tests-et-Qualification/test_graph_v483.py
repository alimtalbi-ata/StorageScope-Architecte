"""Headless structural checks for Tk-safe background routing."""
import unittest
from pathlib import Path

SOURCE = Path(__file__).with_name('desktop.py').read_text(encoding='utf-8')

class AsyncGraphTests(unittest.TestCase):
    def test_background_thread(self):
        self.assertIn('RouteScheduler(scalable_obstacle_routes,self._route_queue.put)', SOURCE)
    def test_generation_guard(self):
        self.assertIn('generation == self._route_generation', SOURCE)
    def test_tk_only_poll(self):
        self.assertIn('self._route_scheduler.submit(generation, key, positions, center)', SOURCE)
        self.assertNotIn("threading.Thread(target=work, daemon=True, name='graph-routing')", SOURCE)
    def test_zoom_cache_key_independent(self):
        self.assertIn('key=(tuple((tuple(node),round(x,3),round(y,3))', SOURCE)
    def test_shutdown_cancels_poll(self):
        self.assertIn('self.after_cancel(self._route_poll_id)', SOURCE)

if __name__ == '__main__': unittest.main()
