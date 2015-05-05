from datetime import datetime
from json import loads, dumps
import unittest
import asyncio

import functools
import asyncio_redis
from rfxcom.protocol.base import BasePacket
from rfxcom_toolbox.emetteur_recepteur import RedisPublisher, RfxcomReader, RfxcomPoolTempSubscriber


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


class WithRedis(unittest.TestCase):
    @async_coro
    def setUp(self):
        self.connection = yield from asyncio_redis.Pool.create(host='localhost', port=6379, poolsize=4)
        yield from self.connection.flushdb()

    def tearDown(self):
        self.connection.close()


class TestRfxcomReader(WithRedis):
    @async_coro
    def test_read_data(self):
        self.subscriber = yield from self.connection.start_subscribe()
        yield from self.subscriber.subscribe([RedisPublisher.RFXCOM_KEY])
        packet = DummyPacket().load(
            {'packet_length': 10, 'packet_type_name': 'Temperature and humidity sensors', 'sub_type': 1,
             'packet_type': 82, 'temperature': 22.2, 'humidity_status': 0, 'humidity': 0,
             'sequence_number': 1,
             'battery_signal_level': 128, 'signal_strength': 128, 'id': '0xBB02',
             'sub_type_name': 'THGN122/123, THGN132, THGR122/228/238/268'})

        RfxcomReaderForTest(RedisPublisher()).handle_temp_humidity(packet)

        message = yield from self.subscriber.next_published()
        self.assertDictEqual(packet.data, loads(message.value))


class TestPoolSubscriber(WithRedis):
    @async_coro
    def test_average_no_data(self):
        pool_temp = RfxcomPoolTempSubscriber(self.connection).start()

        value = yield from pool_temp.get_average()
        self.assertEqual(0.0, value)

    @async_coro
    def test_average_one_data(self):
        pool_temp = RfxcomPoolTempSubscriber(self.connection).start(1)

        yield from self.connection.publish(RedisPublisher.RFXCOM_KEY, dumps({'date': datetime.now().isoformat(), 'temperature': 3.0}))
        yield from asyncio.wait_for(pool_temp.message_loop_task, timeout=1)

        value = yield from pool_temp.get_average()
        self.assertEqual(3.0, value)

    @async_coro
    def test_average_two_data(self):
        pool_temp = RfxcomPoolTempSubscriber(self.connection).start(2)

        yield from self.connection.publish(RedisPublisher.RFXCOM_KEY, dumps({'date': datetime(2015, 2, 14, 15, 0, 0).isoformat(), 'temperature': 3.0}))
        yield from self.connection.publish(RedisPublisher.RFXCOM_KEY, dumps({'date': datetime(2015, 2, 14, 15, 0, 1).isoformat(), 'temperature': 5.0}))
        yield from asyncio.wait_for(pool_temp.message_loop_task, timeout=1)

        value = yield from pool_temp.get_average()
        self.assertEqual(4.0, value)


class RfxcomReaderForTest(RfxcomReader):
    def __init__(self, publisher, event_loop=asyncio.get_event_loop()):
        super().__init__(None, publisher, event_loop)

    def create_transport(self, device, event_loop):
        return None


class DummyPacket(BasePacket):
    def load(self, data):
        self.data = data
        return self
