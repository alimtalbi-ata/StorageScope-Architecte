import threading
import time
import unittest
from route_scheduler import RouteScheduler

class SchedulerTests(unittest.TestCase):
    def test_single_worker(self):
        s=RouteScheduler(lambda p,c,**kw: p,lambda result: None)
        try:
            self.assertTrue(s.worker.is_alive())
            for i in range(100): self.assertTrue(s.submit(i,i,[(i,)],0))
            self.assertEqual(s.worker.name,'graph-routing-worker')
        finally: s.close()

    def test_latest_wins(self):
        started=threading.Event(); release=threading.Event(); delivered=[]
        def compute(p,c,**kw):
            started.set();release.wait(2);return p
        s=RouteScheduler(compute,delivered.append)
        try:
            s.submit(1,'first',[1],0);self.assertTrue(started.wait(1))
            for i in range(2,30):s.submit(i,str(i),[i],0)
            release.set()
            for _ in range(100):
                if delivered:break
                time.sleep(.005)
            self.assertEqual([x[1] for x in delivered],['29'])
        finally:s.close();release.set()

    def test_close_rejects_requests(self):
        s=RouteScheduler(lambda p,c,**kw:None,lambda x:None)
        s.close();self.assertFalse(s.submit(1,'a',[],0))

    def test_worker_exception_delivered(self):
        delivered=[]
        def fail(p,c,**kw):raise ValueError('test failure')
        s=RouteScheduler(fail,delivered.append)
        try:
            s.submit(1,'a',[],0)
            for _ in range(100):
                if delivered:break
                time.sleep(.005)
            self.assertEqual(delivered[0][3],'test failure')
        finally:s.close()
