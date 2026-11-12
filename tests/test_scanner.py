import unittest

from coros_unlock.config import Config
from coros_unlock.scanner import HR_SERVICE_UUID, matches


class FakeDevice:
    def __init__(self, address="uuid-1", name="COROS PACE 3", rssi=-60):
        self.address = address
        self.name = name
        self.rssi = rssi


class FakeAdv:
    def __init__(self, local_name="COROS PACE 3", service_uuids=None, rssi=-60):
        self.local_name = local_name
        self.service_uuids = service_uuids or []
        self.rssi = rssi


class MatchesTests(unittest.TestCase):
    def test_name_substring_match(self):
        cfg = Config(device_name="pace 3")
        self.assertTrue(matches(FakeDevice(), FakeAdv(), cfg))

    def test_case_insensitive(self):
        cfg = Config(device_name="coros")
        self.assertTrue(matches(FakeDevice(), FakeAdv(), cfg))

    def test_rssi_threshold(self):
        cfg = Config(device_name="COROS", rssi_threshold=-50)
        self.assertFalse(matches(FakeDevice(rssi=-70), FakeAdv(rssi=-70), cfg))

    def test_identifier_match(self):
        cfg = Config(device_identifier="uuid-9")
        self.assertTrue(matches(FakeDevice(address="uuid-9"), FakeAdv(), cfg))

    def test_hr_service_required(self):
        cfg = Config(device_name="COROS", require_hr_service=True)
        self.assertFalse(matches(FakeDevice(), FakeAdv(), cfg))
        self.assertTrue(
            matches(
                FakeDevice(),
                FakeAdv(service_uuids=[HR_SERVICE_UUID]),
                cfg,
            )
        )

    def test_no_match_unconfigured(self):
        self.assertFalse(matches(FakeDevice(), FakeAdv(), Config()))


if __name__ == "__main__":
    unittest.main()
