from asyncio import Queue
import asyncio
from json import dumps, loads
from socket import socketpair
import unittest
from datetime import datetime, timezone

from current_cost.sensor import current_cost_async
from current_cost.sensor.current_cost_async import AsyncRedisSubscriber, AsyncCurrentCostReader, AverageMessageHandler, \
    RedisAverageMessageHandler
import functools
from iso8601_json import Iso8601DateEncoder, with_iso8601_date
from rfxcom_toolbox.rfxcom_redis import create_redis_pool


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
    @asyncio.coroutine
    def setUp(self):
        self.connection = yield from create_redis_pool()
        yield from self.connection.flushdb()

    @asyncio.coroutine
    def tearDown(self):
        self.connection.close()


class TestMessageHandler(object):
    queue = Queue()
    @asyncio.coroutine
    def handle(self, message):
        yield from self.queue.put(message)


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


class DummySerial():
    def __init__(self):
        self.rsock, self.wsock = socketpair()
        self.fd = self.rsock

    def read(self, bytes=1):
        return self.rsock.recv(bytes)

    def write(self, data):
        self.wsock.send(data)

    def close(self):
        self.wsock.close()
        self.rsock.close()


class CurrentCostReaderTest(unittest.TestCase):
    def setUp(self):
        current_cost_async.now = lambda: datetime(2012, 12, 13, 14, 15, 16)
        self.serial_device = DummySerial()
        self.handler = TestMessageHandler()
        self.current_cost_reader = AsyncCurrentCostReader(self.serial_device, self.handler)

    def tearDown(self):
        self.current_cost_reader.remove_reader()
        self.serial_device.close()

    @async_coro
    def test_read_sensor(self):
        self.serial_device.write(
            '<msg><src>CC128-v1.29</src><dsb>00302</dsb><time>02:57:28</time><tmpr>21.4</tmpr><sensor>1</sensor><id>00126</id><type>1</type><ch1><watts>00305</watts></ch1></msg>\n'.encode())

        event = yield from asyncio.wait_for(self.handler.queue.get(), 1)
        self.assertDictEqual(event, {'date': (current_cost_async.now().isoformat()), 'watt': 305, 'temperature': 21.4})

    @async_coro
    def test_read_sensor_xml_error_dont_break_loop(self):
        self.serial_device.write('<malformed XML>\n'.encode())
        self.serial_device.write(
            '<msg><src>CC128-v1.29</src><dsb>00302</dsb><time>02:57:28</time><tmpr>21.4</tmpr><sensor>1</sensor><id>00126</id><type>1</type><ch1><watts>00305</watts></ch1></msg>\n'.encode())

        event = yield from asyncio.wait_for(self.handler.queue.get(), 1)
        self.assertDictEqual(event, {'date': (current_cost_async.now().isoformat()), 'watt': 305, 'temperature': 21.4})


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
        self.assertEquals(datetime(2012, 12, 13, 14, 5 ), self.message_handler.next_plain(5 , _14h04))

    @async_coro
    def test_average(self):
        current_cost_async.now = lambda: datetime(2012, 12, 13, 14, 0, 7, tzinfo=timezone.utc)
        self.message_handler.handle(dumps({'date': current_cost_async.now(), 'watt': 100, 'temperature':20.0}, cls=Iso8601DateEncoder))
        self.assertEquals(0, self.message_handler.queue.qsize())

        current_cost_async.now = lambda: datetime(2012, 12, 13, 14, 3, 0, tzinfo=timezone.utc)
        self.message_handler.handle(dumps({'date': current_cost_async.now(), 'watt': 200, 'temperature':30.0}, cls=Iso8601DateEncoder))
        self.assertEquals(0, self.message_handler.queue.qsize())

        current_cost_async.now = lambda: datetime(2012, 12, 13, 14, 10, 0, 1, tzinfo=timezone.utc)
        self.message_handler.handle(dumps({'date': current_cost_async.now(), 'watt': 900, 'temperature':10.0}, cls=Iso8601DateEncoder))

        event_average = yield from asyncio.wait_for(self.message_handler.queue.get(), 1)
        self.assertEqual({'date': current_cost_async.now(), 'watt': 400.0, 'temperature':20.0, 'nb_data': 3, 'minutes': 10}, event_average)


class RedisAverageMessageHandlerTest(WithRedis):
    @async_coro
    def setUp(self):
        yield from super().setUp()
        current_cost_async.now = lambda: datetime(2012, 12, 13, 14, 2, 0, tzinfo=timezone.utc)
        self.message_handler = RedisAverageMessageHandler(self.connection)

    @async_coro
    def test_save_event_redis_function(self):
        now = datetime(2012, 12, 13, 14, 0, 7, tzinfo=timezone.utc)

        yield from self.message_handler.handle(dumps({'date': now, 'watt': 305.0, 'temperature':21.4}, cls=Iso8601DateEncoder))

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

        self.message_handler.handle(dumps({'date': (current_cost_async.now().isoformat()), 'watt': 305, 'temperature':21.4}))

        ttl = yield from self.connection.ttl('current_cost_2012-12-13')
        self.assertEqual(-1, int(ttl))