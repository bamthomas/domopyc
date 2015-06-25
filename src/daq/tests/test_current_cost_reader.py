# coding=utf-8
from datetime import datetime
import unittest
import asyncio
from daq import current_cost_sensor
from daq.current_cost_sensor import AsyncCurrentCostReader
from test_utils.ut_async import async_coro, TestMessageHandler, DummySerial


class CurrentCostReaderTest(unittest.TestCase):
    def setUp(self):
        current_cost_sensor.now = lambda: datetime(2012, 12, 13, 14, 15, 16)
        self.serial_device = DummySerial()
        self.handler = TestMessageHandler()
        self.current_cost_reader = AsyncCurrentCostReader(self.serial_device, self.handler)

    def tearDown(self):
        self.current_cost_reader.remove_reader()
        self.serial_device.close()

    @async_coro
    def test_read_sensor(self):
        self.serial_device.serial.send(
            '<msg><src>CC128-v1.29</src><dsb>00302</dsb><time>02:57:28</time><tmpr>21.4</tmpr><sensor>1</sensor><id>00126</id><type>1</type><ch1><watts>00305</watts></ch1></msg>\n'.encode())

        event = yield from asyncio.wait_for(self.handler.queue.get(), 1)
        self.assertDictEqual(event, {'date': (current_cost_sensor.now().isoformat()), 'watt': 305, 'temperature': 21.4})

    @async_coro
    def test_read_sensor_xml_error_dont_break_loop(self):
        self.serial_device.write('<malformed XML>\n'.encode())
        self.serial_device.serial.send  (
            '<msg><src>CC128-v1.29</src><dsb>00302</dsb><time>02:57:28</time><tmpr>21.4</tmpr><sensor>1</sensor><id>00126</id><type>1</type><ch1><watts>00305</watts></ch1></msg>\n'.encode())

        event = yield from asyncio.wait_for(self.handler.queue.get(), 1)
        self.assertDictEqual(event, {'date': (current_cost_sensor.now().isoformat()), 'watt': 305, 'temperature': 21.4})
