from asyncio import Queue
import asyncio
from json import dumps, loads
import unittest
from datetime import datetime, timezone

from current_cost.sensor import current_cost_async
from current_cost.sensor.current_cost_async import AsyncRedisSubscriber, AverageMessageHandler, \
    RedisAverageMessageHandler
from iso8601_json import Iso8601DateEncoder, with_iso8601_date
from test_utils.ut_async import async_coro, TestMessageHandler
from test_utils.ut_redis import WithRedis


class RedisSubscribeLoopTest(WithRedis):
    @async_coro
    def setUp(self):
        yield from super().setUp()
        self.message_handler = TestMessageHandler()
        self.subscriber = AsyncRedisSubscriber(self.connection, self.message_handler, 'key')

    @async_coro
    def test_subscribe_loop(self):
        self.subscriber.start(1)
        expected = {'date': datetime.now(timezone.utc), 'watt': '123'}

        yield from self.connection.publish('key', dumps(expected, cls=Iso8601DateEncoder))

        event = yield from asyncio.wait_for(self.message_handler.queue.get(), 2)
        self.assertDictEqual(event, expected)


class AverageMessageHandlerForTest(AverageMessageHandler):
    def __init__(self, average_period_minutes=0):
        super().__init__(average_period_minutes)
        self.queue = Queue()

    @asyncio.coroutine
    def save(self, average_message):
        yield from self.queue.put(average_message)


class AverageMessageHandlerTest(unittest.TestCase):
    def setUp(self):
        current_cost_async.now = lambda: datetime(2012, 12, 13, 14, 2, 0, tzinfo=timezone.utc)
        self.message_handler = AverageMessageHandlerForTest(average_period_minutes=10)

    @async_coro
    def test_next_plain(self):
        _14h04 = datetime(2012, 12, 13, 14, 4, 0)
        self.assertEquals(datetime(2012, 12, 13, 14, 10), self.message_handler.next_plain(10, _14h04))
        self.assertEquals(datetime(2012, 12, 13, 14, 15), self.message_handler.next_plain(15, _14h04))
        self.assertEquals(datetime(2012, 12, 13, 14, 5), self.message_handler.next_plain(5, _14h04))

    @async_coro
    def test_average(self):
        current_cost_async.now = lambda: datetime(2012, 12, 13, 14, 0, 7, tzinfo=timezone.utc)
        self.message_handler.handle(dumps({'date': current_cost_async.now(), 'watt': 100, 'temperature': 20.0}, cls=Iso8601DateEncoder))
        self.assertEquals(0, self.message_handler.queue.qsize())

        current_cost_async.now = lambda: datetime(2012, 12, 13, 14, 3, 0, tzinfo=timezone.utc)
        self.message_handler.handle(dumps({'date': current_cost_async.now(), 'watt': 200, 'temperature': 30.0}, cls=Iso8601DateEncoder))
        self.assertEquals(0, self.message_handler.queue.qsize())

        current_cost_async.now = lambda: datetime(2012, 12, 13, 14, 10, 0, 1, tzinfo=timezone.utc)
        self.message_handler.handle(dumps({'date': current_cost_async.now(), 'watt': 900, 'temperature': 10.0}, cls=Iso8601DateEncoder))

        event_average = yield from asyncio.wait_for(self.message_handler.queue.get(), 1)
        self.assertEqual({'date': current_cost_async.now(), 'watt': 400.0, 'temperature': 20.0, 'nb_data': 3, 'minutes': 10}, event_average)


class RedisAverageMessageHandlerTest(WithRedis):
    @async_coro
    def setUp(self):
        yield from super().setUp()
        current_cost_async.now = lambda: datetime(2012, 12, 13, 14, 2, 0, tzinfo=timezone.utc)
        self.message_handler = RedisAverageMessageHandler(self.connection)

    @async_coro
    def test_save_event_redis_function(self):
        now = datetime(2012, 12, 13, 14, 0, 7, tzinfo=timezone.utc)

        yield from self.message_handler.handle(dumps({'date': now, 'watt': 305.0, 'temperature': 21.4}, cls=Iso8601DateEncoder))

        ttl = yield from self.connection.ttl('current_cost_2012-12-13')
        self.assertTrue(int(ttl) > 0)
        self.assertTrue(int(ttl) <= 5 * 24 * 3600)

        event = yield from self.connection.lpop('current_cost_2012-12-13')
        self.assertDictEqual(
            {'date': now, 'watt': 305, 'temperature': 21.4, 'nb_data': 1, 'minutes': 0},
            loads(event, object_hook=with_iso8601_date))

    @async_coro
    def test_save_event_redis_function_no_ttl_if_not_first_element(self):
        yield from self.connection.lpush('current_cost_2012-12-13', ['not used'])

        self.message_handler.handle(dumps({'date': (current_cost_async.now().isoformat()), 'watt': 305, 'temperature': 21.4}))

        ttl = yield from self.connection.ttl('current_cost_2012-12-13')
        self.assertEqual(-1, int(ttl))