import threading, time, unittest
from route_scheduler import RouteScheduler, RouteCancelled
from graph_layout import scalable_obstacle_routes

class CooperativeCancellationTests(unittest.TestCase):
    def test_cancelled_before_routing(self):
        with self.assertRaises(RouteCancelled):
            scalable_obstacle_routes([(('A',),100,140)],100,cancel_check=lambda: True)

    def test_cancelled_during_routing(self):
        calls=[0]
        def cancel():
            calls[0]+=1
            return calls[0]>=3
        with self.assertRaises(RouteCancelled):
            scalable_obstacle_routes([(('A',),100,140)],100,cancel_check=cancel)

    def test_latest_request_interrupts_previous(self):
        entered=threading.Event(); delivered=[]; aborted=threading.Event()
        def compute(p,c,cancel_check=None):
            if p[0]==1:
                entered.set()
                for _ in range(10000):
                    if cancel_check():
                        aborted.set();raise RouteCancelled()
                    time.sleep(.0001)
            return p
        scheduler=RouteScheduler(compute,delivered.append)
        try:
            scheduler.submit(1,'old',[1],0)
            self.assertTrue(entered.wait(1))
            scheduler.submit(2,'new',[2],0)
            for _ in range(200):
                if delivered:break
                time.sleep(.005)
            self.assertTrue(aborted.is_set())
            self.assertEqual([d[1] for d in delivered],['new'])
        finally:scheduler.close()

    def test_close_cancels_running(self):
        entered=threading.Event(); stopped=threading.Event()
        def compute(p,c,cancel_check=None):
            entered.set()
            for _ in range(1000):
                if cancel_check():stopped.set();raise RouteCancelled()
                time.sleep(.001)
        scheduler=RouteScheduler(compute,lambda _:None)
        scheduler.submit(1,'a',[1],0)
        self.assertTrue(entered.wait(1))
        scheduler.close()
        self.assertTrue(stopped.wait(1))
