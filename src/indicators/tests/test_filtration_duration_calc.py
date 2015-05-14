import unittest
from indicators import filtration_duration


class TestFiltrationDurationCalc(unittest.TestCase):
    def test_temperature_less_than_8_degrees_no_filtration(self):
        self.assertEqual(0, filtration_duration.calculate_in_minutes(7.9))

    def test_temperature_greater_than_8_degrees(self):
        self.assertEqual(5 * 60, filtration_duration.calculate_in_minutes(10.0))
        self.assertEqual(12 * 60, filtration_duration.calculate_in_minutes(24.0))
