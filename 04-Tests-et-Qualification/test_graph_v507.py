import unittest
from graph_layout import PartialGeometryRoutingCache, scalable_obstacle_routes

class CalibrationTests(unittest.TestCase):
    def test_no_observation_and_validation(self):
        c=PartialGeometryRoutingCache()
        self.assertEqual(c.calibrate_validation_budget(),12000)
        for args in [(0,), (float('nan'),), (0.1,0,200), (0.1,300,200)]:
            with self.assertRaises(ValueError): c.calibrate_validation_budget(*args)
    def test_calibration_clamps(self):
        c=PartialGeometryRoutingCache()
        c.validation_attempts=1;c.validation_checks=10000;c.validation_time_seconds=1
        self.assertEqual(c.calibrate_validation_budget(.001,1000,24000),1000)
        self.assertEqual(c.calibrate_validation_budget(5,1000,24000),24000)
    def test_multiple_changes_exact_and_telemetry(self):
        old=[(str(i),400+i*260,350) for i in range(36)]
        c=PartialGeometryRoutingCache();c.route(old,100,recent_routes=8)
        new=list(old)
        for i in (12,19,30):new[i]=(str(i),new[i][1]+13,new[i][2])
        self.assertEqual(c.route(new,100,recent_routes=8),scalable_obstacle_routes(new,100,recent_routes=8))
        self.assertGreaterEqual(c.validation_attempts,1)
        self.assertGreaterEqual(c.validation_last_seconds,0)
        self.assertGreater(c.calibrate_validation_budget(),0)
    def test_calibration_changes_only_fallback_not_output(self):
        old=[(str(i),400+i*260,350) for i in range(32)]
        c=PartialGeometryRoutingCache();c.route(old,100,recent_routes=0)
        c.validation_attempts=1;c.validation_checks=1;c.validation_time_seconds=1
        c.calibrate_validation_budget(.01,1,2)
        new=list(old);new[15]=(new[15][0],new[15][1]+20,new[15][2])
        self.assertEqual(c.route(new,100,recent_routes=0),scalable_obstacle_routes(new,100,recent_routes=0))
        self.assertGreater(c.validation_skips,0)
