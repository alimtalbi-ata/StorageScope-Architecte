import unittest
from windows_page_controller_v590 import PageController

class NavigationAtomicTests(unittest.TestCase):
    def test_nested_navigation_during_render_rejected(self):
        c=PageController(('A','B'))
        def render(name):
            with self.assertRaisesRegex(RuntimeError,'Recursive page navigation'):
                c.navigate('B',lambda _:None)
        c.navigate('A',render)
        self.assertEqual(c.current,'A')
    def test_nested_navigation_during_loader_rejected(self):
        c=PageController(('A','B'))
        c.register('A',lambda: c.navigate('B',lambda _:None))
        with self.assertRaises(RuntimeError): c.navigate('A',lambda _:None)
        self.assertIsNone(c.current)
    def test_render_failure_allows_retry(self):
        c=PageController(('A',)); calls=[]
        c.register('A',lambda: calls.append('load'),lambda: calls.append('clean'))
        with self.assertRaises(ValueError): c.navigate('A',lambda _: (_ for _ in ()).throw(ValueError('bad')))
        c.navigate('A',lambda _: calls.append('ok'))
        self.assertEqual(calls,['load','clean','load','ok'])
    def test_invalid_renderer_does_not_initialize(self):
        c=PageController(('A',)); calls=[]
        c.register('A',lambda: calls.append('load'))
        with self.assertRaises(TypeError): c.navigate('A',None)
        self.assertFalse(calls)
    def test_navigation_ui_has_rollback_for_styles_and_preference(self):
        from pathlib import Path
        src=(Path(__file__).parent/'storagescope_windows.py').read_text()
        self.assertIn('previous_styles =',src)
        self.assertIn("preferences.pop('last_page', None)",src)
        self.assertIn('current[\'page\'] = previous',src)
