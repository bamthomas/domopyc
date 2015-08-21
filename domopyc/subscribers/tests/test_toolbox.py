from asyncio import Queue
import asyncio
from datetime import datetime, timezone
from json import dumps
import asynctest
from domopyc.iso8601_json import Iso8601DateEncoder
from domopyc.subscribers import toolbox
from domopyc.subscribers.toolbox import AverageMemoryMessageHandler


class AverageMessageHandlerForTest(AverageMemoryMessageHandler):
    def __init__(self, keys, average_period_minutes=0):
        super().__init__(keys, average_period_minutes)
        self.queue = Queue()

    @asyncio.coroutine
    def save(self, average_message):
        yield from self.queue.put(average_message)


class AverageMessageHandlerTest(asynctest.TestCase):
    def setUp(self):
        toolbox.now = lambda: datetime(2012, 12, 13, 14, 2, 0, tzinfo=timezone.utc)
        self.message_handler = AverageMessageHandlerForTest(['watt', 'temperature'], average_period_minutes=10)

    @asyncio.coroutine
    def test_next_plain(self):
        _14h04 = datetime(2012, 12, 13, 14, 4, 0)
        self.assertEquals(datetime(2012, 12, 13, 14, 10), self.message_handler.next_plain(10, _14h04))
        self.assertEquals(datetime(2012, 12, 13, 14, 15), self.message_handler.next_plain(15, _14h04))
        self.assertEquals(datetime(2012, 12, 13, 14, 5), self.message_handler.next_plain(5, _14h04))

    @asyncio.coroutine
    def test_average_two_keys(self):
        toolbox.now = lambda: datetime(2012, 12, 13, 14, 0, 7, tzinfo=timezone.utc)
        yield from self.message_handler.handle({'date': toolbox.now(), 'watt': 100, 'temperature': 20.0})
        self.assertEquals(0, self.message_handler.queue.qsize())

        toolbox.now = lambda: datetime(2012, 12, 13, 14, 3, 0, tzinfo=timezone.utc)
        yield from self.message_handler.handle({'date': toolbox.now(), 'watt': 200, 'temperature': 30.0})
        self.assertEquals(0, self.message_handler.queue.qsize())

        toolbox.now = lambda: datetime(2012, 12, 13, 14, 10, 0, 1, tzinfo=timezone.utc)
        yield from self.message_handler.handle({'date': toolbox.now(), 'watt': 900, 'temperature': 10.0})

        event_average = yield from asyncio.wait_for(self.message_handler.queue.get(), 1)
        self.assertEqual({'date': toolbox.now(), 'watt': 400.0, 'temperature': 20.0, 'nb_data': 3, 'minutes': 10}, event_average)

    @asyncio.coroutine
    def test_average_one_key(self):
        toolbox.now = lambda: datetime(2015, 8, 21, 11, 52, 0, tzinfo=timezone.utc)
        self.message_handler = AverageMessageHandlerForTest(['temperature'], average_period_minutes=10)

        toolbox.now = lambda: datetime(2015, 8, 21, 11, 52, 4, tzinfo=timezone.utc)
        yield from self.message_handler.handle({'packet_length': 10, 'packet_type': 82, 'humidity_status': 0, 'temperature': 23.0, 'sub_type': 1, 'battery_signal_level': 80, 'sequence_number': 40, 'humidity': 0, 'id': '0xBB02', 'packet_type_name': 'Temperature and humidity sensors', 'signal_strength': 80, 'date': toolbox.now(), 'sub_type_name': 'THGN122/123, THGN132, THGR122/228/238/268'})
        toolbox.now = lambda: datetime(2015, 8, 21, 11, 55, 6, tzinfo=timezone.utc)
        yield from self.message_handler.handle({'packet_length': 10, 'packet_type': 82, 'humidity_status': 0, 'temperature': 24.0, 'sub_type': 1, 'battery_signal_level': 80, 'sequence_number': 41, 'humidity': 0, 'id': '0xBB02', 'packet_type_name': 'Temperature and humidity sensors', 'signal_strength': 80, 'date': toolbox.now(), 'sub_type_name': 'THGN122/123, THGN132, THGR122/228/238/268'})
        toolbox.now = lambda: datetime(2015, 8, 21, 12, 00, 8, tzinfo=timezone.utc)
        yield from self.message_handler.handle({'packet_length': 10, 'packet_type': 82, 'humidity_status': 0, 'temperature': 25.0, 'sub_type': 1, 'battery_signal_level': 64, 'sequence_number': 42, 'humidity': 0, 'id': '0xBB02', 'packet_type_name': 'Temperature and humidity sensors', 'signal_strength': 64, 'date': toolbox.now(), 'sub_type_name': 'THGN122/123, THGN132, THGR122/228/238/268'})

        event_average = yield from asyncio.wait_for(self.message_handler.queue.get(), 1)
        self.assertEqual({'date': toolbox.now(), 'temperature': 24.0, 'nb_data': 3, 'minutes': 10}, event_average)