from asyncio.test_utils import TestLoop, run_briefly
import logging
from io import StringIO
from json import dumps
import unittest
import asyncio

import asyncio_redis
import redis
from rfxcom import protocol
from rfxcom.transport import AsyncioTransport

root = logging.getLogger()
logging.basicConfig()
root.setLevel(logging.INFO)


class RfxcomReader(object):
    def __init__(self, device, event_loop, publisher):
        self.publisher = publisher
        self.rfxcom_transport = AsyncioTransport(device, event_loop,
                             callbacks={protocol.TempHumidity: self.handle_temp_humidity, '*': self.default_callback})

    def handle_temp_humidity(self, packet):
        self.publisher.publish(packet.data)

    def default_callback(self, packet):
        pass


class RedisPublisher(object):
    RFXCOM_KEY = "rfxcom"

    def __init__(self, host='localhost', port=6379):
        self.port = port
        self.host = host

    @asyncio.coroutine
    def publish(self, event):
        connection = yield asyncio_redis.Connection.create(self.host, self.port)
        yield from connection.publish(self.RFXCOM_KEY, dumps(event))


class MockDevice(object):
    def __init__(self):
        self.fd = StringIO()


class TestAsyncioTransport(unittest.TestCase):
    def test_fumee(self):
        def gen():
            yield {'key': 'value'}

        def cb(packet):
            print("pouet")
            self.assertIsNotNone(packet)

        loop = TestLoop(gen=gen)
        device = MockDevice()
        rfxcom_transport = AsyncioTransport(device, loop, callback=cb)
        loop._run_once()


class TestRfxcomReader(unittest.TestCase):
    def setUp(self):
        self.redis = redis.Redis()

    def test_read_data(self):
        dev = MockDevice()
        def gen():
            yield {'packet_length': 10, 'packet_type_name': 'Temperature and humidity sensors', 'sub_type': 1,
                       'packet_type': 82, 'temperature': 22.2, 'humidity_status': 0, 'humidity': 0,
                       'sequence_number': 1,
                       'battery_signal_level': 128, 'signal_strength': 128, 'id': '0xBB02',
                       'sub_type_name': 'THGN122/123, THGN132, THGR122/228/238/268'}
        loop = TestLoop(gen=gen)

        RfxcomReader(dev, loop, RedisPublisher())

        pubsub = self.redis.pubsub()
        pubsub.subscribe(RedisPublisher.RFXCOM_KEY)
        message = pubsub.get_message(True)

        self.assertDictEqual({}, message)