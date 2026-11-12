import unittest

from coros_unlock.presence import PresenceMonitor, PresenceState


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += dt


class PresenceMonitorTests(unittest.TestCase):
    def test_requires_consecutive_detections(self):
        clock = FakeClock()
        mon = PresenceMonitor(present_after=2, absent_after=10, clock=clock)
        self.assertIsNone(mon.mark_detection())
        self.assertEqual(mon.mark_detection(), PresenceState.PRESENT.value)
        self.assertEqual(mon.state, PresenceState.PRESENT)

    def test_streak_resets_after_gap(self):
        clock = FakeClock()
        mon = PresenceMonitor(present_after=2, absent_after=10, clock=clock)
        mon.mark_detection()
        clock.advance(11)
        mon.mark_detection()
        self.assertNotEqual(mon.state, PresenceState.PRESENT)

    def test_absent_transition_on_tick(self):
        clock = FakeClock()
        mon = PresenceMonitor(present_after=1, absent_after=5, clock=clock)
        mon.mark_detection()
        self.assertEqual(mon.state, PresenceState.PRESENT)
        clock.advance(6)
        self.assertEqual(mon.tick(), PresenceState.ABSENT.value)

    def test_no_transition_while_within_window(self):
        clock = FakeClock()
        mon = PresenceMonitor(present_after=1, absent_after=5, clock=clock)
        mon.mark_detection()
        clock.advance(4)
        self.assertIsNone(mon.tick())

    def test_invalid_arguments(self):
        with self.assertRaises(ValueError):
            PresenceMonitor(present_after=0)
        with self.assertRaises(ValueError):
            PresenceMonitor(absent_after=0)


if __name__ == "__main__":
    unittest.main()
