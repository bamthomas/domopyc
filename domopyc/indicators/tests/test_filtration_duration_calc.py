import unittest
from domopyc.indicators import filtration_duration


class TestFiltrationDurationCalc(unittest.TestCase):
    def test_temperature_less_than_10_degrees_no_filtration(self):
        self.assertEqual(0, filtration_duration.calculate_in_minutes(9.9))

    def test_temperature_greater_than_10_degrees(self):
        self.assertEqual(5 * 60, filtration_duration.calculate_in_minutes(10.0))
        self.assertEqual(12 * 60, filtration_duration.calculate_in_minutes(24.0))


class PoolFilterManager(object):
    def __init__(self, full_hours):
        self.full_hours = full_hours


class PoolFilterManagerTest(unittest.TestCase):
    def test_pool_filter_do_not_send_command_twice(self):
        pool_filter_manager = PoolFilterManager([])


