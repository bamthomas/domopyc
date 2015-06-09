from asyncio import Queue
import asyncio
from datetime import datetime, timezone
from json import dumps
import unittest
from iso8601_json import Iso8601DateEncoder
from subscribers import toolbox
from subscribers.toolbox import AverageMemoryMessageHandler
from test_utils.ut_async import async_coro


class AverageMessageHandlerForTest(AverageMemoryMessageHandler):
    def __init__(self, keys, average_period_minutes=0):
        super().__init__(keys, average_period_minutes)
        self.queue = Queue()

    @asyncio.coroutine
    def save(self, average_message):
        yield from self.queue.put(average_message)


class AverageMessageHandlerTest(unittest.TestCase):
    def setUp(self):
        toolbox.now = lambda: datetime(2012, 12, 13, 14, 2, 0, tzinfo=timezone.utc)
        self.message_handler = AverageMessageHandlerForTest(['watt', 'temperature'], average_period_minutes=10)

    @async_coro
    def test_next_plain(self):
        _14h04 = datetime(2012, 12, 13, 14, 4, 0)
        self.assertEquals(datetime(2012, 12, 13, 14, 10), self.message_handler.next_plain(10, _14h04))
        self.assertEquals(datetime(2012, 12, 13, 14, 15), self.message_handler.next_plain(15, _14h04))
        self.assertEquals(datetime(2012, 12, 13, 14, 5), self.message_handler.next_plain(5, _14h04))

    @async_coro
    def test_average(self):
        toolbox.now = lambda: datetime(2012, 12, 13, 14, 0, 7, tzinfo=timezone.utc)
        self.message_handler.handle(dumps({'date': toolbox.now(), 'watt': 100, 'temperature': 20.0}, cls=Iso8601DateEncoder))
        self.assertEquals(0, self.message_handler.queue.qsize())

        toolbox.now = lambda: datetime(2012, 12, 13, 14, 3, 0, tzinfo=timezone.utc)
        self.message_handler.handle(dumps({'date': toolbox.now(), 'watt': 200, 'temperature': 30.0}, cls=Iso8601DateEncoder))
        self.assertEquals(0, self.message_handler.queue.qsize())

        toolbox.now = lambda: datetime(2012, 12, 13, 14, 10, 0, 1, tzinfo=timezone.utc)
        self.message_handler.handle(dumps({'date': toolbox.now(), 'watt': 900, 'temperature': 10.0}, cls=Iso8601DateEncoder))

        event_average = yield from asyncio.wait_for(self.message_handler.queue.get(), 1)
        self.assertEqual({'date': toolbox.now(), 'watt': 400.0, 'temperature': 20.0, 'nb_data': 3, 'minutes': 10}, event_average)
