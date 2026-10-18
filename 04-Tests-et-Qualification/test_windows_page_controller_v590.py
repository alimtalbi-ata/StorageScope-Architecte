import unittest
from windows_page_controller_v590 import PageController

class PageControllerTests(unittest.TestCase):
    def test_lazy_loading_once(self):
        c=PageController(('Accueil','Gouvernance')); events=[]
        c.register('Gouvernance',lambda: events.append('load'))
        c.navigate('Gouvernance',lambda x: events.append(x))
        c.navigate('Gouvernance',lambda x: events.append(x))
        self.assertEqual(events,['load','Gouvernance','Gouvernance'])
    def test_failed_loader_retries_and_cleans(self):
        c=PageController(('A',)); events=[]
        def loader():
            events.append('load')
            if len(events)<3: raise ValueError('bad')
        c.register('A',loader,lambda: events.append('clean'))
        with self.assertRaises(ValueError): c.navigate('A',lambda x:None)
        c.navigate('A',lambda x:events.append('render'))
        self.assertEqual(events,['load','clean','load','render'])
    def test_invalid_page_does_not_render(self):
        c=PageController(('A',)); events=[]
        with self.assertRaises(ValueError): c.navigate('B',events.append)
        self.assertFalse(events)
    def test_recursive_initialization_blocked(self):
        c=PageController(('A',)); c.register('A',lambda: c.navigate('A',lambda x:None))
        with self.assertRaises(RuntimeError): c.navigate('A',lambda x:None)
    def test_render_failure_keeps_previous_page(self):
        c=PageController(('A','B')); c.navigate('A',lambda x:None)
        with self.assertRaises(OSError): c.navigate('B',lambda x: (_ for _ in ()).throw(OSError('render')))
        self.assertEqual(c.current,'A')
