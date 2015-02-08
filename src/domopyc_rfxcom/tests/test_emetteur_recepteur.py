import pty
from json import loads
import unittest
import asyncio

import os
import asyncio_redis
from rfxcom.protocol.base import BasePacket
import serial
from src.domopyc_rfxcom.emetteur_recepteur import RedisPublisher, RfxcomReader


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

        asyncio.get_event_loop().run_until_complete(
            asyncio.Task(RfxcomReaderForTest(RedisPublisher()).handle_temp_humidity(packet)))

        @asyncio.coroutine
        def receive_message():
            message = yield from self.subscriber.next_published()
            self.assertDictEqual(packet.data, loads(message.value))

        asyncio.get_event_loop().run_until_complete(receive_message())


class TestRfxcomAcceptance(unittest.TestCase):

    def setUp(self):
        @asyncio.coroutine
        def setup_redis():
            self.connection = yield from asyncio_redis.Connection.create(host='localhost', port=6379)
            self.subscriber = yield from self.connection.start_subscribe()
            yield from self.subscriber.subscribe([RedisPublisher.RFXCOM_KEY])
        asyncio.get_event_loop().run_until_complete(setup_redis())

    def tearDown(self):
        self.connection.close()

    def test_read_data_and_send_to_redis(self):
        master, slave = pty.openpty()
        s_name = os.ttyname(slave)
        ser = serial.Serial(s_name)

        RfxcomReader(ser, RedisPublisher())
        ser.write(bytes([0x00, 0x00, 0x00, 0x00, 0x08, 0x00]))

        @asyncio.coroutine
        def receive_message():
            message = yield from self.subscriber.next_published()
            self.assertDictEqual({'foo': 'bar'}, loads(message.value))

        asyncio.get_event_loop().run_until_complete(receive_message())


class RfxcomReaderForTest(RfxcomReader):
    def __init__(self, publisher, event_loop=asyncio.get_event_loop()):
        super().__init__(None, publisher, event_loop)

    def create_transport(self, device, event_loop):
        return None


class DummyPacket(BasePacket):
    def load(self, data):
        self.data = data
        return self
