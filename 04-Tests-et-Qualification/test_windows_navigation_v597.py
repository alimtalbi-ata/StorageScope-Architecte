import unittest
from windows_page_controller_v590 import PageController

class NavigationResilienceTests(unittest.TestCase):
    def test_render_failure_reinitializes_on_retry(self):
        c=PageController(('A',)); calls=[]
        c.register('A',lambda:calls.append('load'),lambda:calls.append('clean'))
        with self.assertRaises(OSError):
            c.navigate('A',lambda _: (_ for _ in ()).throw(OSError('render')))
        self.assertIsNone(c.current)
        c.navigate('A',lambda _:calls.append('render'))
        self.assertEqual(calls,['load','clean','load','render'])
    def test_cleanup_failure_does_not_mask_loader_error(self):
        c=PageController(('A',))
        def fail():raise ValueError('original')
        def cleanup():raise RuntimeError('cleanup')
        c.register('A',fail,cleanup)
        with self.assertRaisesRegex(ValueError,'original'):c.navigate('A',lambda _:None)
    def test_cleanup_failure_does_not_mask_render_error(self):
        c=PageController(('A',));c.register('A',lambda:None,lambda: (_ for _ in ()).throw(RuntimeError('cleanup')))
        with self.assertRaisesRegex(OSError,'render'):c.navigate('A',lambda _: (_ for _ in ()).throw(OSError('render')))
    def test_successful_page_not_reloaded_after_render_failure(self):
        c=PageController(('A',));calls=[];c.register('A',lambda:calls.append('load'))
        c.navigate('A',lambda _:None)
        with self.assertRaises(ValueError):c.navigate('A',lambda _: (_ for _ in ()).throw(ValueError('render')))
        c.navigate('A',lambda _:None)
        self.assertEqual(calls,['load'])
    def test_cross_module_navigation_preserves_previous_on_error(self):
        c=PageController(('Gouvernance','Campagnes'))
        c.navigate('Gouvernance',lambda _:None)
        c.register('Campagnes',lambda:None)
        with self.assertRaises(ValueError):c.navigate('Campagnes',lambda _: (_ for _ in ()).throw(ValueError('ui')))
        self.assertEqual(c.current,'Gouvernance')
