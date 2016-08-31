# coding=utf-8
import os
import subprocess
from datetime import datetime
import time
import asyncio
import functools
from unittest import TestCase
from domopyc.daq import current_cost_sensor
from domopyc.daq.current_cost_sensor import AsyncCurrentCostReader, create_serial_factory
from domopyc.test_utils.ut_async import QueuePublisher


def async_coro(f):
    def wrap(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            coro = asyncio.coroutine(f)
            future = coro(*args, **kwargs)
            loop = asyncio.get_event_loop()
            loop.run_until_complete(future)

        return wrapper

    return wrap(f)


class CurrentCostReaderTest(TestCase):
    def setUp(self):
        current_cost_sensor.now = lambda: datetime(2012, 12, 13, 14, 15, 16)
        self.mock_serial = subprocess.Popen(['socat', 'PTY,link=/tmp/read,b9600', 'PTY,link=/tmp/write,b9600'])
        self.wait_for_link_to_be_created('/tmp/read')
        self.serial_write = create_serial_factory({'device': '/tmp/write'})()
        self.publisher = QueuePublisher()
        self.current_cost_reader = AsyncCurrentCostReader(create_serial_factory({'device': '/tmp/read'}),
                                                          self.publisher)

    def tearDown(self):
        self.current_cost_reader.close()
        self.mock_serial.kill()

    @async_coro
    def test_read_sensor(self):
        self.serial_write.write(
            '<msg><src>CC128-v1.29</src><dsb>00302</dsb><time>02:57:28</time><tmpr>21.4</tmpr><sensor>1</sensor><id>00126</id><type>1</type><ch1><watts>00305</watts></ch1></msg>\n'.encode())

        event = yield from asyncio.wait_for(self.publisher.queue.get(), 1)
        self.assertDictEqual(event, {'date': (current_cost_sensor.now().isoformat()), 'watt': 305, 'temperature': 21.4})

    @async_coro
    def test_read_sensor_xml_error_dont_break_loop(self):
        self.serial_write.write('<malformed XML>\n'.encode())
        self.serial_write.write(
            '<msg><src>CC128-v1.29</src><dsb>00302</dsb><time>02:57:28</time><tmpr>21.4</tmpr><sensor>1</sensor><id>00126</id><type>1</type><ch1><watts>00305</watts></ch1></msg>\n'.encode())

        event = yield from asyncio.wait_for(self.publisher.queue.get(), 1)
        self.assertDictEqual(event, {'date': (current_cost_sensor.now().isoformat()), 'watt': 305, 'temperature': 21.4})

    @async_coro
    def test_read_sensor_while_device_is_turned_off_and_on(self):
        serial_file_descriptor = self.current_cost_reader._serial_drv.fd
        self.mock_serial.kill()
        self.assertIsNotNone(self.current_cost_reader.event_loop._selector.get_key(self.current_cost_reader._serial_drv.fd))

        self.current_cost_reader.read_callback()

        with self.assertRaises(KeyError):
            self.current_cost_reader.event_loop._selector.get_key(serial_file_descriptor)
        self.mock_serial = subprocess.Popen(['socat', 'PTY,link=/tmp/read,b9600', 'PTY,link=/tmp/write,b9600'])
        self.wait_for_link_to_be_created('/tmp/read')
        yield from asyncio.sleep(1)
        self.assertIsNotNone(self.current_cost_reader.event_loop._selector.get_key(self.current_cost_reader._serial_drv.fd))

    @staticmethod
    def wait_for_link_to_be_created(link_path, timeout_seconds=1):
        elapsed_time = 0
        time_step = 0.1
        while elapsed_time < timeout_seconds and not os.path.exists(link_path):
            time.sleep(time_step)
            elapsed_time += time_step
        if not os.path.exists(link_path):
            raise TimeoutError('%s not found' % link_path)
