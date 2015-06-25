# coding=utf-8
import asyncio
from datetime import datetime, timezone
from json import loads
import binascii
from daq import rfxcom_emiter_receiver
from daq.publishers.redis_publisher import RedisPublisher
from daq.rfxcom_emiter_receiver import RfxTrx433e
from rfxcom.protocol.base import BasePacket
from test_utils.ut_async import async_coro, DummySerial
from test_utils.ut_redis import WithRedis


class TestRfxTrx433e(WithRedis):

    @async_coro
    def setUp(self):
        yield from super().setUp()
        self.serial_device = DummySerial()

    def tearDown(self):
        self.serial_device.close()

    @async_coro
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

        RfxTrx433e(self.serial_device, RedisPublisher(self.connection, rfxcom_emiter_receiver.RFXCOM_KEY)).handle_temp_humidity(packet)

        message = yield from asyncio.wait_for(self.subscriber.next_published(), 1)
        self.assertDictEqual(dict(packet.data, date=rfxcom_emiter_receiver.now().isoformat()), loads(message.value))

    @async_coro
    def test_write_data(self):
        rfxcom_device = RfxTrx433e(self.serial_device, RedisPublisher(self.connection, rfxcom_emiter_receiver.RFXCOM_KEY))
        yield from asyncio.sleep(0.4)
        rfxcom_message = self.serial_device.serial.recv(14)
        yield from asyncio.sleep(0.1)
        rfxcom_message = self.serial_device.serial.recv(14)
        yield from asyncio.sleep(0.1)
        rfxcom_message = self.serial_device.serial.recv(14)
        yield from asyncio.sleep(0.1)

        yield from self.connection.publish(rfxcom_emiter_receiver.RFXCOM_KEY_CMD, '{"code_device": "1234567", "value": "1"}')
        yield from asyncio.sleep(0.4)
        rfxcom_message = self.serial_device.serial.recv(12)
        print(rfxcom_message)
        self.assertEqual(b'0b1100010123456702010f70', binascii.hexlify(rfxcom_message))



class DummyPacket(BasePacket):
    def load(self, data):
        self.data = data
        return self
