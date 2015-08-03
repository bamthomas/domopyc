# coding=utf-8
import asyncio
from datetime import datetime, timezone
from json import loads
import binascii
from domopyc.daq import rfxcom_emiter_receiver
from domopyc.daq.publishers.redis_publisher import RedisPublisher
from domopyc.daq.rfxcom_emiter_receiver import RfxTrx433e, RfxTrx433eMessageHandler, RFXCOM_KEY_CMD
from rfxcom.protocol.base import BasePacket
from domopyc.subscribers.redis_toolbox import AsyncRedisSubscriber
from domopyc.test_utils.ut_async import DummySerial
from domopyc.test_utils.ut_redis import WithRedis


class TestRfxTrx433e(WithRedis):

    @asyncio.coroutine
    def setUp(self):
        yield from super().setUp()
        self.serial_device = DummySerial()

    def tearDown(self):
        self.serial_device.close()

    @asyncio.coroutine
    def test_read_data(self):
        rfxcom_emiter_receiver.now = lambda: datetime(2015, 2, 14, 15, 0, 0, tzinfo=timezone.utc)
        self.subscriber = yield from self.connection.start_subscribe()
        yield from self.subscriber.subscribe([rfxcom_emiter_receiver.RFXCOM_KEY])
        packet = DummyPacket().load(
            {'packet_length': 10, 'packet_type_name': 'Temperature and humidity sensors', 'sub_type': 1,
             'packet_type': 82, 'temperature': 22.2, 'humidity_status': 0, 'humidity': 0,
             'sequence_number': 1,
             'battery_signal_level': 128, 'signal_strength': 128, 'id': '0xBB02',
             'sub_type_name': 'THGN122/123, THGN132, THGR122/228/238/268'})

        RfxTrx433e(self.serial_device, RedisPublisher(self.connection, rfxcom_emiter_receiver.RFXCOM_KEY),
                   AsyncRedisSubscriber(self.connection, RfxTrx433eMessageHandler(), RFXCOM_KEY_CMD)).handle_temp_humidity(packet)

        message = yield from asyncio.wait_for(self.subscriber.next_published(), 1)
        self.assertDictEqual(dict(packet.data, date=rfxcom_emiter_receiver.now().isoformat()), loads(message.value))

    @asyncio.coroutine
    def test_write_data(self):
        subscriber = AsyncRedisSubscriber(self.connection, RfxTrx433eMessageHandler(), RFXCOM_KEY_CMD).start(for_n_messages=1)
        rfxcom_device = RfxTrx433eForTest(None, RedisPublisher(self.connection, rfxcom_emiter_receiver.RFXCOM_KEY), subscriber)

        yield from self.connection.publish(rfxcom_emiter_receiver.RFXCOM_KEY_CMD, '{"code_device": "1234567", "value": "1"}')
        yield from asyncio.wait_for(subscriber.message_loop_task, 2)

        self.assertEqual(b'0b1100010123456702010f70', binascii.hexlify(rfxcom_device.rfxcom_transport.data_out.pop()))


class RfxTrx433eForTest(RfxTrx433e):
    class MockTransport(object):
        def __init__(self):
            self.data_out = []

        def write(self, data):
            self.data_out.append(data)

    def __init__(self, device, publisher, subscriber):
        super().__init__(device, publisher, subscriber)

    def create_transport(self, device, event_loop):
        return RfxTrx433eForTest.MockTransport()


class DummyPacket(BasePacket):
    def load(self, data):
        self.data = data
        return self
