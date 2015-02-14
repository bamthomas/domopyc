from datetime import datetime
from json import loads, dumps
import unittest
import asyncio
import iso8601

import asyncio_redis
from rfxcom.protocol.base import BasePacket
from rfxcom_toolbox.emetteur_recepteur import RedisPublisher, RfxcomReader


class TestRfxcomReader(unittest.TestCase):

    def setUp(self):
        @asyncio.coroutine
        def setup_redis():
            self.connection = yield from asyncio_redis.Connection.create(host='localhost', port=6379)
            self.subscriber = yield from self.connection.start_subscribe()
            yield from self.subscriber.subscribe([RedisPublisher.RFXCOM_KEY])
        asyncio.get_event_loop().run_until_complete(setup_redis())

    def tearDown(self):
        self.connection.close()

    def test_read_data(self):
        packet = DummyPacket().load(
            {'packet_length': 10, 'packet_type_name': 'Temperature and humidity sensors', 'sub_type': 1,
             'packet_type': 82, 'temperature': 22.2, 'humidity_status': 0, 'humidity': 0,
             'sequence_number': 1,
             'battery_signal_level': 128, 'signal_strength': 128, 'id': '0xBB02',
             'sub_type_name': 'THGN122/123, THGN132, THGR122/228/238/268'})

        RfxcomReaderForTest(RedisPublisher()).handle_temp_humidity(packet)

        @asyncio.coroutine
        def receive_message():
            message = yield from self.subscriber.next_published()
            self.assertDictEqual(packet.data, loads(message.value))

        asyncio.get_event_loop().run_until_complete(receive_message())


class RfxcomPoolTempSubscriber(object):
    key = 'pool_temperature'
    def __init__(self, redis_conn):
        self.redis_conn = redis_conn
        @asyncio.coroutine
        def setup_redis():
            self.subscriber = yield from self.redis_conn.start_subscribe()
            yield from self.subscriber.subscribe([RedisPublisher.RFXCOM_KEY])
        asyncio.get_event_loop().run_until_complete(setup_redis())

    def start(self):
        asyncio.async(self.loop())
        return self

    @asyncio.coroutine
    def loop(self):
        while True:
            message_str = yield from self.subscriber.next_published()
            message = loads(message_str.value)
            message['date'] = iso8601.parse_date(message['date'])
            yield from self.redis_conn.zadd(RfxcomPoolTempSubscriber.key, {str(message['temperature']): message['date'].timestamp()})

    @asyncio.coroutine
    def get_average(self):
        val = yield from self.redis_conn.zrange(RfxcomPoolTempSubscriber.key, 0, -1)
        d = yield from val.asdict()
        return float(list(d)[0])


class TestPoolSubscriber(unittest.TestCase):
    def setUp(self):
        @asyncio.coroutine
        def setup_redis():
            self.connection = yield from asyncio_redis.Pool.create(host='localhost', port=6379, poolsize=2)
        asyncio.get_event_loop().run_until_complete(setup_redis())

    def test_read_one_data(self):
        pool_temp = RfxcomPoolTempSubscriber(self.connection).start()
        asyncio.get_event_loop().run_until_complete(self.connection.publish(RedisPublisher.RFXCOM_KEY, dumps({'date': datetime.now().isoformat(), 'temperature': 3.0})))

        @asyncio.coroutine
        def check_val():
            value = yield from pool_temp.get_average()
            self.assertEqual(3.0, value)
        asyncio.get_event_loop().run_until_complete(check_val())


class RfxcomReaderForTest(RfxcomReader):
    def __init__(self, publisher, event_loop=asyncio.get_event_loop()):
        super().__init__(None, publisher, event_loop)

    def create_transport(self, device, event_loop):
        return None


class DummyPacket(BasePacket):
    def load(self, data):
        self.data = data
        return self
