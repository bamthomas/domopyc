from asyncio import Queue
import asyncio
from json import dumps, loads
import unittest
from datetime import datetime, timezone, timedelta
from daq import rfxcom_emiter_receiver
from daq.current_cost_sensor import CURRENT_COST_KEY

from iso8601_json import Iso8601DateEncoder, with_iso8601_date
from subscribers import redis_toolbox
from subscribers.redis_toolbox import AsyncRedisSubscriber, AverageMemoryMessageHandler, RedisAverageMessageHandler, RedisTimeCappedSubscriber
from test_utils.ut_async import async_coro, TestMessageHandler, TestExceptionMessageHandler
from test_utils.ut_redis import WithRedis


class RedisSubscribeLoopTest(WithRedis):
    @async_coro
    def setUp(self):
        yield from super().setUp()

    @async_coro
    def test_subscribe_loop(self):
        message_handler = TestMessageHandler()
        AsyncRedisSubscriber(self.connection, message_handler, 'key').start(1)
        expected = {'date': datetime.now(timezone.utc), 'watt': '123'}

        yield from self.connection.publish('key', dumps(expected, cls=Iso8601DateEncoder))

        event = yield from asyncio.wait_for(message_handler.queue.get(), 2)
        self.assertDictEqual(event, expected)

    @async_coro
    def test_should_not_leave_main_loop_when_an_exception_occurs_in_main_loop(self):
        handler = TestExceptionMessageHandler()
        exception_subscriber = AsyncRedisSubscriber(self.connection, handler, 'key')
        exception_subscriber.start(2)
        expected = {'date': datetime.now(timezone.utc), 'watt': '123'}

        yield from self.connection.publish('key', dumps(expected, cls=Iso8601DateEncoder))
        yield from self.connection.publish('key', dumps(expected, cls=Iso8601DateEncoder))
        yield from asyncio.wait_for(exception_subscriber.message_loop_task, timeout=1)

        self.assertEqual(handler.queue.qsize(), 2)


class RedisAverageMessageHandlerTest(WithRedis):
    @async_coro
    def setUp(self):
        yield from super().setUp()
        redis_toolbox.now = lambda: datetime(2012, 12, 13, 14, 2, 0, tzinfo=timezone.utc)
        self.message_handler = RedisAverageMessageHandler(self.connection, ['watt', 'temperature'])

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

        self.message_handler.handle(dumps({'date': (redis_toolbox.now().isoformat()), 'watt': 305, 'temperature': 21.4}))

        ttl = yield from self.connection.ttl('current_cost_2012-12-13')
        self.assertEqual(-1, int(ttl))


class TestRedisTimeCappedSubscriber(WithRedis):

    @async_coro
    def setUp(self):
        yield from super().setUp()

    @async_coro
    def test_average_no_data(self):
        pool_temp = RedisTimeCappedSubscriber(self.connection, 'pool_temperature').start()

        value = yield from pool_temp.get_average()
        self.assertEqual(0.0, value)

    @async_coro
    def test_average_one_data(self):
        pool_temp = RedisTimeCappedSubscriber(self.connection, 'pool_temperature').start(1)

        yield from self.connection.publish(rfxcom_emiter_receiver.RFXCOM_KEY, dumps({'date': datetime.now().isoformat(), 'temperature': 3.0}))
        yield from asyncio.wait_for(pool_temp.message_loop_task, timeout=1)

        value = yield from pool_temp.get_average()
        self.assertEqual(3.0, value)

    @async_coro
    def test_average_two_data(self):
        pool_temp = RedisTimeCappedSubscriber(self.connection, 'pool_temperature').start(2)

        yield from self.connection.publish(rfxcom_emiter_receiver.RFXCOM_KEY, dumps({'date': datetime(2015, 2, 14, 15, 0, 0).isoformat(), 'temperature': 3.0}))
        yield from self.connection.publish(rfxcom_emiter_receiver.RFXCOM_KEY, dumps({'date': datetime(2015, 2, 14, 15, 0, 1).isoformat(), 'temperature': 4.0}))
        yield from asyncio.wait_for(pool_temp.message_loop_task, timeout=1)

        value = yield from pool_temp.get_average()
        self.assertEqual(3.5, value)

    @async_coro
    def test_average_two_equal_data(self):
        pool_temp = RedisTimeCappedSubscriber(self.connection, 'pool_temperature').start(2)

        yield from self.connection.publish(rfxcom_emiter_receiver.RFXCOM_KEY, dumps({'date': datetime(2015, 2, 14, 15, 0, 0).isoformat(), 'temperature': 3.0}))
        yield from self.connection.publish(rfxcom_emiter_receiver.RFXCOM_KEY, dumps({'date': datetime(2015, 2, 14, 15, 0, 1).isoformat(), 'temperature': 3.0}))
        yield from asyncio.wait_for(pool_temp.message_loop_task, timeout=1)

        value = yield from pool_temp.get_average()
        self.assertEqual(2, (yield from self.connection.zcard('pool_temperature')))
        self.assertEqual(3, value)

    @async_coro
    def test_capped_collection(self):
        pool_temp = RedisTimeCappedSubscriber(self.connection, 'pool_temperature', 10).start(3)
        redis_toolbox.now = lambda: datetime(2015, 2, 14, 15, 0, 10, tzinfo=timezone.utc)

        yield from self.connection.publish(rfxcom_emiter_receiver.RFXCOM_KEY, dumps({'date': datetime(2015, 2, 14, 15, 0, 0).isoformat(), 'temperature': 2.0}))
        yield from self.connection.publish(rfxcom_emiter_receiver.RFXCOM_KEY, dumps({'date': datetime(2015, 2, 14, 15, 0, 1).isoformat(), 'temperature': 4.0}))
        yield from self.connection.publish(rfxcom_emiter_receiver.RFXCOM_KEY, dumps({'date': datetime(2015, 2, 14, 15, 0, 2).isoformat(), 'temperature': 6.0}))
        yield from asyncio.wait_for(pool_temp.message_loop_task, timeout=1)

        value = yield from pool_temp.get_average()
        self.assertEqual(5.0, value)

    @async_coro
    def test_get_live_data(self):
        live_data_handler = RedisTimeCappedSubscriber(self.connection, 'live_data', 3600, pubsub_key=CURRENT_COST_KEY, indicator_key='watt').start()
        yield from live_data_handler.handle({'date': redis_toolbox.now(), 'watt': 100})

        data = yield from live_data_handler.get_data()

        self.assertEqual(1, len(data))
        self.assertEqual({'date': redis_toolbox.now(), 'watt': 100}, data[0])

    @async_coro
    def test_get_live_data_keeps_one_hour_data(self):
        test_now = datetime.now()
        live_data_handler = RedisTimeCappedSubscriber(self.connection, 'live_data', 3600, pubsub_key=CURRENT_COST_KEY, indicator_key='watt')

        redis_toolbox.now = lambda: test_now
        yield from live_data_handler.handle({'date': redis_toolbox.now(), 'watt': 100})
        redis_toolbox.now = lambda: test_now + timedelta(seconds=1800)
        yield from live_data_handler.handle({'date': redis_toolbox.now(), 'watt': 200})
        redis_toolbox.now = lambda: test_now + timedelta(seconds=3660)
        yield from live_data_handler.handle({'date': redis_toolbox.now(), 'watt': 300})

        self.assertEqual(2, len((yield from live_data_handler.get_data(since_seconds=3600))))
        self.assertEqual(1, len((yield from live_data_handler.get_data(since_seconds=1800))))

